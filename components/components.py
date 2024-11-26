from system.base_components import Component
import system.base_components as base_components
import components.control_components as control_components
import system.data as data
import utils.node_wrapper as nw
import utils.utils as utils
import utils.enum as utils_enum
import maya.cmds as cmds

class ColorManager(Component):

    def get_shader(self, color):
        return utils.get_first_connected_node(self.io_node[color.name], as_source=True)
    
    def get_shader_sg(self, color):
        return utils.get_first_connected_node(self.get_shader(color)["outColor"], as_source=True)

    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = super(ColorManager, self)._init_node_data(instance_name, **attr_kwargs)

        node_data_dict[self._io_name.node_name].add_attr_data(data.AttrData("color", type="compound", parent="install"))
        for color_enum in utils_enum.Colors:
            node_data_dict[self._io_name.node_name].add_attr_data(data.AttrData(color_enum.name, type="message", parent="color"))

        return node_data_dict
    
    def _pre_build_component(self):
        node_data_dict = super(ColorManager, self)._pre_build_component()

        io_node = self.io_node

        for color_enum in utils_enum.Colors:
            index_color = cmds.colorIndex(color_enum.value, q=True)
            shader = nw.Node(cmds.shadingNode("lambert", name=color_enum.name, asShader=True))
            shader["color"] = index_color
            shader_sg = nw.Node(cmds.sets(name="{0}SG".format(shader), renderable=True, noSurfaceShader=True, empty=True))

            shader["outColor"] >> shader_sg["surfaceShader"]

            io_node[color_enum.name] >> shader["color"]

            node_data_dict.add_node_data(node_data=data.NodeData(node=shader), key="{}Shader".format(color_enum.name))
            node_data_dict.add_node_data(node_data=data.NodeData(node=shader_sg), key="{}ShaderSG".format(color_enum.name))

        return node_data_dict

    def apply_color(self, obj, color):
        if color == utils_enum.Colors.none:
            return
        shader = self.get_shader(color)
        shader_sg = self.get_shader_sg(color)

        shapes = cmds.listRelatives(str(obj), shapes=True)

        for shape in shapes:
            shape = nw.Node(shape)
            if shape.node_type in ["nurbsCurve", "locator"]:
                shape["overrideEnabled"] = True
                shape["overrideRGBColors"] = 1
                shape["overrideColorRGB"] = shader["color"]

            else:
                cmds.sets([str(shape)], e=True, forceElement=str(shader_sg))

    @classmethod
    def get_instance(cls, info=None):
        # see if it's found in the character component
        container = info
        if issubclass(type(info), Component):
            container = info.container_node
        while container is not None and not container.has_attr("colorManagerComponent"):
            container = container.get_container()


        if container is not None:
            color_containers = container["colorManagerComponent"].get_as_source_connection_list()
            if len(color_containers) > 0:
                return cls(color_containers[0].node)

        # if no container found
        class_inst = cls()
        component_container_name = "{}:{}".format(class_inst.instance_namespace, "component_container")
        if cmds.objExists(component_container_name):
            return cls(nw.Container(component_container_name))
    
        color_manager_inst = cls()
        color_manager_inst.create_component()

        return color_manager_inst

