import system.globals as globals
import utils.node_wrapper as nw
import maya.cmds as cmds
import utils.utils as utils
import utils.enum as utils_enum
from enum import Enum

class AttrData:
    def __init__(self, attr_name, value=None, locked=False, keyable=False, alias=None, connection=[], publish_name=None, **add_attr_kwargs):
        self.attr_name = attr_name
        self.add_attr_kwargs = add_attr_kwargs
        self.value = value
        self.locked = locked
        self.keyable = keyable
        self.alias = alias
        self.connection = connection
        self.publish_name = publish_name


    def __str__(self):
        return "<AttrValuesData> name:{} | value:{} | lock:{} | keyable: {} | alias: {}| connection:{} | kwargs:{} | publish name: {}".format(
            self.attr_name, 
            self.value, 
            self.locked, 
            self.keyable,
            self.alias,
            self.connection,
            self.add_attr_kwargs,
            self.publish_name
        )

class NodeData():
    def __init__(self, node=None, node_name="", node_type="", map_node_attr=""):
        self.node = node
        self.node_name = node_name
        self.node_type = node_type
        self.map_node_attr=map_node_attr
        self.attr_values = {}

    def __str__(self):
        ret_str = "<NodeBuildData>\n"
        ret_str += "\tNode:{}\n".format(str(self.node))
        ret_str += "\tName:{}\n".format(self.node_name)
        ret_str += "\tType:{}\n".format(self.node_type)
        ret_str += "\tDynamic Attrs:\n"
        ret_str += "\tAttr Values:\n"
        for x in self.attr_values:
            ret_str += "\t\t{}\n".format(self.attr_values[x])
        return ret_str
    
    def add_attr_data(self, *args):
        for attr_data in args:
            self.attr_values[attr_data.attr_name] = attr_data

class NodeBuildDataDict(dict):
    def add_node_data(self, node_data:NodeData, key=None):
        if key is not None:
            self[key] = node_data
        elif node_data.node_name is not None and node_data.node_name != "":
            self[node_data.node_name] = node_data
        elif node_data.node is not None:
            self[str(node_data.node)] = node_data
        else:
            cmds.warning("node data was not added")
            

    def create_nodes(self, namespace=":"):
        namespace = utils.Namespace.add_outer_colons(namespace)

        for node_key in self.keys():
            node_data = self[node_key]

            if node_data.node is None:
                node_name = utils.Namespace.strip_namespace(name = str(node_data.node_name))
                node_name = namespace + node_name
                node_data.node_name = node_name
            
            

            if node_data.node is None:
                # create node
                if node_data.node_type == "container":
                    node_data.node = nw.Container.create_node(node_data.node_name)
                else:
                    node_data.node = nw.Node.create_node(node_data.node_type, node_data.node_name)

            # getNumParents
            compound_num_children_dict = {}
            # get the keys
            for attr_key in node_data.attr_values:
                attr_data = node_data.attr_values[attr_key]
                if attr_data.add_attr_kwargs is not None and "parent" in attr_data.add_attr_kwargs.keys():
                    attr_name = attr_data.add_attr_kwargs["parent"]
                    if attr_name not in compound_num_children_dict.keys():
                        compound_num_children_dict[attr_name] = 0
                    
                    compound_num_children_dict[attr_name] += 1


            # remove input and output compound attrs if no children were found
            if "input" not in compound_num_children_dict.keys() and "input" in node_data.attr_values:
                if node_data.attr_values["input"].add_attr_kwargs is not None:
                    node_data.attr_values.pop("input")
            if "output" not in compound_num_children_dict.keys() and "output" in node_data.attr_values:
                if node_data.attr_values["output"].add_attr_kwargs is not None:
                    node_data.attr_values.pop("output")

            # add attrs
            node = node_data.node
            for attr_key in node_data.attr_values:
                attr_data = node_data.attr_values[attr_key]
                if attr_data.add_attr_kwargs is not None and attr_data.add_attr_kwargs != {}:
                    if attr_data.attr_name in compound_num_children_dict.keys() and attr_data.add_attr_kwargs["type"] =="compound":
                        attr_data.add_attr_kwargs["numberOfChildren"] = compound_num_children_dict[attr_data.attr_name]
                    if attr_data.add_attr_kwargs["type"] !="compound" or "numberOfChildren" in attr_data.add_attr_kwargs.keys():
                        node.add_attr(attr_data.attr_name, **attr_data.add_attr_kwargs)         

    def connect_nodes(self):
        for node_key in self.keys():
            node = self[node_key].node

            for attr_key in self[node_key].attr_values:
                attr_value = self[node_key].attr_values[attr_key]
                if not node.has_attr(attr_value.attr_name):
                    cmds.warning("{} not an attribute of {} ... skipping setting and connecting".format(attr_value.attr_name, node))
                    continue
                
                # set value
                if attr_value.value is not None:
                    if not node[attr_value.attr_name].is_connected():
                        node[attr_value.attr_name] = attr_value.value

                # connect attr
                if attr_value.connection is not None:
                    for connection in attr_value.connection:
                        if isinstance(connection, nw.Attr):
                            node[attr_value.attr_name] >> connection
                        elif isinstance(connection, tuple):
                            dest_node_key, dest_attr = connection
                            if dest_node_key not in self.keys():
                                cmds.warning("{} key not in node_dict ... skipping connection".format(dest_node_key))
                                continue
                            dest_node = self[dest_node_key].node
                            if not dest_node.has_attr(dest_attr):
                                cmds.warning("{} not an attribute of {} ... skipping connection".format(dest_attr, dest_node))
                                continue
                            node[attr_value.attr_name] >> dest_node[dest_attr]
                # set as keyable
                if attr_value.keyable:
                    node[attr_value.attr_name].set_keyable(attr_value.keyable)
                
                # set alias
                if attr_value.alias is not None:
                    if node.has_attr(attr_value.attr_name):
                        node[attr_value.attr_name].set_alias(attr_value.alias)

                # set locked
                if attr_value.locked:
                    node[attr_value.attr_name].set_locked(attr_value.locked)

    def publish_attrs(self, container_node):
        for node_key in self.keys():
            node = self[node_key].node
            if node == container_node:
                continue
            for attr_key in self[node_key].attr_values:
                attr_value = self[node_key].attr_values[attr_key]
                if not node.has_attr(attr_value.attr_name):
                    cmds.warning("{} not an attribute of {} ... skipping publish in {} container".format(attr_value.attr_name, node, container_node))
                    continue
                if attr_value.publish_name is not None:
                    if isinstance(attr_value.publish_name, str):
                        container_node.publish_attr(node[attr_value.attr_name], attr_value.publish_name)
                    elif attr_value:
                        container_node.publish_attr(node[attr_value.attr_name], attr_value.attr_name)

    def map_to_container(self):
        for node_key in self.keys():
            node_data = self[node_key]
            if node_data.map_node_attr is not None and node_data.map_node_attr != "":
                utils.map_node_to_container(node_data.map_node_attr, node_data.node)

    def handle_node_data(self, namespace):
        self.create_nodes(namespace)
        self.connect_nodes()

