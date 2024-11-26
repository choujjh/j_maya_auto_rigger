from enum import Enum
import maya.cmds as cmds
import maya.api.OpenMaya as om2
import utils.node_wrapper as nw

class MayaEnumAttr(Enum):
    @classmethod
    def maya_enum_str(cls):
        return_str = ""
        num_enums = len(cls)
        for i, enum in enumerate(cls):
            return_str += enum.name
            if i < num_enums - 1:
                return_str += ":"
        return return_str
    
    @classmethod
    def get(cls, index):
        for i, curr_enum in enumerate(cls):
            if i == index:
                return curr_enum
            
    @classmethod
    def index_of(cls, enum):
        index = 0
        for item in cls:
            if item == enum:
                return index
            index += 1
    
    @ classmethod
    def get_enum_dict(cls):
        enum_dict = {data.name: data.value for data in cls}
        return enum_dict
            
    @classmethod
    def create_remap(cls, node_name, enum_dict=None):
        if enum_dict is None:
            enum_dict = cls.get_enum_dict()
        out_min = 0
        out_max = 0

        for key in enum_dict:
            value = enum_dict[key]
            if not isinstance(value, int) and isinstance(value, float):
                cmds.error("enum does not have numeric values")
            out_min = value
            out_max = value
            break
            

        # find max
        for key in enum_dict:
            value = enum_dict[key]
            if value < out_min:
                out_min = value
            if value > out_max:
                out_max = value

        map_len = len(enum_dict.keys())
        interval_len = 1.0/float(map_len-1)
        remap_node = nw.Node.create_node("remapValue", node_name)
        remap_node["outputMin"] = out_min
        remap_node["outputMax"] = out_max

        remap_node["inputMax"] = map_len - 1

        out_diff = out_max - out_min
        for index, key in enumerate(enum_dict.keys()):
            value = enum_dict[key] - out_min

            remap_node["value[{}].value_FloatValue".format(index)] = float(value)/out_diff
            remap_node["value[{}].value_Position".format(index)] = interval_len * index
            remap_node["value[{}].value_Interp".format(index)] = 1

        return remap_node
    
    @classmethod
    def long_name(cls, item):
        return "utils.enum.{}.{}".format(type(item).__name__, item.name)

class ComponentTypes(MayaEnumAttr):
    anim = 0
    character = 1
    component = 2
    control = 3
    hier = 4
    matrix = 5
    motion = 6
    setup = 7


class Colors(MayaEnumAttr):
    none = -1
    blue = 6
    dark_blue = 15
    dark_red = 11
    gold = 25
    green = 14
    light_blue = 18
    light_green = 19
    light_orange = 21
    light_pink = 20
    magenta = 9
    purple = 8
    red = 13
    yellow = 17

    @classmethod
    def create_remap(cls, name):
        enum_dict = cls.get_enum_dict()
        out_min = 0
        out_max = 0

        for key in enum_dict:
            value = enum_dict[key]
            if not isinstance(value, int) and not isinstance(value, float):
                cmds.error("enum does not have numeric values")
            out_min = value
            out_max = value
            break
            
        # find max
        for key in enum_dict:
            value = enum_dict[key]
            if value < out_min:
                out_min = value
            if value > out_max:
                out_max = value

        map_len = len(enum_dict.keys())
        interval_len = 1.0/float(map_len-1)
        remap_node = nw.Node.create_node("remapValue", name)
        remap_node["outputMin"] = out_min
        remap_node["outputMax"] = out_max

        remap_node["inputMax"] = map_len - 1

        out_diff = out_max - out_min
        for index, key in enumerate(enum_dict.keys()):
            value = enum_dict[key] - out_min

            remap_node["value[{}].value_FloatValue".format(index)] = float(value)/out_diff
            remap_node["value[{}].value_Position".format(index)] = interval_len * index
            remap_node["value[{}].value_Interp".format(index)] = 1

        return remap_node
    
class CharacterSide(MayaEnumAttr):
    none = "none"
    mid = "M"
    right = "R"
    left = "L"
    front = "Frnt"
    back = "Bck"
    top = "Top"
    bottom = "Btm"
    in_ = "In"
    out = "out"
    
    @classmethod
    def opposite(cls, side):
        opposite_dict = {
            cls.none: cls.none,
            cls.mid: cls.mid,

            cls.right: cls.left,
            cls.left: cls.right,

            cls.mid: cls.mid,

            cls.front: cls.back,
            cls.back: cls.front,

            cls.in_:cls.out,
            cls.out:cls.in_,

            cls.top: cls.bottom,
            cls.bottom: cls.top,
        }
        return opposite_dict[side]
    
    @classmethod
    def opposite_mapping(cls):
        enum_dict = {data.name: cls.index_of(cls.opposite(data)) for data in cls}
        return enum_dict
    
    @classmethod
    def maya_enum_str(cls):
        maya_str = super().maya_enum_str()
        maya_str.replace("_", "")
        return maya_str
    
    @classmethod
    def create_remap(cls, node_name):
        return super().create_remap(node_name, enum_dict=cls.opposite_mapping())

class AxisEnums(MayaEnumAttr):
    x = [1.0, 0.0, 0.0]
    y = [0.0, 1.0, 0.0]
    z = [0.0, 0.0, 1.0]
    neg_x = [-1.0, 0.0, 0.0]
    neg_y = [0.0, -1.0, 0.0]
    neg_z = [0.0, 0.0, -1.0]

    @classmethod
    def other_axes(cls, axis):
        index = cls.index_of(axis)
        if index < 3:
            other_index = [(index+1) % 3, (index+2) % 3]
        else:
            index = index - 3
            other_index = [((index+1) % 3) + 3, ((index+2) % 3) + 3]
        other_index = sorted(other_index)
        return [AxisEnums.get(other_index[0]), AxisEnums.get(other_index[1])]
    
    @classmethod
    def scale_vec(cls, axis):
        axis = axis.value[:]
        for index in range(len(axis)):
            if axis[index] == 0:
                axis[index] = 1

        return axis
    
    @classmethod
    def opposite(cls, axis):
        opposite_dict = {
            cls.x: cls.neg_x,
            cls.neg_x: cls.x,

            cls.y: cls.neg_y,
            cls.neg_y: cls.y,

            cls.z: cls.neg_z,
            cls.neg_z: cls.z,
        }

        return opposite_dict[axis]
    
    @classmethod
    def create_remap(cls, node_name):
        enum_dict = {data.name: cls.index_of(cls.opposite(data)) for data in cls}
        return super().create_remap(node_name, enum_dict)

class SelectorWeightTypes(MayaEnumAttr):
    wave = 0
    zipper = 1 