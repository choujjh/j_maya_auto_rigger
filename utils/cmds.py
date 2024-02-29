import maya.cmds as cmds
import utils.node_wrapper as nw

def convert_node_to_string(*args):
    args = list(args)
    for index in range(len(args)):
        if isinstance(args[index], nw.Node):
            args[index] = str(args[index])
    return args
            
def command_parse(function, *args, **kwargs):
    converted_node_list = convert_node_to_string(*args)
    curr_list = []
    if len(converted_node_list) == 0:
        curr_list = function(**kwargs)
    else:
        curr_list = function(*converted_node_list, **kwargs)
    if curr_list:
        return curr_list
    else:
        return []

def ls(*args, **kwargs):
    return [nw.Node(x) for x in command_parse(cmds.ls, *args, **kwargs)]

def select(*args, **kwargs):
    return [nw.Node(x) for x in command_parse(cmds.select, *args, **kwargs)]
