from system.base_components import Component
import utils.enum as utils_enum
import utils.utils as utils
import components.components as components
import components.control_components as control_components
import components.setup_components as setup_components
import components.anim_component as anim_components
import utils.node_wrapper as nw
import maya.cmds as cmds

import system.data as data

class CharacterComponent(Component):
    component_type = utils_enum.ComponentTypes.character
    has_inst_name_attr = True
    is_rebuildable = False
    root_transform_name = "charGrp"
    
    # add post modules

    @property
    def root_cntrl_node(self):
        if self.container_node is not None and self.container_node.has_attr("rootCntrl"):
            return utils.get_first_connected_node(self.container_node["rootCntrl"], as_source=True)
    
    @property
    def non_move_grp_node(self):
        if self.container_node is not None and self.container_node.has_attr("setupGrp"):
            return utils.get_first_connected_node(self.container_node["setupGrp"], as_source=True)
        
    @property
    def setup_grp_node(self):
        if self.container_node is not None and self.container_node.has_attr("setupGrp"):
            return utils.get_first_connected_node(self.container_node["setupGrp"], as_source=True)

    @property
    def anim_grp_node(self):
        if self.container_node is not None and self.container_node.has_attr("animGrp"):
            return utils.get_first_connected_node(self.container_node["animGrp"], as_source=True)

    def get_component_ui_attrs(self):
        container_node = self.container_node
        return [
            container_node["primarySide"],
            container_node["nonMirrorSide"],
            container_node["setupColor"],
            container_node["nonMirrorColor"],
            container_node["mirrorSideColor"],
            container_node["secondarySideColor"],
            container_node["mirrorSecondarySideColor"],
        ]

    def _init_node_data(self, instance_name=None, **attr_kwargs):
        node_data_dict = super()._init_node_data(instance_name, **attr_kwargs)

        side_index_of = utils_enum.CharacterSide.index_of
        side_enum = utils_enum.CharacterSide

        color_index_of  = utils_enum.Colors.index_of
        color_enum = utils_enum.Colors

        node_data_dict[self._io_name.node_name].add_attr_data(
            data.AttrData("primarySide", publish_name=True, type="enum", enumName=utils_enum.CharacterSide.maya_enum_str(), value=side_index_of(side_enum.left)),
            data.AttrData("nonMirrorSide", publish_name=True, type="enum", enumName=utils_enum.CharacterSide.maya_enum_str(), value=side_index_of(side_enum.mid)),
            data.AttrData("setupColor", publish_name=True, type="enum", enumName=utils_enum.Colors.maya_enum_str(), value=color_index_of(color_enum.yellow)),
            data.AttrData("nonMirrorColor", publish_name=True, type="enum", enumName=utils_enum.Colors.maya_enum_str(), value=color_index_of(color_enum.gold)),
            data.AttrData("primarySideColor", publish_name=True, type="enum", enumName=utils_enum.Colors.maya_enum_str(), value=color_index_of(color_enum.blue)),
            data.AttrData("mirrorSideColor", publish_name=True, type="enum", enumName=utils_enum.Colors.maya_enum_str(), value=color_index_of(color_enum.red)),
            data.AttrData("secondarySideColor", publish_name=True, type="enum", enumName=utils_enum.Colors.maya_enum_str(), value=color_index_of(color_enum.light_blue)),
            data.AttrData("mirrorSecondarySideColor", publish_name=True, type="enum", enumName=utils_enum.Colors.maya_enum_str(), value=color_index_of(color_enum.light_pink)),
            data.AttrData("setupGrpVisibility", publish_name=True, type="bool", value=True),
            data.AttrData("animGrpVisibility", publish_name=True, type="bool", value=True),
            data.AttrData("hierGrpVisibility", publish_name=True, type="bool", value=False),
            data.AttrData("geoGrpVisibility", publish_name=True, type="bool", value=False),
        )

        node_data_dict["container"].add_attr_data(
            data.AttrData("colorManagerComponent", type="message"),
            data.AttrData("axisVectorComponent", type="message"),
        )
        return node_data_dict

    def _pre_build_component(self):
        node_data_dict = super()._pre_build_component()

        io_node = self.io_node

        color_manager_inst = self.insert_component(components.ColorManager)
        utils.map_node_to_container("colorManagerComponent", color_manager_inst.container_node)

        axis_vector_inst = self.insert_component(components.AxesVectors)
        utils.map_node_to_container("axisVectorComponent", axis_vector_inst.container_node)

        root_cntrl_inst = self.insert_component(
            control_components.CircleControl,
            shape_color = self.get_enum_color(io_node["nonMirrorColor"]),
            build_scale=5.0,
            build_rotate=[0, 0, 90],
            transform_parent=self.transform_node
        )
        utils.map_node_to_container("rootCntrl", root_cntrl_inst.transform_node, self.container_node, "charContainer")

        hier_inst = self.insert_component(components.HierComponent, transform_parent=root_cntrl_inst.transform_node)
        
        utils.map_node_to_container("hierComponent", hier_inst.container_node)

        # non move group
        non_move_grp = nw.Node.create_node("transform", "nonMoveGrp")
        setup_grp  = nw.Node.create_node("transform", "setupGrp")
        io_node["setupGrpVisibility"] >> setup_grp["visibility"]
        cmds.parent(str(non_move_grp), str(self.transform_node))
        cmds.parent(str(setup_grp), str(non_move_grp))

        # creating transforms
        anim_grp = nw.Node.create_node("transform", "animGrp")
        geo_grp = nw.Node.create_node("transform", "geoGrp")
        io_node["animGrpVisibility"] >> anim_grp["visibility"]
        io_node["geoGrpVisibility"] >> geo_grp["visibility"]
        cmds.parent([str(x) for x in [geo_grp, anim_grp, self.root_cntrl_node]])

        # adding transforms
        self.container_node.add_nodes(non_move_grp, setup_grp, anim_grp, geo_grp)

        # mapping to container
        utils.map_node_to_container("setupGrp", setup_grp)
        utils.map_node_to_container("animGrp", anim_grp)
        utils.map_node_to_container("nonMoveGrp", non_move_grp)
        utils.map_node_to_container("geoGrp", geo_grp)

        self.anim_grp_node["inheritsTransform"] = False
        self.anim_grp_node["inheritsTransform"].set_locked(True)
        io_node["hierGrpVisibility"] >> hier_inst.transform_node["visibility"]
        hier_inst.transform_node["inheritsTransform"] = False
        hier_inst.transform_node["inheritsTransform"].set_locked(True)

        return node_data_dict
    
    def insert_component(self, component, transform_parent=None, transform_relative=True, **component_kwargs):
        if utils_enum.ComponentTypes.setup == component.component_type:
            transform_parent = self.setup_grp_node
        elif utils_enum.ComponentTypes.anim == component.component_type:
            transform_parent = self.anim_grp_node

        return super().insert_component(component, transform_parent=transform_parent, transform_relative=transform_relative, **component_kwargs)