class ComponentInsertData:
    def __init__(self, attr_name=None, attr_value=None, as_dest=True):
        self.attr_name = attr_name
        self.attr_value = attr_value
        self.as_dest = as_dest

    def __str__(self):
        return "name: {} - value: {} - as destination: {}".format(self.attr_name, self.attr_value, self.as_dest)

class IOName():
    node_name = globals.IO_NODE_NAME
    connect_attr_name = "{}Node".format(globals.IO_NODE_NAME)
    frz_cache_node_name = "freeze{}Cache".format(globals.IO_NODE_NAME.capitalize())
    frz_cache_key = "freeze_{}_cache".format(globals.IO_NODE_NAME)
    connect_frz_cache_attr_name = "freeze{}CacheNode".format(globals.IO_NODE_NAME.capitalize())

class HierBuildData:
    def __init__(self, *args, name=None, hier_init=None, input_matrix=None, input_local_matrix=None, link_hier_output_matrix=True, link_hier_kwargs=False, **kwargs):
        hier_attr_names = HierAttrNames

        self.name = None
        self.hier_init = None
        self.input_matrix = None
        self.local_matrix = None
        self.kwargs = {}
        if len(args) > 0 and isinstance(args[0], nw.Node) and args[0].node_type == "transform":
            self.input_matrix = args[0]["worldMatrix"][0]
            self.local_matrix = args[0]["dagLocalMatrix"]
            self.name = utils.Namespace.strip_namespace(args[0].name) + "_transform"
        elif len(args) > 0 and isinstance(args[0], nw.Attr) and HierData.is_hier_attr(args[0]):
                self.hier_init = args[0][hier_attr_names.hier_init_matrix.value]
                self.name = args[0][hier_attr_names.hier_name.value]
                if link_hier_output_matrix:
                    self.input_matrix = args[0][hier_attr_names.output_world_matrix.value]
                    self.local_matrix = args[0][hier_attr_names.output_local_matrix.value]
                else:
                    self.input_matrix = args[0][hier_attr_names.input_world_matrix.value]
                    self.local_matrix = args[0][hier_attr_names.input_local_matrix.value]
                if link_hier_kwargs:
                    self.kwargs = args[0]["hierKwargData"]
        if name is not None:
            self.name = name
        if hier_init is not  None:
            self.hier_init = hier_init
        if input_matrix is not None:
            self.input_matrix = input_matrix
        if input_local_matrix is not None:
            self.local_matrix = input_local_matrix
        if kwargs != {}:
            self.kwargs = kwargs

    def hier_component_insert_list(self, attr):
        
        component_insert_data_list = []
        if self.hier_init is not None:
            component_insert_data_list.append(ComponentInsertData(attr_name="{}.{}".format(attr, HierAttrNames.hier_init_matrix.value), attr_value=self.hier_init))
        if self.name is not None:
            component_insert_data_list.append(ComponentInsertData(attr_name="{}.{}".format(attr, HierAttrNames.hier_name.value), attr_value=self.name))
        if self.input_matrix is not None:
            component_insert_data_list.append(ComponentInsertData(attr_name="{}.{}".format(attr, HierAttrNames.input_world_matrix.value), attr_value=self.input_matrix))
        if self.local_matrix is not None:
            component_insert_data_list.append(ComponentInsertData(attr_name="{}.{}".format(attr, HierAttrNames.input_local_matrix.value), attr_value=self.local_matrix))
        if isinstance(self.kwargs, nw.Attr) or isinstance(self.kwargs, str):
            component_insert_data_list.append(ComponentInsertData(attr_name="{}.{}".format(attr, HierAttrNames.hier_kwarg_data.value), attr_value=self.kwargs))

        elif "kwargs" in self.kwargs.keys():
            component_insert_data_list.append(ComponentInsertData(attr_name="{}.{}".format(attr, HierAttrNames.hier_kwarg_data.value), attr_value=self.kwargs["kwargs"]))
        elif self.kwargs != {} and self.kwargs is not None:
            self.kwargs = utils.kwarg_to_dict(**self.kwargs)

            if isinstance(self.kwargs, dict):
                component_insert_data_list.append(ComponentInsertData(attr_name="{}.{}".format(attr, HierAttrNames.hier_kwarg_data.value), attr_value=str(self.kwargs)))
            else:
                component_insert_data_list.append(ComponentInsertData(attr_name="{}.{}".format(attr, HierAttrNames.hier_kwarg_data.value), attr_value=self.kwargs))

        return component_insert_data_list
    
    def __str__(self):
        return "<HierBuildData> name:{} | hier_init:{} | input_matrix:{} | input_inverse_matrix:{} | kwargs:{}".format(
            self.name,
            self.hier_init,
            self.input_matrix,
            self.local_matrix,
            self.kwargs
        )
