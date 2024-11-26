from maya.api import OpenMaya as om2
import maya.cmds as cmds
import re
import ast
import math
# import components.control_components as control_components
import utils.enum as utils_enum

from typing import Union

import utils.node_wrapper as nw
import utils.apiundo as apiundo

def get_dep_node(node: Union[om2.MObject, om2.MPlug, str]):
    """converts to dependency node using input. if none found None 
    will be returned

    Args:
        node (Union[om2.MObject, om2.MPlug, str]): input to convert 
        to dependency node

    Returns:
        Union[None, om2.MFnDependencyNode]:
    """
    if isinstance(node, om2.MFnDependencyNode):
        return node
    if isinstance(node, om2.MObject):
        if node.hasFn(om2.MFn.kDependencyNode):
            return om2.MFnDependencyNode(node)
    
    # if can be added to a MSelectionList
    m_sel_list = om2.MSelectionList()
    if isinstance(node, str):
        full_name = cmds.ls(node, l=True)
        if len(full_name) > 1:
            cmds.error("more than 1 object named {}".format(node))
        node = full_name[0]
    elif isinstance(node, om2.MPlug):
        return get_dep_node(node.node())
    elif isinstance(node, nw.Node):
        return node.get_dep_node()
    
    # if not string or mplug
    else:
        return None
    
    m_sel_list.add(node)
    dep_node = m_sel_list.getDependNode(0)
    return om2.MFnDependencyNode(dep_node)

def get_child_plug(plug: om2.MPlug, attr: str):
    """returns the child plug of "plug" given a child attribute. 
    returns all child plugs in a dict{attribute:plug} if "attr" is None

    Args:
        plug (om2.MPlug): parent plug of attr
        attr (str): attribute to find

    Returns:
        Union[om2.MPlug, dict{str, om2.MPlug}: child MPlug
    """
    child_plugs = [plug.child(index) for index in range(plug.numChildren())]
    child_plugs = {x.name().rsplit(".", 1)[1]: x for x in child_plugs}
    if attr == None:
        return child_plugs
    if attr in child_plugs.keys():
        return child_plugs[attr]
    return None

def get_plug(attr_parent: Union[om2.MPlug, om2.MFnDependencyNode, str],
             attr: Union[om2.MPlug, str]): 
    """returns the given attribute as a plug. If attr_parent is 
    provided it finds the attribute under that parent (either a 
    dependency node or another plug) as a plug

    Args:
        attr (Union[om2.MPlug, str]):
        attr_parent (Union[om2.MPlug, om2.MFnDependencyNode, str], 
        optional): parent of attribute. Defaults to None. When none 
        find"s dependency node of attr

    Returns:
        om2.MPlug: 
    """
    if isinstance(attr, om2.MPlug):
        return attr
    elif isinstance(attr_parent, om2.MPlug):
        attr_str = str(attr)
        curr_plug = attr_parent
        for x in [x for x in re.split(r"[.|\[|\]]", attr_str) if x != ""]:
            if curr_plug.isArray:
                curr_plug = curr_plug.elementByLogicalIndex(int(x))
            elif curr_plug.isCompound:
                if isinstance(attr, int):
                    curr_plug = curr_plug.child(attr)
                else:
                    curr_plug = get_child_plug(curr_plug, x)
                if curr_plug is None:
                    return None
            else:
                return None
        return curr_plug
    elif attr_parent == None:
        attr_parent = get_dep_node(attr)
        attr_str = attr.split(".", 1)[1]
        return get_plug(attr_parent, attr_str)
    elif isinstance(attr_parent, str):
        attr_parent = get_dep_node(attr_parent)
        return get_plug(attr_parent, attr)
    elif isinstance(attr_parent, om2.MFnDependencyNode):
        split_attr = re.split(r"[.|\[|\]]", attr, 1)
        plug = attr_parent.findPlug(split_attr[0], False)
        if len(split_attr) == 1:
            return plug
        return get_plug(plug, split_attr[1])
    