class AxesVectors(Component):
    
    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = super(AxesVectors, self)._init_node_data(instance_name, **attr_kwargs)

        for axis in utils_enum.AxisEnums:
            parent_name = "{}Vector".format(axis.name)
            axis_vector = axis.value
            axes_data = data.AttrData(parent_name, publish_name=True, type="double3", parent="output")
            axes_x_data = data.AttrData("{}X".format(parent_name), value=axis_vector[0], type="double", parent=parent_name)
            axes_y_data = data.AttrData("{}Y".format(parent_name), value=axis_vector[1], type="double", parent=parent_name)
            axes_z_data = data.AttrData("{}Z".format(parent_name), value=axis_vector[2], type="double", parent=parent_name)

            node_data_dict[self._io_name.node_name].add_attr_data(
                axes_data,
                axes_x_data,
                axes_y_data,
                axes_z_data
            )

        return node_data_dict

    @classmethod
    def get_instance(cls, info=None):
        # see if it's found in the character component
        container = info
        if issubclass(type(info), Component):
            container = info.container_node
        while container is not None and not container.has_attr("axisVectorComponent"):
            container = container.get_container()


        if container is not None:
            color_containers = container["axisVectorComponent"].get_as_source_connection_list()
            if len(color_containers) > 0:
                return cls(color_containers[0].node)



        # padd this out later
        class_inst = cls()
        component_container_name = "{}:{}".format(class_inst.instance_namespace, "component_container")
        if cmds.objExists(component_container_name):
            return cls(nw.Container(component_container_name))
    
        axes_vector_inst = cls()
        axes_vector_inst.create_component()

        return axes_vector_inst
    
    def make_choice_node(self, name=""):
        if name is not None and name != "":
            choice = nw.Node.create_node("choice", name)
        else:
            choice = nw.Node.create_node("choice")
        io_node = self.io_node
        for index, axis in enumerate(utils_enum.AxisEnums):
            io_node["{}Vector".format(axis.name)] >> choice["input"][index]

        return choice

class WeightSelectorComponent(Component):
    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = super()._init_node_data(instance_name, **attr_kwargs)

        node_data_dict[self._io_name.node_name].add_attr_data(
            data.AttrData("numWeights", publish_name=True, type="long", parent="install", min=1),
            data.AttrData("selector", publish_name=True, type="double", parent="input", min=0),
            data.AttrData("weight", publish_name=True, type="double", parent="output", multi=True),
            data.AttrData("weightType", publish_name=True, type="enum", enumName=utils_enum.SelectorWeightTypes.maya_enum_str(), parent="install"),
            data.AttrData("weightInverse", publish_name=True, type="bool", parent="install")
        )

        return node_data_dict
    
    def _pre_build_component(self):
        node_data_dict = super()._pre_build_component()

        io_node = self.io_node

        num_weights = int(io_node["numWeights"].value)

        
        if num_weights > 1:
            step = 1/(num_weights - 1)
            for index in range(num_weights):
                remap_node = nw.Node.create_node("remapValue", "selectorRemap{}".format(index))

                # connections
                io_node["selector"] >> remap_node["inputValue"]
                remap_node["inputMax"] = io_node["numWeights"].value - 1

                remap_node["outValue"] >> io_node["weight"][index]

                inv_selector_value = 0
                selector_value = 1
                if io_node["weightInverse"].value:
                    inv_selector_value = 1
                    selector_value = 0

                position_value_list = []
                # initialize remaps
                # if not first
                if index > 0:
                    position_value_list.append((step * (index - 1), inv_selector_value))
                # middle
                position_value_list.append((step * index, selector_value))
                # if not first or if zip
                if index < num_weights - 1 and io_node["weightType"].value == 0:
                    position_value_list.append((step * (index + 1), inv_selector_value))

                if index == 0 and io_node["weightType"].value == 1:
                    position_value_list = [(0, selector_value), (1, selector_value)]

                for index, val in enumerate(position_value_list):
                    remap_node["value"][index]["value_Position"] = val[0]
                    remap_node["value"][index]["value_FloatValue"] = val[1]
                    


                node_data_dict.add_node_data(data.NodeData(remap_node))
        else:
            io_node["weight"][0] = 1

        return node_data_dict

