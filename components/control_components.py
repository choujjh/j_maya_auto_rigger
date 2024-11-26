from system.base_components import Component
from components.components import ColorManager

import utils.node_wrapper as nw
import system.data as data
import maya.cmds as cmds
import utils.enum as utils_enum
import utils.utils as utils
import warnings

import ast as ast

class ControlComponent(Component):
    component_type = utils_enum.ComponentTypes.control
    has_inst_name_attr = True
    root_transform_name = "control"

    has_shape_color_attr = False
    shape_color_default = utils_enum.Colors.none

    has_axis_attr = False
    axis_default = utils_enum.AxisEnums.x

    publish_attr_default = ["translate", "rotate", "scale"]
    
    def __init__(self, container_node=None, parent_container_node=None):
        super(ControlComponent, self).__init__(container_node, parent_container_node)
        self.input_shape = None
        
    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = super(ControlComponent, self)._init_node_data(instance_name, **attr_kwargs)

        node_data_dict[self._io_name.node_name].add_attr_data(
            data.AttrData("offsetMatrix", connection=[("rootTransform", "offsetParentMatrix")], publish_name="offsetMatrix", type="matrix", parent="input"),
            data.AttrData("worldMatrix", publish_name=True, type="matrix", parent="output"),
            data.AttrData("localMatrix", publish_name=True, type="matrix", parent="output"),
            data.AttrData("publishAttrList", type="string", publish_name=True, parent="install"),

            data.AttrData("buildTranslate", type="double3", publish_name=True, parent="install"),
            data.AttrData("buildTranslateX", type="double", parent="buildTranslate"),
            data.AttrData("buildTranslateY", type="double", parent="buildTranslate"),
            data.AttrData("buildTranslateZ", type="double", parent="buildTranslate"),

            data.AttrData("buildRotate", type="double3", publish_name=True, parent="install"),
            data.AttrData("buildRotateX", type="double", parent="buildRotate"),
            data.AttrData("buildRotateY", type="double", parent="buildRotate"),
            data.AttrData("buildRotateZ", type="double", parent="buildRotate"),

            data.AttrData("buildScale", type="double3", publish_name=True, parent="install"),
            data.AttrData("buildScaleX", type="double", value=1.0, parent="buildScale"),
            data.AttrData("buildScaleY", type="double", value=1.0, parent="buildScale"),
            data.AttrData("buildScaleZ", type="double", value=1.0, parent="buildScale"),
        )

        node_data_dict["rootTransform"].add_attr_data(
            data.AttrData("worldMatrix[0]", connection=[(self._io_name.node_name, "worldMatrix")]),
            data.AttrData("dagLocalMatrix", connection=[(self._io_name.node_name, "localMatrix")]),
        )

        if type(self).has_shape_color_attr:
            node_data_dict[self._io_name.node_name].add_attr_data(
                data.AttrData("shapeColor", type="enum", publish_name=True, parent="install", value=utils_enum.Colors.index_of(type(self).shape_color_default), enumName=utils_enum.Colors.maya_enum_str())
            )

        if type(self).has_axis_attr:
            node_data_dict[self._io_name.node_name].add_attr_data(
                data.AttrData("axis", type="enum", publish_name=True, parent="install", value=utils_enum.AxisEnums.index_of(type(self).axis_default), enumName=utils_enum.AxisEnums.maya_enum_str())
            )

        return node_data_dict

    def _add_shapes(self):
        return []
    def freeze_shape_transform(self, transform):
        transform = nw.Node(transform)
        transform_locked_attrs = utils.get_transform_locked_attrs(str(transform))

        for locked_attrs in transform_locked_attrs:
            locked_attrs.set_locked(False)
        scale = transform["scale"].value
        
        cmds.makeIdentity(str(transform), apply=True)

        if scale[0] * scale[1] * scale[2] < 0:
            shapes = [nw.Node(x) for x in cmds.listRelatives(str(transform), shapes=True)]
            for x in shapes:
                if x.node_type == "nurbsSurface":
                    cmds.reverseSurface(str(x))
                    x["opposite"] = False
                elif x.node_type == "mesh":
                    cmds.polyNormal(str(x), normalMode=0, constructionHistory=False)
                    x["opposite"] = False

        for locked_attrs in transform_locked_attrs:
            locked_attrs.set_locked(True)

    def _process_shapes(self, node_data_dict):
        transform_list = []
        if self.input_shape is not None:
            transform_node = None
            if isinstance(self.input_shape, nw.Node) and self.input_shape.node_type == "transform":
                transform_node = self.input_shape
            elif issubclass(type(self.input_shape), Component):
                transform_node = self.input_shape.transform_node

            if transform_node is not None:
                transform_node = cmds.duplicate(str(transform_node), renameChildren=True)[0]
                transform_shapes = cmds.listRelatives(transform_node, shapes=True)
                transform_children = [x for x in cmds.listRelatives(transform_node) if x not in transform_shapes]

                if len(transform_children) > 0:
                    cmds.delete(transform_children)
                
                # resetting everything for input shape
                transform_list = [nw.Node(transform_node)]
                curr_transform = transform_list[0]
                curr_transform["offsetParentMatrix"] = utils.identity_matrix()
                transform_locked_attrs = utils.get_transform_locked_attrs(str(curr_transform))
                
                # 0ing out the control
                cmds.parent(str(curr_transform), w=True)
                curr_transform["tx"] = 0.0
                curr_transform["ty"] = 0.0
                curr_transform["tz"] = 0.0
                curr_transform["rx"] = 0.0
                curr_transform["ry"] = 0.0
                curr_transform["rz"] = 0.0
                curr_transform["sx"] = 1.0
                curr_transform["sy"] = 1.0
                curr_transform["sz"] = 1.0
                for locked_attrs in transform_locked_attrs:
                    locked_attrs.set_locked(True)
                
                # applying color
                shape_color = self._get_shape_color()
                if shape_color is not None:
                    color_component = ColorManager.get_instance(self)
                    color_component.apply_color(transform_list[0], shape_color)
        
        if transform_list == []:
            transform_list = self._add_shapes()


        shape_list = []
        # clean up transforms
        for transform in transform_list:
            transform = str(transform)

            self.freeze_shape_transform(transform)

            cmds.delete(transform, constructionHistory=True)
            shape_list.extend(cmds.listRelatives(transform, shapes=True))

        

        transform_node = self.transform_node


        for index, shape in enumerate(shape_list):
            cmds.parent(shape, str(transform_node), relative=True, shape=True)

            shape_key = "shape{}".format(index+1)
            shape_node = nw.Node(shape)
            shape_node.rename("{}Shape{}".format(transform_node, index+1))

            node_data_dict.add_node_data(data.NodeData(node=shape_node), key=shape_key)
            
            shape_color = self._get_shape_color()
            if shape_color is not None:
                color_component = ColorManager.get_instance(self)
                color_component.apply_color(transform_node, shape_color)

        

        if transform_list != []:
            cmds.delete(transform_list)

        # offset with install values
        io_node = self.io_node
        transform_node["translate"] = io_node["buildTranslate"].value
        transform_node["rotate"] = io_node["buildRotate"].value
        transform_node["scale"] = io_node["buildScale"].value

        self.freeze_shape_transform(str(transform_node))
        # cmds.makeIdentity(str(transform_node), apply=True)
        transform_node["rotatePivot"] = [0.0, 0.0, 0.0]
        transform_node["scalePivot"] = [0.0, 0.0, 0.0]

        return node_data_dict

    def filter_attr_kwargs(self, attr_kwargs):

        # filter axis and shape_color
        for key in ["axis", "shape_color"]:
            if key in attr_kwargs.keys():
                attr_data = attr_kwargs[key]
                if isinstance(attr_data, data.ComponentInsertData):
                    if issubclass(type(attr_data.attr_value), utils_enum.MayaEnumAttr):
                        attr_data.attr_value = type(attr_kwargs[key]).index_of(attr_data.attr_value)
                elif issubclass(type(attr_data), utils_enum.MayaEnumAttr):
                    attr_kwargs[key] = type(attr_kwargs[key]).index_of(attr_kwargs[key])

        # filter publish_attr_list
        publish_attr_list_key = "publish_attr_list"
        if publish_attr_list_key in attr_kwargs.keys():
            if isinstance(attr_kwargs[publish_attr_list_key], data.ComponentInsertData):
                attr_kwargs[publish_attr_list_key].attr_value = str(attr_kwargs[publish_attr_list_key].attr_value)
            else:
                attr_kwargs[publish_attr_list_key] = str(attr_kwargs[publish_attr_list_key])
        else:
            attr_kwargs[publish_attr_list_key] = type(self).publish_attr_default

        filtered_attrs = super(ControlComponent, self).filter_attr_kwargs(attr_kwargs)
        for component_data in filtered_attrs:
            if isinstance(component_data, data.ComponentInsertData):
                if component_data.attr_name in ["buildTranslate", "buildRotate", "buildScale"]:
                    if not isinstance(component_data.attr_value, list):
                        component_data.attr_value = [component_data.attr_value, component_data.attr_value, component_data.attr_value]
                    elif isinstance(component_data.attr_value, list) and len(component_data.attr_value) != 3:
                        correct_len_list = [0.0, 0.0, 0.0]
                        loop_range = len(component_data.attr_value)
                        if loop_range > 3:
                            loop_range = 3
                        for index in range(loop_range):
                            correct_len_list[index] = component_data.attr_value[index]
                        component_data.attr_value = correct_len_list
                        
        return filtered_attrs

    def create_component(self, namespace=":", instance_name=None, input_shape=None, **attr_kwargs):
        if "input_shape" in attr_kwargs.keys():
            self.input_shape = attr_kwargs.pop("input_shape")
        self.input_shape = input_shape
        self.initialize_component(namespace=namespace, instance_name=instance_name, **attr_kwargs)
        self.build_component(input_shape=self.input_shape)

    def initialize_component(self, namespace=":", instance_name=None, **attr_kwargs):
        if "input_shape" in attr_kwargs.keys():
            self.input_shape = attr_kwargs.pop("input_shape")
            
        return super().initialize_component(namespace, instance_name, **attr_kwargs)

    def build_component(self, input_shape=None):
        if self.input_shape is None:
            self.input_shape = input_shape
        return super(ControlComponent, self).build_component()

    def _pre_build_component(self):
        node_data_dict = super(ControlComponent, self)._pre_build_component()

        node_data_dict = self._process_shapes(node_data_dict)

        # getting publish attributes in install
        publish_attr_list = self.io_node["publishAttrList"].value
        if publish_attr_list != "None":
            publish_attr_list = ast.literal_eval(publish_attr_list)

        #publishing those attributes onto container
        transform_node = self.transform_node
        if isinstance(publish_attr_list, list):
            for attr in publish_attr_list:
                node_data_dict["rootTransform"].add_attr_data(data.AttrData(attr, publish_name=True))

            for attr in ["translate", "rotate", "scale"]:
                if attr not in publish_attr_list:
                    for axis in ["X", "Y", "Z"]:
                        axis = "{}{}".format(attr, axis)
                        if axis not in publish_attr_list:
                            cmds.setAttr(str(transform_node[axis]), lock=True, keyable=False)
            if "visibility" not in publish_attr_list:
                cmds.setAttr(str(transform_node["visibility"]), lock=True, keyable=False)
            

        return node_data_dict
    
    def _get_shape_color(self):
        io_node = self.io_node
        if not io_node.has_attr("shapeColor"):
            return None
        return utils_enum.Colors.get(io_node["shapeColor"].value)

    def _get_axis_vec(self):
        io_node = self.io_node
        if not io_node.has_attr("axis"):
            cmds.warning("axis attr not found. returning default vec")
            return [1.0, 0.0, 0.0]
        axis = utils_enum.AxisEnums.get(io_node["axis"].value)
        return axis.value
    
    def promote_attr_to_keyable(self, attr:nw.Attr, name=None, **kwargs):
        
        def get_num_min_max_kwargs(attr:nw.Attr):
            # has max and mins
            kwargs={}
            if attr_type in ["double", "long"]:
                for attr_exists, attr_query_key, attr_add_key in zip(
                    ["softMaxExists", "softMinExists", "maxExists", "minExists"],
                    ["softMax", "softMin", "maximum", "minimum"],
                    ["softMaxValue", "softMinValue", "maxValue", "minValue"]):

                    if cmds.attributeQuery(attr.attr_short_name, node=str(attr.node), **{attr_exists:True}):
                        kwargs[attr_add_key] = cmds.attributeQuery(attr.attr_short_name, node=str(attr.node), **{attr_query_key:True})[0]

            return kwargs

        transform_node = self.transform_node
        if kwargs == {}:
            attr_type = attr.attr_type
            if attr_type == "compound":
                raise RuntimeError("{} of type compound. compound type not supported".format(attr))

            if name is None:
                name = attr.attr_short_name

            # non settable
            if attr_type in ["string", "nurbsCurve", "nurbsSurface","mesh", "matrix", "message"]:
                warn_str = "{} of type {} is not keyable. attribute created without keyable".format(attr, attr_type)
                warnings.warn(warn_str)
            else:
                kwargs["keyable"] = True

            # has max and mins
            if attr_type in ["double", "long"]:
                kwargs.update(get_num_min_max_kwargs(attr))

            # enum
            if attr_type == "enum":
                enum_string = cmds.attributeQuery(attr.attr_short_name, node=str(attr.node), listEnum=True)
                kwargs["enumName"] = enum_string[0]

            # compound attrs
            if attr_type in ["double3", "double2"]:
                transform_node.add_attr(name, type=attr_type, **kwargs)
                for child_attr in attr:
                    child_kwargs = get_num_min_max_kwargs(child_attr)
                    child_name = child_attr.attr_name.replace(attr.attr_name, name)
                    transform_node.add_attr(child_name, parent=name, type=child_attr.attr_type, **kwargs, **child_kwargs)
            
            else:
                transform_node.add_attr(name, type=attr_type, **kwargs)

            attr_connection = attr.get_as_dest_connection_list()
            if attr_connection == [] and attr_type not in ["nurbsCurve", "nurbsSurface","mesh", "message"]:
                try:
                    transform_node[name] = attr.value
                except:
                    pass
                transform_node[name] >> attr
            else:
                attr_connection[0] >> transform_node[name]
                transform_node[name] >> ~attr

        # has add attr kwargs
        else:
            if name is not None:
                kwargs["long_name"] = name
            kwargs["keyable"] = True

            transform_node.add_attr(**kwargs)
            if attr.has_source_connection():
                ~attr
            transform_node[name] >> attr
            
