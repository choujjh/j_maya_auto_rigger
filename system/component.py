import maya.cmds as cmds
import utils.node_wrapper as nw
from enum import Enum
from utils.node_wrapper import Container

class ComponentContainer(Container):
    def __init__(self, node):
        super(ComponentContainer, self).__init__(node)

    @classmethod
    def create_node(cls, name:str=None):
        node = super(ComponentContainer, cls).create_node(name)
        node.__class__ = ComponentContainer
        return node

    def get_install_node(self):
        attr = self["installNode"]
        install_node = attr.get_connection_list(asSource=True, asDestination=False)[0].node
        return install_node
    
    def get_input_node(self):
        install_node = self.get_install_node()
        input_node = install_node["inputNode"].get_connection_list(asSource=True, asDestination=False)[0].node
        return input_node


    def get_output_node(self):
        install_node = self.get_install_node()
        output_node = install_node["inputNode"].get_connection_list(asSource=True, asDestination=False)[0].node
        return output_node

    def lock(self):
        # publish attrs on input and output and publishAttrs
        # delete publishAttrs attr

        try:

            print(self.get_install_node())
            print(self.get_input_node())
            print(self.get_output_node())
        except:
            pass
        

        super(ComponentContainer, self).lock()

    def unlock(self):
        # add parent attr and connect
        
        try:
            print(self.get_published_attributes())

            print(self.get_install_node())
            print(self.get_input_node())
            print(self.get_output_node())
        except:
            pass

        super(ComponentContainer, self).lock()

