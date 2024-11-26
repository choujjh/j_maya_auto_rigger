from system.base_components import Component
import utils.node_wrapper as nw
import system.data as data
import utils.utils as utils
import utils.enum as utils_enum
import components.control_components as control_components
import components.components as components
import components.motion_component as motion_components

import maya.cmds as cmds

class SetupComponent(Component):
    component_type = utils_enum.ComponentTypes.setup
    is_rebuildable = True
    root_transform_name = "grp"
    has_side_attr = True
    has_inst_name_attr = True

    def get_default_control_class(self):
        return type(self).default_control
    
    def get_default_control_color(self):
        return type(self).default_control_color

    def __init__(self, container_node=None, parent_container_node=None):
        super(SetupComponent, self).__init__(container_node, parent_container_node)

    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = super(SetupComponent, self)._init_node_data(instance_name, **attr_kwargs)

        node_data_dict = self._add_hier_data(node_data_dict)
        node_data_dict[self._io_name.node_name].add_attr_data(
            data.AttrData("attachedEndMatrix", type="matrix", parent="install")
        )
        return node_data_dict

    def _pre_build_component(self):
        node_data_dict = super(SetupComponent, self)._pre_build_component()
        io_node = self.io_node

        io_node_hier_attr = io_node[data.HierDataAttrNames.hier.value]
        hier_attr_names = data.HierAttrNames

        # get all named hiers
        hier_list = []
        for hier_index in range(len(io_node_hier_attr)):
            attr = io_node_hier_attr[hier_index]
            if attr[hier_attr_names.hier_name.value].value != "" and attr[hier_attr_names.hier_name.value].value is not None:
                hier_list.append(hier_index)

        # creating visual help curve
        guide_curve = nw.Node(cmds.curve(name="guide", degree=1, point=[[0.0, x, 0.0] for x in range(len(hier_list))]))
        guide_curve_shape = nw.Node(cmds.listRelatives(str(guide_curve), shapes=True)[0])
        guide_curve_shape["overrideEnabled"] = True
        guide_curve_shape["overrideDisplayType"] = 2

        # create world_points for guide_curve
        guild_curve_world_point = nw.Node.create_node("pointMatrixMult", "guildWorldPoint")
        guide_curve["worldMatrix"][0] >> guild_curve_world_point["inMatrix"]

        # attach curve
        attach_curve = nw.Node(cmds.curve(name="guide", degree=1, point=[[0.0, x, 0.0] for x in range(2)]))
        attach_curve_shape = nw.Node(cmds.listRelatives(str(attach_curve), shapes=True)[0])
        attach_curve_shape["overrideEnabled"] = True
        attach_curve_shape["overrideDisplayType"] = 2
        cmds.parent(str(attach_curve_shape), str(guide_curve), relative=True, shape=True)
        attach_curve.delete_node()

        # attach curve connections and nodes
        attach_start_point = nw.Node.create_node("pointMatrixMult", "{}Pnt".format("attachStartPoint"))
        io_node[data.HierDataAttrNames.hier_parent_init.value] >> attach_start_point["inMatrix"]
        attach_end_point = nw.Node.create_node("pointMatrixMult", "{}Pnt".format("attachEndPoint"))
        io_node["attachedEndMatrix"] >> attach_end_point["inMatrix"]

        io_node[data.HierDataAttrNames.hier.value][0][data.HierAttrNames.hier_init_matrix.value] >> io_node["attachedEndMatrix"]

        # expression str
        expr_str = []

        # attach curve expression
        expr_str.append("{0}.xValue = {1}X - {2}X;".format(
            attach_curve_shape["controlPoints"][0], 
            attach_start_point["output"],
            guild_curve_world_point["output"]))
        expr_str.append("{0}.yValue = {1}Y - {2}Y;".format(
            attach_curve_shape["controlPoints"][0], 
            attach_start_point["output"],
            guild_curve_world_point["output"]))
        expr_str.append("{0}.zValue = {1}Z - {2}Z;".format(
            attach_curve_shape["controlPoints"][0], 
            attach_start_point["output"],
            guild_curve_world_point["output"]))
        expr_str.append("{0}.xValue = {1}X - {2}X;".format(
            attach_curve_shape["controlPoints"][1], 
            attach_end_point["output"],
            guild_curve_world_point["output"]))
        expr_str.append("{0}.yValue = {1}Y - {2}Y;".format(
            attach_curve_shape["controlPoints"][1], 
            attach_end_point["output"],
            guild_curve_world_point["output"]))
        expr_str.append("{0}.zValue = {1}Z - {2}Z;".format(
            attach_curve_shape["controlPoints"][1], 
            attach_end_point["output"],
            guild_curve_world_point["output"]))

        # looping over hiers
        for index, hier_index in enumerate(hier_list):
            attr = io_node_hier_attr[hier_index]

            # convert string to dict for kwargs
            hier_kwargs = utils.convert_kwarg_data(attr[hier_attr_names.hier_kwarg_data.value])

            # get specified control component
            control_class = control_components.SphereControl
            if "control_class" in hier_kwargs.keys():
                control_class = hier_kwargs["control_class"]
                hier_kwargs.pop("control_class")

            # create controls
            control_inst = self.promote_to_control(attr, control_class, **hier_kwargs)
            if attr[hier_attr_names.hier_init_matrix.value].has_source_connection():
                ~attr[hier_attr_names.hier_init_matrix.value]
            attr[hier_attr_names.output_world_matrix.value] >> attr[hier_attr_names.hier_init_matrix.value]

            # world point for matrix
            hier_name = attr[hier_attr_names.hier_name.value].value
            matrix_point = nw.Node.create_node("pointMatrixMult", "{}Pnt".format(hier_name))
            
            attr[hier_attr_names.input_world_matrix.value] >> matrix_point["inMatrix"]

            # expression for guide shape points
            expr_str.append("{0}.xValue = {1}X - {2}X;".format(
                guide_curve_shape["controlPoints"][index], 
                matrix_point["output"],
                guild_curve_world_point["output"]))
            expr_str.append("{0}.yValue = {1}Y - {2}Y;".format(
                guide_curve_shape["controlPoints"][index], 
                matrix_point["output"],
                guild_curve_world_point["output"]))
            expr_str.append("{0}.zValue = {1}Z - {2}Z;".format(
                guide_curve_shape["controlPoints"][index], 
                matrix_point["output"],
                guild_curve_world_point["output"]))

            # setting up no scales from controls
            pick_matrix = nw.Node.create_node("pickMatrix", "hier_non_scale_matrix{}".format(index))
            
            pick_matrix["useScale"] = 0
            pick_matrix["useShear"] = 0
            io_node[data.HierDataAttrNames.hier.value][index][data.HierAttrNames.input_world_matrix.value] >> pick_matrix["inputMatrix"]
            
            # adding nodes
            node_data_dict.add_node_data(node_data=data.NodeData(node=matrix_point))
            node_data_dict.add_node_data(node_data=data.NodeData(pick_matrix))

        expr_node = nw.Node(cmds.expression(string="\n".join(expr_str), name="guidExpr"))

        cmds.parent(str(guide_curve), str(self.transform_node), relative=True)

        node_data_dict.add_node_data(node_data=data.NodeData(node=guide_curve))
        node_data_dict.add_node_data(node_data=data.NodeData(node=guide_curve_shape))
        node_data_dict.add_node_data(node_data=data.NodeData(node=attach_curve_shape))
        node_data_dict.add_node_data(node_data=data.NodeData(node=attach_start_point))
        node_data_dict.add_node_data(node_data=data.NodeData(node=attach_end_point))
        node_data_dict.add_node_data(node_data=data.NodeData(node=pick_matrix))
        node_data_dict.add_node_data(node_data=data.NodeData(node=guild_curve_world_point))
        node_data_dict.add_node_data(node_data=data.NodeData(node=expr_node))

        return node_data_dict
    
    def input_matrix_pre_attr(self, index):
        return self.input_matrix_pre_node(index)["outputMatrix"]
    
    def input_matrix_pre_node(self, index):
        io_node = self.io_node
        return utils.get_first_connected_node_of_type(io_node[data.HierDataAttrNames.hier.value][index][data.HierAttrNames.input_world_matrix.value], "pickMatrix", as_dest=False, as_source=True)

    def build_component(self):
        super(SetupComponent, self).build_component()
        
        self._setup_output_hier()
        self.rename_nodes()

    def _setup_output_hier(self):
        pass

