import maya.cmds as cmds

import utils.node_wrapper as nw
import utils.enum as utils_enum
import utils.utils as utils
import system.data as data

import re

def get_component(container_node):
    if container_node is None:
        return None
    if container_node.has_attr("componentClass"):
        component_class = utils.string_to_class(container_node["componentClass"].value)
        return component_class(container_node)


class Component:
    component_type = utils_enum.ComponentTypes.component
    is_rebuildable = False
    root_transform_name = ""
    has_inst_name_attr = False
    has_side_attr = False
    side_attr_default = utils_enum.CharacterSide.none

    
    @property
    def instance_namespace(self):
        namespace = utils.camel_to_snake(self.class_short_name)
        if self.io_node is None or not self.io_node.has_attr("componentInstName"):
            return namespace
        instance_name = self.io_node["componentInstName"].value
        if instance_name is not None and instance_name.find(".") != -1:
            instance_name = instance_name.rsplit(".", 1)[-1]
        if self.io_node.has_attr(data.HierDataAttrNames.hier_side.value):
            index =self.io_node[data.HierDataAttrNames.hier_side.value].value
            if index > 0:
                side = utils_enum.CharacterSide.get(index).value
                instance_name = "{}_{}".format(side, instance_name)
        if instance_name is not None and instance_name != "":
            return "{}__{}".format(instance_name, namespace)
        return namespace

    @property
    def mirror_instance_namespace(self):
        namespace = utils.camel_to_snake(self.class_short_name)
        if self.io_node is None or not self.io_node.has_attr("componentInstName"):
            return namespace
        instance_name = self.io_node["componentInstName"].value
        if instance_name is not None and instance_name.find(".") != -1:
            instance_name = instance_name.rsplit(".", 1)[-1]
        if self.io_node.has_attr(data.HierDataAttrNames.hier_side.value):
            index =self.io_node[data.HierDataAttrNames.hier_side.value].value
            if index > 0:
                side = utils_enum.CharacterSide.opposite(utils_enum.CharacterSide.get(index)).value
                instance_name = "{}_{}".format(side, instance_name)
        if instance_name is not None and instance_name != "":
            return "{}__{}".format(instance_name, namespace)
        return namespace

    @property
    def transform_node(self):
        if self.container_node is not None and self.container_node.has_attr("rootTransformNode"):
            return utils.get_first_connected_node(self.container_node["rootTransformNode"], as_source=True)
        
    @property
    def subcomponent_grp_node(self):
        if self.container_node is not None and self.container_node.has_attr("subComponentGrp"):
            return utils.get_first_connected_node(self.container_node["subComponentGrp"], as_source=True)

    @property
    def io_node(self):
        if self.container_node is not None:
            return utils.get_first_connected_node(self.container_node[self._io_name.connect_attr_name], as_source=True)
    
    @property
    def class_name(self):
        return utils.class_type_to_str(type(self))
    
    @property
    def class_short_name(self):
        return self.class_name.split(".")[-1]
    
    @property
    def mirror_dest_container(self):
        if self.container_node.has_attr("mirrorSource"):
            mirror_source_node = utils.get_first_connected_node(self.container_node["mirrorSource"], as_source=True, as_dest=False)
            if mirror_source_node.has_attr("mirrorDest"):
                return mirror_source_node
            else:
                return utils.get_first_connected_node(mirror_source_node["mirrorComponent"], as_source=True, as_dest=False)
            
    @property
    def mirror_source_container(self):
        if self.container_node.has_attr("mirrorDest"):
            mirror_dest_node = utils.get_first_connected_node(self.container_node["mirrorDest"], as_source=False, as_dest=True)
            if mirror_dest_node.has_attr("mirrorSource"):
                return mirror_dest_node
            else:
                return utils.get_first_connected_node(mirror_dest_node["mirrorComponent"], as_source=False, as_dest=True)

    @property
    def has_parent(self):
        io_node = self.io_node
        if io_node.has_attr[data.HierDataAttrNames.hier_parent.value] and io_node.has_attr[data.HierDataAttrNames.hier_parent_init.value]:
            return io_node.has_attr[data.HierDataAttrNames.hier_parent.value].has_source_connection() and io_node.has_attr[data.HierDataAttrNames.hier_parent_init.value].has_source_connection()
        return False

    def get_component_ui_attrs(self):
        return []

    def __init__(self, container_node=None, parent_container_node=None):
        self.container_node = container_node
        self.parent_container_node = parent_container_node

        self._io_name = data.IOName

    def insert_component(self, component, transform_parent=None, transform_relative=True, build=True, **component_kwargs):
        if self.container_node is None:
            cmds.warning("unable to insert component {}".format(Component.__name__))

        current_namespace = utils.Namespace.get_namespace(str(self.container_node))
        cmds.namespace(setNamespace=":")

        if component_kwargs == {}:
            insert_component_inst = component(parent_container_node=self.container_node)
        else:
            insert_component_inst = component(parent_container_node=self.container_node)

        combined_namespace = utils.Namespace.combine_namespace([current_namespace, insert_component_inst.instance_namespace])

        insert_component_inst.initialize_component(combined_namespace, **component_kwargs)

        #parent the transform
        transform_node = insert_component_inst.transform_node
        if transform_parent is not None:
            cmds.parent(str(transform_node), str(transform_parent), relative=transform_relative)
        elif transform_node is not None:
            if transform_parent is not None:
                cmds.parent(str(transform_node), str(transform_parent), relative=transform_relative)
            
            # get container with transform
            curr_container = self.container_node
            transform_parent = None
            while transform_parent is None:
                if curr_container.has_attr("rootTransformNode"):
                    curr_component = self
                    if curr_container != self.container_node:
                        curr_component = Component(curr_container)
                    
                    transform_parent = curr_component.subcomponent_grp_node
                    if transform_parent is None:
                        transform_parent = nw.Node.create_node("transform", name="sub_component_grp")
                        cmds.parent(str(transform_parent), str(curr_component.transform_node))
                        curr_container.add_nodes(transform_parent)
                        utils.map_node_to_container("subComponentGrp", transform_parent)
                    break
                if curr_container.get_container() is None:
                    break
                curr_container = curr_container.get_container()
                

            # get container here and sent it to parent
            if transform_parent is not None:

                cmds.parent(str(transform_node), str(transform_parent))

        self.container_node.add_nodes(insert_component_inst.container_node)

        if build:
            insert_component_inst.build_component()

        return insert_component_inst

    def rename_nodes(self, *args):
        #renamed nodes
        if len(args) == 0:
            nodes = self.container_node.get_nodes()
        else:
            nodes = args

        old_namespace = utils.Namespace.get_namespace(str(self.container_node))
        old_namespace = ":{}".format(utils.Namespace.strip_outer_colons(old_namespace))
        
        # creating new namespace
        new_namespace = old_namespace

        # splitting up parent and trailing namespace
        parent_namespace, trailing_namespace = old_namespace.rsplit(":", 1)
        
        # if trailing doesn't equal instance_namespace, rename the namespace
        if utils.strip_trailing_numbers(trailing_namespace) != self.instance_namespace:
            new_namespace = utils.Namespace.combine_namespace([parent_namespace, self.instance_namespace])
            new_namespace = utils.Namespace.strip_outer_colons(new_namespace)
            
            new_namespace = utils.Namespace.rename_namespace(old_namespace, new_namespace)

        # stripping colons from namespace
        new_namespace = utils.Namespace.strip_outer_colons(new_namespace)

        for node in nodes:
            if utils.Namespace.get_namespace(str(node)) != new_namespace and node.node_type != "container":
                
                new_node_name = node.name.rsplit(":")[-1]
                new_node_name = "{}:{}".format(new_namespace, new_node_name)
                node.rename(new_node_name)
        
    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = data.NodeBuildDataDict()

        container_data = data.NodeData(node_name="component_container", node_type="container")

        node_data_dict.add_node_data(container_data, key="container")

        io_data = data.NodeData(node_name=self._io_name.node_name, node_type = "network", map_node_attr=self._io_name.connect_attr_name)
        io_data.add_attr_data(
            data.AttrData("containerNode", type="message"),
            data.AttrData("install", type="compound"),
            data.AttrData("componentName", value=self.class_name, locked=True, publish_name=True, type="string", parent="install"),
            data.AttrData("componentClass", value=self.class_name, locked=True, publish_name=True, type="string", parent="install"),
            data.AttrData("componentType", 
                keyable=True,
                value=utils_enum.ComponentTypes.index_of(type(self).component_type), 
                locked=True,
                publish_name=True,
                type="enum", enum_name=utils_enum.ComponentTypes.maya_enum_str(), parent="install"),
            data.AttrData("built", type="bool", publish_name=True, locked=True),
            data.AttrData("input", type="compound"),
            data.AttrData("output", type="compound")
        )

        node_data_dict.add_node_data(io_data, self._io_name.node_name)

        if type(self).root_transform_name != "" and type(self).root_transform_name is not None:
            node_data_dict = self._add_transform_data(node_data_dict)
        if type(self).has_inst_name_attr or (instance_name is not None):
            node_data_dict = self._add_component_inst_name_data(node_data_dict, instance_name)
        if type(self).has_side_attr:
            node_data_dict = self._add_side_data(node_data_dict)
        if "mirror_dest" in attr_kwargs.keys():
            node_data_dict = self._add_mirror_dest_data(node_data_dict)

        return node_data_dict

    def _add_component_inst_name_data(self, node_data_dict, instance_name):
        node_data_dict[self._io_name.node_name].add_attr_data(data.AttrData("componentInstName", publish_name=True, type="string", parent="install"))

        if instance_name != "" and instance_name is not None:
            node_data_dict[self._io_name.node_name].attr_values["componentInstName"].value=instance_name

        return node_data_dict

    def _add_hier_data(self, node_data_dict, publish=True):        
        node_data_dict[self._io_name.node_name].add_attr_data(
            *data.HierData.hier_data_creation_data(publish)
        )

        return node_data_dict

    def _add_mirror_dest_data(self, node_data_dict):
        node_data_dict["container"].add_attr_data(
            data.AttrData("mirrorDest", type="message")
        )
        return node_data_dict

    def _add_transform_data(self, node_data_dict):        
        transform_data = data.NodeData(node_name=type(self).root_transform_name, node_type="transform", map_node_attr="rootTransformNode")
        transform_data.add_attr_data(data.AttrData("containerNode", type="message"))

        node_data_dict.add_node_data(transform_data, key="rootTransform")

        return node_data_dict

    def _add_side_data(self, node_data_dict):
        side_data = data.AttrData("side", type="enum", enum_name=utils_enum.CharacterSide.maya_enum_str(), value=utils_enum.CharacterSide.index_of((type(self).side_attr_default)), parent="install")
        node_data_dict[self._io_name.node_name].add_attr_data(side_data)

        return node_data_dict
    
    def get_parent_component_of_type(self, component_type):
        if isinstance(component_type, utils_enum.ComponentTypes):
            container_node = self.container_node
            while container_node != None:
                if container_node.has_attr("componentType") and container_node["componentType"].value == component_type.value:
                    return get_component(container_node)
                container_node = container_node.get_container()

    def get_child_component_of_type(self, component_type):
        if isinstance(component_type, utils_enum.ComponentTypes):
            child_containers = self.container_node.get_child_containers()
            child_containers = [x for x in child_containers if x.has_attr("componentType") and x["componentType"].value == component_type.value]
            child_containers = [get_component(x) for x in child_containers]
            return child_containers

        return []

    def get_enum_color(self, index):
        if isinstance(index, nw.Attr):
            index = index.value
        return utils_enum.Colors.get(index)
    def get_enum_side(self, index):
        if isinstance(index, nw.Attr):
            index = index.value
        return utils_enum.CharacterSide.get(index)

    def get_shape_color(self):
        char_inst = self.get_parent_component_of_type(utils_enum.ComponentTypes.character)
        anim_inst = self.get_parent_component_of_type(utils_enum.ComponentTypes.anim)
        
        if char_inst is not None:
            char_io_node = char_inst.io_node
            if self.get_parent_component_of_type(utils_enum.ComponentTypes.setup) is not None:
                # setup_inst = get_component(char_inst)
                return self.get_enum_color(char_io_node["setupColor"])

            elif anim_inst is not None:
                anim_io_node = anim_inst.io_node

                attr = None
                hier_side_enum = self.get_enum_side(anim_io_node[data.HierDataAttrNames.hier_side.value])
                hier_side_index = anim_io_node[data.HierDataAttrNames.hier_side.value].value
                opposite_index = utils_enum.CharacterSide.opposite(hier_side_enum)
                opposite_index = utils_enum.CharacterSide.index_of(opposite_index)
                if hier_side_index == char_io_node["primarySide"].value:
                    
                    if anim_io_node["level"].value == 0:
                        attr = "primarySideColor"
                    else:
                        attr = "secondarySideColor"
                elif opposite_index == char_io_node["primarySide"].value:
                    if anim_io_node["level"].value == 0:
                        attr = "mirrorSideColor"
                    else:
                        attr = "mirrorSecondarySideColor"
                elif hier_side_index == char_io_node["nonMirrorSide"].value:
                    attr = "nonMirrorColor"


                if attr is not None:
                    return self.get_enum_color(char_io_node[attr])

    def promote_to_control(self, attr, control, name=None, parent=None, freeze_control=True, **control_kwargs):
        matrix_attr = None
        local_matrix_attr = None

        hier_attr_names = data.HierAttrNames

        if attr.attr_type == "matrix":
            matrix_attr = attr
        
        if attr.attr_type == "compound":
            if data.HierData.is_hier_attr(attr):
                name = attr[hier_attr_names.hier_name.value]
                matrix_attr = attr[hier_attr_names.input_world_matrix.value]
                local_matrix_attr = attr[hier_attr_names.input_local_matrix.value]
        
        prev_connected_attr = None
        connection_list = matrix_attr.get_as_dest_connection_list()
        if len(connection_list) > 0:
            attr_name = connection_list[0].attr_name
            ~matrix_attr
            prev_connected_attr = connection_list[0].node[attr_name]
        
        # name kwargs
        if name is not None:
            if isinstance(name, nw.Attr):
                control_kwargs["instance_name"] = name.value
            else:
                control_kwargs["instance_name"] = name

        # mirrored input shape
        mirror_attr = self.get_mirrored_attr(matrix_attr)

        if mirror_attr is not None:
            mirror_control_io_node = mirror_attr.get_as_dest_connection_list()
            if len(mirror_control_io_node) > 0:
                mirror_control_component = get_component(mirror_control_io_node[0].node.get_container())
                control = type(mirror_control_component)
                control_kwargs["input_shape"] = mirror_control_component.transform_node
                control_kwargs["build_scale"]= -1
        
        # todo add shape color
        shape_color = self.get_shape_color()
        if shape_color is not None:
            control_kwargs["shape_color"] = shape_color


        control_component = self.insert_component(control, transform_parent=parent, **control_kwargs)
        control_transform_node = control_component.transform_node
        
        if matrix_attr.value is not None:
            if prev_connected_attr is not None:
                prev_connected_attr >> control_component.io_node["offsetMatrix"]
            else:
                if freeze_control:
                    control_component.io_node["offsetMatrix"] = matrix_attr.value
                else:
                    cmds.xform(str(control_transform_node), ws=True, matrix=matrix_attr.value)
                    
        control_io_node = control_component.io_node
        control_io_node["worldMatrix"] >> matrix_attr
        if local_matrix_attr is not None:
            if len(local_matrix_attr.get_as_dest_connection_list()) == 0:
                control_io_node["localMatrix"] >> local_matrix_attr
        
        return control_component

    def initialize_component(self, namespace=":", instance_name=None, **attr_kwargs):
        
        if self.container_node is None:
            
            # Node data
            node_data_dict = self._init_node_data(instance_name=instance_name, **attr_kwargs)

            if namespace == ":":
                namespace = utils.Namespace.combine_namespace([self.instance_namespace])
            

            namespace = utils.Namespace.strip_outer_colons(namespace)

            namespace = utils.Namespace.add_namespace(namespace)
            namespace = utils.Namespace.add_outer_colons(namespace)
                
            # add namespaces to names
            for node_key in node_data_dict:
                node_data_dict[node_key].node_name = "{}{}".format(namespace, node_data_dict[node_key].node_name)

            node_data_dict.handle_node_data(namespace)

            self.container_node = node_data_dict["container"].node
            container_add_nodes = [node_data_dict[node_key].node for node_key in node_data_dict if node_data_dict[node_key].node is not self.container_node]
            self.container_node.add_nodes(*container_add_nodes, include_network=True, include_hierarchy_below=True)

            node_data_dict.map_to_container()

            node_data_dict.publish_attrs(self.container_node)

            # attr_data_list = self.filter_attr_kwargs()
            self.initialize_attrs(attr_kwargs)

        else:
            raise RuntimeError("cannot create template from already existing component")

    def filter_attr_kwargs(self, attr_kwargs):

        attr_data_list = []
        for key in attr_kwargs:
            attr_data = attr_kwargs[key]

            if isinstance(attr_data, data.ComponentInsertData):
                attr_data_list.append(attr_data)
                continue

            # getting attribute name
            attr_name = key
            if not self.container_node.has_attr(utils.snake_to_camel(attr_name)):
                attr_name=utils.snake_to_camel(attr_name.replace("__", "."))
                
                attr_split_parts = []

                beg=0
                end=-1
                for index in range(1, len(attr_name)):
                    # see if end needs to be set
                    if index + 1 == len(attr_name):
                        end = index
                    elif not attr_name[index].isdigit() and attr_name[index+1].isdigit():
                        end = index
                    elif attr_name[index].isdigit() and not attr_name[index+1].isdigit():
                        end = index


                    # of end is > begining
                    if end >= beg:
                        if attr_name[beg].isdigit():
                            attr_split_parts.append("[" + attr_name[beg: end + 1] + "].")
                        else:
                            attr_split_parts.append(attr_name[beg: end + 1])
                        beg = end + 1
                        end = -1

                        #lowercase after every
                        if beg + 1 < len(attr_name):
                            if attr_name[beg].isupper():
                                attr_split_parts.append(attr_name[beg:beg+1].lower())
                                beg += 1
                
                attr_name = "".join(attr_split_parts)
                attr_name = attr_name.replace("]..[", "][")
                if attr_name[-1] == ".":
                    attr_name=attr_name[:-1]
            else:
                attr_name = utils.snake_to_camel(attr_name)

            # hier data key
            pattern = r"{}\d+".format(data.HierDataAttrNames.hier.value)

            if re.fullmatch(pattern, utils.snake_to_camel(key)):

                key_index = utils.get_trailing_numbers(key)
                hier_names = data.HierDataAttrNames
                if isinstance(attr_data, nw.Node) and attr_data.node_type=="transform":
                    hier_build_data = data.HierBuildData(attr_data)
                elif isinstance(attr_data, nw.Attr) and data.HierData.is_hier_attr(attr_data):
                    hier_build_data = data.HierBuildData(attr_data)
                elif isinstance(attr_data, data.HierBuildData):
                    hier_build_data = attr_data
                
                hier_build_data_list = hier_build_data.hier_component_insert_list("{}[{}]".format(hier_names.hier.value, key_index))
                for x in hier_build_data_list:
                    if x.attr_name not in attr_kwargs:

                        attr_data_list.append(x)
            elif issubclass(type(attr_data), utils_enum.MayaEnumAttr):
                if self.container_node[attr_name].attr_type == "string":
                    attr_data_list.append(data.ComponentInsertData(attr_name=attr_name, attr_value=type(attr_data).long_name(attr_data)))
                else:
                    attr_data_list.append(data.ComponentInsertData(attr_name=attr_name, attr_value=type(attr_data).index_of(attr_data)))

            elif isinstance(attr_data, type):
                attr_data_list.append(data.ComponentInsertData(attr_name=attr_name, attr_value=str(attr_data)))
            
            else:
                attr_data_list.append(data.ComponentInsertData(attr_name=attr_name, attr_value=attr_data))

        return attr_data_list

    def initialize_attrs(self, attr_kwargs):
        attr_kwargs = self.filter_attr_kwargs(attr_kwargs)
        
        for attr_data in attr_kwargs:
            if not self.container_node.has_attr(attr_data.attr_name):
                cmds.warning("{}.{} attribute not found ... skipping".format(self.container_node, attr_data.attr_name))
                continue
            attr = self.container_node[attr_data.attr_name]
            # connecting or setting
            locked = attr.is_locked()
            attr.set_locked(False)
            if isinstance(attr_data.attr_value, nw.Attr):
                if attr_data.as_dest:
                    attr_data.attr_value >> self.container_node[attr_data.attr_name]
                else:
                    self.container_node[attr_data.attr_name] >> attr_data.attr_value
            else:
                self.container_node[attr_data.attr_name] = attr_data.attr_value
            attr.set_locked(locked)

    def create_component(self, namespace=":", instance_name=None, **attr_kwargs): 
        self.initialize_component(namespace=namespace, instance_name=instance_name, **attr_kwargs)
        self.build_component()
    

    def parent(self, attr):
        if self.has_hier() and data.HierData.is_hier_attr(attr):
            io_node = self.io_node
            self.unparent()
            attr[data.HierAttrNames.output_world_matrix.value] >> io_node[data.HierDataAttrNames.hier_parent.value]
            attr[data.HierAttrNames.hier_init_matrix.value] >> io_node[data.HierDataAttrNames.hier_parent_init.value]
            return True
        return False

    def unparent(self):
        if self.has_hier():
            io_node = self.io_node
            if io_node[data.HierDataAttrNames.hier_parent.value].has_source_connection():
                ~io_node[data.HierDataAttrNames.hier_parent.value]
                io_node[data.HierDataAttrNames.hier_parent.value] = utils.identity_matrix()
            if io_node[data.HierDataAttrNames.hier_parent_init.value].has_source_connection():
                ~io_node[data.HierDataAttrNames.hier_parent_init.value]
                io_node[data.HierDataAttrNames.hier_parent_init.value] = utils.identity_matrix()
            return True
        return False

    def has_hier(self):
        io_node = self.io_node
        if io_node.has_attr("{}[0]".format(data.HierDataAttrNames.hier.value)) and data.HierData.is_hier_attr(io_node[data.HierDataAttrNames.hier.value][0]):
            return True
        return False

    def _override_mirror_kwargs(self, scale_matrix, **mirror_kwargs):
        return {}

    def mirror_component_list(self, *components, direction, dynamic=False, ):
        return_components = []
        for component in components:
            return_components.append(component.mirror_component(direction, dynamic=dynamic))
        for component in components:
            component.mirror_component_input_connections()

        return return_components

    def mirror_component(self, direction, dynamic=False):
        mirror_inst = None
        if self.has_hier():
            # getting scale matrix
            if direction.name.find("neg") != 0:
                direction = utils_enum.AxisEnums.opposite(direction)
            direction_axis = utils_enum.AxisEnums.scale_vec(direction)
            
            scale_matrix = utils.Matrix(utils.scale_matrix(direction_axis))

            # io node and container node
            io_node = self.io_node
            container_node = self.container_node

            # parent component
            parent_container = self.container_node.get_container()
            parent_inst = None
            if parent_container is not None:
                parent_inst = get_component(parent_container)

            # adding mirror source attr
            container_node.add_attr("mirrorSource", type="message")

            # getting mirror kwargs
            mirror_kwargs = self._override_mirror_kwargs(scale_matrix)
            mirror_kwargs["mirror_dest"] = container_node["mirrorSource"]
            hier_attr = io_node[data.HierDataAttrNames.hier.value]
            # mirror helper input kwargs
            mirror_helper_kwargs = {"hier{}".format(i):data.HierBuildData(hier_attr[i], link_hier_output_matrix=False) for i in range(len(hier_attr))}
            mirror_helper_kwargs["scale_matrix"] = scale_matrix
            mirror_helper_kwargs["componentInstName"] = io_node["componentInstName"]
            mirror_helper_kwargs["hier_side"] = io_node[data.HierDataAttrNames.hier_side.value]

            for attr in ["primaryAxis", "secondaryAxis"]:
                if io_node.has_attr(attr):
                    mirror_helper_kwargs[attr] = io_node[attr]
            
            # making mirror helper kwargs
            from components.components import MirrorHelperComponent
            
            if parent_inst is None:
                mirror_helper_inst = MirrorHelperComponent(parent_container_node=parent_container)
                mirror_helper_inst.create_component(**mirror_helper_kwargs)
            else:
                mirror_helper_inst = parent_inst.insert_component(
                    MirrorHelperComponent,
                    **mirror_helper_kwargs)

            # mirror helper nodes
            mirror_helper_io_node = mirror_helper_inst.io_node
            mirror_helper_hier_attr = mirror_helper_io_node[data.HierDataAttrNames.hier.value]

            # mirror kwargs
            mirror_kwargs.update({"hier{}".format(i):mirror_helper_hier_attr[i] for i in range(len(mirror_helper_hier_attr))})  
            mirror_kwargs["hier_side"] = mirror_helper_io_node["mirrorSide"]
            mirror_kwargs["componentInstName"] = mirror_helper_io_node["componentInstName"]
            for key, attr in zip(["primaryAxis", "secondaryAxis"], ["mirrorPrimaryAxis", "mirrorSecondaryAxis"]):
                if mirror_helper_io_node.has_attr(key):
                    mirror_kwargs[key] = mirror_helper_io_node[attr]

            # creating component
            mirror_inst = None
            if parent_inst is None:
                mirror_inst = type(self)(parent_container_node=parent_container)
                mirror_inst.create_component(**mirror_kwargs)
            else:
                mirror_inst = parent_inst.insert_component(
                    type(self),
                    **mirror_kwargs
                )

            # delete if its not dynamic
            if not dynamic:
                mirror_helper_inst.container_node.delete_node()
        
        return mirror_inst

    def mirror_component_input_connections(self):        
        io_node = self.io_node
        namespace = utils.Namespace.get_namespace(str(io_node))

        mirror_container = self.mirror_dest_container
        mirror_inst = get_component(mirror_container)
        if mirror_container is None:
            return
        external_connection_list = [x for x in self.container_node.get_external_connection_list() if x[1].node == io_node and str(x[0]).find(namespace) != 0]

        # generating input list
        for x in external_connection_list:
            source_attr = x[0]
            mirror_attr = self.get_mirrored_attr(source_attr)
            if mirror_attr is not None:
                source_attr = mirror_attr

            source_attr >> mirror_container[x[1].attr_name]

        # parent them
        mirror_parent_attr = mirror_inst.io_node[data.HierDataAttrNames.hier_parent.value]
        mirror_hier_attr = mirror_parent_attr.get_as_dest_connection_list()
        if len(mirror_hier_attr) > 0 and data.HierData.is_hier_attr(mirror_hier_attr[0].parent):
            mirror_inst.unparent()
            mirror_inst.parent(mirror_hier_attr[0].parent)
            
    def get_mirrored_attr(self, attr):
        attr_str = str(attr)

        original_container = attr.node
        if attr.node.node_type != "container":
            original_container = original_container.get_container()
        if original_container is None:
            return None
        original_component_inst = get_component(original_container)

        container = original_container
        component_inst = original_component_inst

        while True:
            if container is None:
                break
            if component_inst is None:
                break

            
            if component_inst is not None:
                if component_inst.instance_namespace not in attr_str:
                    component_inst.rename_nodes()

            container = container.get_container()
            if container is not None:
                component_inst = get_component(container)
        
        attr_str = str(attr)

        container = original_container
        component_inst = original_component_inst

        while True:
            if container is None:
                break
            if component_inst is None:
                break
        
            old_comp_namespace = component_inst.instance_namespace
            new_comp_namespace = component_inst.mirror_instance_namespace

            if old_comp_namespace != new_comp_namespace:
                attr_str = attr_str.replace(old_comp_namespace, new_comp_namespace)

            container = container.get_container()
            if container is not None:
                component_inst = get_component(container)

        mirror_attr_node = None
        attr_str_split = attr_str.split(".", 1)
        if nw.Node.exists(attr_str_split[0]):
            mirror_attr_node = nw.Node(attr_str_split[0])
            if mirror_attr_node.has_attr(attr_str_split[1]):


                return mirror_attr_node[attr_str_split[1]]

    def build_component(self):
        if not self.try_delete_build_nodes():
            return
        io_node = self.io_node
        io_node["built"].set_locked(False)
        io_node["built"] = True
        io_node["built"].set_locked(True)

        node_data_dict = self._pre_build_component()
        namespace = utils.Namespace.get_namespace(str(self.container_node))
        node_data_dict.handle_node_data(namespace)

        node_data_dict.publish_attrs(self.container_node)
        container_add_nodes = [node_data_dict[node_key].node for node_key in node_data_dict if node_data_dict[node_key].node is not self.container_node]
        container_add_nodes = [node for node in container_add_nodes if node.get_container() is None]
        self.container_node.add_nodes(*container_add_nodes, include_hierarchy_below=True)
        self.rename_nodes()

    def _pre_build_component(self):
        node_data_dict = data.NodeBuildDataDict()
        node_data_dict.add_node_data(data.NodeData(node=self.container_node), key="container")
        node_data_dict.add_node_data(data.NodeData(node=self.io_node), key=data.IOName.node_name)
        if self.transform_node is not None:
            node_data_dict.add_node_data(data.NodeData(node=self.transform_node), key="rootTransform")

        return node_data_dict
    
    def try_delete_build_nodes(self):
        container_node = self.container_node
        namespace_list = [utils.Namespace.get_namespace(str(x)) for x in container_node.get_child_containers(all=True)]
        attr_list = container_node.get_dynamic_attribute_list()
        non_delete_nodes = []
        for attr in attr_list:
            connections = attr.get_as_source_connection_list()
            for connection in connections:
                if connection.node in container_node.get_nodes():
                    non_delete_nodes.append(connection.node)

        non_delete_nodes = list(set(non_delete_nodes))
        delete_nodes = [x for x in container_node.get_nodes() if x not in non_delete_nodes]
        if delete_nodes == []:
            return True
        if not type(self).is_rebuildable:
            cmds.warning("component {} is not rebuildable".format(str(self.container_node)))
            return False

        for node in delete_nodes:
            node.delete_node()

        for namespace in namespace_list[::-1]:
            utils.Namespace.delete(namespace)
        return True
    
    def gen_input_local_matrices(self, gen_first_local_hier=False):
        io_node = self.io_node
        if not io_node.has_attr(data.HierDataAttrNames.hier.value):
            return

        io_node_hier_attr = io_node[data.HierDataAttrNames.hier.value]
        hier_attr_names = data.HierAttrNames

        for index in range(len(io_node_hier_attr)):
            curr_world_attr = io_node_hier_attr[index][hier_attr_names.input_world_matrix.value]
            parent_world_matrix = io_node_hier_attr[index-1][hier_attr_names.input_world_matrix.value]
            
            if index == 0 and not gen_first_local_hier:
                continue
            if index == 0:
                parent_world_matrix = io_node[data.HierDataAttrNames.hier_parent.value]
            
            curr_local_attr = io_node_hier_attr[index][hier_attr_names.input_local_matrix.value]
            
            # check if it's equivalent
            if curr_local_attr.value is not None:
                gen_local_matrix = utils.Matrix(utils.Matrix(curr_world_attr) * utils.Matrix(parent_world_matrix).inverse())
                if gen_local_matrix.isEquivalent(utils.Matrix(curr_local_attr)):
                    continue

            # disconnecting
            connections = curr_local_attr.get_as_dest_connection_list()
            if len(connections) > 0:
                ~curr_local_attr

            from components.matrix_component import OffsetMatrixComponent
            self.insert_component(
                OffsetMatrixComponent, 
                target_matrix=curr_world_attr, 
                space_matrix=parent_world_matrix, 
                local_matrix=data.ComponentInsertData(attr_name="offsetMatrix", attr_value=curr_local_attr, as_dest=False),
                instance_name="hier{}_local".format(index))
    def __eq__(self, other):
        if isinstance(other, Component):
            return other.container_node == self.container_node
        return False
