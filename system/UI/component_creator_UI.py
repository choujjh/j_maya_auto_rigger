import maya.cmds as cmds

from PySide2 import QtCore
from PySide2 import QtWidgets
from PySide2 import QtGui
import utils.ui as util_uis
import utils.cmds as util_cmds
import utils.enum as util_enums
import utils.node_wrapper as nw
import components.character_component as character_components
import components.anim_component as anim_components
import system.base_components as base_components
import components.components as components


import re
from functools import partial


"""
class AttrTreeWidget(QtWidgets.QTreeWidget):
    class AttrTreeItem(QtWidgets.QTreeWidgetItem):
        def __init__(self, parent, dropdown_connection, item_name=None, item_type=0, item_multi_checked=False):
            super(AttrTreeWidget.AttrTreeItem, self).__init__(parent)

            self._dropdown_options = ["bool", "compound", "double2", "double3", "enum", "float", "int", "matrix", "mesh", "message", "nurbsCurve", "nurbsSurface", "string"]

            self.enum_attributes = None
            self.attr_type_combo_box = None
            self.attr_multi_check_box = None

            self._dropdown_connection = dropdown_connection 

            index = item_type
            if isinstance(item_type, str) and item_type in self._dropdown_options:
                index = self._dropdown_options.index(item_type)
            self._attr_type_index = index
            self._attr_multi = item_multi_checked

            self.add_widgets()
            self.set_values(item_name=item_name)
            self.setFlags(self.flags() | QtCore.Qt.ItemIsEditable)

        def get_all_children(self, item=None):
            children = []
            if item is None:
                item=self
            for i in range(item.childCount()):
                child = item.child(i)
                children.append(child)
                children.extend(item.get_all_children(child))
            return children
        
        def add_widgets(self):
            self.create_dropdown_option_box()
            self.create_multi_checkbox()

            self.set_values(item_type=self._attr_type_index, item_multi_checked=self._attr_multi)

        def create_dropdown_option_box(self):
            dropdown_cb = QtWidgets.QComboBox()
            dropdown_cb.addItems(self._dropdown_options)

            self.attr_type_combo_box = dropdown_cb
            self.treeWidget().setItemWidget(self, 1, self.attr_type_combo_box)

            self.attr_type_combo_box.currentIndexChanged.connect(self._update_internal_vals)
            self.attr_type_combo_box.currentIndexChanged.connect(self._dropdown_connection)

            # self.attr_type_combo_box.currentIndexChanged.connect(self._type_change)
        
        def create_multi_checkbox(self):
            cb = QtWidgets.QCheckBox()

            center_layout = QtWidgets.QHBoxLayout()
            center_layout.addWidget(cb)
            center_layout.setAlignment(QtCore.Qt.AlignHCenter)

            center_widget = QtWidgets.QWidget()
            center_widget.setLayout(center_layout)

            self.attr_multi_check_box = cb
            self.treeWidget().setItemWidget(self, 2, center_widget)

            self.attr_multi_check_box.stateChanged.connect(self._update_internal_vals)

        def get_values(self):
            item_name = self.text(0)
            item_type = self.attr_type_combo_box.currentText()
            item_type_index = self.attr_type_combo_box.currentIndex()
            item_multi_checked = self.attr_multi_check_box.isChecked()
            return {"name":item_name, "type_index":item_type_index, "type_string":item_type, "multi_value":item_multi_checked}
        
        def set_values(self, item_name=None, item_type=0, item_multi_checked=False):
            if item_name is not None:
                self.setText(0, item_name)
            if item_type is not None:
                index = item_type
                if isinstance(item_type, str) and item_type in self._dropdown_options:
                    index = self._dropdown_options.index(item_type)
                self.attr_type_combo_box.setCurrentIndex(index)
            if item_multi_checked is not None:
                self.attr_multi_check_box.setChecked(item_multi_checked)

        def unparent_children(self):
            update_children_list = self.get_all_children()

            item_parent = self.parent()
            # top level
            item_index = -1
            
            if item_parent is None:
                item_index = self.treeWidget().indexOfTopLevelItem(self)
            # other
            else:
                item_index = item_parent.indexOfChild(self)
                
            for index in range(self.childCount()-1, -1, -1):
                child_item = self.takeChild(index)
                if item_parent is None:
                    tree_widget = self.treeWidget()
                    tree_widget.insertTopLevelItem(item_index+1, child_item)
                else:
                    item_parent.insertChild(item_index+1, child_item)

            for child_item in update_children_list:
                child_item.add_widgets()

        def _update_internal_vals(self):
            self._attr_type_index = self.attr_type_combo_box.currentIndex()
            self._attr_multi = self.attr_multi_check_box.isChecked()

        def get_parent_string(self):
            item=self.parent()
            if item is None:
                return None
            return item.get_values()["name"]

        def generate_add_attr_parameters(self):
            values = self.get_values()
            kwargs = {"long_name":values["name"], "type":values["type_string"], "multi":values["multi_value"]}
            parent_str = self.get_parent_string()
            if parent_str is not None:
                kwargs["parent"] = parent_str
            if values["type_string"] == "enum":
                if self.enum_attributes is None:
                    enum_attributes = ["Green", "Blue"]
                else:
                    enum_attributes = [x for x in self.enum_attributes if x != ""]
                kwargs["enumName"] = ":".join(enum_attributes)
            if values["type_string"] == "compound":
                kwargs["numberOfChildren"] = self.childCount()
            return kwargs

    type_change_event = QtCore.Signal()
    def __init__(self):
        super(AttrTreeWidget, self).__init__()

        self.setHeaderLabels(["name", "type", "multi"])
        self.setColumnWidth(0, 200)
        self.setColumnWidth(1, 120)
        self.setColumnWidth(2, 60)

        # drag and drop
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)

        self.type_change_event.connect(self.type_change)
        self.itemChanged.connect(self.set_unique_name)

    def selectedItems(self):
        selected_items = super(AttrTreeWidget, self).selectedItems()
        if selected_items is None:
            return []
        return selected_items
    
    def dropEvent(self, event):
        # save data
        items = []
        selected_items = self.selectedItems()
        for item in selected_items:
            items.append(item)
            items.extend(item.get_all_children())

        super(AttrTreeWidget, self).dropEvent(event)

        # reparent if not under compound
        for item in selected_items:
            item_parent = item.parent()
            if item_parent is not None:
                if item_parent.get_values()["type_string"] not in ["compound", "double3", "double2"]:
                    item_parent.unparent_children()

            self.setCurrentIndex(self.indexFromItem(item))

        # rebuild data
        for item in items:
            item.add_widgets()

    def add_item(self, item_name="tempAttrName", item_type=0, item_multi_checked=False, parent_item=None,):
        if parent_item is None:
            parent_item = self
        item = AttrTreeWidget.AttrTreeItem(parent_item, self.dropdown_connection, item_name=item_name, item_type=item_type, item_multi_checked=item_multi_checked)
        self.set_unique_name(item)

    def delete_selected_item(self):
        selected_items = self.selectedItems()
        for item in selected_items:
            item_parent = item.parent()
            if item_parent is None:
                self.takeTopLevelItem(self.indexOfTopLevelItem(item))
            else:
                item_parent.removeChild(item)

    def dropdown_connection(self):
        self.type_change_event.emit()

    def type_change(self):
        try:
            self.type_change_event.disconnect(self.type_change)
        except:
            pass

        selected_items = self.selectedItems()
        for item in selected_items:
            attr_type = item.get_values()["type_string"]
            if attr_type != "compound":
                item.unparent_children()

        self.type_change_event.connect(self.type_change)

    def get_all_items(self):
        item_list = []
        for i in range(self.topLevelItemCount()):
            top_level_child = self.topLevelItem(i)
            item_list.append(top_level_child)
            item_list.extend(top_level_child.get_all_children())
        return item_list

    def generate_attribute_parameters(self):
        all_attr = [item.generate_add_attr_parameters() for item in self.get_all_items()]
        return all_attr

    def set_unique_name(self, item, column=0):
        current_item_name = item.get_values()["name"]
        current_item_name = re.sub(r"[^a-zA-Z0-9_]", "_", current_item_name)
        item_names = [curr_item.get_values()["name"] for curr_item in self.get_all_items() if curr_item != item]
        
        if current_item_name in item_names:
            new_name = re.sub(r'\d+$', "", current_item_name)
            new_name_index = re.search(r'\d+$', current_item_name)
            if new_name_index is None:
                new_name_index = 1
            else:
                new_name_index = int(new_name_index.group())
            new_full_name = "{0}{1}".format(new_name, new_name_index)
            while new_full_name in item_names:
                new_name_index += 1
                new_full_name = "{0}{1}".format(new_name, new_name_index)

            item.set_values(item_name=new_full_name)

class AddEnumAttrWidget(QtWidgets.QWidget):
    update_item = QtCore.Signal(list)
    def __init__(self):
        super(AddEnumAttrWidget, self).__init__()

        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.enum_list_widget = QtWidgets.QListWidget()
        self.enum_list_widget.setSpacing(1)

    def create_layout(self):
        # enum_layout
        enum_layout = QtWidgets.QVBoxLayout()
        enum_layout.addWidget(QtWidgets.QLabel("Enum Names"))
        enum_layout.addWidget(self.enum_list_widget)
        enum_layout.setContentsMargins(0, 0, 0, 0)

        # enum_widget
        self.setLayout(enum_layout)
    
    def create_connections(self):
        self.enum_list_widget.itemChanged.connect(self.update_enum_list)

    def get_enum_list_widget(self):
        return self.enum_list_widget
    
    def reset_enum_items(self):
        self.set_enum_list(["Green", "Blue"])

    def add_enum_item(self, text=""):
        item = QtWidgets.QListWidgetItem(text)
        item.setSizeHint(QtCore.QSize(100, 15))
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        self.enum_list_widget.addItem(item)

    def update_enum_list(self, emit_signal=True):
        index = self.enum_list_widget.count() - 1

        if self.enum_list_widget.item(index).text() != "":
            self.add_enum_item()
        index -= 1

        while index >= 0:
            if self.enum_list_widget.item(index).text() == "":
                self.enum_list_widget.takeItem(index)

            index -= 1
        if emit_signal:
            self.update_item.emit(self.get_enum_list_values())

    def set_enum_list(self, text_list):
        try:
            self.enum_list_widget.itemChanged.disconnect(self.update_enum_list)
        except:
            pass
        self.enum_list_widget.clear()
        if text_list is None:
            text_list = ["Green", "Blue"]
        for text in text_list:
            self.add_enum_item(text)
        
        self.update_enum_list(emit_signal=False)

        self.enum_list_widget.itemChanged.connect(self.update_enum_list)

    def get_enum_list_values(self):
        return [self.enum_list_widget.item(x).text() for x in range(self.enum_list_widget.count())]

class AddAttrUI(utils_ui.JBaseMayaDialog):
    def __init__(self, parent=utils_ui.maya_main_window()):
        super(AddAttrUI, self).__init__("Attr Creator", parent)
        self.setMinimumWidth(450)
        self.setMinimumHeight(200)

    def create_widgets(self):
        
        self.add_attr_tree = AttrTreeWidget()

        self.enum_list_widget = AddEnumAttrWidget()
        self.enum_list_widget.reset_enum_items()

        self.add_attr_btn = QtWidgets.QPushButton()
        self.delete_attr_btn = QtWidgets.QPushButton()
        self.clear_attr_btn = QtWidgets.QPushButton()
        self.add_attr_btn.setIcon(QtGui.QIcon(":item_add.png"))
        self.delete_attr_btn.setIcon(QtGui.QIcon(":item_delete.png"))
        self.clear_attr_btn.setIcon(QtGui.QIcon(":clearAll.png"))
        QtGui.QIcon
        self.add_all_attrs_btn = QtWidgets.QPushButton("Add All Attributes")
    def create_layout(self):

        # button layout
        button_layout = QtWidgets.QVBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(self.add_attr_btn)
        button_layout.addWidget(self.delete_attr_btn)
        button_layout.addWidget(self.clear_attr_btn)
        button_layout.addStretch()

        # button with tree
        tree_layout = QtWidgets.QHBoxLayout()
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.addLayout(button_layout)
        tree_layout.addWidget(self.add_attr_tree)

        # inner layout
        inner_layout = QtWidgets.QVBoxLayout()
        inner_layout.setContentsMargins(10, 10, 10, 10)
        inner_layout.addLayout(tree_layout)
        inner_layout.addWidget(self.enum_list_widget)
        self.enum_list_widget.hide()

        # creating border for inner layout
        inner_border = QtWidgets.QFrame()
        inner_border.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Sunken)
        inner_border.setLayout(inner_layout)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(inner_border)
        layout.addWidget(self.add_all_attrs_btn)

        self.setLayout(layout)
    def create_connections(self):
        self.add_attr_tree.currentItemChanged.connect(self.update_enum_list_selection)
        self.add_attr_tree.type_change_event.connect(self.update_enum_list_type_change)
        self.enum_list_widget.update_item.connect(self.update_tree_saved_enum)
        

        self.add_attr_btn.clicked.connect(self.add_attr_tree.add_item)
        self.delete_attr_btn.clicked.connect(self.add_attr_tree.delete_selected_item)
        self.clear_attr_btn.clicked.connect(self.add_attr_tree.clear)

        self.add_all_attrs_btn.clicked.connect(self.add_all_attr)
    
    def update_enum_list_type_change(self):
        selected_items = self.add_attr_tree.selectedItems()
        enum_list_vis = False
        for item in selected_items:
            item_data = item.get_values()
            if item_data["type_string"] == "enum":
                enum_list_vis = True
            else:
                item.enum_attributes = None
        self.update_enum_list_vis(enum_list_vis)

    def update_enum_list_selection(self, current, previous):
        enum_list_vis = False
        if current is not None:
            item_data = current.get_values()
            if item_data["type_string"] == "enum":
                self.enum_list_widget.set_enum_list(current.enum_attributes)
                enum_list_vis = True
            else:
                self.enum_list_widget.reset_enum_items()
            
        self.update_enum_list_vis(enum_list_vis)

    def update_enum_list_vis(self, enum_list_vis):
        if enum_list_vis:
            self.enum_list_widget.show()
        else:
            self.enum_list_widget.hide()

    def update_tree_saved_enum(self, enum_list_values):
        for item in self.add_attr_tree.selectedItems():
            item.enum_attributes = enum_list_values

    def add_all_attr(self):
        add_attr_args_list = self.add_attr_tree.generate_attribute_parameters()
        selection = utils_cmds.ls(sl=True)
        for obj in selection:
            for add_attr_args in add_attr_args_list:
                obj.add_attr(**add_attr_args)
"""
class ComponentCreatorUI(util_uis.JBaseMayaDialog):
    def __init__(self, parent=util_uis.maya_main_window()):
        self.current_ui_component = None
        self._component_info_widgets = []
        super(ComponentCreatorUI, self).__init__("Component Creator", parent)

    def create_widgets(self):
        self.character_component_list_wdg = util_uis.ComponentListUI("Character Components")
        self.animation_component_list_wdg = util_uis.ComponentListUI("Animation Components")

        self.parent_btn = QtWidgets.QPushButton("Parent")
        self.rename_btn = QtWidgets.QPushButton("Rename")
        self.delete_btn = QtWidgets.QPushButton("Delete")
        self.mirror_shape_btn = QtWidgets.QPushButton("Mirror Shape")
        self.mirror_btn = QtWidgets.QPushButton("Mirror")
        self.parent_shape_btn = QtWidgets.QPushButton("Parent Shape")
        self.publish_btn = QtWidgets.QPushButton("Publish")
        self.build_btn = QtWidgets.QPushButton("Build")

    def create_layout(self):
        content_margins = 10

        component_layout = QtWidgets.QVBoxLayout()
        component_layout.addWidget(self.character_component_list_wdg)
        component_layout.addWidget(self.animation_component_list_wdg)

        button_grid_layout = QtWidgets.QGridLayout()
        # button_grid_layout.addWidget(self.parent_btn, 0, 0)
        # button_grid_layout.addWidget(self.rename_btn, 0, 1)
        # button_grid_layout.addWidget(self.delete_btn, 0, 2)
        # button_grid_layout.addWidget(self.mirror_shape_btn, 1, 0)
        # button_grid_layout.addWidget(self.mirror_btn, 1, 1)
        # button_grid_layout.addWidget(self.parent_shape_btn, 1, 2)
        # button_grid_layout.addWidget(self.publish_btn, 2, 0)
        # button_grid_layout.addWidget(self.build_btn, 2, 1)

        button_grid_layout.addWidget(self.parent_btn, 0, 0)
        button_grid_layout.addWidget(self.mirror_btn, 0, 1)
        button_grid_layout.addWidget(self.build_btn, 0, 2)
        
        self.char_info_layout = QtWidgets.QVBoxLayout()
        self.char_info_layout.setContentsMargins(5, 5, 5, 5)
        self.char_info_layout.setSpacing(5)

        self.component_info_layout = QtWidgets.QVBoxLayout()
        self.component_info_layout.setContentsMargins(5, 5, 5, 5)
        self.component_info_layout.setSpacing(5)
        
        info_layout = QtWidgets.QVBoxLayout()
        info_layout.addWidget(QtWidgets.QLabel("Character Attributes"))
        info_layout.addWidget(util_uis.JBorderWidget(layout=self.char_info_layout))
        info_layout.addWidget(QtWidgets.QLabel("Component Attributes"))
        info_layout.addWidget(util_uis.JBorderWidget(layout=self.component_info_layout))
        info_layout.addStretch()
        info_layout.addLayout(button_grid_layout)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(*[content_margins for x in range(4)])
        layout.addLayout(component_layout)
        layout.addLayout(info_layout)

        self.setLayout(layout)

    def create_connections(self):
        self.character_component_list_wdg.add_btn.clicked.connect(self.add_character_component)
        self.character_component_list_wdg.delete_btn.clicked.connect(self.character_component_list_wdg.delete_current_component)
        self.character_component_list_wdg.table_wdg.currentCellChanged.connect(self.refresh_anim_components)
        self.character_component_list_wdg.table_wdg.currentCellChanged.connect(partial(self.update_component_info, self.character_component_list_wdg))

        self.animation_component_list_wdg.add_btn.clicked.connect(self.initialize_anim_component)
        self.animation_component_list_wdg.delete_btn.clicked.connect(self.animation_component_list_wdg.delete_current_component)
        self.animation_component_list_wdg.table_wdg.currentCellChanged.connect(partial(self.update_component_info, self.animation_component_list_wdg))

        # button connections
        self.parent_btn.clicked.connect(self.parent_btn_action)
        self.mirror_btn.clicked.connect(self.mirror_btn_action)
        self.build_btn.clicked.connect(self.build_btn_action)

    def update_component_info(self, component_list_wdg, *args):
        #see if it can be built
        self.current_ui_component = component_list_wdg.get_current_component()
        io_node = self.current_ui_component.io_node

        for component_wdg in self._component_info_widgets:
            component_wdg.deleteLater()
        self._component_info_widgets = []

        character_component = self.character_component_list_wdg.get_current_component()
        char_attrs = [character_component.container_node[x] for x in ["setupGrpVisibility", "animGrpVisibility", "hierGrpVisibility"]]
        for char_attr in char_attrs:
            self._component_info_widgets.append(util_uis.AttrItem(char_attr))
            self.char_info_layout.addWidget(self._component_info_widgets[-1])

        for attr in self.current_ui_component.get_component_ui_attrs():
            self._component_info_widgets.append(util_uis.AttrItem(attr))
            self.component_info_layout.addWidget(self._component_info_widgets[-1])

        # set buttons
        if self.current_ui_component is None or io_node["built"].value:
            self.build_btn.setEnabled(False)
        else:
            self.build_btn.setEnabled(True)

        # set mirror
        if self.current_ui_component is None or not io_node["built"].value:
            self.mirror_btn.setEnabled(False)
        else:
            is_mirrorable = self.current_ui_component.mirror_dest_container == None and self.current_ui_component.mirror_source_container == None and type(self.current_ui_component).component_type == util_enums.ComponentTypes.anim
            self.mirror_btn.setEnabled(is_mirrorable)

        # set parent
        # component_has_parent self._curr_selected_component(util_enums.)

    def parent_btn_action(self, *args):
        selection = [nw.Node(x) for x in cmds.ls(sl=True, long=True)]
        if len(selection) < 2:
            cmds.warning("need to select at least 2 setup objects")
            return
        
        # getting parent all set up 
        parent = selection.pop(-1)
        parent_container = parent
        if parent.node_type != "container":
            parent_container = parent.get_container()
        parent_inst = base_components.get_component(parent_container)
        parent_setup_inst = parent_inst.get_parent_component_of_type(util_enums.ComponentTypes.setup)

        # checking to see if it's in setup component
        if parent_setup_inst is None:
            cmds.warning("{} is not a setup control".format(parent))
            return

        # getting anim attr
        anim_inst = parent_inst.get_parent_component_of_type(util_enums.ComponentTypes.anim)
        if anim_inst is None:
            cmds.warning("{} does not have a parent anim component".format(parent))
            return
        parent_attr = None

        for x in parent_container["worldMatrix"].get_as_source_connection_list():
            if x.attr_name.startswith("hier["):
                parent_attr = x
                break
        if parent_attr is None:
            cmds.warning("hier attr not found")
            return
        parent_attr_name = parent_attr.attr_name.rsplit(".")[0]
        if not anim_inst.container_node.has_attr(parent_attr_name):
            cmds.warning("{}.{} not found".format(anim_inst.component_container, parent_attr_name))
        parent_anim_attr = anim_inst.container_node[parent_attr_name]
        
        # parenting everything else
        parented_instances = [parent_inst]
        for curr in selection:
            curr_container = curr
            
            if curr.node_type != "container":
                curr_container = curr.get_container()

            curr_inst = base_components.get_component(curr_container)
            curr_inst = curr_inst.get_parent_component_of_type(util_enums.ComponentTypes.anim)
            if curr_inst is None:
                cmds.warning("{} does not have a parent anim component".format(curr))
                parented_instances.append(curr_inst)
            else:
                if curr_inst not in parented_instances:
                    curr_inst.parent(parent_anim_attr)
                    parented_instances.append(curr_inst)

    def mirror_btn_action(self, *args):
        mirror_window = util_uis.MirrorPlane(parent=self)
        mirror_window.exec_()

        if mirror_window.return_axis is not None:
            mirror_inst = self.current_ui_component.mirror_component(direction=mirror_window.return_axis, dynamic=True)
            char_inst = self.character_component_list_wdg.get_current_component()

            hier_inst = components.HierComponent.get_instance(char_inst)
            hier_inst.add_hiers(mirror_inst)

            self.current_ui_component.mirror_component_input_connections()
            self.refresh_anim_components()
        
    def build_btn_action(self, *args):
        self.current_ui_component.build_component()

        anim_inst = self.current_ui_component

        char_inst = self.character_component_list_wdg.get_current_component()
        hier_inst = components.HierComponent.get_instance(char_inst)
        hier_inst.add_hiers(anim_inst)


        self.refresh_anim_components()

    def add_character_component(self):
        char_class = self.open_component_window(character_components)
        if char_class is None:
            return
        char_inst = char_class()

        char_inst.create_component()


        self.character_component_list_wdg.add_component_info(char_inst)

        self.refresh_anim_components()

    def initialize_anim_component(self):
        #check for character class
        anim_class = self.open_component_window(anim_components)
        if anim_class is None:
            return

        # insert into character class
        char_inst = self.character_component_list_wdg.get_current_component()
        char_inst.insert_component(anim_class, hier_parent=char_inst.root_cntrl_node["worldMatrix"][0], build=False)

        # refresh anim components
        self.refresh_anim_components()

    def refresh_anim_components(self):
        char_inst = self.character_component_list_wdg.get_current_component()
        anim_components = char_inst.get_child_component_of_type(util_enums.ComponentTypes.anim)

        self.animation_component_list_wdg.add_component_info(*anim_components, clear_prev_entries=True)

    def open_component_window(self, module):
        curr = util_uis.SelectComponentUI(parent=self, module=module)
        curr.exec_()
        if curr.return_class is None:
            return None
        return getattr(module, curr.return_class)
    
    def _curr_selected_component(self, component_type):
        sel = cmds.ls(sl=True, ln=True)
        if len(sel) < 0:
            return None
        sel = nw.Node(sel[0])
        if sel.node_type=="container":
            component = base_components.get_component(nw.Container(sel))
            if component is None:
                return None
            return component.get_parent_component_of_type(component_type)

