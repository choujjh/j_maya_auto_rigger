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
        output_node = install_node["outputNode"].get_connection_list(asSource=True, asDestination=False)[0].node
        return output_node

    def lock(self):
        super(ComponentContainer, self).unlock(proprigate=True)
        try:
            input_node = self.get_input_node()
            output_node = self.get_output_node()
            install_node = self.get_install_node()

            self.publish_node_dynamic_attrs(self.get_input_node())
            self.publish_node_dynamic_attrs(self.get_output_node())

            self.add_node([self.get_input_node(), self.get_output_node(), self.get_install_node()])

            self.lock_publish_attr()
            
            for node in self.get_children():
                if node not in [input_node, output_node, install_node]:
                    if not node.has_attr("parent"):
                        node.add_attr("parent", type="message")
                    install_node["otherNodes"] >> node["parent"]

        finally:
            super(ComponentContainer, self).lock(proprigate=True)

    def unlock(self):
        # add parent attr and connect
        super(ComponentContainer, self).unlock(proprigate=True)
        self.unlock_publish_attr()

    def lock_publish_attr(self):
        install_node = self.get_install_node()
        if not install_node.has_attr("publishAttrs"):
            return
        publish_attr_connection_list = []
        
        for attr in install_node["publishAttrs"]:
            publish_attr_connection_list.extend(attr.get_dest_connection_list())

        non_add_node_list = [self.get_input_node(), self.get_output_node(), install_node]
        current_published_list = self.get_published_attrs()
        for attr in publish_attr_connection_list:
            node = attr.node
            if node not in non_add_node_list and attr not in current_published_list:
                self.publish_attr(attr, "{}_{}".format(node.name, attr.attr_name))

        for attr in install_node["publishAttrs"]:
            ~attr
        install_node.delete_attr("publishAttrs")

    def unlock_publish_attr(self):
        install_node = self.get_install_node()
        input_node = self.get_input_node()
        output_node = self.get_output_node()

        if not install_node.has_attr("publishAttrs"):
            install_node.add_attr("publishAttrs", type="message", multi=True)

        publish_attr_dict = self.get_published_attr_map()
        for index, attr in enumerate(publish_attr_dict.keys()):
            if publish_attr_dict[attr].node not in [input_node, output_node, install_node]:
                if install_node.has_attr("publishAttr"):
                    publish_attr_dict[attr] >> install_node["publishAttr"][index]

    def publish_node_dynamic_attrs(self, node:nw.Node):
        published_attrs = self.get_published_attrs()
        for attr in node.get_dynamic_attribute_list():
            if attr not in published_attrs and attr.attr_name != "parent":
                self.publish_attr(attr, "{}_{}".format(node.name, attr.attr_name))

    def install_parent():
        pass

class Component:
    class ComponentTypes(Enum):
        setup_component = "setup_component"
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
        self.container_node.add_node([input_node, self.install_node, output_node])

        # publish install attrs
        self._publish_install_attrs()

        self.container_node.lock()
        self.container_node.unlock()

    def publish(self, container_node):
        pass

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