"""
class CompoundComponent(Component):
    component_type = utils_enum.ComponentTypes.compound
    freeze_component = None

    @property
    def freeze_io_cache_node(self):
        container_node = self.container_node
        if container_node.has_attr(self._io_name.connect_frz_cache_attr_name):
            return utils.get_first_connected_node(container_node[self._io_name.connect_frz_cache_attr_name], as_source=True)

    def _init_node_data(self, instance_name=None):
        node_data_dict = super(CompoundComponent, self)._init_node_data(instance_name)
    
        if type(self).freeze_component is not None:

            freeze_component_inst = type(self).freeze_component()
            freeze_node_data_dict = freeze_component_inst.gen_store_node_data()

            node_data_dict[self._io_name.frz_cache_key] = freeze_node_data_dict[self._io_name.frz_cache_key]

        return node_data_dict

    def unfreeze(self):
        freeze_component = self.insert_component(type(self).freeze_component)
        publish_names = freeze_component.container_node.get_published_attrs()
        publish_names = {x.attr_name: x for x in publish_names}

        freeze_io_cache = self.freeze_io_cache_node

        for compound_attr in ["install", "input", "output"]:
            if freeze_io_cache.has_attr(compound_attr):
                for attr in self.freeze_io_cache_node[compound_attr]:
                    if attr.attr_type != "compound" and attr.parent.attr_type not in ["double2", "double3"]:
                        attr_name = attr.attr_name
                        if attr_name in publish_names.keys():
                            if compound_attr == "output":
                                publish_names[attr_name] >> attr
                            else:
                                attr >> publish_names[attr_name]

    def freeze(self):
        freeze_container_node = self.get_sub_container_nodes(utils_enum.ComponentTypes.freeze)
        if freeze_container_node is None:
            cmds.warning("no freeze container found for {}".format(self.container_node))
            return
        freeze_container_node = freeze_container_node[0]

        freeze_namespace = utils.Namespace.get_namespace(str(freeze_container_node))

        freeze_container_node.delete_node()
        utils.Namespace.delete(freeze_namespace)

    def build_component(self):
        super(CompoundComponent, self).build_component()

        if type(self).freeze_component is not None:
            self.unfreeze()

    def _pre_build_component(self):
        node_data_dict = super(CompoundComponent, self)._pre_build_component()
        freeze_io_cache_node = self.freeze_io_cache_node
        if freeze_io_cache_node is not None:
            node_data_dict.add_node_data(data.NodeData(node=freeze_io_cache_node), key=self._io_name.frz_cache_key)

        return node_data_dict
    
class DynamicComponent(Component):
    component_type = utils_enum.ComponentTypes.dynamic
    has_inst_name_attr = True

    def _init_node_data(self, instance_name=None):
        node_data_dict = super(DynamicComponent, self)._init_node_data(instance_name)
        node_data_dict[self._io_name.node_name].add_attr_data(
            data.AttrData("method", publish_name="method", type="enum", enum_name="append:merge:chain", parent="install"))
        return node_data_dict
    
    #Todo add dynamic
    # add freeze

class CharacterComponent(CompoundComponent):
    component_type = utils_enum.ComponentTypes.character
    has_inst_name_attr = True
    # add post modules

class MotionComponent(CompoundComponent):
    component_type = utils_enum.ComponentTypes.motion

    # add freeze
    # add dynamic
"""

class CharacterComponent(Component):
    component_type = utils_enum.ComponentTypes.character
    has_inst_name_attr = True
    # add post modules