"""
class ComponentCreatorUI(util_ui.JBaseMayaDialog):

    def __init__(self, parent=util_ui.maya_main_window()):
        self._add_attr_window = None
        self._selection_sj = -1
        self._container_attr_link_sj_list = []
        self._install_node = None
        self._component_container = None
        super(ComponentCreatorUI, self).__init__("Component Creator", parent)

        # init ui
        self.update_refs()
        self.update_ui_container_info()

    def create_widgets(self):
        column_spacing = [105, 150]
        self.container_name_wgt = util_ui.JLabeledWidget(QtWidgets.QLineEdit(), "Container:", spacing=column_spacing)
        self.container_name_wgt.other_widget.setEnabled(False)
        self.instance_name_wgt = util_ui.JLabeledWidget(QtWidgets.QLineEdit(), "Instance Name:", spacing=column_spacing)
        self.component_name_wgt = util_ui.JLabeledWidget(QtWidgets.QLineEdit(), "Component Name:", spacing=column_spacing)
        self.component_type_wgt = util_ui.JLabeledWidget(QtWidgets.QComboBox(), "Component Type:", spacing=column_spacing)
        self.component_type_wgt.other_widget.addItems(component_old.Component.ComponentTypes.get_component_type_names())

        self.create_template_btn = QtWidgets.QPushButton("Create Template")
        self.rename_btn = QtWidgets.QPushButton("Rename")
        self.add_freeze_btn = QtWidgets.QPushButton("Add Freeze")
        self.lock_container_btn = QtWidgets.QPushButton("Lock Container")
        self.unlock_container_btn = QtWidgets.QPushButton("Unlock Container")

        self.add_attr_btn = QtWidgets.QPushButton("Add Attribute UI")
        self.publish_btn = QtWidgets.QPushButton("Publish")
        
    def create_layout(self):
        layout = QtWidgets.QVBoxLayout()

        container_layout = util_ui.JBorderWidget()
        container_layout.layout.setContentsMargins(5, 5, 5, 5)
        container_layout.layout.addWidget(self.container_name_wgt)
        container_layout.layout.addWidget(self.instance_name_wgt)
        container_layout.layout.addWidget(self.component_name_wgt)
        container_layout.layout.addWidget(self.component_type_wgt)

        container_options_layout = QtWidgets.QGridLayout()
        container_options_layout.addWidget(self.create_template_btn, 0, 0)
        container_options_layout.addWidget(self.rename_btn, 0, 1)
        container_options_layout.addWidget(self.add_freeze_btn, 1, 0)
        container_options_layout.addWidget(self.lock_container_btn, 2, 0)
        container_options_layout.addWidget(self.unlock_container_btn, 2, 1)
        
        container_layout.layout.addLayout(container_options_layout)

        layout.addWidget(container_layout)
        layout.addStretch()
        layout.addWidget(self.add_attr_btn)
        layout.addWidget(self.publish_btn)

        self.setLayout(layout)

    def create_connections(self):
        self.create_template_btn.clicked.connect(self.create_template_act)
        self.rename_btn.clicked.connect(self.rename_container_nodes)

        self.add_freeze_btn.clicked.connect(self.add_freeze)

        self.lock_container_btn.clicked.connect(self.lock_container_act)
        self.unlock_container_btn.clicked.connect(self.unlock_container_act)

        self.add_attr_btn.clicked.connect(self.create_add_attr_window)
        self.publish_btn.clicked.connect(self.publish_container)

    def create_template_act(self):
        ComponentCreator.create_template(self.component_type_wgt.other_widget.currentIndex())
    def rename_container_nodes(self):
        ComponentCreator.rename_container_nodes(self._component_container)
    def add_freeze(self):
        ComponentCreator.add_freeze_input(self._component_container)
    def lock_container_act(self):
        ComponentCreator.lock_container(self._component_container)
    def unlock_container_act(self):
        ComponentCreator.unlock_container(self._component_container)
    def create_add_attr_window(self):
        if self._add_attr_window is None:
            self._add_attr_window = AddAttrUI(parent=self)
        self._add_attr_window.show()
    def publish_container(self):
        ComponentCreator.publish_container(self._component_container)

    def showEvent(self, event):
        self.create_selection_sj()
        return super(ComponentCreatorUI, self).showEvent(event)

    def hideEvent(self, event):
        self.delete_selection_sj()
        if self._add_attr_window is not None:
            self._add_attr_window.hide()
        return super(ComponentCreatorUI, self).hideEvent(event)
    
    def create_selection_sj(self):
        if cmds.scriptJob(exists=self._selection_sj):
            cmds.scriptJob(kill=self._selection_sj)
        self._selection_sj = cmds.scriptJob(event=["SelectionChanged", self.update_container_attr_sj_list])

    def delete_selection_sj(self):
        if cmds.scriptJob(exists=self._selection_sj):
            cmds.scriptJob(kill=self._selection_sj)

    def get_component_container(self):
        selection = util_cmds.ls(sl=True)
        for node in selection:
            if node.type == "container":
                return node
            container = node.get_container()
            if container is not None:
                return container
    
    def update_refs(self):
        self._component_container = self.get_component_container()
        if self._component_container is not None and self._component_container.has_attr("installNode"):
            self._install_node = self._component_container["installNode"].get_source_connection_list()[0].node

    def update_container_attr_sj_list(self):
        self.update_refs()
        self.update_ui_container_info()

    def update_ui_container_info(self):

        self.container_name_wgt.other_widget.setText("")
        self.instance_name_wgt.other_widget.setText("")
        self.component_name_wgt.other_widget.setText("")
        self.component_type_wgt.other_widget.setCurrentIndex(0)

        if self._component_container is not None and self._install_node is not None:
            self.container_name_wgt.other_widget.setText(str(self._component_container))

            install_attrs = [(self.instance_name_wgt, self._install_node["instanceName"].value),
                                (self.component_name_wgt, self._install_node["componentName"].value)]

            for line_edit, value in install_attrs:
                if value is None:
                    value = ""
                line_edit.other_widget.setText(value)
            self.component_type_wgt.other_widget.setCurrentIndex(self._install_node["componentType"].value)
        
class ComponentCreator():
    @classmethod
    def create_template(cls, component_type):
        # check to see what type it is
        component_type = component_old.Component.ComponentTypes.get(component_type)
        print(component_type)
        if component_type == "control_component":
            component_inst = component_old.ControlComponent()

        else:
            component_inst = component_old.Component()
        component_inst.create_template()

    @classmethod
    def publish_container(cls, container):
        # check to see if name is already taken
        # warning if component name is empty
        if container is not None:
            component_inst = component_old.Component(container_node=container)
            component_inst.publish()
    @classmethod
    def lock_container(cls, container):
        if container is not None:
            component_old.ComponentContainer(str(container)).lock()
    @classmethod
    def unlock_container(cls, container):
        if container is not None:
            component_old.ComponentContainer(str(container)).unlock()
    @ classmethod
    def rename_container_nodes(cls, container):
        if container is not None:
            component_inst = component_old.Component(container_node=container)
            component_inst.rename_component()

    @classmethod
    def add_freeze_input(cls, container):
        if container is not None:
            component_inst = component_old.Component(container_node=container)
            component_inst.add_freeze_component()
"""
"""
from PySide2 import QtGui
from PySide2.QtGui import *
from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtUiTools import *
import shiboken2

widgets = {}
try:
    widgets = {widget.objectName(): widget for widget in QApplication.allWidgets()}
except Exception:
    pass
_widget = widgets.get("MayaWindow", None)


class dataDialog(QDialog):
    
    dataReturned = Signal(str)
    def __init__(self, parent = None):
        super().__init__(parent)
        
        self.returnData = None
        self.addWidgets()
    
    def addWidgets(self):
        self.setLayout(QVBoxLayout())
        self.radioButtons  = [QRadioButton("my info 1"), QRadioButton("my info 2"), QRadioButton("my info 3")]
        for radioButton in self.radioButtons:
            self.layout().addWidget(radioButton )
        
        h = QHBoxLayout()
        confirmButton = QPushButton("confirm")
        cancelButton = QPushButton("cancel")
        h.addWidget(confirmButton )
        h.addWidget(cancelButton )
        
        confirmButton.clicked.connect(self.confirmRadioButton)
        cancelButton.clicked.connect(self.close)
        
        self.layout().addLayout(h)
        
    def confirmRadioButton(self):
        for radioButton in self.radioButtons:
            if radioButton.isChecked():
                self.returnData = radioButton.text()
                self.dataReturned.emit(radioButton.text())
        self.close()
        

class myWindow(QMainWindow):
    def __init__(self, parent=_widget):
        super().__init__(parent)
        
        self.data = None
        self.data1 = None
        self.addWidgets()
    
    def addWidgets(self):
        w = QWidget()
        w.setLayout(QVBoxLayout())
        self.setCentralWidget(w)
        
        self.button = QPushButton("spawn Window")
        self.button.clicked.connect(self.spawnWindow)
        self.button2 = QPushButton("spawn Window")
        self.button2.clicked.connect(self.spawnWindow1)
        self.button1 = QPushButton("print data")
        self.button1.clicked.connect(self.printData)
        
        w.layout().addWidget(QLabel("to open dialog"))
        w.layout().addWidget(self.button)
        w.layout().addWidget(self.button2)
        w.layout().addWidget(QLabel("to print the data"))
        w.layout().addWidget(self.button1)
        
    def spawnWindow(self):
        dlg = dataDialog(self)
        dlg.exec_()
        self.data = dlg.returnData
        
    def spawnWindow1(self):
        dlg = dataDialog(self)
        dlg.dataReturned.connect(self.gatherData)
        dlg.exec_()
    
    def gatherData(self, inString):
        self.data1 = inString

    def printData(self):
        print(self.data)
        print(self.data1)
        
        
a = myWindow()
a.show()
"""