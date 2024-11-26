from maya.api import OpenMaya as om2
import maya.cmds as cmds
from typing import Union
import utils.utils as utils
import utils.apiundo as apiundo

def derive_node(arg):
    node = Node(arg)
    if node.node_type == "container":
        return Container(node)
    return node

class Node():
    """
    A Class encapsulating a node
    """
    """
    Attributes:
    full_name (str): returns full name of node ie. parent2|parent1|name
    name (str): returns node name ie. name
    type (str): node type
    """
    def __init__(self, node):
        """_summary_

        Args:
            node ():
        """
        if isinstance(node, str):
            if not cmds.objExists(node):
                cmds.error("node {0} does not exist".format(node))
                return
        self._dep_node = utils.get_dep_node(node)
        self.__attr_cache = {}
        self.__full_attr_list = None
    
    # properties
    @property 
    def full_name(self):
        # return self._dep_node_.absoluteName()
        return self._dep_node.uniqueName()
    @property 
    def name(self):
        if self.full_name.find("|") != -1:
            return self.full_name.rsplit("|", 1)[1]
        return self.full_name
    @property
    def node_type(self):
        return self._dep_node.typeName
    @property
    def mobject(self):
        return self._dep_node.object()

    @staticmethod
    def create_node(node_type:str, name:str=None):
        """create node

        Args:
            type (str):
            name (str):
        """
        if name:
            return Node(cmds.createNode(node_type, name=name))
        return Node(cmds.createNode(node_type))
    
    @staticmethod
    def exists(node):
        return cmds.objExists(str(node))

    def has_attr(self, attr_name):
        try:
            self.__getitem__(attr_name)
            return True
        except:
            return False

    def obj_exists(self):
        return cmds.objExists(str(self))

    def add_attr(self, long_name="", **kwargs):
        if "parent" in kwargs.keys():
            if isinstance(kwargs["parent"], Attr):
                kwargs["parent"] = kwargs["parent"].attr_name
            else:
                kwargs["parent"] = str(kwargs["parent"])

        attr_type=""
        if "type" in kwargs.keys():
            attr_type=kwargs["type"]
            kwargs.pop("type")
        if "longName" in kwargs.keys():
            kwargs.pop("longName")
        
        # dataType attribute
        if attr_type in ["string", "nurbsCurve", "nurbsSurface", "mesh", "matrix"]:
            kwargs["dataType"] = attr_type

        # attributeType attribute
        elif attr_type in ["compound", "message", "double", "long", "bool", "enum", "double3", "double2"]:
            kwargs["attributeType"] = attr_type

        new_kwargs = {}
        for key in kwargs:
            new_kwargs[utils.snake_to_camel(key)] = kwargs[key]

        cmds.addAttr(str(self), longName=long_name, **new_kwargs)
        

    def delete_attr(self, attr):
        cmds.deleteAttr(str(self), at=attr)

    def get_connection_list(self, asSource, asDestination):
        connections = set()
        if asSource:
            connection_list = cmds.listConnections(str(self), connections=True, source=True, destination=False, plugs=True)
            if connection_list is not None:
                connection_list = [(Attr(None, x), Attr(self, y)) for x, y in zip(connection_list[1::2], connection_list[::2])]
                connections.update(connection_list)
        if asDestination:
            connection_list = cmds.listConnections(str(self), connections=True, source=False, destination=True, plugs=True)
            if connection_list is not None:
                connection_list = [(Attr(self, x), Attr(None, y)) for x, y in zip(connection_list[::2], connection_list[1::2])]
                connections.update(connection_list)
        if self.node_type == "container":
            self_container = Container(self)
            published_attrs = self_container.get_published_attrs()

            connections = [x for x in connections if x[0] not in published_attrs and x[1] not in published_attrs]
        connections = [x for x in connections if x[0].node.node_type != "hyperLayout" and x[1].node.node_type != "hyperLayout"]
        return connections

    def _check_node_in_attr_list(self, attribute_list):
        if attribute_list:
            attribute_list = [self[x] for x in attribute_list]
            attribute_list = [x for x in attribute_list if x.node == self]
            return attribute_list
        return []

    def get_keyable_attribute_list(self):
        attribute_list = cmds.listAttr(str(self), keyable=True)
        return self._check_node_in_attr_list(attribute_list)
    def get_unlocked_attribute_list(self):
        attribute_list = cmds.listAttr(str(self), unlocked=True)
        return self._check_node_in_attr_list(attribute_list)
    def get_dynamic_attribute_list(self):
        attribute_list = cmds.listAttr(str(self), userDefined=True)
        return self._check_node_in_attr_list(attribute_list)
    def get_channel_box_list(self):
        attribute_list = cmds.listAttr(str(self), channelBox=True)
        return self._check_node_in_attr_list(attribute_list)

    def delete_node(self, clean=True):
        """delete node
        """
        if not self.obj_exists():
            return
        if not clean:
            cmds.delete(str(self))

        # delete history
        cmds.delete(str(self), constructionHistory=True)
        children = cmds.listRelatives(str(self), allDescendents=True)

        all_children = [self]
        if children is not None:
            all_children.extend([Node(x) for x in children])

        # unpublish
        node_container = self.get_container()
        if node_container is not None:
            publish_attrs = node_container.get_published_attrs()
            filter_publish_attrs = [x for x in publish_attrs if x.node == self]
            for attr in filter_publish_attrs:
                node_container.unpublish_attr(attr)

        # loop from child to parent
        for node in all_children[::-1]:
            # if container delete outside connections
            if node.node_type == "container":
                self_container = Container(node=node)
                connections = self_container.get_external_connection_list()
                for _, dest in connections:
                    ~dest

            # delete connections
            connections = node.get_connection_list(True, True)
            for _, dest in connections:
                ~dest

            cmds.delete(str(node))

    def get_container(self):
        container = cmds.container(findContainer=self.full_name, query=True)
        if container is not None:
            return Container(container)
        return container

    def get_top_level_attribute_list(self, reCache=False):
        """gets a list of top level attr for the node

        Args:
            reCache (bool, optional): reCaches Attributes. Defaults to False.

        Returns:
            list(Attr):
        """
        if self.__full_attr_list is None or reCache:
            attr_count = self._dep_node.attributeCount()
            attributes = [self._dep_node.attribute(x) for x in range(attr_count)]
            self.__full_attr_list = [Attr(self, self._dep_node.findPlug(x, False)) for x in attributes]

            for attr in self.__full_attr_list:
                attr_name = attr.attr_name
                self.__attr_cache[attr_name] = attr

        return self.__full_attr_list
    
    def get_dep_node(self):
        """returns Dependency Node

        Returns:
            OpenMaya.MFnDependencyNode:
        """
        return self._dep_node
    
    def get_attr_cache(self):
        return self.__attr_cache

    def rename(self, new_name:str):
        """renames encapsulated node

        Args:
            new_name (str):
        """
        curr_name = self.name
        self._dep_node.setName(new_name)
        apiundo.commit(
            undo=lambda: self._dep_node.setName(curr_name),
            redo=lambda: self._dep_node.setName(new_name)
        )

    # operator overloads
    def __str__(self):
        """string representation of node. returns self.full_name

        Returns:
            str:
        """
        return self.full_name
    def __getitem__(self, attr: str):
        """gets the attr of a node encapsulated in the Attr class

        Args:
            attr (str): attribute name

        Returns:
            Attr: returns Attr class of node"s attribute
        """
        attr_instance = None
        try:
            attr_instance = self._get_cached_attr(attr)
        except:
            raise RuntimeError("{0}.{1} attribute not found".format(self.name, attr))

        return attr_instance
    def __setitem__(self, attr: str, new_value):
        """sets the attribute"s value of a given node

        Args:
            attr (str): attribute name
            new_value (_type_): value to set attribute to
        """
        attr = self.__getitem__(attr)
        attr.set(new_value)

    def _get_cached_attr(self, attr):
        """checks to see if attr is cached
        gets the attr of a node encapsulated in the Attr class

        Args:
            attr (str): attribute name

        Returns:
            Attr: returns Attr class of nodes attribute
        """
        if attr not in self.__attr_cache.keys():
            self.__attr_cache[attr] = Attr(self, utils.get_plug(
                self._dep_node, attr))
        return self.__attr_cache[attr]
    
    def __eq__(self, other):
        """Returns True if the other object is of type Node and the 
        other's plug matches self's plug

        Args:
            other (_type_): 

        Returns:
            bool: 
        """
        if isinstance(other, Node):
            if str(self) == str(other):
                return True
            
        return False
    def __hash__(self):
        return hash(self.full_name)

