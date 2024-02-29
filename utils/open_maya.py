from maya.api import OpenMaya as om2
import maya.cmds as cmds
import re
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
        redo(src_plug, dest_plug)
        apiundo.commit(
            redo = lambda: redo(src_plug, dest_plug),
            undo = lambda: undo(src_plug, dest_plug)
        )