class BipedCharacter(CharacterComponent):
    def _pre_build_component(self):
        node_data_dict = super()._pre_build_component()

        setup_kwargs=utils.kwarg_to_dict(control_class=control_components.SphereControl, build_scale=0.3)
        fk_kwargs=utils.kwarg_to_dict(
            hier_control_class=control_components.BoxControl,
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
        )
        ik_kwargs=utils.kwarg_to_dict(
            root_cntrl=utils.kwarg_to_dict(
                control_class=control_components.BoxControl,
                build_scale=[0.3, 1.2, 1.2],
                name="ikHip"
            ),
            goal_cntrl=utils.kwarg_to_dict(
                control_class=control_components.BoxControl,
                build_scale=[0.3, 1.2, 1.2],
                name="ikFoot"
            ),
            pole_cntrl=utils.kwarg_to_dict(
                control_class=control_components.Pyramid4Control,
                build_rotate=[0, 45, 0],
                build_scale=0.6,
                name="ikPole"
            )
        )

        spine_anim_inst = self.insert_component(
            anim_components.HingeAnimComponent,
            hier_parent=self.root_cntrl_node["worldMatrix"][0],
            instance_name="Spine",
            hier_side=utils_enum.CharacterSide.mid,
            hier0=data.HierBuildData(name="spine1", input_matrix=utils.translate_to_matrix([0, 11, 1]), publish_attr_list=["translate"], **setup_kwargs),
            hier1=data.HierBuildData(name="spine2", input_matrix=utils.translate_to_matrix([0, 15.5, 0.95]), publish_attr_list=["translate"], **setup_kwargs),
            hier2=data.HierBuildData(name="spine3", input_matrix=utils.translate_to_matrix([0, 20, 1]), publish_attr_list=["translate"], **setup_kwargs),
            ik_parent_matrix=self.root_cntrl_node["worldMatrix"][0],
            ik_kwargs=ik_kwargs,
            fk_kwargs=fk_kwargs,
            setup_kwargs=setup_kwargs,
        )

        leg_anim_inst = self.insert_component(
            anim_components.HingeAnimComponent,
            instance_name="Leg",
            hier_side=utils_enum.CharacterSide.left,
            hier0=data.HierBuildData(name="hip", input_matrix=utils.translate_to_matrix([2.7, 11, 1]), publish_attr_list=["translate"], **setup_kwargs),
            hier1=data.HierBuildData(name="knee", input_matrix=utils.translate_to_matrix([3.1, 6, 2]), publish_attr_list=["translate"], **setup_kwargs),
            hier2=data.HierBuildData(name="ankle", input_matrix=utils.translate_to_matrix([3.3, 1, 1]), publish_attr_list=["translate"], **setup_kwargs),
            ik_parent_matrix=self.root_cntrl_node["worldMatrix"][0],
            ik_kwargs=ik_kwargs,
            fk_kwargs=fk_kwargs,
            setup_kwargs=setup_kwargs,
        )

        arm_anim_inst = self.insert_component(
            anim_components.HingeAnimComponent,
            instance_name="Arm",
            hier_side=utils_enum.CharacterSide.left,
            hier0=data.HierBuildData(name="hip", input_matrix=utils.translate_to_matrix([3, 20, 1]), publish_attr_list=["translate"], **setup_kwargs),
            hier1=data.HierBuildData(name="knee", input_matrix=utils.translate_to_matrix([5.5, 17.5, 0]), publish_attr_list=["translate"], **setup_kwargs),
            hier2=data.HierBuildData(name="ankle", input_matrix=utils.translate_to_matrix([8, 15, 1]), publish_attr_list=["translate"], **setup_kwargs),
            ik_parent_matrix=self.root_cntrl_node["worldMatrix"][0],
            ik_kwargs=ik_kwargs,
            fk_kwargs=fk_kwargs,
            setup_kwargs=setup_kwargs,
        )

        leg_anim_inst.parent(spine_anim_inst.io_node["hier"][0])
        arm_anim_inst.parent(spine_anim_inst.io_node["hier"][2])


        mirror_components = self.mirror_component_list(
            leg_anim_inst,
            arm_anim_inst, 
            direction=utils_enum.AxisEnums.x, dynamic=True)

        hier_component = components.HierComponent.get_instance(self)
        hier_component.add_hiers(leg_anim_inst, arm_anim_inst, spine_anim_inst, *mirror_components)

        return node_data_dict