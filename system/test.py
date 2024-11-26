import components.control_components as control_components
import components.setup_components as setup_components
import components.anim_component as anim_components
import components.components as components
import system.base_components as base_components
import components.character_component as character_components
import components.motion_component as motion_components

import utils.enum as utils_enum
import utils.node_wrapper as nw
import utils.utils as utils
import system.data as data
from maya.api import OpenMaya as om2
# import utils.ui as util_ui
import utils.cmds as util_cmds
import system.ui.component_creator_UI as ui
import utils.ui as util_uis

import importlib

importlib.reload(data)
importlib.reload(utils)
importlib.reload(utils_enum)
importlib.reload(nw)
importlib.reload(util_cmds)
importlib.reload(util_uis)

importlib.reload(base_components)
importlib.reload(components)
importlib.reload(control_components)
importlib.reload(motion_components)
importlib.reload(setup_components)
importlib.reload(anim_components)
importlib.reload(character_components)
importlib.reload(ui)



import maya.cmds as cmds


def test():
    cmds.file(new=True, force=True)
    
    """
    setup_kwargs=utils.kwarg_to_dict(control_class=control_components.SphereControl, shape_color=utils_enum.Colors.yellow, build_scale=0.3)

    leg_setup_inst = setup_components.HingeSetup()
    leg_setup_inst.create_component(
        instance_name="Leg",
        hier_side=utils_enum.CharacterSide.left,
        hier0=data.HierBuildData(name="hip", input_matrix=utils.translate_to_matrix([2.7, 11, 1]), publish_attr_list=["translate"], **setup_kwargs),
        hier1=data.HierBuildData(name="knee", input_matrix=utils.translate_to_matrix([3.1, 6, 2]), publish_attr_list=["translate"], **setup_kwargs),
        hier2=data.HierBuildData(name="ankle", input_matrix=utils.translate_to_matrix([3.3, 1, 1]), publish_attr_list=["translate"], **setup_kwargs),
    )
    leg_setup_io_node = leg_setup_inst.io_node

    leg_setup_io_node_hier_attr = leg_setup_io_node[data.HierDataAttrNames.hier.value]

    leg_anim_inst = anim_components.HingeAnimComponent()
    leg_anim_inst.create_component(
        componentInstName=leg_setup_io_node["componentInstName"],
        hier_side=leg_setup_io_node[data.HierDataAttrNames.hier_side.value],
        hier0=leg_setup_io_node_hier_attr[0],
        hier1=leg_setup_io_node_hier_attr[1],
        hier2=leg_setup_io_node_hier_attr[2],
        ik_root_matrix=leg_setup_io_node_hier_attr[0][data.HierAttrNames.output_world_matrix.value],
        ik_pole_matrix=leg_setup_io_node["poleMatrix"],
        ik_goal_matrix=leg_setup_io_node_hier_attr[2][data.HierAttrNames.output_world_matrix.value],
        fk_kwargs=utils.kwarg_to_dict(
            hier_control_class=control_components.BoxControl,
            hier_shape_color=utils_enum.Colors.blue,
            hier0=utils.kwarg_to_dict(
                build_translate = [2.5, 0.0, 0.0],
                build_scale = [1.9, 0.8, 0.8]
            ),
            hier1=utils.kwarg_to_dict(
                build_translate = [2.5, 0.0, 0.0],
                build_scale = [1.9, 0.7, 0.7]
            ),
            hier2=utils.kwarg_to_dict(
                build_translate = [0.5, 0.0, 0.0],
                build_scale = 0.5
            ),
        ),
        ik_kwargs=utils.kwarg_to_dict(
            root_cntrl=utils.kwarg_to_dict(
                control_class=control_components.BoxControl,
                shape_color=utils_enum.Colors.blue,
                build_scale=[0.3, 1.2, 1.2],
                name="ikHip"
            ),
            goal_cntrl=utils.kwarg_to_dict(
                control_class=control_components.BoxControl,
                shape_color=utils_enum.Colors.blue,
                build_scale=[0.3, 1.2, 1.2],
                name="ikFoot"
            ),
            pole_cntrl=utils.kwarg_to_dict(
                control_class=control_components.Pyramid4Control,
                shape_color=utils_enum.Colors.blue,
                build_rotate=[0, 45, 0],
                build_scale=0.6,
                name="ikPole"
            )
        )
    )

    arm_setup_inst = setup_components.HingeSetup()
    arm_setup_inst.create_component(
        instance_name="Arm",
        hier_side=utils_enum.CharacterSide.left,
        hier0=data.HierBuildData(name="hip", input_matrix=utils.translate_to_matrix([3, 20, 1]), publish_attr_list=["translate"], **setup_kwargs),
        hier1=data.HierBuildData(name="knee", input_matrix=utils.translate_to_matrix([5.5, 17.5, 0]), publish_attr_list=["translate"], **setup_kwargs),
        hier2=data.HierBuildData(name="ankle", input_matrix=utils.translate_to_matrix([8, 15, 1]), publish_attr_list=["translate"], **setup_kwargs),
    )

    arm_setup_inst.parent(leg_setup_io_node["hier"][0])
    arm_setup_io_node = arm_setup_inst.io_node

    

    arm_setup_io_node_hier_attr = arm_setup_io_node[data.HierDataAttrNames.hier.value]

    arm_anim_inst = anim_components.HingeAnimComponent()
    arm_anim_inst.create_component(
        componentInstName=arm_setup_io_node["componentInstName"],
        hier_side=arm_setup_io_node[data.HierDataAttrNames.hier_side.value],
        hier0=arm_setup_io_node_hier_attr[0],
        hier1=arm_setup_io_node_hier_attr[1],
        hier2=arm_setup_io_node_hier_attr[2],
        ik_root_matrix=arm_setup_io_node_hier_attr[0][data.HierAttrNames.output_world_matrix.value],
        ik_pole_matrix=arm_setup_io_node["poleMatrix"],
        ik_goal_matrix=arm_setup_io_node_hier_attr[2][data.HierAttrNames.output_world_matrix.value],
        fk_kwargs=utils.kwarg_to_dict(
            hier_control_class=control_components.BoxControl,
            hier_shape_color=utils_enum.Colors.blue,
            hier0=utils.kwarg_to_dict(
                build_translate = [2, 0.0, 0.0],
                build_scale = [1.5, 0.8, 0.8]
            ),
            hier1=utils.kwarg_to_dict(
                build_translate = [2, 0.0, 0.0],
                build_scale = [1.5, 0.7, 0.7]
            ),
            hier2=utils.kwarg_to_dict(
                build_translate = [0.5, 0.0, 0.0],
                build_scale = 0.5
            ),
        ),
        ik_kwargs=utils.kwarg_to_dict(
            root_cntrl=utils.kwarg_to_dict(
                control_class=control_components.BoxControl,
                shape_color=utils_enum.Colors.blue,
                build_scale=[0.3, 1.2, 1.2],
                name="ikHip"
            ),
            goal_cntrl=utils.kwarg_to_dict(
                control_class=control_components.BoxControl,
                shape_color=utils_enum.Colors.blue,
                build_scale=[0.3, 1.2, 1.2],
                name="ikFoot"
            ),
            pole_cntrl=utils.kwarg_to_dict(
                control_class=control_components.Pyramid4Control,
                shape_color=utils_enum.Colors.blue,
                build_rotate=[0, 45, 0],
                build_scale=0.6,
                name="ikPole"
            )
        )
    )

    leg_setup_inst.mirror(direction=utils_enum.AxisEnums.x, mirror_dependencies=True, dynamic=True, shape_color=utils_enum.Colors.red)
    arm_setup_inst.mirror(direction=utils_enum.AxisEnums.x, mirror_dependencies=True, dynamic=True, shape_color=utils_enum.Colors.red)
    """
    component_ui = ui.ComponentCreatorUI()
    component_ui.show()

    # -------------------------------------------------------------------------

    # char_inst = character_components.CharacterComponent()
    # char_inst.create_component(
    #     instance_name="maleA",
    # )

    # anim_inst = char_inst.insert_component(
    #     anim_components.HingeAnimComponent,
    #     build=False
    # )

    # anim_io_node = anim_inst.io_node
    # anim_io_node["hierSide"] = utils_enum.CharacterSide.index_of(utils_enum.CharacterSide.left)
    # anim_io_node["componentInstName"] = "leg"
    # anim_io_node["hier"][0][data.HierAttrNames.hier_name.value] = "hip"
    # anim_io_node["hier"][1][data.HierAttrNames.hier_name.value] = "knee"
    # anim_io_node["hier"][2][data.HierAttrNames.hier_name.value] = "ankle"

    # anim_inst.rename_nodes()
    # anim_inst.build_component()

    # hip_cntrl = nw.Node("maleA__character_component:L_leg__hinge_anim_component:hinge_setup:hip__sphere_control:control")
    # hip_cntrl["t"] = [3, 6, 0]
    # knee_cntrl = nw.Node("maleA__character_component:L_leg__hinge_anim_component:hinge_setup:knee__sphere_control:control")
    # knee_cntrl["t"] = [3, 0, 0.5]
    # ankle_cntrl = nw.Node("maleA__character_component:L_leg__hinge_anim_component:hinge_setup:ankle__sphere_control:control")
    # ankle_cntrl["t"] = [3, -5, 0]

    # anim_inst.mirror_component(direction=utils_enum.AxisEnums.x, dynamic=True)


    # -------------------------------------------------------------------------
    # char_inst = character_components.BipedCharacter()
    # char_inst.create_component(
    #     instance_name="Tanner",
    #     primary_side = utils_enum.CharacterSide.left,
    #     non_mirror_side = utils_enum.CharacterSide.mid,
    #     non_mirror_color = utils_enum.Colors.yellow,
    #     setup_color = utils_enum.Colors.yellow,
    #     primary_side_color = utils_enum.Colors.blue,
    #     mirror_side_color = utils_enum.Colors.red,
    #     secondary_side_color = utils_enum.Colors.light_blue,
    #     mirror_secondary_side_color = utils_enum.Colors.light_pink
    # )

    # setup_kwargs=utils.kwarg_to_dict(control_class=control_components.SphereControl, build_scale=0.3)
    # fk_kwargs=utils.kwarg_to_dict(
    #     hier_control_class=control_components.BoxControl,
    #     hier0=utils.kwarg_to_dict(
    #         build_translate = [2.5, 0.0, 0.0],
    #         build_scale = [1.9, 0.8, 0.8]
    #     ),
    #     hier1=utils.kwarg_to_dict(
    #         build_translate = [2.5, 0.0, 0.0],
    #         build_scale = [1.9, 0.7, 0.7]
    #     ),
    #     hier2=utils.kwarg_to_dict(
    #         build_translate = [0.5, 0.0, 0.0],
    #         build_scale = 0.5
    #     ),
    # )
    # ik_kwargs=utils.kwarg_to_dict(
    #     root_cntrl=utils.kwarg_to_dict(
    #         control_class=control_components.BoxControl,
    #         build_scale=[0.3, 1.2, 1.2],
    #         name="ikHip"
    #     ),
    #     goal_cntrl=utils.kwarg_to_dict(
    #         control_class=control_components.BoxControl,
    #         build_scale=[0.3, 1.2, 1.2],
    #         name="ikFoot"
    #     ),
    #     pole_cntrl=utils.kwarg_to_dict(
    #         control_class=control_components.Pyramid4Control,
    #         build_rotate=[0, 45, 0],
    #         build_scale=0.6,
    #         name="ikPole"
    #     )
    # )

    # spine_anim_inst = char_inst.insert_component(
    #     anim_components.HingeAnimComponent,
    #     hier_parent=char_inst.root_cntrl_node["worldMatrix"][0],
    #     instance_name="Spine",
    #     hier_side=utils_enum.CharacterSide.mid,
    #     ik_parent_matrix=char_inst.root_cntrl_node["worldMatrix"][0],
    #     ik_kwargs=ik_kwargs,
    #     fk_kwargs=fk_kwargs,
    #     setup_kwargs=setup_kwargs,
    # )

    # leg_anim_inst = char_inst.insert_component(
    #     anim_components.HingeAnimComponent,
    #     instance_name="Leg",
    #     hier_side=utils_enum.CharacterSide.left,
    #     ik_parent_matrix=char_inst.root_cntrl_node["worldMatrix"][0],
    #     ik_kwargs=ik_kwargs,
    #     fk_kwargs=fk_kwargs,
    #     setup_kwargs=setup_kwargs,
    # )

    # arm_anim_inst = char_inst.insert_component(
    #     anim_components.HingeAnimComponent,
    #     instance_name="Arm",
    #     hier_side=utils_enum.CharacterSide.left,
    #     ik_parent_matrix=char_inst.root_cntrl_node["worldMatrix"][0],
    #     ik_kwargs=ik_kwargs,
    #     fk_kwargs=fk_kwargs,
    #     setup_kwargs=setup_kwargs,
    # )

    # leg_anim_inst.parent(spine_anim_inst.io_node["hier"][0])
    # arm_anim_inst.parent(spine_anim_inst.io_node["hier"][2])


    # mirror_components = char_inst.mirror_component_list(
    #     leg_anim_inst,
    #     arm_anim_inst, 
    #     direction=utils_enum.AxisEnums.x, dynamic=True)

    # hier_component = components.HierComponent.get_instance(char_inst)
    # hier_component.add_hiers(leg_anim_inst, arm_anim_inst, spine_anim_inst, *mirror_components)