class Component:
    class ComponentTypes(Enum):
        anim_component = "anim_component"
        component_container = "container_component"
        control = "control_component"
        dynamic = "dynamic_component"
        freeze = "freeze_component"
        
        @classmethod
        def maya_enum_str(cls):
            return_str = ""
            num_enums = len(cls)
            for i, enum in enumerate(cls):
                return_str += enum.value
                if i < num_enums:
                    return_str += ":"
            return return_str
        @classmethod
        def get(cls, index):
            for i, curr_enum in enumerate(cls):
                if i == index:
                    return curr_enum
                
        @ classmethod
        def get_component_type_names(cls):
            return [x.value for x in cls]


    def __init__(self):
        self.install_node = None
        pass

    def _add_install_attrs(self):
        self.install_node.add_attr("parent", type="message")
        self.install_node.add_attr("containerChildren", type="compound", numberOfChildren=3)
        self.install_node.add_attr("inputNode", type="message", parent="containerChildren")
        self.install_node.add_attr("outputNode", type="message", parent="containerChildren")
        self.install_node.add_attr("otherNodes", type="message", parent="containerChildren")
        self.install_node.add_attr("containerNode", type="message")

        self.install_node.add_attr("moduleType", attributeType="enum", enumName=Component.ComponentTypes.maya_enum_str())
        self.install_node.add_attr("moduleName", type="string")
        self.install_node.add_attr("InstanceName", type="string")
        self.install_node.add_attr("Version", attributeType="enum", enumName="")
        self.install_node.add_attr("publishAttrs", type="message", multi=True)

    def _publish_install_attrs(self):
        add_attrs = ["moduleType", "moduleName", "InstanceName", "Version"]
        for attr in add_attrs:
            self.container_node.publish_attr(self.install_node[attr], attr)

    def install(self):
        input_node = nw.Node.create_node("network", name="input")
        self.install_node = nw.Node.create_node("network", name="install")
        output_node = nw.Node.create_node("network", name="output")

        self.container_node = ComponentContainer.create_node(name="component_container")

        # adding install attributes
        self._add_install_attrs()

        # adding input and output attributes
        input_node.add_attr("parent", type="message")
        output_node.add_attr("parent", type="message")

        # container attributes
        self.container_node.add_attr("installNode", type="message")

        # connect to children
        self.container_node["installNode"] >> self.install_node["containerNode"]
        self.install_node["inputNode"] >> input_node["parent"]
        self.install_node["outputNode"] >> output_node["parent"]

        # add to container
        self.container_node.add_children([input_node, self.install_node, output_node])

        # publish install attrs
        self._publish_install_attrs()

        self.container_node.lock()
        self.container_node.unlock()

    def publish(self, container_node):
        pass
        # with container_node:
            
        #     container_children = container_node.get_children()
        #     install_node = None
        #     input_node = None
        #     output_node = None
            
        #     for node in container_children:
        #         if str(node).endswith("install"):
        #             install_node = node
        #         elif str(node).endswith("input"):
        #             input_node = node
        #         elif str(node).endswith("output"):
        #             output_node = node

        #     # error checking
        #     if install_node is None:
        #         raise RuntimeError("install node does not exist in {0}".format(str(container_node)))
        #     if input_node is None:
        #         raise RuntimeError("input node does not exist in {0}".format(str(container_node)))
        #     if output_node is None:
        #         raise RuntimeError("output node does not exist in {0}".format(str(container_node)))
        #     if install_node["moduleType"].value == "":
        #         raise RuntimeError("{0} attribute is empty".format(install_node["moduleType"]))
        #     if install_node["nodePrefix"].value in [None, ""]:
        #         cmds.warning("{0} attribute is empty".format(install_node["moduleType"]))
            
        #     # add other nodes
        #     container_node.add_children([input_node, install_node, output_node])
        #     container_children = container_node.get_children()

        #     # add published attrs
        #     publish_attr_set = set()
        #     for attr in install_node["publishAttrs"]:
        #         connection_list = attr.get_dest_connection_list()
        #         for connection in connection_list:
        #             # if connection.node.type == "container":
        #             #     publish_attr_set.add(("{0}".format(connection.attr_short_name), str(connection)))
        #             # publish_attr_set.add((connection, "{0}_{1}".format(str(connection.node), connection.attr_short_name)))
        #             publish_attr_set.add((connection, connection.name.replace(".", "_")))

        #     install_node.delete_attr("publishAttrs")

        #     for attr, attr_bind_name in publish_attr_set:
        #         container_node.publish_attr(attr, attr_bind_name)

        #     for node in container_children:
        #         if not node.has_attr("parent") and node != install_node:
        #             node.add_attr("parent", type="message")
        #             install_node["other"] >> node["parent"]   

        #     install_exclude_list = ["container_children", "input", "output", "other", "publishAttrs"]
        #     for attr in install_node.get_dynamic_attribute_list():
        #         if attr.attr_name not in install_exclude_list:
        #             container_node.publish_attr(attr, (attr.attr_name))

        #     for attr in input_node.get_dynamic_attribute_list():
        #         if attr.attr_name != "parent":
        #             container_node.publish_attr(attr, "input_{0}".format(attr.attr_name))

        #     for attr in output_node.get_dynamic_attribute_list():
        #         if attr.attr_name != "parent":
        #             container_node.publish_attr(attr, "output_{0}".format(attr.attr_name))
            
        #     node_prefix = install_node["nodePrefix"].value
        #     if node_prefix == None:
        #         node_prefix=""
        #     for node in container_children:
        #         self.rename_node(node, node_prefix) 


        #     container_node.rename(self.new_name_convention("container", node_prefix))    

    # TODO
    # how to handle container attr being published
    # how to handle alreayd named nodes in published attributes
    def rename_node(self, node, node_prefix):
        name = node.name
        if name.find("__") != -1:
            name = name.rsplit("__")[-1]

        new_name = self.new_name_convention(name, node_prefix)

        node.rename(new_name)

    def new_name_convention(self, node_name, node_prefix):
        new_name = "{}__{}".format(node_prefix, node_name)
        return new_name

    def build(self):
        pass

    def freeze(self):
        pass
    def unfreeze(self):
        pass

class Control(Component):
    pass