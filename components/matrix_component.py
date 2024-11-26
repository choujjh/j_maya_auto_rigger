from system.base_components import Component
import system.data as data
import utils.node_wrapper as nw
import utils.enum as utils_enum
import maya.cmds as cmds

class MotionComponent(Component):
    component_type = utils_enum.ComponentTypes.matrix
    has_inst_name_attr = True

class MatrixPointComponent(Component):
    component_type = utils_enum.ComponentTypes.matrix
    def __init__(self, container_node=None, parent_container_node=None):
        super(MatrixPointComponent, self).__init__(container_node, parent_container_node)

    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = super(MatrixPointComponent, self)._init_node_data(instance_name, **attr_kwargs)

        node_data_dict[self._io_name.node_name].add_attr_data(
            data.AttrData("worldMatrix", publish_name=True, type="matrix", parent="input"),
            data.AttrData("objectInvSpace", publish_name="objectInvSpace", type="matrix", parent="input"),
            data.AttrData("point", publish_name="point", type="double3", parent="output"),
            data.AttrData("pointX", type="double", parent="point"),
            data.AttrData("pointY", type="double", parent="point"),
            data.AttrData("pointZ", type="double", parent="point"),
        )
        return node_data_dict
    
    def _pre_build_component(self):
        node_data_dict = super(MatrixPointComponent, self)._pre_build_component()

        io_node = self.io_node

        mult_matrix = nw.Node.create_node("multMatrix", name="spaceMult")
        vec_point = nw.Node.create_node("vectorProduct", name="point")

        io_node["worldMatrix"] >> mult_matrix["matrixIn[0]"]
        io_node["objectInvSpace"] >> mult_matrix["matrixIn[1]"]

        mult_matrix["matrixSum"] >> vec_point["matrix"]
        vec_point["output"] >> io_node["point"]

        vec_point["operation"] = 4

        node_data_dict.add_node_data(data.NodeData(node=mult_matrix), "multMatrix")
        node_data_dict.add_node_data(data.NodeData(node=vec_point), "vecPoint")


        return node_data_dict
    
class OffsetMatrixComponent(Component):
    component_type = utils_enum.ComponentTypes.matrix
    has_inst_name_attr=True
    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = super()._init_node_data(instance_name, **attr_kwargs)

        node_data_dict[self._io_name.node_name].add_attr_data(
            # matricies
            data.AttrData("targetMatrix", publish_name=True, type="matrix", parent="input"),
            data.AttrData("spaceMatrix", publish_name=True, type="matrix", parent="input"),
            data.AttrData("offsetMatrix", publish_name=True, type="matrix", parent="output"),
        )

        return node_data_dict
    
    def _pre_build_component(self):
        node_data_dict = super()._pre_build_component()

        mult_matrix = nw.Node.create_node("multMatrix", "offsetMatrixMult")
        inv_matrix = nw.Node.create_node("inverseMatrix", "spaceMatrixInv")

        io_node = self.io_node

        io_node["spaceMatrix"] >> inv_matrix["inputMatrix"]

        io_node["targetMatrix"] >> mult_matrix["matrixIn[0]"]
        inv_matrix["outputMatrix"] >> mult_matrix["matrixIn[1]"]

        mult_matrix["matrixSum"] >> io_node["offsetMatrix"]

        node_data_dict.add_node_data(data.NodeData(mult_matrix))
        node_data_dict.add_node_data(data.NodeData(inv_matrix))

        return node_data_dict

class SpaceMatrixComponent(Component):
    component_type = utils_enum.ComponentTypes.matrix
    has_inst_name_attr=True
    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = super()._init_node_data(instance_name, **attr_kwargs)

        node_data_dict[self._io_name.node_name].add_attr_data(
            # matricies
            data.AttrData("targetMatrix", publish_name=True, type="matrix", parent="input"),
            data.AttrData("offsetMatrix", publish_name=True, type="matrix", parent="input"),
            data.AttrData("spaceMatrix", publish_name=True, type="matrix", parent="output"),
        )

        return node_data_dict
    
    def _pre_build_component(self):
        node_data_dict = super()._pre_build_component()

        mult_matrix = nw.Node.create_node("multMatrix")
        inv_matrix = nw.Node.create_node("inverseMatrix")

        io_node = self.io_node

        io_node["offsetMatrix"] >> inv_matrix["inputMatrix"]


        inv_matrix["outputMatrix"] >> mult_matrix["matrixIn[0]"]
        io_node["targetMatrix"] >> mult_matrix["matrixIn[1]"]

        mult_matrix["matrixSum"] >> io_node["spaceMatrix"]

        node_data_dict.add_node_data(data.NodeData(mult_matrix))
        node_data_dict.add_node_data(data.NodeData(inv_matrix))

        return node_data_dict

class MergeHierComponent(Component):
    component_type = utils_enum.ComponentTypes.matrix
    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = super()._init_node_data(instance_name, **attr_kwargs)

        node_data_dict[self._io_name.node_name].add_attr_data(
            data.AttrData("parentMatrix", publish_name=True, type="matrix", parent="input"),
            data.AttrData("hier", publish_name=True, type="compound", parent="input", multi=True),
            data.AttrData("inMatrix", type="matrix", parent="hier"),
            data.AttrData("weight", type="double", parent="hier"),

            data.AttrData("worldMatrix", publish_name=True, type="matrix", parent="output"),
            data.AttrData("localMatrix", publish_name=True, type="matrix", parent="output"),

        )
        return node_data_dict
    
    def _pre_build_component(self):
        node_data_dict = super()._pre_build_component()

        # getting / creating nodes
        io_node = self.io_node
        blend_matrix = nw.Node.create_node("blendMatrix", "localBlendMatrix")
        mult_matrix = nw.Node.create_node("multMatrix", "worldMult")

        # connect to blend
        for index in range(len(io_node["hier"])):
            if index == 0:
                io_node["hier"][index]["inMatrix"] >> blend_matrix["inputMatrix"]
            else:
                io_node["hier"][index]["inMatrix"] >> blend_matrix["target"][index-1]["targetMatrix"]
                io_node["hier"][index]["weight"] >> blend_matrix["target"][index-1]["weight"]

        # connections to mult matrix
        blend_matrix["outputMatrix"] >> mult_matrix["matrixIn"][0]
        io_node["parentMatrix"] >> mult_matrix["matrixIn"][1]

        #connections to output
        mult_matrix["matrixSum"] >> io_node["worldMatrix"]
        blend_matrix["outputMatrix"] >> io_node["localMatrix"]

        # adding to container
        node_data_dict.add_node_data(data.NodeData(blend_matrix))
        node_data_dict.add_node_data(data.NodeData(mult_matrix))


        return node_data_dict