class MirrorHelperComponent(Component):
    has_inst_name_attr=True

    @property
    def instance_namespace(self):
        namespace = super().instance_namespace
        side_index = 0
        if self.io_node is not None:
            side_index = self.io_node[data.HierDataAttrNames.hier_side.value].value
        if side_index > 0:
            namespace = namespace.split("_", 1)
            opposite_side_index = self.io_node["mirrorSide"].value
            opposite_side_name = utils_enum.CharacterSide.get(opposite_side_index).value

            namespace = "{}{}_{}".format(namespace[0], opposite_side_name, namespace[1])

        return namespace

    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = super(MirrorHelperComponent, self)._init_node_data(instance_name, **attr_kwargs)

        self._add_hier_data(node_data_dict)
        node_data_dict[self._io_name.node_name].add_attr_data(
            data.AttrData("mirrorSide", publish_name=True, type="enum", enumName=utils_enum.CharacterSide.maya_enum_str(), parent="output"),
            data.AttrData("scaleMatrix", publish_name=True, type="matrix", parent="input"),
            data.AttrData("parentMatrix", publish_name=True, type="matrix", parent="input"),
            data.AttrData("primaryAxis", publish_name=True, type="enum", enumName=utils_enum.AxisEnums.maya_enum_str(), parent="input"),
            data.AttrData("secondaryAxis", publish_name=True, type="enum", enumName=utils_enum.AxisEnums.maya_enum_str(), parent="input"),
            data.AttrData("mirrorPrimaryAxis", publish_name=True, type="enum", enumName=utils_enum.AxisEnums.maya_enum_str(), parent="output"),
            data.AttrData("mirrorSecondaryAxis", publish_name=True, type="enum", enumName=utils_enum.AxisEnums.maya_enum_str(), parent="output"),
        )

        return node_data_dict

    def _pre_build_component(self):
        # reference to nodes
        io_node = self.io_node
        hier_attr = io_node[data.HierDataAttrNames.hier.value]

        # creating remap for side
        node_data_dict = super(MirrorHelperComponent, self)._pre_build_component()
        side_remap = utils_enum.CharacterSide.create_remap("mirrorSideRemap")
        io_node[data.HierDataAttrNames.hier_side.value] >> side_remap["inputValue"]
        side_remap["outValue"] >> io_node["mirrorSide"]
        
        node_data_dict.add_node_data(data.NodeData(side_remap))

        # primary axis
        primary_axis_remap = utils_enum.AxisEnums.create_remap("primMirrorAxisRemap")
        io_node["primaryAxis"] >> primary_axis_remap["inputValue"]
        primary_axis_remap["outValue"] >> io_node["mirrorPrimaryAxis"]

        node_data_dict.add_node_data(data.NodeData(primary_axis_remap))

        # secondary axis
        secondary_axis_remap = utils_enum.AxisEnums.create_remap("secMirrorAxisRemap")
        io_node["secondaryAxis"] >> secondary_axis_remap["inputValue"]
        secondary_axis_remap["outValue"] >> io_node["mirrorSecondaryAxis"]

        node_data_dict.add_node_data(data.NodeData(secondary_axis_remap))
        
        # hiers
        for index in range(len(hier_attr)):
            mirror_world_matrix = nw.Node.create_node("multMatrix", "worldMatrixMult{}".format(index))
            mirror_local_matrix = nw.Node.create_node("multMatrix", "localMatrixMult{}".format(index))

            #world matrix
            hier_attr[index][data.HierAttrNames.input_world_matrix.value] >> mirror_world_matrix["matrixIn"][0]
            io_node["scaleMatrix"] >> mirror_world_matrix["matrixIn"][1]
            mirror_world_matrix["matrixSum"] >> hier_attr[index][data.HierAttrNames.output_world_matrix.value]

            #local matrix
            hier_attr[index][data.HierAttrNames.input_local_matrix.value] >> mirror_local_matrix["matrixIn"][0]
            io_node["scaleMatrix"] >> mirror_local_matrix["matrixIn"][1]
            mirror_local_matrix["matrixSum"] >> hier_attr[index][data.HierAttrNames.output_local_matrix.value]

            node_data_dict.add_node_data(data.NodeData(mirror_world_matrix))
            node_data_dict.add_node_data(data.NodeData(mirror_local_matrix))

            hier_kwargs={

            }


        return node_data_dict

    def mirror_component(self, direction, **component_kwargs):
        return None
    
