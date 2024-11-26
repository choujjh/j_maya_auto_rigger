from system.base_components import Component
import utils.enum as utils_enum
import components.control_components as control_components
import components.matrix_component as matrix_components
import components.components as components
import system.data as data
import utils.node_wrapper as nw
import utils.utils as utils
import utils.enum as utils_enum
import maya.cmds as cmds

class MotionComponent(Component):
    component_type = utils_enum.ComponentTypes.motion
    has_inst_name_attr = True

class FKComponent(MotionComponent):
    root_transform_name = "fk_cntrl_grp"
    
    # @property
    # def instance_namespace(self):
    #     return self.class_name

    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = super(FKComponent, self)._init_node_data(instance_name, **attr_kwargs)

        node_data_dict = self._add_hier_data(node_data_dict)

        node_data_dict = self._add_transform_data(node_data_dict)

        return node_data_dict

    def _pre_build_component(self):
        node_data_dict = super(FKComponent, self)._pre_build_component()
        
        io_node = self.io_node

        io_node_hier_attr = io_node[data.HierDataAttrNames.hier.value]
        hier_attr_names = data.HierAttrNames

        parent = None

        self.gen_input_local_matrices()

        for index in range(len(io_node_hier_attr)):
            curr_local_attr = io_node_hier_attr[index][hier_attr_names.input_local_matrix.value]

            if index == 0:
                connections = curr_local_attr.get_as_dest_connection_list()
                if len(connections) > 0:
                    ~curr_local_attr
                parent_space_offset_component = self.insert_component(
                    matrix_components.OffsetMatrixComponent, 
                    space_matrix=io_node[data.HierDataAttrNames.hier_parent_init.value], 
                    target_matrix=io_node_hier_attr[index][hier_attr_names.input_world_matrix.value],
                    component_name="hier0_local"
                    )
                parent_space_mult = nw.Node.create_node("multMatrix", "parentSpaceMult")

                parent_space_offset_component.io_node["offsetMatrix"] >> parent_space_mult["matrixIn"][0]
                io_node[data.HierDataAttrNames.hier_parent.value] >> parent_space_mult["matrixIn"][1]

                parent_space_mult["matrixSum"] >> curr_local_attr

            kwarg_data = utils.convert_kwarg_data(io_node_hier_attr[index][hier_attr_names.hier_kwarg_data.value])
            control=control_components.SphereControl
            input_shape = None
            if "control_class" in kwarg_data.keys():
                control=kwarg_data["control_class"]
                kwarg_data.pop("control_class")
            if "shape_node" in kwarg_data.keys():
                input_shape = nw.derive_node(kwarg_data["shape_node"])
                kwarg_data.pop("shape_node")
                container = None

                if input_shape.node_type == "transform":
                    control=control_components.ControlComponent
                    if input_shape.get_container() is not None:
                        container = input_shape.get_container()
                if input_shape.node_type == "container":
                    container = input_shape
                
                control = utils.string_to_class(container["componentClass"].value)
                input_shape = control(container).transform_node

            control_inst = self.promote_to_control(attr=curr_local_attr, parent=parent, control=control, input_shape=input_shape, **kwarg_data)
            parent = control_inst.transform_node

            control_inst.io_node["worldMatrix"] >> io_node_hier_attr[index][hier_attr_names.output_world_matrix.value]
            control_inst.io_node["localMatrix"] >> io_node_hier_attr[index][hier_attr_names.output_local_matrix.value]

        node_data_dict.add_node_data(data.NodeData(node=parent_space_mult))

        return node_data_dict