class Container(Node):
    def __init__(self, node):
        super(Container, self).__init__(node)

    def get_nodes(self):
        child_nodes = cmds.container(str(self), query=True, nodeList=True)
        if child_nodes:
            return [Node(x) for x in child_nodes]

    def lock(self, proprigate=False):
        if proprigate:
            container_list = []
            current_container = self
            while current_container is not None:
                container_list.append(current_container)
                current_container = current_container.get_container()
        else:
            container_list = [self]

        for container in container_list:
            cmds.lockNode(str(container), lock=True, lockUnpublished=True)

    def unlock(self, proprigate=False):
        if proprigate:
            container_list = []
            current_container = self
            while current_container is not None:
                container_list.append(current_container)
                current_container = current_container.get_container()

        else:
            container_list = [self]

        container_list = container_list[::-1]
        for container in container_list:
            cmds.lockNode(str(container), lock=False, lockUnpublished=False)

    def __enter__(self):
        self.unlock()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.lock()

    def add_nodes(self, *args, include_network=False, include_hierarchy_above=False, include_hierarchy_below=False, force=False):
        args = [str(x) for x in args]
        conversionNodes = []
        for node in args:
            node_conversionNodes = cmds.listConnections(node, source=True, destination=True)
            node_conversionNodes = cmds.ls(node_conversionNodes, type='unitConversion')
            conversionNodes.extend(node_conversionNodes)
        args.extend(conversionNodes)
        cmds.container(str(self), addNode=args, edit=True, iha=include_hierarchy_above, ihb=include_hierarchy_below, inc=include_network, force=force)

    def get_container(self):
        containers = cmds.container(str(self),  query=True, parentContainer=True)
        if containers is not None:
            return Container(containers[0])
        return containers

    def remove_nodes(self, *args):
        args = [str(x) for x in args]
        remove_list = args.copy()
        for node in args:
            curr_remove_nodes = cmds.listRelatives(node, allDescendents=True)
            if curr_remove_nodes is not None:
                remove_list.extend(curr_remove_nodes)
        cmds.container(str(self), edit=True, removeNode=remove_list, force=True)

    def publish_attr(self, attr, attr_bind_name:str):
        if attr.node in self.get_nodes():
            cmds.container(str(self), edit=True, publishAndBind=[str(attr), attr_bind_name])
        else:
            raise RuntimeError("{} is not a node of container {}".format(attr.node, str(self)))

    def unpublish_attr(self, attr):
        cmds.container(str(self), edit=True, unbindAndUnpublish=str(attr))

    def get_published_attr_map(self):

        m_object = self.mobject
        if m_object.hasFn(om2.MFn.kContainer):
            mfn_container = om2.MFnContainerNode(m_object)
            plug_list, attr_list = mfn_container.getPublishedPlugs()
            return {x:Attr(None, y) for x, y in zip(attr_list, plug_list)}
        return {}

    def get_published_attrs(self):
        m_object = self.mobject
        if m_object.hasFn(om2.MFn.kContainer):
            mfn_container = om2.MFnContainerNode(m_object)
            plug_list, _ = mfn_container.getPublishedPlugs()
            return [Attr(None, x) for x in plug_list]
        return []

    def get_external_connection_list(self):
        container_nodes = self.get_nodes()
        connection_list = []

        external_connection_list = cmds.container(str(self), query=True, connectionList=True)
        if external_connection_list is None:
            external_connection_list = []
        for attr in external_connection_list:
            curr_attr = Attr(None, attr)

            if curr_attr.attr_type not in ["compound", "double3", "double2"] and curr_attr.__len__() is not None:
                curr_attr = curr_attr[0]

            input_connections = curr_attr.get_as_dest_connection_list()
            output_connections = curr_attr.get_as_source_connection_list()
            for input in input_connections:
                if input.node in container_nodes:
                    connection_list.append((input, curr_attr))
            for output in output_connections:
                if output.node in container_nodes:
                    connection_list.append((curr_attr, output))
        return connection_list

    def get_child_containers(self, all=False):
        sub_containers = [Container(x) for x in self.get_nodes() if x.node_type == "container"]
        return_child_containers = []
        if not all:
            return sub_containers
        for container in sub_containers:
            container = Container(container)
            return_child_containers.append(container)
            return_child_containers.extend(container.get_child_containers(all=all))
        return return_child_containers

    @classmethod
    def create_node(cls, name:str=None):
        node = super(Container, cls).create_node("container", name)
        node.__class__ = Container
        return node

    def __setitem__(self, attr: str, new_value):
        publish_attr_map = self.get_published_attr_map()
        if attr in publish_attr_map.keys():
            attr = publish_attr_map[attr]
            attr.set(new_value)
        else:
            super().__setitem__(attr, new_value)

    def __getitem__(self, attr: str):
        publish_attr_map = self.get_published_attr_map()
        if attr in publish_attr_map.keys():
            return publish_attr_map[attr]
        if attr.find("[") != -1 or attr.find(".") != -1:
            if attr.find("[") != -1:
                parent_attr, back_attrs = attr.split("[", 1)
                index, back_attrs = back_attrs.split("]", 1)
                if parent_attr in publish_attr_map.keys():
                    return_attr = publish_attr_map[parent_attr][int(index)]
                    if back_attrs != "":
                        return return_attr[back_attrs]
                    return return_attr
            else:
                parent_attr, back_attrs = attr.split(".", 1)
                if parent_attr in publish_attr_map.keys():
                    return publish_attr_map[parent_attr][back_attrs]
        return super().__getitem__(attr)
        
    