def connect_plugs(src_plug: om2.MPlug, dest_plug: om2.MPlug):
        """connects source plug to destination plug

        Args:
            src_plug (om2.MPlug):
            dest_plug (om2.MPlug):
        """
        def redo(src_plug, dest_plug):
            dgMod = om2.MDGModifier()
            dgMod.connect(src_plug, dest_plug)
            dgMod.doIt()
        def undo(src_plug, dest_plug):
            dgMod = om2.MDGModifier()
            dgMod.disconnect(src_plug, dest_plug)
            dgMod.doIt()
        try:
            redo(src_plug, dest_plug)
            apiundo.commit(
                redo = lambda: redo(src_plug, dest_plug),
                undo = lambda: undo(src_plug, dest_plug)
            )
        except:
            cmds.connectAttr(str(src_plug), str(dest_plug), force=True)

class Namespace:
    @classmethod
    def get_namespace(cls, name):
        if name.find(":") == -1:
            return ":"
        else:
            return name.split("|")[-1].rpartition(":")[0]
    
    @classmethod
    def strip_namespace(cls, name):
        if name.find(":") == -1:
            return name
        else:
            return name.rpartition(":")[-1]
    
    @classmethod
    def delete(cls, name):
        cmds.namespace(removeNamespace=name)

    @classmethod
    def exists(cls, name):
        return cmds.namespace(exists=name)

    @classmethod
    def combine_namespace(cls, namespace_list):
        namespace_list = [re.sub(r'^:+|:+$', '', x) for x in namespace_list]
        namespace = ":".join(namespace_list)
        namespace = "{}:".format(namespace)
        return namespace
    
    @classmethod
    def add_namespace(cls, namespace):

        # add an index at the end of a namespace
        namespace = strip_trailing_numbers(namespace)
        namespace_index = Namespace.get_namespace_greatest_index(namespace)
        if namespace_index == 0:
            Namespace._plain_rename_namespace(namespace, namespace + "1")
            namespace = namespace + "2"
        elif namespace_index > 0:
            namespace = namespace + str(namespace_index + 1)

        cmds.namespace(addNamespace=cls.strip_outer_colons(namespace))
        return namespace

    @classmethod
    def rename_namespace(cls, old_namespace, new_namespace):
        old_namespace = cls.strip_outer_colons(old_namespace)
        new_namespace = cls.strip_outer_colons(new_namespace)

        # add an index at the end of a namespace
        new_namespace = strip_trailing_numbers(new_namespace)
        new_namespace_index = Namespace.get_namespace_greatest_index(new_namespace)
        if new_namespace_index == 0:
            Namespace._plain_rename_namespace(new_namespace, new_namespace + "1")
            new_namespace = new_namespace + "2"
        elif new_namespace_index > 0:
            new_namespace = new_namespace + str(new_namespace_index + 1)

        Namespace._plain_rename_namespace(old_namespace, new_namespace)
        return new_namespace

    @classmethod
    def _plain_rename_namespace(cls, old_namespace, new_namespace):
        old_namespace = cls.strip_outer_colons(old_namespace)
        new_namespace = cls.strip_outer_colons(new_namespace)

        if new_namespace.find(":") == -1:
            cmds.namespace(rename=[old_namespace, new_namespace])
        else:
            new_parent, new_namespace = new_namespace.rsplit(":", 1)
            new_parent = cls.strip_outer_colons(new_parent)
            new_namespace = cls.strip_outer_colons(new_namespace)
            cmds.namespace(rename=[old_namespace, new_namespace], parent=new_parent)

    @classmethod
    def strip_outer_colons(cls, namespace):
        return re.sub(r'^:+|:+$', '', namespace)
    
    @classmethod
    def add_outer_colons(cls, namespace):
        return ":{}:".format(re.sub(r'^:+|:+$', '', namespace))
    
    @classmethod
    def get_namespace_greatest_index(cls, namespace):
        namespace = Namespace.strip_outer_colons(namespace)
        namespace = re.sub(r'\d+$', '', namespace)

        if namespace.find(":") >= 0:
            parent_namespace = namespace.rsplit(":", 1)[0]
        else:
            parent_namespace = ":"
        
        cmds.namespace(setNamespace=parent_namespace)
        children_namespaces = cmds.namespaceInfo(listOnlyNamespaces=True)
        cmds.namespace(setNamespace=":")
        if children_namespaces is None:
            return -1
        
        children_namespaces = [x for x in children_namespaces if x.startswith(namespace)]
        children_index = [x.split(namespace)[-1] for x in children_namespaces]

        if children_index == []:
            return -1

        if len(children_index) == 1 and children_index[0] == "":
            return 0
        else:
            children_index = [int(x) for x in children_index if bool(re.match(r'^\d+$', x))]
            return max(children_index)