class IKComponent(MotionComponent):
    # root_transform_name = "ik_cntrl_grp"

    # @property
    # def instance_namespace(self):
    #     return self.class_name

    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = super()._init_node_data(instance_name, **attr_kwargs)

        node_data_dict[self._io_name.node_name].add_attr_data(
            # matricies
            data.AttrData("rootMatrix", publish_name=True, type="matrix", parent="input"),
            data.AttrData("goalMatrix", publish_name=True, type="matrix", parent="input"),
            data.AttrData("poleMatrix", publish_name=True, type="matrix", parent="input"),

            # ik tune attributes
            data.AttrData("stretchy", value=True, publish_name=True, type="bool", parent="install"),
            # node_data_dict[self._io_name.node_name].add_attr_data(data.AttrData("soft", value=False, publish_name=True, type="bool", parent="install"})),
            data.AttrData("preserveMinLength", value=True, publish_name=True, type="bool", parent="install"),
            data.AttrData("orientEndMatrix", value=True, publish_name=True, type="bool", parent="install"),

            # axes attributes
            data.AttrData("primaryAxis", value=0, publish_name=True, type="enum", enum_name=utils_enum.AxisEnums.maya_enum_str(), parent="install"),
            data.AttrData("secondaryAxis", value=1, publish_name=True, type="enum", enum_name=utils_enum.AxisEnums.maya_enum_str(), parent="install"),
            data.AttrData("primaryAxisVector", publish_name=True, type="double3", parent="install"),
            data.AttrData("primaryAxisVectorX", type="double", parent="primaryAxisVector"),
            data.AttrData("primaryAxisVectorY", type="double", parent="primaryAxisVector"),
            data.AttrData("primaryAxisVectorZ", type="double", parent="primaryAxisVector"),
            data.AttrData("secondaryAxisVector", publish_name=True, type="double3", parent="install"),
            data.AttrData("secondaryAxisVectorX", type="double", parent="secondaryAxisVector"),
            data.AttrData("secondaryAxisVectorY", type="double", parent="secondaryAxisVector"),
            data.AttrData("secondaryAxisVectorZ", type="double", parent="secondaryAxisVector"),
        )

        node_data_dict = self._add_hier_data(node_data_dict)

        return node_data_dict
    
    def _pre_build_component(self):
        node_data_dict = super()._pre_build_component()

        io_node = self.io_node

        io_node_hier_attr = io_node[data.HierDataAttrNames.hier.value]
        hier_attr_names = data.HierAttrNames


        # setting up vectors
        primaryVectorChoice = components.AxesVectors.get_instance(self).make_choice_node("primaryVectorChoice")
        io_node["primaryAxis"] >> primaryVectorChoice["selector"]
        primaryVectorChoice["output"] >> io_node["primaryAxisVector"]
        secondaryVectorChoice = components.AxesVectors.get_instance(self).make_choice_node("secondaryVectorChoice")
        io_node["secondaryAxis"] >> secondaryVectorChoice["selector"]
        secondaryVectorChoice["output"] >> io_node["secondaryAxisVector"]

        node_data_dict.add_node_data(data.NodeData(node=primaryVectorChoice))
        node_data_dict.add_node_data(data.NodeData(node=secondaryVectorChoice))


        
        for i in range(len(io_node_hier_attr)):
            name = io_node_hier_attr[i][hier_attr_names.hier_name.value].value
            if name is None or name == "":
                io_node_hier_attr[i][hier_attr_names.hier_name.value] = "hier{}".format(i)

        indicies_len = len(io_node_hier_attr)

        indicies = range(indicies_len)

        if indicies_len == 2 or indicies_len == 3:

            # create aim
            parent_matrix = nw.Node.create_node("aimMatrix", "parent_matrix")
            io_node["rootMatrix"] >> parent_matrix["inputMatrix"]
            io_node["goalMatrix"] >> parent_matrix["primaryTargetMatrix"]
            io_node["poleMatrix"] >> parent_matrix["secondaryTargetMatrix"]
            io_node["primaryAxisVector"] >> parent_matrix["primaryInputAxis"]
            io_node["secondaryAxisVector"] >> parent_matrix["secondaryInputAxis"]
            parent_matrix["secondaryMode"] = 1

            node_data_dict.add_node_data(data.NodeData(node=parent_matrix))

            # end orientation
            end_orientation = nw.Node.create_node("blendMatrix")
            io_node["goalMatrix"] >> end_orientation["target[0].targetMatrix"]
            end_orientation["target[0].translateWeight"] = 0
            io_node["orientEndMatrix"] >> end_orientation["target[0].weight"]

            node_data_dict.add_node_data(data.NodeData(node=end_orientation))

            # creating initial position world points
            hier_init_pnt_list = []
            hier_loc_matrix_list = []
            parent_matrix_attr = parent_matrix["outputMatrix"]
            for index in indicies:
                name = io_node_hier_attr[index][hier_attr_names.hier_name.value].value

                # point matrix
                hier_init_point = nw.Node.create_node("pointMatrixMult", "{}_initPntMatrixMult".format(name))
                io_node_hier_attr[index][hier_attr_names.input_world_matrix.value] >> hier_init_point["inMatrix"]
                hier_init_pnt_list.append(hier_init_point)

                # local matrix
                local_matrix = nw.Node.create_node("composeMatrix", "{}_localMatrixComp".format(name))
                hier_loc_matrix_list.append(local_matrix)

                # world matrix
                world_matrix = nw.Node.create_node("multMatrix", "{}_worldMatrixMult".format(name))
                local_matrix["outputMatrix"] >> world_matrix["matrixIn[0]"]
                parent_matrix_attr >> world_matrix["matrixIn[1]"]

                parent_matrix_attr = world_matrix["matrixSum"]

                if index == indicies[-1]:
                    parent_matrix_attr >> end_orientation["inputMatrix"]
                    parent_matrix_attr = end_orientation["outputMatrix"]

                # connect everything to the output side
                parent_matrix_attr >> io_node_hier_attr[index][hier_attr_names.output_world_matrix.value]
                if index > 0 and index != indicies[-1]:
                    local_matrix["outputMatrix"] >> io_node_hier_attr[index][hier_attr_names.output_local_matrix.value]
                elif index == indicies[-1]:
                    # get the world matrix attrs
                    if indicies_len > 1:
                        parent_world_matrix_attr = io_node_hier_attr[indicies[-2]][hier_attr_names.output_world_matrix.value]
                        parent_world_matrix_attr = parent_world_matrix_attr.get_connection_list(asSource=False, asDestination=True)[0]

                        offset_matrix_inst = self.insert_component(matrix_components.OffsetMatrixComponent, component_name="endLocal", space_matrix=parent_world_matrix_attr, target_matrix=parent_matrix_attr)
                        offset_matrix_inst.io_node["offsetMatrix"] >> io_node_hier_attr[index][hier_attr_names.output_local_matrix.value]

                    else:
                        
                        parent_matrix_attr >> io_node_hier_attr[index][hier_attr_names.output_local_matrix.value]
                    
                else:
                    parent_matrix_attr >> io_node_hier_attr[index][hier_attr_names.output_local_matrix.value]

                # adding to container
                node_data_dict.add_node_data(data.NodeData(node=hier_init_point))
                node_data_dict.add_node_data(data.NodeData(node=local_matrix))
                node_data_dict.add_node_data(data.NodeData(node=world_matrix))



            # goal and root position world points
            root_world_point = nw.Node.create_node("pointMatrixMult", "rootWorldPnt")
            goal_world_point = nw.Node.create_node("pointMatrixMult", "goalWorldPnt")

            io_node["rootMatrix"] >> root_world_point["inMatrix"]
            io_node["goalMatrix"] >> goal_world_point["inMatrix"]

            node_data_dict.add_node_data(data.NodeData(node=root_world_point))
            node_data_dict.add_node_data(data.NodeData(node=goal_world_point))

            # rotate axis vector
            rotate_axis_vector = nw.Node.create_node("vectorProduct", "rotateAxisVector")
            io_node["primaryAxisVector"] >> rotate_axis_vector["input1"]
            io_node["secondaryAxisVector"] >> rotate_axis_vector["input2"]
            rotate_axis_vector["operation"] = 2

            node_data_dict.add_node_data(data.NodeData(node=rotate_axis_vector))

            

            # expression string
            expression_str = []

            if indicies_len == 3:
                expression_str.extend([
                    "float $len1 = mag(<<{0}.outputX - {1}.outputX, {0}.outputY - {1}.outputY, {0}.outputZ - {1}.outputZ>>); \n".format(hier_init_pnt_list[1], hier_init_pnt_list[0]),
                    "float $len2 = mag(<<{0}.outputX - {1}.outputX, {0}.outputY - {1}.outputY, {0}.outputZ - {1}.outputZ>>); \n".format(hier_init_pnt_list[2], hier_init_pnt_list[1]),
                    "float $totalLen = mag(<<{0}.outputX - {1}.outputX, {0}.outputY - {1}.outputY, {0}.outputZ - {1}.outputZ>>); \n\n".format(goal_world_point, root_world_point),

                    "float $ratio = $len1 / ($len1 + $len2);\n"
                    "float $resultLen1 = $ratio * $totalLen;\n"
                    "float $resultLen2 = (1.0 - $ratio) * $totalLen;\n"
                    "float $resultRot1 = 0.0;\n"
                    "float $resultRot2 = 0.0;\n\n"
                    "//combined length is shorter than total length\n"
                    "if (($len1 + $len2) < $totalLen){\n",
                    "\tif ({}.stretchy == 0){{\n".format(io_node),
                    "\t\t$resultLen1 = $len1;\n"
                    "\t\t$resultLen2 = $len2;\n"
                    "\t}\n"
                    "}\n"

                    "else {\n",
                    "\tif ({}.preserveMinLength == 1){{\n".format(io_node),
                    "\t\t$resultLen1 = $len1;\n"
                    "\t\t$resultLen2 = $len2;\n"
                    "\t\tfloat $squaredLen1 = $len1 * $len1;\n"
                    "\t\tfloat $squaredLen2 = $len2 * $len2;\n"
                    "\t\tfloat $squaredTotalLen = $totalLen * $totalLen;\n"
                    "\t\t$resultRot1 = acosd(($squaredLen1 + $squaredTotalLen - $squaredLen2) / (2 * $len1 * $totalLen));\n"
                    "\t\t$resultRot2 = acosd(($squaredLen1 + $squaredLen2 - $squaredTotalLen) / (2 * $len1 * $len2));\n"
                    "\t\t$resultRot2 = -180 + $resultRot2;\n"
                    "\t}\n"
                    "}\n"
                ])
            else:
                expression_str.extend([
                    "float $len1 = mag(<<{0}.outputX - {1}.outputX, {0}.outputY - {1}.outputY, {0}.outputZ - {1}.outputZ>>); \n".format(hier_init_pnt_list[1], hier_init_pnt_list[0]),
                    "float $totalLen = mag(<<{0}.outputX - {1}.outputX, {0}.outputY - {1}.outputY, {0}.outputZ - {1}.outputZ>>); \n\n".format(goal_world_point, root_world_point),

                    "float $resultLen1 = $totalLen;\n"
                    "float $resultRot1 = 0.0;\n\n"
                    "//combined length is shorter than total length\n"
                    "if ($len1 < $totalLen){\n",
                    "\tif ({}.stretchy == 0){{\n".format(io_node),
                    "\t\t$resultLen1 = $len1;\n"
                    "\t}\n"
                    "}\n"

                    "else {\n",
                    "\tif ({}.preserveMinLength == 1){{\n".format(io_node),
                    "\t\t$resultLen1 = $len1;\n"
                    "\t}\n"
                    "}\n"
                ])

            expression_str.extend([
                "{}.inputRotateX = {}.outputX * $resultRot1;\n".format(hier_loc_matrix_list[0], rotate_axis_vector),
                "{}.inputRotateY = {}.outputY * $resultRot1;\n".format(hier_loc_matrix_list[0], rotate_axis_vector),
                "{}.inputRotateZ = {}.outputZ * $resultRot1;\n".format(hier_loc_matrix_list[0], rotate_axis_vector),

                "{}.inputTranslateX = {}.primaryAxisVectorX * $resultLen1;\n".format(hier_loc_matrix_list[1], io_node),
                "{}.inputTranslateY = {}.primaryAxisVectorY * $resultLen1;\n".format(hier_loc_matrix_list[1], io_node),
                "{}.inputTranslateZ = {}.primaryAxisVectorZ * $resultLen1;\n".format(hier_loc_matrix_list[1], io_node),
            ])
            if indicies_len == 3:
                expression_str.extend([
                    "{}.inputRotateX = {}.outputX * $resultRot2;\n".format(hier_loc_matrix_list[1], rotate_axis_vector),
                    "{}.inputRotateY = {}.outputY * $resultRot2;\n".format(hier_loc_matrix_list[1], rotate_axis_vector),
                    "{}.inputRotateZ = {}.outputZ * $resultRot2;\n".format(hier_loc_matrix_list[1], rotate_axis_vector),

                    "{}.inputTranslateX = {}.primaryAxisVectorX * $resultLen2;\n".format(hier_loc_matrix_list[2], io_node),
                    "{}.inputTranslateY = {}.primaryAxisVectorY * $resultLen2;\n".format(hier_loc_matrix_list[2], io_node),
                    "{}.inputTranslateZ = {}.primaryAxisVectorZ * $resultLen2;\n".format(hier_loc_matrix_list[2], io_node),
                ])

            expression_str = "".join(expression_str)
            expression = nw.Node(cmds.expression(string=expression_str, name="ik_expression"))
            node_data_dict.add_node_data(data.NodeData(node=expression))

        else:
            cmds.warning("IKComponent only supports 2 or 3 hierInputs")

        return node_data_dict