class AttrIter():
    """
    Iterator for attr. Iterates through child attrs at a depth equal
    to max depth
    """
    """
    Attributes:
    parent_attr (Attr): 
    current_attr (Attr): current child of parent attr
    depth (int): depth of search
    curr_index (int): index of the current elements
    max_depth (int): max depth to stop at (and include)

    """
    def __init__(self, attr, max_depth:int=-1):
        """initializes data to iterate through AttrIter

        Args:
            attr (Attr): starting attribute to iterate through
            max_depth (int, optional): max depth to search of attr. 
            Defaults to -1.
        """
        self.__original_attr__ = attr
        self.__current_attr__ = None
        self.__max_depth__ = max_depth
        self.__depth__ = 0

    def _reached_max_depth(self):
        return self.__depth__ + 1 > self.__max_depth__ and self.__max_depth__ >= 0
    def __next__(self):
        """gets next attr

        Raises:
            StopIteration: stops the iterator

        Returns:
            Attr: 
        """
        # when to stop iteration
        if not self.__original_attr__.has_children() and len(self.__original_attr__) > 0:
            raise StopIteration
        

        
        # to get the starting one
        if self.__current_attr__ is None:
            self.__current_attr__ = self.__original_attr__[0]
            self.__depth__ += 1
            return self.__current_attr__
        
        # if attr has children
        elif self.__current_attr__.has_children() and len(self.__current_attr__) > 0 and not self._reached_max_depth():
            self.__current_attr__ = self.__current_attr__[0]
            self.__depth__ += 1
            return self.__current_attr__
        
        # if at the end of list of attributes
        elif self.__current_attr__.index + 1 >= len(self.__current_attr__.parent):
            for x in range(100):
                if self.__current_attr__.index + 1 >= len(self.__current_attr__.parent):
                    self.__current_attr__ = self.__current_attr__.parent
                    self.__depth__ -= 1
                    if self.__current_attr__ == self.__original_attr__:
                        raise StopIteration
                    continue

            index = self.__current_attr__.index
            parent = self.__current_attr__.parent
            self.__current_attr__ = parent[index + 1]
            return self.__current_attr__
            

        # go to sibling
        elif self.__current_attr__.index + 1 < len(self.__current_attr__.parent):
            index = self.__current_attr__.index
            parent = self.__current_attr__.parent
            self.__current_attr__ = parent[index + 1]
            return self.__current_attr__
        
        raise StopIteration
    def __iter__(self):
        """returns self as it"s iterator

        Returns:
            AttrIter: returns itself
        """
        return self
    