def get_is_locked_and_unlock_attr(attr):
    state = attr.is_locked()
    attr.set_locked(False)
    return state

def get_first_connected_node(attr, as_source=False, as_dest=False):
    node = attr.node
    if node is None:
        return None
    connections = attr.get_connection_list(as_source, as_dest)
    if connections == []:
        return None
    return nw.derive_node(connections[0].node)

def get_first_connected_node_of_type(attr, node_type, as_source=False, as_dest=False):
    node = attr.node
    if node is None:
        return None
    connections = attr.get_connection_list(as_source, as_dest)
    if connections == []:
        return None
    for attr in connections:
        if attr.node.node_type == node_type:

            return nw.derive_node(attr.node)

def map_node_to_container(container_attr_name, node, container_node=None, dest_message_attr_name="containerNode"):
    if container_node is None:
        container_node = node.get_container()
    if container_node is not None:
        if not container_node.has_attr(container_attr_name):
            container_node.add_attr(container_attr_name, type="message")

        if not node.has_attr(dest_message_attr_name):
            node.add_attr(dest_message_attr_name, type="message")

        container_node[container_attr_name] >> node[dest_message_attr_name]

def strip_trailing_numbers(input_string):
    return re.sub(r'\d+$', '', input_string)

def get_trailing_numbers(input_string):
    match = re.search(r'\d+$', input_string)
    if match:
        return int(match.group())
    else:
        return ""

def camel_to_snake(camel_str):
    # Find all instances where a lowercase letter is followed by an uppercase letter
    # and insert an underscore between them, then convert to lowercase
    snake_str = re.sub(r'(?<!^)(?=[A-Z])', '_', camel_str).lower()
    if snake_str.find("f_k") >= 0:
        snake_str = snake_str.replace("f_k", "fk")
    if snake_str.find("i_k") >= 0:
        snake_str = snake_str.replace("i_k", "ik")
    return snake_str

def snake_to_camel(snake_str):
    # Split the string by underscores
    if snake_str.find("fk") > 0:
        snake_str = snake_str.replace("fk","FK")
    if snake_str.find("ik") > 0:
        snake_str = snake_str.replace("ik","IK")
    components = snake_str.split('_')
    # Capitalize the first letter of each component except the first one, and join them
    camel_case_str = components[0] + ''.join(x.title() for x in components[1:])
    return camel_case_str

def convert_kwarg_data(kwargs):
    if isinstance(kwargs, nw.Attr):
        kwargs = kwargs.value
    if kwargs == None:
        kwargs = {}
    elif isinstance(kwargs, str):
        kwargs = ast.literal_eval(kwargs)

    for key in kwargs:
        if isinstance(kwargs[key], dict):
            convert_kwarg_data(kwargs[key])
        elif re.search(r"<class\s+'([^']*)'>", str(kwargs[key])) or (isinstance(kwargs[key], str) and kwargs[key].find(".") >= 0):
            kwargs[key] = string_to_class(kwargs[key])

    return kwargs

def class_type_to_str(class_type):
    if not isinstance(class_type, type) and not re.search(r"<class\s+'([^']*)'>", str(class_type)):
        return None
    pattern = r"'([^']*)'"

    match = re.search(pattern, str(class_type))

    if match:
        return match.group(1)
    else:
        return ""

def string_to_class(class_str):
    if re.search(r"<class\s+'([^']*)'>", str(class_str)):
        class_str = class_type_to_str(class_str)

    module_list = class_str.split(".")

    mod = __import__(module_list[0], {}, {}, [module_list[0]])
    module_list.pop(0)

    for module in module_list:
        if hasattr(mod, module):
            mod = getattr(mod, module)
        else:
            return None
    return mod

