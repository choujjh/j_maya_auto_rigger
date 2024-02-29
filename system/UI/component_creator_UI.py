import maya.cmds as cmds

from PySide2 import QtCore
from PySide2 import QtWidgets
from PySide2 import QtGui
import re

import utils.node_wrapper as nw
import system.component as component
import utils.ui as util_ui
import utils.cmds as util_cmds

import importlib
importlib.reload(nw)
importlib.reload(component)
importlib.reload(util_ui)
importlib.reload(util_cmds)

class AttrTreeWidget(QtWidgets.QTreeWidget):
    class AttrTreeItem(QtWidgets.QTreeWidgetItem):
        def __init__(self, parent, dropdown_connection, item_name=None, item_type=0, item_multi_checked=False):
            super(AttrTreeWidget.AttrTreeItem, self).__init__(parent)

            self._dropdown_options = ["bool", "compound", "enum", "float", "int", "matrix", "mesh", "message", "nurbsCurve", "nurbsSurface", "string"]

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
                if item_parent.get_values()["type_string"] != "compound":
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

class AddAttrUI(util_ui.JBaseMayaDialog):
    def __init__(self, parent=util_ui.maya_main_window()):
        super(AddAttrUI, self).__init__("Attr Creator", parent)
        self.setMinimumWidth(450)
        self.setMinimumHeight(200)

    def create_widgets(self):
        
        self.add_attr_tree = AttrTreeWidget()

        self.enum_list_widget = AddEnumAttrWidget()
        self.enum_list_widget.reset_enum_items()

        self.add_attr_btn = QtWidgets.QPushButton("Add Attribute")
        self.delete_attr_btn = QtWidgets.QPushButton("Delete Attribute")
        self.clear_attr_btn = QtWidgets.QPushButton("Clear Attribute")
        self.add_all_attrs_btn = QtWidgets.QPushButton("Add All Attributes")
    def create_layout(self):

        # button layout
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(self.add_attr_btn)
        button_layout.addWidget(self.delete_attr_btn)
        button_layout.addWidget(self.clear_attr_btn)


        # inner layout
        inner_layout = QtWidgets.QVBoxLayout()
        inner_layout.setContentsMargins(10, 10, 10, 10)
        inner_layout.addWidget(self.add_attr_tree)
        inner_layout.addWidget(self.enum_list_widget)
        inner_layout.addLayout(button_layout)
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
        selection = util_cmds.ls(sl=True)
        for obj in selection:
            for add_attr_args in add_attr_args_list:
                obj.add_attr(**add_attr_args)

class ComponentCreatorUI(util_ui.JBaseMayaDialog):
    def __init__(self, parent=util_ui.maya_main_window()):
        super(ComponentCreatorUI, self).__init__("Component Creator", parent)
        self._add_attr_window = None
        self._selection_sj = -1
        self._container_attr_link_sj_list = []

    def create_widgets(self):
        column_spacing = [105, 150]
        self.container_name_wgt = util_ui.JLabeledWidget(QtWidgets.QLineEdit(), "Container:", spacing=column_spacing)
        self.container_name_wgt.other_widget.setEnabled(False)
        self.user_defined_name_wgt = util_ui.JLabeledWidget(QtWidgets.QLineEdit(), "User Defined Name:", spacing=column_spacing)
        self.component_name_wgt = util_ui.JLabeledWidget(QtWidgets.QLineEdit(), "Component Name:", spacing=column_spacing)
        self.module_type_wgt = util_ui.JLabeledWidget(QtWidgets.QComboBox(), "Component Type:", spacing=column_spacing)
        self.module_type_wgt.other_widget.addItems(component.Component.ComponentTypes.get_component_type_names())

        self.create_template_btn = QtWidgets.QPushButton("Create Template")
        self.rename_btn = QtWidgets.QPushButton("Rename")
        self.lock_container_btn = QtWidgets.QPushButton("Lock Container")
        self.unlock_container_btn = QtWidgets.QPushButton("Unlock Container")

        self.add_attr_btn = QtWidgets.QPushButton("Add Attribute UI")
        self.publish_btn = QtWidgets.QPushButton("Publish")
        
    def create_layout(self):
        layout = QtWidgets.QVBoxLayout()

        container_layout = util_ui.JBorderWidget()
        container_layout.layout.setContentsMargins(5, 5, 5, 5)
        container_layout.layout.addWidget(self.container_name_wgt)
        container_layout.layout.addWidget(self.user_defined_name_wgt)
        container_layout.layout.addWidget(self.component_name_wgt)
        container_layout.layout.addWidget(self.module_type_wgt)

        container_options_layout = QtWidgets.QGridLayout()
        container_options_layout.addWidget(self.create_template_btn, 0, 0)
        container_options_layout.addWidget(self.rename_btn, 0, 1)
        container_options_layout.addWidget(self.lock_container_btn, 1, 0)
        container_options_layout.addWidget(self.unlock_container_btn, 1, 1)
        
        container_layout.layout.addLayout(container_options_layout)

        layout.addWidget(container_layout)
        layout.addStretch()
        layout.addWidget(self.add_attr_btn)
        layout.addWidget(self.publish_btn)

        self.setLayout(layout)

    def create_connections(self):
        self.create_template_btn.clicked.connect(self.create_template_cmd)
        self.publish_btn.clicked.connect(ComponentCreator.publish_template)
        self.add_attr_btn.clicked.connect(self.create_add_attr_window)
        self.lock_container_btn.clicked.connect(ComponentCreator.lock_container)
        self.unlock_container_btn.clicked.connect(ComponentCreator.unlock_container)

    def create_add_attr_window(self):
        if self._add_attr_window is None:
            self._add_attr_window = AddAttrUI(parent=self)
        self._add_attr_window.show()

    def create_template_cmd(self):
        ComponentCreator.create_template(self.module_type_wgt.other_widget.currentIndex())

    def publish_template_cmd(self):
        ComponentCreator.publish_template()

    def showEvent(self, event):
        # self.create_selection_sj()
        return super(ComponentCreatorUI, self).showEvent(event)

    def hideEvent(self, event):
        # self.delete_selection_sj()
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
    def update_container_attr_sj_list(self):
        for sj in self._container_attr_link_sj_list:
            if cmds.scriptJob(exists=sj):
                cmds.scriptJob(kill=sj)
        self._container_attr_link_sj_list = []
        print("update_container_attr_sj_list")
        print(cmds.ls(sl=True))
        pass
    def update_ui_container_info(self):
        pass
        print("update_ui_container_info")
        print(cmds.ls(sl=True))


        
class ComponentCreator():
    @classmethod
    def create_template(cls, component_type):
        component_template = component.Component()
        component_template.install()

    @classmethod
    def is_container(cls, object):
        return cmds.objectType(object) == "container"

    @classmethod
    def publish_template(cls):
        pass
        # component_template = component.Component("tempName", None)
        # selection = cmds.ls(sl=True)
        # if len(selection) > 0:
        #     if cls.is_container(selection[0]):
        #         component_template.publish(nw.Container(selection[0]))
    @classmethod
    def lock_container(cls):
        selection = cmds.ls(sl=True)
        if len(selection) > 0:
            if cls.is_container(selection[0]):
                component.ComponentContainer(selection[0]).lock()
    @classmethod
    def unlock_container(cls, object):
        selection = cmds.ls(sl=True)
        if len(selection) > 0:
            if cls.is_container(selection[0]):
                component.ComponentContainer(selection[0]).unlock()