class PoleVecCalcComponent(Component):
    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = super()._init_node_data(instance_name, **attr_kwargs)

        node_data_dict[self._io_name.node_name].add_attr_data(
            data.AttrData("startMatrix", publish_name=True, type="matrix", parent="input"),
            data.AttrData("endMatrix", publish_name=True, type="matrix", parent="input"),
            data.AttrData("dirMatrix", publish_name=True, type="matrix", parent="input"),
            data.AttrData("outputMatrix", publish_name=True, type="matrix", parent="output"),
            data.AttrData("poleScalar", publish_name=True, type="double", parent="input", min=0.1, value=1),
            data.AttrData("primaryAimAxis", publish_name=True, type="double3", parent="input"),
            data.AttrData("primaryAimAxisX", type="double", parent="primaryAimAxis", value=1),
            data.AttrData("primaryAimAxisY", type="double", parent="primaryAimAxis"),
            data.AttrData("primaryAimAxisZ", type="double", parent="primaryAimAxis"),
            data.AttrData("secondaryAimAxis", publish_name=True, type="double3", parent="input"),
            data.AttrData("secondaryAimAxisX", type="double", parent="secondaryAimAxis"),
            data.AttrData("secondaryAimAxisY", type="double", parent="secondaryAimAxis", value=1),
            data.AttrData("secondaryAimAxisZ", type="double", parent="secondaryAimAxis"),
        )

        return node_data_dict
    
    def _pre_build_component(self):
        node_data_dict =  super()._pre_build_component()

        add_nodes = []

        start_end_distance = nw.Node.create_node("distanceBetween", "start_end_dist")
        start_dir_distance = nw.Node.create_node("distanceBetween", "start_dir_dist")
        dir_end_distance = nw.Node.create_node("distanceBetween", "dir_end_dist")

        io_node = self.io_node

        # connecting to distances
        io_node["startMatrix"] >> start_end_distance["inMatrix1"]
        io_node["endMatrix"] >> start_end_distance["inMatrix2"]

        io_node["startMatrix"] >> start_dir_distance["inMatrix1"]
        io_node["dirMatrix"] >> start_dir_distance["inMatrix2"]

        io_node["dirMatrix"] >> dir_end_distance["inMatrix1"]
        io_node["endMatrix"] >> dir_end_distance["inMatrix2"]

        # aim matrix
        aim_matrix = nw.Node.create_node("aimMatrix", "aim")

        io_node["startMatrix"] >> aim_matrix["inputMatrix"]
        io_node["endMatrix"] >> aim_matrix["primaryTargetMatrix"]
        io_node["primaryAimAxis"] >> aim_matrix["primaryInputAxis"]
        io_node["dirMatrix"] >> aim_matrix["secondaryTargetMatrix"]
        io_node["secondaryAimAxis"] >> aim_matrix["secondaryInputAxis"]
        aim_matrix["secondaryMode"] = 1

        # matrix nodes
        compose_matrix = nw.Node.create_node("composeMatrix", "poleOffsetMatrix")
        mult_matrix = nw.Node.create_node("multMatrix", "poleWorldMatrix")


        compose_matrix["outputMatrix"] >> mult_matrix["matrixIn"][0]
        aim_matrix["outputMatrix"] >> mult_matrix["matrixIn"][1]

        mult_matrix["matrixSum"] >> io_node["outputMatrix"]

        # expression
        side_dists = [start_dir_distance["distance"], 
                      dir_end_distance["distance"], 
                      start_end_distance["distance"]]
        expr_str = [
            "$dist = (pow({2},2) + pow({0},2) - pow({1},2))/(2 * {2});".format(*side_dists),
            "$primaryVal = $dist;",
            "$secondaryVal = 1.75 * {} * sqrt(abs(pow({}, 2)) - abs(pow($dist, 2)));".format(io_node["poleScalar"], side_dists[0]),
            "{} = $primaryVal * {} + $secondaryVal * {};".format(compose_matrix["inputTranslateX"], io_node["primaryAimAxisX"], io_node["secondaryAimAxisX"]),
            "{} = $primaryVal * {} + $secondaryVal * {};".format(compose_matrix["inputTranslateY"], io_node["primaryAimAxisY"], io_node["secondaryAimAxisY"]),
            "{} = $primaryVal * {} + $secondaryVal * {};".format(compose_matrix["inputTranslateZ"], io_node["primaryAimAxisZ"], io_node["secondaryAimAxisZ"]),   
        ]

        expr_node = nw.Node(cmds.expression(string="\n".join(expr_str), name="poleOffsetExpr"))

        add_nodes = [start_end_distance, start_dir_distance, dir_end_distance, 
                     aim_matrix, compose_matrix, mult_matrix, expr_node]
        for node in add_nodes:
            node_data_dict.add_node_data(data.NodeData(node))

        return node_data_dict
    