def kwarg_to_dict(**kwargs):
    for key in kwargs:
        if isinstance(kwargs[key], utils_enum.MayaEnumAttr):
            kwargs[key] = utils_enum.MayaEnumAttr.long_name(kwargs[key])
        if isinstance(kwargs[key], type):
            kwargs[key] = str(kwargs[key])
    return kwargs

def identity_matrix():
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0
    ]

def zero_matrix():
    return [0.0 for x in range(16)]

def translate_to_matrix(translation):
    matrix = identity_matrix()
    matrix[12] = translation[0]
    matrix[13] = translation[1]
    matrix[14] = translation[2]

    return matrix

def scale_matrix(scale):
    matrix = identity_matrix()
    matrix[0] = scale[0]
    matrix[5] = scale[1]
    matrix[10] = scale[2]

    return matrix

class Matrix(om2.MMatrix):
    def __init__(self, *args):
        if len(args) > 0 and isinstance(args[0], nw.Attr):
            if args[0].value is None:
                
                super(Matrix, self).__init__(zero_matrix())
            else:
                super(Matrix, self).__init__(args[0].value)
        elif len(args) == 16:
            super(Matrix, self).__init__(args)
        else:
            super(Matrix, self).__init__(*args)

    def get(self, r, c):
        return self[r * 4 + c]

    def setT(self, t):
        self[12] = t[0]
        self[13] = t[1]
        self[14] = t[2]

    def __str__(self):
        # values = [x for x in self.transpose()]
        # return"[[{},{},{},{}],\n [{}, {}, {}, {}],\n [{}, {}, {}, {}],\n [{}, {}, {}, {}]]".format(*values)
        return "Translate: {}, {}, {} | Rotate: {}, {}, {} | Scale: {}, {}, {}".format(*self.asT(), *self.asR(), *self.asS())
    
    def asR(self):
        return self.asDegrees()

    def asT(self):
        return self[12], self[13], self[14]

    def asS(self):

        return om2.MVector(self.axis(0)).length(), om2.MVector(self.axis(1)).length(), om2.MVector(self.axis(2)).length()

    def axis(self, index):
        i = index * 4
        return self[i], self[i + 1], self[i + 2]

    def asRadians(self):
        rx, ry, rz, ro = om2.MTransformationMatrix(self).rotationComponents(asQuaternion=False)
        return rx, ry, rz

    def asDegrees(self):
        rx, ry, rz, ro = om2.MTransformationMatrix(self).rotationComponents(asQuaternion=False)
        return math.degrees(rx), math.degrees(ry), math.degrees(rz)

    def rotation(self):
        return om2.Euler(om2.MTransformationMatrix(self).rotation())

    def quaternion(self):
        return om2.QuaternionOrPoint().setValue(self)

class Vector(om2.MVector):
    pass

import system.data as data
def attach_locators_to_output_hier(component, local_matrix=False, local_rotation_axis=False):
    io_node = component.io_node
    num_hiers = len(io_node[data.HierDataAttrNames.hier.value])

    locs = create_locators(num_hiers, local_matrix, local_rotation_axis=local_rotation_axis)

    for index in range(num_hiers):
        if local_matrix:
            io_node[data.HierDataAttrNames.hier.value][index][data.HierAttrNames.output_local_matrix.value] >> locs[index]["offsetParentMatrix"]
        else:
            io_node[data.HierDataAttrNames.hier.value][index][data.HierAttrNames.output_world_matrix.value] >> locs[index]["offsetParentMatrix"]

    return locs

def create_locators(num_locators, parented=False, local_rotation_axis=False):
    locators = []
    for i in range(num_locators):
        locators.append(nw.Node(cmds.spaceLocator()[0]))
        if local_rotation_axis:
            cmds.toggle(str(locators[-1]), localAxis=True)
        if i > 0 and parented:
            cmds.parent(str(locators[-1]), str(locators[-2]))

    return locators

def get_transform_locked_attrs(transform_node):
    transform_attrs = ["tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz", "visibility"]

    if not isinstance(transform_node, nw.Node):
        transform_node = nw.Node(transform_node)

    return [transform_node[attr] for attr in transform_attrs if transform_node[attr].is_locked()]

        