class HingeSetup(SetupComponent):
    def _init_node_data(self, instance_name=None, **attr_kwargs):

        node_data_dict = super(HingeSetup, self)._init_node_data(instance_name, **attr_kwargs)

        node_data_dict[self._io_name.node_name].add_attr_data(
            data.AttrData("primaryAxis", value=0, publish_name=True, type="enum", enum_name=utils_enum.AxisEnums.maya_enum_str(), parent="install"),
            data.AttrData("secondaryAxis", value=1, publish_name=True, type="enum", enum_name=utils_enum.AxisEnums.maya_enum_str(), parent="install"),
            data.AttrData("poleMatrix", publish_name=True, type="matrix", parent="output"),
            data.AttrData("poleScalarInput", publish_name=True, type="double", parent="input", min=0.1, value=1),
            data.AttrData("poleScalarOutput", publish_name=True, type="double", parent="output", min=0.1, value=1),
        )

        return node_data_dict

    def _override_mirror_kwargs(self, scale_matrix, **mirror_kwargs):
        kwargs = super()._override_mirror_kwargs(scale_matrix, **mirror_kwargs)
        kwargs["poleScalarInput"] = self.io_node["poleScalarOutput"]

        
        return kwargs

    def filter_attr_kwargs(self, attr_kwargs):
        hier_data_keys = [x for x in attr_kwargs.keys() if utils.snake_to_camel(x).startswith(data.HierDataAttrNames.hier_data.value)]
        hier_data_keys = [x for x in hier_data_keys if utils.snake_to_camel(x) not in ["hier{}".format(index) for index in range(3)]]

        for delete_keys in hier_data_keys:
            attr_kwargs.pop(delete_keys)

        return super().filter_attr_kwargs(attr_kwargs)

    def _setup_output_hier(self):
        io_node = self.io_node

        io_node_hier_attr = io_node[data.HierDataAttrNames.hier.value]
        hier_attr_names = data.HierAttrNames

        hier_name = data.HierDataAttrNames.hier.value
        output_world_name = hier_attr_names.output_world_matrix.value
        output_local_name = hier_attr_names.output_local_matrix.value

        ik_inst = self.insert_component(
            motion_components.IKComponent, 
            root_matrix = self.input_matrix_pre_attr(0),
            pole_matrix = self.input_matrix_pre_attr(1),
            goal_matrix = self.input_matrix_pre_attr(2),

            primary_axis = io_node["primaryAxis"],
            secondary_axis = io_node["secondaryAxis"],
            orient_end_matrix = False,

            hier0=data.HierBuildData(io_node_hier_attr[0], input_matrix=self.input_matrix_pre_attr(0), link_hier_output_matrix=False),
            hier1=data.HierBuildData(io_node_hier_attr[1], input_matrix=self.input_matrix_pre_attr(1), link_hier_output_matrix=False),
            hier2=data.HierBuildData(io_node_hier_attr[2], input_matrix=self.input_matrix_pre_attr(2), link_hier_output_matrix=False)
            
        )
        ik_io_node = ik_inst.io_node

        pole_vec_inst = self.insert_component(
            components.PoleVecCalcComponent,
            start_matrix=ik_io_node[data.HierDataAttrNames.hier.value][0][data.HierAttrNames.output_world_matrix.value],
            dir_matrix=ik_io_node[data.HierDataAttrNames.hier.value][1][data.HierAttrNames.output_world_matrix.value],
            end_matrix=ik_io_node[data.HierDataAttrNames.hier.value][2][data.HierAttrNames.output_world_matrix.value],


            primary_aim_axis=ik_io_node["primaryAxisVector"],
            secondary_aim_axis=ik_io_node["secondaryAxisVector"]
        )

        if io_node["poleScalarInput"].has_source_connection():
            io_node["poleScalarInput"] >> pole_vec_inst.io_node["poleScalar"]

        hier_kwargs = utils.convert_kwarg_data(io_node[data.HierDataAttrNames.hier.value][0][data.HierAttrNames.hier_kwarg_data.value])

        # get specified control component
        control_class = control_components.SphereControl
        if "control_class" in hier_kwargs.keys():
            control_class = hier_kwargs["control_class"]
            hier_kwargs.pop("control_class")

        pole_vec_inst.io_node["outputMatrix"] >> io_node["poleMatrix"]
        
        if "publish_attr_list" in hier_kwargs.keys():
            hier_kwargs.pop("publish_attr_list")

        pole_vector_control_inst = self.promote_to_control(
            io_node["poleMatrix"],
            control_class,
            publish_attr_list=[],
            instance_name="poleSetup",
            **hier_kwargs
        )

        pole_vector_control_inst.promote_attr_to_keyable(pole_vec_inst.io_node["poleScalar"])


        for i in range(3):
            ik_io_node[hier_name][i][output_world_name] >> io_node[hier_name][i][output_world_name]
            ik_io_node[hier_name][i][output_local_name] >> io_node[hier_name][i][output_local_name]

        
            pole_vec_inst.io_node["poleScalar"] >> io_node["poleScalarOutput"]

            