class Attr():
    """
    A Class encapsulating an attribute
    """
    """
    Attributes:
    dep_node (Node): node that"s the parent of this attr
    plug (str): plug of the given attribute
    name(str): attr name with node name ie. node.attr
    attr_name(str): attr name ie. attr
    attr_type(str): plug"s attribute type
    index(int): the index of the attribute. returns -1 if not a child of 
    another attribute
    parent(Attr): returns the parent of the attribute. returns None if
    not a child of another attribute
    """
    

    __attr_data_map__ = {
        "kDoubleAngleAttribute":    {"get": lambda x: x.asMAngle().asDegrees(),     "set": lambda x, y: x.setDouble(om2.MAngle(y, 2).asRadians())},
        "kDoubleLinearAttribute":   {"get": lambda x: x.asDouble(),                 "set": lambda x, y: x.setDouble(y)},
        "kEnumAttribute":           {"get": lambda x: x.asInt(),                    "set": lambda x, y: x.setInt(y)},
        #"kMatrixAttribute":         {"get": None,                                   "set": None},
        #"kMessageAttribute":        {"get": None,                                   "set": None},
        "kNumericAttribute":        {"get": lambda x: x.asDouble(),                 "set": lambda x, y: x.setDouble(y)},
        #"kTypedAttribute":          {"get": None,                                   "set": None},
    }
    
    def __init__(self, node:Node, attr: Union[om2.MPlug, str]):
        """initializes Attr data

        Args:
            node (Node): plug's node
            attr (Union[om2.MPlug, str]):
            depth (int): used for iterating through Attr
        """
        self.node = node
        
        self.plug = utils.get_plug(None, attr)
        if self.plug is None:
            cmds.error("{} attribute\"s plug not found".format(attr))

        if self.node == None:
            self.node = Node(self.plug)
        if self.node == None:
            cmds.error("{} attribute\"s node not found".format(attr))

    @property
    def name(self):
        return "{}.{}".format(self.node.full_name, self.attr_name)
    @property
    def attr_name(self):
        return str(self.plug).split(".", 1)[1]
    @property
    def attr_short_name(self):
        return str(self.plug.partialName())
    @property
    def attr_type(self):
        if cmds.getAttr(str(self), type=True) == "TdataCompound":
            return "compound"
        return cmds.getAttr(str(self), type=True)

        # return self._plug_attr_type(self.plug)
    @property
    def value(self):
        return self._get_value(self.plug)
    @property
    def index(self):
        if self.plug.isElement:
            return self.plug.logicalIndex()
        elif self.plug.isChild:
            parent_plug = self.plug.parent()
            child_plug_list = [parent_plug.child(x) for x in 
                               range(parent_plug.numChildren())]
            child_attr_dict = {x.name().split(".", 1)[1]: i for i, x in 
                               enumerate(child_plug_list)}
            return child_attr_dict[self.attr_name]
        return -1
    @property
    def parent(self):
        if self.plug.isElement:
            return Attr(self.node, self.plug.array())
        elif self.plug.isChild:
            return Attr(self.node, self.plug.parent())
        else:
            return None
    # helper functions
    @staticmethod
    def _plug_attr_type(plug: om2.MPlug):
        """Get"s a plug"s attribute type

        Args:
            plug (om2.MPlug):

        Returns:
            str:
        """
        return plug.attribute().apiTypeStr
    def disconnect(self, children:bool=False, asSource:bool=False, asDestination:bool=True):
        """Disconnects attributes

        Args:
            children (bool, optional): if true disconnects children. Defaults to False.
            asSource (bool, optional): if true disconnects everything it's connected to. Defaults to False.
            asDestination (bool, optional): if true disconnects everything connected to it. Defaults to True.
        """
        def redo(connection_pairs):
            dgMod = om2.MDGModifier()
            for connection in connection_pairs:
                dgMod.disconnect(connection[0], connection[1])
            dgMod.doIt()
        def undo(connection_pairs):
            dgMod = om2.MDGModifier()
            for connection in connection_pairs:
                dgMod.connect(connection[0], connection[1])
            dgMod.doIt()
        
        connection_pairs = []
        if children and self.has_children():
            for child_attr in self:
                if asSource:
                    for attr in child_attr.get_connection_list(True, False):
                        connection_pairs.append((child_attr.plug, attr.plug))
                if asDestination:
                    for attr in child_attr.get_connection_list(False, True):
                        connection_pairs.append((attr.plug, child_attr.plug))
        if asSource:
            for attr in self.get_connection_list(True, False):
                connection_pairs.append((self.plug, attr.plug))
        if asDestination:
            for attr in self.get_connection_list(False, True):
                connection_pairs.append((attr.plug, self.plug))
        
        if connection_pairs == []:
            cmds.warning("nothing to disconnect from {0}".format(str(self.plug)))
            return
        locked = self.is_locked()
        if locked:
            self.set_locked(False)
        redo(connection_pairs)
        apiundo.commit(
            redo = lambda: redo(connection_pairs),
            undo = lambda: undo(connection_pairs)
        )
        if locked:
            self.set_locked(True)
    
    def has_source_connection(self):
        return self.is_connected()

    def get_plug(self):
        return self.plug
    def is_connected(self, asSource=False, asDestination=True):
        if self.get_connection_list(asSource, asDestination) == []:
            return False
        return True

    def get_connection_list(self, asSource: bool, asDestination: bool):
        """Get connections of attr

        Args:
            source (bool): get connections with attr as source
            destination (bool): get connections with attr as destination

        Returns:
            om2.MPlug:
        """
        return [Attr(None, x) for x in self.plug.connectedTo(asDestination, asSource)]
    def get_as_dest_connection_list(self):
        """Gets a list of all the Attr that are connected to this Attr

        Returns:
            list(Attr): 
        """
        return self.get_connection_list(False, True)
    def get_as_source_connection_list(self):
        """Gets a list of all the Attr that this Attr is connected to (this 
        Attr being the source)

        Returns:
            list(Attr): 
        """
        return self.get_connection_list(True, False)
    # functions
    def set(self, value):
        """Tries to set value of plug but resets to previous values if 
        unsuccessful

        Args:
            value ():
        """
        orig_val = self.value
        def do(plug, value):
            if isinstance(value, Attr):
                value = value.value
            self._set_value(plug, value)
        
        try:
            do(self.plug, value)
        except ValueError:
            self._set_value(self.plug, orig_val)
            cmds.warning("set info, mismatch {} was not changed".format(str(self.plug)))
        except:
            self._set_value(self.plug, orig_val)
            cmds.warning("error occured when setting {} was not changed".format(str(self.plug)))
        
        apiundo.commit(
            redo = lambda: do(self.plug, value),
            undo = lambda: do(self.plug, orig_val)
        )
    def set_locked(self, lock):
        cmds.setAttr(str(self), lock=lock)
    def is_locked(self):
        return cmds.getAttr(str(self), lock=True)
    def set_keyable(self, keyable):
        cmds.setAttr(str(self), edit=True, keyable=keyable)
    def is_keyable(self):
        return cmds.getAttr(str(self), keyable=True)
    def set_alias(self, alias):
        cmds.aliasAttr(alias, self.name)
    def has_attr(self, sub_attr):
        try:
            self[sub_attr]
            return True
        except:
            return False
    def _set_value(self, plug: om2.MPlug, value):
        """Sets value on plug. is recurrsive when plug is has children or
        elements. 
        Limitation if a list if given that's smaller than the
        number of values in the node's array then it won't be resized and
        the old values stay

        Args:
            plug (om2.MPlug): plug to get value from
            value ():

        Raises:
            ValueError: if number of children is mismatched by length of
            value
        """
        attr_type = cmds.getAttr(str(self), type=True)
        locked = self.is_locked()
        if locked:
            self.set_locked(False)
        if plug.isArray:
            for index in range(len(value)):
                curr_plug = plug.elementByLogicalIndex(index)
                self._set_value(curr_plug, value[index])
        elif plug.isCompound:
            num_plug_element_list = plug.numChildren()
            if num_plug_element_list != len(value):
                raise ValueError()
            for index in range(num_plug_element_list):
                curr_plug = plug.child(index)
                self._set_value(curr_plug, value[index])
        elif attr_type == "string":
            cmds.setAttr(str(self), value, type="string")
        elif attr_type == "matrix":
            cmds.setAttr(str(self), value, type='matrix')
        elif self._plug_attr_type(plug) in self.__attr_data_map__.keys():
            self.__attr_data_map__[self._plug_attr_type(plug)]["set"](plug, value)
        else:
            cmds.setAttr(str(self), value)

        if locked:
            self.set_locked(True)

    def _get_value(self, plug: om2.MPlug):
        """Gets value on plug. is recurrsive when plug is has children or
        elements

        Args:
            plug (om2.MPlug): plug to get value(s) from

        Returns:
        """
        
        if plug.isArray:
            plug_list = [plug.elementByLogicalIndex(i) for i in range(plug.numElements())]
            plug_list = [self._get_value(x) for x in plug_list]
            return plug_list
        elif plug.isCompound:
            plug_list = [plug.child(i) for i in range(plug.numChildren())]
            plug_list = [self._get_value(x) for x in plug_list]
            return tuple(plug_list)
        elif self._plug_attr_type(plug) in self.__attr_data_map__.keys():
            return self.__attr_data_map__[self._plug_attr_type(plug)]["get"](plug)
        # else:
            # attr_type = cmds.getAttr(str(self), type=True)
        return_value = cmds.getAttr(str(self))
            # if attr_type == "matrix":
            #     return_value = [return_value[i:i+4] for i in range(0, len(return_value), 4)]
        return return_value
    def __eq__(self, other):
        """Returns True if the other object is of type Attr and the 
        other's plug matches self's plug

        Args:
            other (_type_): 

        Returns:
            bool: 
        """
        if isinstance(other, Attr):
            return str(self) == str(other)
        return False
    
    def __hash__(self):
        return hash(str(self))
    
    # Operator overloads connections and disconnections as well as get item
    def __str__(self):
        """Return self.name

        Returns:
            str:
        """
        return self.name
    
    def __rshift__(self, other):
        """Tries to connect this attr to the other

        ie. this[attr] >> other[attr]

        Args:
            other ():
        """
        if isinstance(other, Attr):
            source_locked = self.is_locked()
            dest_locked = other.is_locked()
            if source_locked:
                self.set_locked(False)
            if dest_locked:
                other.set_locked(False)
            utils.connect_plugs(self.plug, other.plug)
            if source_locked:
                self.set_locked(True)
            if dest_locked:
                other.set_locked(True)
        else:
            cmds.error("{} not class Attr".format(other))
    def __lshift__(self, other):
        """Tries to connect the other attr to this attr

        ie. this[attr] << other[attr]

        Args:
            other ():
        """
        if isinstance(other, Attr):
            source_locked = other.is_locked()
            dest_locked = self.is_locked()
            if source_locked:
                other.set_locked(False)
            if dest_locked:
                self.set_locked(False)
            utils.connect_plugs(other.plug, self.plug)
            if source_locked:
                other.set_locked(True)
            if dest_locked:
                self.set_locked(True)
        else:
            cmds.error("{} not class Attr".format(other))
    def __invert__(self):
        """Disconnects anything to this attribute with this attribute
        as the destination

        Returns:
            Attr: returns self
        """
        self.disconnect()
        return self
    def __getitem__(self, attr: str):
        """Get a child attribute of this attr

        Args:
            attr (str): child attr name

        Returns:
            Attr:
        """
        full_attr_name = self.attr_name
        if self.plug.isArray:
            full_attr_name = "{0}[{1}]".format(full_attr_name, attr)
        elif self.plug.isCompound:
            full_attr_name = "{0}.{1}".format(full_attr_name, attr)

        if full_attr_name in self.node.get_attr_cache().keys():
            return self.node.get_attr_cache()[full_attr_name]

        plug = utils.get_plug(self.plug, attr)
        return Attr(self.node, plug)
    
    def __setitem__(self, attr: str, new_value):
        """Gets the new attribute and sets a child attribute"s value to new value

        Args:
            attr (str): child attr name
            new_value (): value to set attr to
        """
        attr = self.__getitem__(attr)
        if isinstance(new_value, Attr):
            new_value = new_value.value
        attr.set(new_value)

    def has_children(self):
        """tell if attribute has children
        """
        return self.plug.isArray or self.plug.isCompound

    def __len__(self):
        """Gets length of child attributes, returns -1 if there are no children

        Returns:
            int:
        """
        if self.plug.isArray:
            return self.plug.numElements()
        elif self.plug.isCompound:
            return self.plug.numChildren()
    # Iterator overloads
    def __iter__(self):
        """Gets the iterator object

        Raises:
            TypeError: if attribute is not a compound or array

        Returns:
            AttrIter: 
        """
        if not self.has_children():
            raise TypeError("attribute is not of type compound or array")
        iter_obj = AttrIter(self)
        return iter_obj
            
    # Math Operator Overloads
    def _base_math_operators(self, x, y, function):
        """Takes 2 inputs, extracts the values and preforms the given 
        function on those 2 values

        Args:
            x (_type_): value
            y (_type_): value
            function (_type_): function to compute value

        Returns:
            _type_: 
        """
        if isinstance(x, Attr):
            x = x.value
        if isinstance(y, Attr):
            y = y.value
        return function(x, y)
    def __add__(self, other):
        """Add the value of the object with the object on the right
        side of the operator

        Returns:
            value: calculated value
        """
        return self._base_math_operators(self, other, lambda x, y: x + y)
    def __radd__(self, other):
        """Add the value of the object with the object on the left
        side of the operator

        Returns:
            value: calculated value
        """
        return self._base_math_operators(self, other, lambda x, y: y + x)
    def __sub__(self, other):
        """Subtract the value of the object with the object on the right
        side of the operator

        Returns:
            value: calculated value
        """
        return self._base_math_operators(self, other, lambda x, y: x - y)
    def __rsub__(self, other):
        """Subtract the value of the object with the object on the left
        side of the operator

        Returns:
            value: calculated value
        """
        return self._base_math_operators(self, other, lambda x, y: y - x)
    def __mul__(self, other):
        """Multiply the value of the object with the object on the right
        side of the operator

        Returns:
            value: calculated value
        """
        return self._base_math_operators(self, other, lambda x, y: x * y)
    def __rmul__(self, other):
        """Multiply the value of the object with the object on the left
        side of the operator

        Returns:
            value: calculated value
        """
        return self._base_math_operators(self, other, lambda x, y: y * x)
    def __truediv__(self, other):
        """Divides the value of the object with the object on the left
        side of the operator

        Returns:
            value: calculated value
        """
        return self._base_math_operators(self, other, lambda x, y: x / y)
    def __rtruediv__(self, other):
        """Divides the value of the object with the object on the right
        side of the operator

        Returns:
            value: calculated value
        """
        return self._base_math_operators(self, other, lambda x, y: y / x)

    

    # TODO: 
        # node
            # disconnect attr from other side ----------------
            # get_shapes ----------------
            # get_children ----------------
            # get_parent ----------------
            # has_attr ----------------
            
            # get non default value
        
            # node functions
        
            # rewrite iterator (to include parent plugs)
            # get connections (get if attribute is connected to something)
        
        # skin cluster

        # container

