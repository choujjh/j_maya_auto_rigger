from system.base_components import Component
import components.control_components as control_components
import components.motion_component as motion_components
import components.matrix_component as matrix_components
import components.setup_components as setup_components
import components.components as components
import utils.node_wrapper as nw
import utils.enum as utils_enum
import utils.utils as utils
import system.data as data
import re

import maya.cmds as cmds

class AnimComponent(Component):
    component_type = utils_enum.ComponentTypes.anim
    root_transform_name = "animGrp"
    has_inst_name_attr = True
    has_side_attr = True

    def get_component_ui_attrs(self):
        return [self.container_node["level"]]

    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = super()._init_node_data(instance_name, **attr_kwargs)

        node_data_dict[self._io_name.node_name].add_attr_data(
            data.AttrData("level", publish_name=True, type="enum", enumName="primary:secondary")
        )
        return node_data_dict

class HingeAnimComponent(AnimComponent):
    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = super(HingeAnimComponent, self)._init_node_data(instance_name, **attr_kwargs)

        self._add_hier_data(node_data_dict)

        setup_kwargs=utils.kwarg_to_dict(control_class=control_components.SphereControl, build_scale=0.3)
        fk_kwargs=utils.kwarg_to_dict(
            hier_control_class=control_components.BoxControl,
            hier0=utils.kwarg_to_dict(
                build_translate = [1, 0.0, 0.0],
                build_scale = 0.5
            ),
            hier1=utils.kwarg_to_dict(
                build_translate = [1, 0.0, 0.0],
                build_scale = 0.5
            ),
            hier2=utils.kwarg_to_dict(
                build_translate = [1, 0.0, 0.0],
                build_scale = 0.5
            ),
        )
        ik_kwargs=utils.kwarg_to_dict(
            root_cntrl=utils.kwarg_to_dict(
                control_class=control_components.BoxControl,
                build_scale = 0.5
            ),
            goal_cntrl=utils.kwarg_to_dict(
                control_class=control_components.BoxControl,
                build_scale = 0.5
            ),
            pole_cntrl=utils.kwarg_to_dict(
                control_class=control_components.Pyramid4Control,
                build_rotate=[0, 45, 0],
                build_scale = 0.5
            )
        )

        node_data_dict[self._io_name.node_name].add_attr_data(
            data.AttrData("primaryAxis", value=0, publish_name=True, type="enum", enum_name=utils_enum.AxisEnums.maya_enum_str(), parent="install"),
            data.AttrData("secondaryAxis", value=1, publish_name=True, type="enum", enum_name=utils_enum.AxisEnums.maya_enum_str(), parent="install"),
            data.AttrData("fkKwargs", type="string", parent="install", publish_name=True, value=fk_kwargs),
            data.AttrData("ikKwargs", type="string", parent="install", publish_name=True, value=ik_kwargs),
            data.AttrData("setupKwargs", type="string", parent="install", publish_name=True, value=setup_kwargs),
            data.AttrData("primaryAxis", value=0, publish_name=True, type="enum", enum_name=utils_enum.AxisEnums.maya_enum_str(), parent="install"),
            data.AttrData("secondaryAxis", value=1, publish_name=True, type="enum", enum_name=utils_enum.AxisEnums.maya_enum_str(), parent="install"),
            data.AttrData("selector", publish_name=True, type="double", min=0, max=1),
            data.AttrData("ikParentMatrix", publish_name=True, type="matrix", parent="input"),
            data.AttrData("poleScalar", publish_name=True, type="double"),
        )

        return node_data_dict

    def get_component_ui_attrs(self):
        return_attrs = super().get_component_ui_attrs()
        container_node = self.container_node

        return_attrs.extend([
            container_node["primaryAxis"],
            container_node["secondaryAxis"],
        ])
        if cmds.objExists("{}:{}".format(utils.Namespace.get_namespace(str(self.container_node)), "hinge_setup:poleSetup__sphere_control:control")):
            pole_scalar_cntrl = nw.Node("{}:{}".format(utils.Namespace.get_namespace(str(self.container_node)), "hinge_setup:poleSetup__sphere_control:control"))
            return_attrs.append(pole_scalar_cntrl["poleScalar"])

        return_attrs.extend([
            container_node[data.HierDataAttrNames.hier.value][0][data.HierAttrNames.hier_name.value],
            container_node[data.HierDataAttrNames.hier.value][1][data.HierAttrNames.hier_name.value],
            container_node[data.HierDataAttrNames.hier.value][2][data.HierAttrNames.hier_name.value],
        ])
        
        return return_attrs

    def filter_attr_kwargs(self, attr_kwargs):
        hier_data_keys = [x for x in attr_kwargs.keys() if utils.snake_to_camel(x).startswith(data.HierDataAttrNames.hier_data.value)]
        hier_data_keys = [x for x in hier_data_keys if utils.snake_to_camel(x) not in ["hier{}".format(index) for index in range(3)]]

        for delete_key in hier_data_keys:
            attr_kwargs.pop(delete_key)

        hier_data_indexes = [utils.get_trailing_numbers(x) for x in attr_kwargs.keys() if utils.snake_to_camel(x).startswith("hier")]
        for index in range(3):
            if index not in hier_data_indexes:
                translate_matrix = utils.translate_to_matrix([0, 2.5*index, 0])
                if index == 1:
                    translate_matrix = utils.translate_to_matrix([0, 2.5*index, 0.3])
                attr_kwargs["hier{}".format(index)] = data.HierBuildData(name="temp{}".format(index), input_matrix=translate_matrix, publish_attr_list=["translate"], radius=0.3, shape_color=utils_enum.Colors.yellow)

        return super().filter_attr_kwargs(attr_kwargs)

    def _override_mirror_kwargs(self, scale_matrix, **mirror_kwargs):
        mirror_kwargs =  super()._override_mirror_kwargs(scale_matrix, **mirror_kwargs)

        io_node = self.io_node

        mirror_kwargs["level"] = io_node["level"].value
        mirror_kwargs["fkKwargs"] = {}
        mirror_kwargs["ikKwargs"] = {}
        mirror_kwargs["setupKwargs"] = {}
        mirror_kwargs["poleScalar"] = io_node["poleScalar"]

        return mirror_kwargs

    def _pre_build_component(self):
        def _kwarg_to_hier_data_kwargs(kwargs):
            pattern = r"{}\d+".format(data.HierDataAttrNames.hier.value)
            non_hier_kwargs = {x:kwargs[x] for x in kwargs if x.find("hier") != 0}
            hier_single_kwargs = {x:kwargs[x] for x in kwargs if x.find("hier") == 0 and re.fullmatch(pattern, utils.snake_to_camel(x))}
            hier_generic_kwargs = {x.replace("hier_", ""):kwargs[x] for x in kwargs if x not in non_hier_kwargs.keys() and x not in hier_single_kwargs}

            hier_single_kwarg_list = [hier_generic_kwargs.copy(), hier_generic_kwargs.copy(), hier_generic_kwargs.copy()]

            for index in range(3):
                hier_data_key = "hier{}".format(index)
                if hier_data_key in hier_single_kwargs:
                    hier_single_kwarg_list[index].update(utils.convert_kwarg_data(hier_single_kwargs[hier_data_key]))

            return non_hier_kwargs, hier_single_kwarg_list
        
        node_data_dict = super()._pre_build_component()

        # character component
        char_inst = self.get_parent_component_of_type(utils_enum.ComponentTypes.character)

        # nodes
        io_node = self.io_node
        motion_transform = self.transform_node
        ik_cntrl_grp = nw.Node.create_node("transform", "ikCntrlGrp")
        cmds.parent(str(ik_cntrl_grp), str(motion_transform))
        io_node_hier_attr = io_node[data.HierDataAttrNames.hier.value]

        # setting hier attr and hier names
        io_node_hier_attr = io_node[data.HierDataAttrNames.hier.value]
        hier_attr_names = data.HierAttrNames
        hier_data_attr_names = data.HierDataAttrNames

        # setup component
        setup_kwargs = utils.convert_kwarg_data(io_node["setupKwargs"])
        setup_non_hier_kwargs, setup_hier_data_kwarg_list = _kwarg_to_hier_data_kwargs(setup_kwargs)

        for setup_hier_kwarg in setup_hier_data_kwarg_list:
            for key in setup_non_hier_kwargs.keys():
                if key not in setup_hier_kwarg.keys():
                    setup_hier_kwarg[key] = setup_non_hier_kwargs[key]
        
        setup_pole_vec_scalar_kwargs = {}
        
        if io_node["poleScalar"].has_source_connection():
            setup_pole_vec_scalar_kwargs["poleScalarInput"] = io_node["poleScalar"]

        setup_inst = self.insert_component(
            setup_components.HingeSetup,
            transform_parent=char_inst.setup_grp_node,
            primary_axis = io_node["primaryAxis"],
            secondary_axis = io_node["secondaryAxis"],
            hier_parent = io_node["hierParent"],
            hier_parent_init = io_node["hierParentInit"],
            hier0 = data.HierBuildData(io_node_hier_attr[0], link_hier_output_matrix=False, **setup_hier_data_kwarg_list[0]),
            hier1 = data.HierBuildData(io_node_hier_attr[1], link_hier_output_matrix=False, **setup_hier_data_kwarg_list[1]),
            hier2 = data.HierBuildData(io_node_hier_attr[2], link_hier_output_matrix=False, **setup_hier_data_kwarg_list[2]),
            **setup_pole_vec_scalar_kwargs,
        )
        setup_io_node = setup_inst.io_node
        setup_hier_attr = setup_io_node[hier_data_attr_names.hier.value]

        if not io_node["poleScalar"].has_source_connection():
            setup_io_node["poleScalarOutput"] >> io_node["poleScalar"]

        if not self.container_node.has_attr("mirrorDest"):
            # getting all the setup_io_node to connect to input
            for index in range(len(io_node_hier_attr)):
                connection_list = io_node_hier_attr[index][hier_attr_names.input_world_matrix.value].get_as_source_connection_list()
                ~connection_list[0]

                setup_hier_attr[index][hier_attr_names.input_world_matrix.value] >> io_node_hier_attr[index][hier_attr_names.input_world_matrix.value]

        #connect setup to init
        for index in range(len(setup_hier_attr)):
            if io_node_hier_attr[index][hier_attr_names.hier_init_matrix.value].has_source_connection():
                ~io_node_hier_attr[index][hier_attr_names.hier_init_matrix.value]
            setup_hier_attr[index][hier_attr_names.output_world_matrix.value] >> io_node_hier_attr[index][hier_attr_names.hier_init_matrix.value]

        # fk component
        fk_kwargs = utils.convert_kwarg_data(io_node["fkKwargs"])
        fk_non_hier_kwargs, fk_hier_data_kwarg_list = _kwarg_to_hier_data_kwargs(fk_kwargs)

        io_node_hier_attr = io_node[data.HierDataAttrNames.hier.value]
        fk_inst = self.insert_component(
            motion_components.FKComponent,
            hier_parent=io_node[data.HierDataAttrNames.hier_parent.value],
            hier_parent_init=io_node[data.HierDataAttrNames.hier_parent_init.value],
            transform_parent=motion_transform,
            hier0=data.HierBuildData(setup_hier_attr[0], **fk_hier_data_kwarg_list[0]),
            hier1=data.HierBuildData(setup_hier_attr[1], **fk_hier_data_kwarg_list[1]),
            hier2=data.HierBuildData(setup_hier_attr[2], **fk_hier_data_kwarg_list[2]),
            **fk_non_hier_kwargs
        )
        fk_io_node = fk_inst.io_node


        # ik component
        ik_kwargs = utils.convert_kwarg_data(io_node["ikKwargs"])
        ik_non_hier_kwargs, ik_hier_data_kwarg_list = _kwarg_to_hier_data_kwargs(ik_kwargs)
        ik_kwarg_cntrl_list=[]
        for key in ["root_cntrl", "goal_cntrl", "pole_cntrl"]:
            if key in ik_non_hier_kwargs.keys():
                ik_kwarg_cntrl_list.append(ik_non_hier_kwargs.pop(key))
            else:
                ik_kwarg_cntrl_list.append({})

        ik_root_cntrl_kwargs, ik_goal_cntrl_kwargs, ik_pole_cntrl_kwargs = ik_kwarg_cntrl_list
        
        # parenting ik root control to ik component
        offset_matrix_inst = self.insert_component(
            matrix_components.OffsetMatrixComponent,
            space_matrix = io_node[data.HierDataAttrNames.hier_parent_init.value],
            target_matrix = io_node_hier_attr[0][data.HierAttrNames.hier_init_matrix.value])
        mult_matrix = nw.Node.create_node("multMatrix", "ikRootMatrix")
        offset_matrix_inst.io_node["offsetMatrix"] >> mult_matrix["matrixIn"][0]
        io_node[data.HierDataAttrNames.hier_parent.value] >> mult_matrix["matrixIn"][1]

        # parenting others
        mult_matrix_goal = nw.Node.create_node("multMatrix", "ikGoalParentFollow")
        mult_matrix_pole = nw.Node.create_node("multMatrix", "ikGoalPoleFollow")

        setup_hier_attr[2][hier_attr_names.output_world_matrix.value] >> mult_matrix_goal["matrixIn"][0]
        io_node["ikParentMatrix"] >> mult_matrix_goal["matrixIn"][1]
        setup_io_node["poleMatrix"] >> mult_matrix_pole["matrixIn"][0]
        io_node["ikParentMatrix"] >> mult_matrix_pole["matrixIn"][1]

        # insert ik component
        ik_inst = self.insert_component(
            motion_components.IKComponent,
            hier0=data.HierBuildData(setup_hier_attr[0], **ik_hier_data_kwarg_list[0]),
            hier1=data.HierBuildData(setup_hier_attr[1], **ik_hier_data_kwarg_list[1]),
            hier2=data.HierBuildData(setup_hier_attr[2], **ik_hier_data_kwarg_list[2]),

            root_matrix=mult_matrix["matrixSum"],
            pole_matrix=mult_matrix_pole["matrixSum"],
            goal_matrix=mult_matrix_goal["matrixSum"],
            
            primary_axis=io_node["primaryAxis"],
            secondary_axis=io_node["secondaryAxis"],
            **ik_non_hier_kwargs
        )
        
        node_data_dict.add_node_data(data.NodeData(node=mult_matrix))
        node_data_dict.add_node_data(data.NodeData(node=mult_matrix_goal))
        node_data_dict.add_node_data(data.NodeData(node=mult_matrix))

        ik_inst.container_node.add_nodes(ik_cntrl_grp)
        ik_inst.rename_nodes()

        #promoting IK to controls
        ik_io_node = ik_inst.io_node
        for name, attr, kwargs in zip(
            ["ikRoot", "ikGoal", "ikPole"],
            ["rootMatrix", "goalMatrix", "poleMatrix"],
            [ik_root_cntrl_kwargs, ik_goal_cntrl_kwargs, ik_pole_cntrl_kwargs]):

            component_class = control_components.BoxControl

            if "control_class" in kwargs:
                component_class = kwargs.pop("control_class")
            if "name" in kwargs:
                name = kwargs.pop("name")

            if "shape_node" in kwargs.keys():
                input_shape = nw.derive_node(kwargs["shape_node"])
                kwargs.pop("shape_node")
                container = None

                if input_shape.node_type == "transform":
                    if input_shape.get_container() is not None:
                        container = input_shape.get_container()
                if input_shape.node_type == "container":
                    container = input_shape
                
                component_class = utils.string_to_class(container["componentClass"].value)
                kwargs["input_shape"] = component_class(container).transform_node

            control_inst = ik_inst.promote_to_control(
                ik_io_node[attr], component_class, parent=ik_cntrl_grp, name=name, **kwargs)

            if attr=="goalMatrix":
                control_inst.promote_attr_to_keyable(ik_io_node["stretchy"], "stretchy")
                control_inst.promote_attr_to_keyable(ik_io_node["preserveMinLength"], "preserveMinLength")
                control_inst.promote_attr_to_keyable(ik_io_node["orientEndMatrix"], "orientEndMatrix")

        # merging hiers
        selector_inst = self.insert_component(
            components.WeightSelectorComponent, 
            weight_type=utils_enum.SelectorWeightTypes.wave, 
            num_weights=2,
            selector = io_node["selector"],
        )
        selector_io_node = selector_inst.io_node

        hier_parent = io_node[hier_data_attr_names.hier_parent_init.value]
        for index in range(3):
            
            if index == 0:
                merge_hier_inst = self.insert_component(
                    matrix_components.MergeHierComponent,
                    hier0inMatrix = fk_io_node[hier_data_attr_names.hier.value][index][hier_attr_names.output_world_matrix.value],
                    hier0weight = selector_io_node["weight"][0],
                    hier1inMatrix = ik_io_node[hier_data_attr_names.hier.value][index][hier_attr_names.output_world_matrix.value],
                    hier1weight = selector_io_node["weight"][1],
                )

            else:

                merge_hier_inst = self.insert_component(
                    matrix_components.MergeHierComponent,
                    hier0inMatrix = fk_io_node[hier_data_attr_names.hier.value][index][hier_attr_names.output_local_matrix.value],
                    hier0weight = selector_io_node["weight"][0],
                    hier1inMatrix = ik_io_node[hier_data_attr_names.hier.value][index][hier_attr_names.output_local_matrix.value],
                    hier1weight = selector_io_node["weight"][1],
                    parentMatrix = hier_parent
                )

            merge_hier_io_node = merge_hier_inst.io_node
            hier_parent = merge_hier_io_node["worldMatrix"]

            merge_hier_io_node["worldMatrix"] >> io_node[hier_data_attr_names.hier.value][index][hier_attr_names.output_world_matrix.value]
            merge_hier_io_node["localMatrix"] >> io_node[hier_data_attr_names.hier.value][index][hier_attr_names.output_local_matrix.value]

        # adding gear icon
        primary_axis_vec = utils_enum.AxisEnums.get(io_node["primaryAxis"].value)
        primary_axis_vec = utils_enum.AxisEnums.opposite(primary_axis_vec).value
        primary_axis_vec = utils.Vector(primary_axis_vec)
        secondary_axis_vec = utils.Vector(utils_enum.AxisEnums.get(io_node["secondaryAxis"].value).value)

        gear_control_inst = self.insert_component(
            control_components.GearControl,
            shape_color = utils_enum.Colors.gold,
            transform_parent=motion_transform,
            build_translate=[x for x in 1.7 * secondary_axis_vec],
            build_rotate=[x for x in 90 *primary_axis_vec],
            build_scale=0.5,
        )
        gear_control_inst.transform_node["inheritsTransform"] = False

        # get output world matrix prev
        gear_ws_attr = io_node[hier_data_attr_names.hier.value][index][hier_attr_names.output_world_matrix.value].get_as_dest_connection_list()[0]
        gear_ws_attr >> gear_control_inst.io_node["offsetMatrix"]

        # add ik control
        gear_control_inst.promote_attr_to_keyable(io_node["selector"], name="switch", type="enum", enumName="FK:IK")

        # groups visibility
        gear_control_inst.transform_node["switch"] >> ik_cntrl_grp["visibility"]
        reverse_node = nw.Node.create_node("reverse", "fkVisibilityReverse")
        gear_control_inst.transform_node["switch"] >> reverse_node["inputX"]
        reverse_node["outputX"] >> fk_inst.transform_node["visibility"]

        node_data_dict.add_node_data(data.NodeData(node=reverse_node))

        return node_data_dict    