class HierComponent(Component):
    component_type=utils_enum.ComponentTypes.hier
    root_transform_name="hierGrp"
    
    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = super()._init_node_data(instance_name, **attr_kwargs)

        node_data_dict[self._io_name.node_name].add_attr_data(
            data.AttrData("hiers", publish_name=True, type="message", multi=True),
            data.AttrData("jntRadius", publish_name=True, type="float", value=1.0)
        )
        return node_data_dict

    @classmethod
    def get_instance(cls, info=None):
        # see if it's found in the character component
        container = info
        if issubclass(type(info), Component):
            container = info.container_node
        while container is not None and not container.has_attr("hierComponent"):
            container = container.get_container()


        if container is not None:
            hier_containers = container["hierComponent"].get_as_source_connection_list()
            if len(hier_containers) > 0:
                return cls(nw.Container(hier_containers[0].node))

        # if no container found
        class_inst = cls()
        component_container_name = "{}:{}".format(class_inst.instance_namespace, "component_container")
        if cmds.objExists(component_container_name):
            return cls(nw.Container(component_container_name))
    
        hier_inst = cls()
        hier_inst.create_component()

        return hier_inst

    def add_hiers(self, *input_component_list):
        for input_component in input_component_list:
            if isinstance(input_component, nw.Container):
                input_component = base_components.get_component(input_component)
            input_container = input_component.container_node
            
            first_available_index = -1

            io_node = self.io_node

            for i in range(len(io_node["hiers"])):
                if not io_node["hiers"][i].has_source_connection():
                    first_available_index = i
            if first_available_index == -1:
                first_available_index = len(io_node["hiers"])

            side=utils_enum.CharacterSide.get(input_container[data.HierDataAttrNames.hier_side.value].value)

            # input hier attrs
            input_hier_attrs = input_container[data.HierDataAttrNames.hier.value]
            input_container[data.HierDataAttrNames.hier_data.value] >> io_node["hiers"][first_available_index]
            interface = nw.Node.create_node("network", name="{}_{}_interface".format(side.value, input_container["componentInstName"].value))

            #adding attrs to interface
            interface.add_attr("parentMatrix", type="matrix")
            interface.add_attr("side", type="enum", enumName=utils_enum.CharacterSide.maya_enum_str())
            interface.add_attr("hiers", type="compound", numberOfChildren=4, multi=True)
            interface.add_attr("name", type="string", parent="hiers")
            interface.add_attr("initMatrix", type="matrix", parent="hiers")
            interface.add_attr("worldMatrix", type="matrix", parent="hiers")
            interface.add_attr("localMatrix", type="matrix", parent="hiers")

            input_container[data.HierDataAttrNames.hier_parent.value] >> interface["parentMatrix"]
            input_container[data.HierDataAttrNames.hier_side.value] >> interface["side"]

            jnt_parent = self.transform_node
            jnt_name_pre = "{}_{}".format(side.value, input_container["componentInstName"].value)

            for index in range(len(input_hier_attrs)):
                input_hier_attrs[index][data.HierAttrNames.hier_name.value] >> interface["hiers"][index]["name"]
                input_hier_attrs[index][data.HierAttrNames.hier_init_matrix.value] >> interface["hiers"][index]["initMatrix"]
                input_hier_attrs[index][data.HierAttrNames.output_world_matrix.value] >> interface["hiers"][index]["worldMatrix"]
                input_hier_attrs[index][data.HierAttrNames.output_local_matrix.value] >> interface["hiers"][index]["localMatrix"]

                jnt = nw.Node(cmds.joint(name="{}_{}".format(jnt_name_pre, interface["hiers"][index]["name"].value)))
                # cmds.parent(str(jnt_parent), str(jnt), relative=False)
                interface["hiers"][index]["localMatrix"] >> jnt["offsetParentMatrix"]
                self.container_node.add_nodes(jnt)

                io_node["jntRadius"] >> jnt["radius"]

                if index == 0:
                    cmds.parent(str(jnt), str(jnt_parent), relative=True)

            self.container_node.add_nodes(interface)
            self.rename_nodes()

    