class HierDataAttrNames(Enum):
    hier_data = "hierData"
    hier = "hier"
    hier_parent = "hierParent"
    hier_parent_init = "hierParentInit"
    hier_side = "hierSide"
class HierAttrNames(Enum):
    hier_name = "hierName"
    hier_init_matrix = "hierInitMatrix"
    hier_kwarg_data = "hierKwargData"
    input_world_matrix = "inputWorldMatrix"
    input_local_matrix = "inputLocalMatrix"
    output_world_matrix = "outputWorldMatrix"
    output_local_matrix = "outputLocalMatrix"
class HierData:
    
    def __init__(self):
        pass
    @classmethod
    def hier_data_creation_data(cls, publish=True):
        attr_data = [
            AttrData(HierDataAttrNames.hier_data.value, publish_name=publish, type="compound"),
            AttrData(HierDataAttrNames.hier.value, type="compound", parent=HierDataAttrNames.hier_data.value, multi=True),
            AttrData(HierDataAttrNames.hier_parent.value, type="matrix", parent=HierDataAttrNames.hier_data.value),
            AttrData(HierDataAttrNames.hier_parent_init.value, type="matrix", parent=HierDataAttrNames.hier_data.value),
            AttrData(HierDataAttrNames.hier_side.value, type="enum", parent=HierDataAttrNames.hier_data.value, enumName=utils_enum.CharacterSide.maya_enum_str())
        ]
        attr_data.extend(cls.hier_creation_data())
        return attr_data
    @classmethod
    def hier_creation_data(cls):
        return [
            AttrData(HierAttrNames.hier_name.value, type="string", parent=HierDataAttrNames.hier.value),
            AttrData(HierAttrNames.hier_name.hier_init_matrix.value, type="matrix", parent=HierDataAttrNames.hier.value),
            AttrData(HierAttrNames.hier_name.hier_kwarg_data.value, type="string", parent=HierDataAttrNames.hier.value),
            AttrData(HierAttrNames.hier_name.input_world_matrix.value, type="matrix", parent=HierDataAttrNames.hier.value),
            AttrData(HierAttrNames.hier_name.input_local_matrix.value, type="matrix", parent=HierDataAttrNames.hier.value),
            AttrData(HierAttrNames.hier_name.output_world_matrix.value, type="matrix", parent=HierDataAttrNames.hier.value),
            AttrData(HierAttrNames.hier_name.output_local_matrix.value, type="matrix", parent=HierDataAttrNames.hier.value),
        ]

    @classmethod
    def is_hier_attr(cls, attr):
        attr_data = [x.attr_name for x in cls.hier_creation_data()]
        for attr_name in attr_data:
            if not attr.has_attr(attr_name):
                return False
        return True