class AxisControl(ControlComponent):
    def __init__(self, container_node=None, parent_container_node=None):
        super(AxisControl, self).__init__(container_node, parent_container_node)
    
    def _add_shapes(self):
        x_axis = cmds.curve(degree=1, point=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
        y_axis = cmds.curve(degree=1, point=[[0.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        z_axis = cmds.curve(degree=1, point=[[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]])

        color_component = ColorManager.get_instance(self)

        color_component.apply_color(nw.Node(x_axis), utils_enum.Colors.red)
        color_component.apply_color(nw.Node(y_axis), utils_enum.Colors.green)
        color_component.apply_color(nw.Node(z_axis), utils_enum.Colors.blue)
        
        return [x_axis, y_axis, z_axis]
    
class BoxControl(ControlComponent):
    has_shape_color_attr = True
    def __init__(self, container_node=None, parent_container_node=None):
        super(BoxControl, self).__init__(container_node, parent_container_node)
    
    def _add_shapes(self):
        x = 1.0
        y = 1.0
        z = 1.0
        box = cmds.curve(degree=1, point=[
            [x, y, z],
            [-x, y, z], [-x, -y, z],  [-x, y, z],
            [-x, y, -z], [-x, -y, -z], [-x, y, -z],
            [x, y, -z], [x, -y, -z], [x, y, -z],
            [x, y, z], [x, -y, z],                      # going to other plane
            [-x, -y, z], [-x, -y, -z], [x, -y, -z], [x, -y, z]
        ])
        
        return [box]
    
class CircleControl(ControlComponent):
    has_axis_attr = True
    has_shape_color_attr = True

    def _add_shapes(self):
        circle = cmds.circle(normal=self._get_axis_vec())[0]

        return [circle]

class DiamondControl(ControlComponent):
    has_shape_color_attr = True
    publish_attr_default = ["translate", "rotate"]
    def initialize_component(self, namespace=":", instance_name=None, **attr_kwargs):
        return super().initialize_component(namespace, instance_name, **attr_kwargs)

    def _add_shapes(self):
        diamond = cmds.sphere(axis=self._get_axis_vec(), sections=4, spans=2, degree=1)[0]
        return [diamond]

class DiamondWireControl(ControlComponent):
    has_shape_color_attr = True
    publish_attr_default = ["translate"]
    def initialize_component(self, namespace=":", instance_name=None, **attr_kwargs):
        return super().initialize_component(namespace, instance_name, **attr_kwargs)

    def _add_shapes(self):
        diamond = cmds.curve(degree=1, point=[
            [0, 1, 0], [1, 0, 0], [0, -1, 0],
            [0, 0, 1], [0, 1, 0],
            [-1, 0, 0], [0, -1, 0],
            [0, 0, -1],
            [1, 0, 0], [0, 0, 1], [-1, 0, 0], [0, 0, -1],
            [0, 1, 0]
        ])
        return [diamond]

class GearControl(ControlComponent):
    has_shape_color_attr=True
    publish_attr_default=[]

    def _add_shapes(self):
        outer_shape = cmds.curve(degree=3, point=[
            [0.303359, 0, 0.940211], [0.662567, 0, 0.732822], [0.707107, 0, 0.720888], [0.751647, 0, 0.732822],
            [0.925336, 0, 0.833101], [0.973133, 0, 0.839394], [1.011381, 0, 0.810046], [1.20721, 0, 0.470859],
            [1.213503, 0, 0.423061], [1.184155, 0, 0.384813], [1.010466, 0, 0.284534], [0.97786, 0, 0.251929], 
            [0.965926, 0, 0.207388], [0.965926, 0, -0.207388], [0.97786, 0, -0.251929], [1.010466, 0, -0.284534], 
            [1.184155, 0, -0.384814], [1.213503, 0, -0.423061], [1.20721, 0, -0.470859], [1.011381, 0, -0.810045], 
            [0.973133, 0, -0.839394], [0.925336, 0, -0.833101], [0.751647, 0, -0.732822], [0.707107, 0, -0.720888], 
            [0.662567, 0, -0.732822], [0.303359, 0, -0.940211], [0.270754, 0, -0.972816], [0.258819, 0, -1.017356], 
            [0.258819, 0, -1.217915], [0.24037, 0, -1.262455], [0.19583, 0, -1.280904], [-0.19583, 0, -1.280904], 
            [-0.24037, 0, -1.262455], [-0.258819, 0, -1.217915], [-0.258819, 0, -1.017356], [-0.270754, 0, -0.972816], 
            [-0.303359, 0, -0.940211], [-0.662567, 0, -0.732822], [-0.707107, 0, -0.720888], [-0.751647, 0, -0.732822], 
            [-0.925336, 0, -0.833101], [-0.973133, 0, -0.839394], [-1.011381, 0, -0.810046], [-1.20721, 0, -0.470859], 
            [-1.213503, 0, -0.423061], [-1.184155, 0, -0.384813], [-1.010466, 0, -0.284534], [-0.97786, 0, -0.251929], 
            [-0.965926, 0, -0.207388], [-0.965926, 0, 0.207388], [-0.97786, 0, 0.251929], [-1.010466, 0, 0.284534], 
            [-1.184155, 0, 0.384814], [-1.213503, 0, 0.423061], [-1.20721, 0, 0.470859], [-1.011381, 0, 0.810045], 
            [-0.973133, 0, 0.839394], [-0.925336, 0, 0.833101], [-0.751647, 0, 0.732822], [-0.707107, 0, 0.720888], 
            [-0.662567, 0, 0.732822], [-0.303359, 0, 0.940211], [-0.270754, 0, 0.972816], [-0.258819, 0, 1.017356], 
            [-0.258819, 0, 1.217915], [-0.24037, 0, 1.262455], [-0.19583, 0, 1.280904], [0.19583, 0, 1.280904], 
            [0.24037, 0, 1.262455], [0.258819, 0, 1.217915], [0.258819, 0, 1.017356], [0.270754, 0, 0.972816], 
            [0.303359, 0, 0.940211],
        ])
        inner_shape = cmds.curve(degree=3, point=[ 
            [0.0942458, 0, 0.586178], [0.154925, 0, 0.578189], [0.21147, 0, 0.554768], [0.374708, 0, 0.460522], 
            [0.423264, 0, 0.423264], [0.460522, 0, 0.374708], [0.554768, 0, 0.21147], [0.578189, 0, 0.154925], 
            [0.586178, 0, 0.0942458], [0.586178, 0, -0.0942458], [0.578189, 0, -0.154925], [0.554768, 0, -0.21147], 
            [0.460522, 0, -0.374708], [0.423264, 0, -0.423264], [0.374708, 0, -0.460522], [0.21147, 0, -0.554768], 
            [0.154925, 0, -0.578189], [0.0942458, 0, -0.586178], [-0.0942458, 0, -0.586178], [-0.154925, 0, -0.578189], 
            [-0.21147, 0, -0.554768], [-0.374708, 0, -0.460522], [-0.423264, 0, -0.423264], [-0.460522, 0, -0.374708], 
            [-0.554768, 0, -0.21147], [-0.578189, 0, -0.154925], [-0.586178, 0, -0.0942458], [-0.586178, 0, 0.0942458], 
            [-0.578189, 0, 0.154925], [-0.554768, 0, 0.21147], [-0.460522, 0, 0.374708], [-0.423264, 0, 0.423264], 
            [-0.374708, 0, 0.460522], [-0.21147, 0, 0.554768], [-0.154925, 0, 0.578189], [-0.0942458, 0, 0.586178], 
            [0.0942458, 0, 0.586178],
        ])
        
        return [inner_shape, outer_shape]
    
class GimbalControl(ControlComponent):
    def __init__(self, container_node=None, parent_container_node=None):
        super(GimbalControl, self).__init__(container_node, parent_container_node)

    def _add_shapes(self):
        circle1 = cmds.circle(normal=[1.0, 0.0, 0.0])[0]
        circle2 = cmds.circle(normal=[0.0, 1.0, 0.0])[0]
        circle3 = cmds.circle(normal=[0.0, 0.0, 1.0])[0]

        color_component = ColorManager.get_instance(self)

        color_component.apply_color(nw.Node(circle1), utils_enum.Colors.red)
        color_component.apply_color(nw.Node(circle2), utils_enum.Colors.green)
        color_component.apply_color(nw.Node(circle3), utils_enum.Colors.blue)
        
        return [circle1, circle2, circle3]

class Pyramid4Control(ControlComponent):
    has_shape_color_attr = True
    publish_attr_default = ["translate"]
    def initialize_component(self, namespace=":", instance_name=None, **attr_kwargs):
        return super().initialize_component(namespace, instance_name, **attr_kwargs)

    def _add_shapes(self):
        pyramid = cmds.curve(degree=1, point=[
            [1, 0, 1], [1, 0, -1], [0, 1.4, 0], [1, 0, 1],
            [-1, 0, 1], [0, 1.4, 0], [-1, 0, -1], [-1, 0, 1], 
            [-1, 0, -1], [1, 0, -1]
        ])
        return [pyramid]

class RootControl(ControlComponent):

    def _add_shapes(self):
        pass
        
        return []

class SphereControl(ControlComponent):
    has_shape_color_attr = True
    has_axis_attr = True
    axis_default = utils_enum.AxisEnums.y
    publish_attr_default = ["translate", "rotate"]
    def initialize_component(self, namespace=":", instance_name=None, **attr_kwargs):
        return super().initialize_component(namespace, instance_name, **attr_kwargs)

    def _add_shapes(self):
        sphere = cmds.sphere(axis=self._get_axis_vec())[0]
        return [sphere]