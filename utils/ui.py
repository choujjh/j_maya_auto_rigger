import maya.OpenMayaUI as omui
import maya.cmds as cmds

from PySide2 import QtCore
from PySide2 import QtWidgets
from PySide2 import QtGui
from shiboken2 import wrapInstance
import abc
from functools import partial
import inspect

from enum import Enum
import system.data as data

import system.globals as globals
import utils.enum as util_enums
import system.base_components as base_components
import utils.node_wrapper as nw


def maya_main_window():
    """Return the Maya main window"""
    main_window_ptr = omui.MQtUtil.mainWindow()
    if globals.USING_PY3:
        return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)
    else:
        return wrapInstance(long(main_window_ptr), QtWidgets.QWidget)

def set_color_if_connected(attr, widget):
    if attr.has_source_connection():
        widget.setStyleSheet("background-color: #f1f1a5")
        widget.setDisabled(True)

class JBaseMayaDialog(QtWidgets.QDialog):
    __metaclass__ = abc.ABCMeta

    def __init__(self, window_title, parent=maya_main_window()):
        super(JBaseMayaDialog, self).__init__(parent)
        self.setWindowTitle(window_title)

        if globals.USING_PY3:
            self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        else:
            self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)

        self.create_widgets()
        self.create_layout()
        self.create_connections()

    @abc.abstractmethod
    def create_widgets(self):
        pass
    @abc.abstractmethod
    def create_layout(self):
        pass
    @abc.abstractmethod
    def create_connections(self):
        pass
class JWidgetLayoutOrientation(Enum):
    horizontal = "horizontal"
    verticle = "verticle"

class JLabeledWidget(QtWidgets.QWidget):
    def __init__(self, widget, label="...", spacing=[50, 50], orientation:JWidgetLayoutOrientation=JWidgetLayoutOrientation.horizontal):
        super(JLabeledWidget, self).__init__()
        self.label_widget = QtWidgets.QLabel(label)
        self.other_widget = widget

        self.layout = QtWidgets.QGridLayout()
        self.layout.addWidget(self.label_widget, 0, 0)
        self.layout.setVerticalSpacing(0)
        if orientation == JWidgetLayoutOrientation.horizontal:
            self.layout.addWidget(self.other_widget, 0, 1)
            self.layout.setColumnMinimumWidth(0, spacing[0])
            self.layout.setColumnMinimumWidth(1, spacing[1])
        else:
            self.layout.addWidget(self.other_widget, 1, 0)

        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.layout)

class JBorderWidget(QtWidgets.QFrame):
    def __init__(self, widget=None, layout=None, frame_style=QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Sunken, orientation:JWidgetLayoutOrientation=JWidgetLayoutOrientation.verticle):
        super(JBorderWidget, self).__init__()
        if widget is not None:
            self.widget = widget


        self.setFrameStyle(frame_style)
        self.layout=layout
        if self.layout is None:
            if orientation==JWidgetLayoutOrientation.horizontal:
                self.layout=QtWidgets.QHBoxLayout()
            else:
                self.layout=QtWidgets.QVBoxLayout()
        if widget is not None:
            self.layout.addWidget(self.widget)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.layout)

class ComponentListUI(QtWidgets.QWidget):

    tableCellChanged = QtCore.Signal()
    def __init__(self, widget_label=""):
        super(ComponentListUI, self).__init__()

        self._widget_label=widget_label
        self._component_list = []
        self._table_widgets_array = []
        self.create_widgets()
        self.create_layout()

    def create_widgets(self):
        self.label = QtWidgets.QLabel(self._widget_label)
        self.add_btn = QtWidgets.QPushButton()
        self.add_btn.setIcon(QtGui.QIcon(":item_add.png"))

        self.delete_btn = QtWidgets.QPushButton()
        self.delete_btn.setIcon(QtGui.QIcon(":delete.png"))

        self.table_wdg = QtWidgets.QTableWidget()
        
        table_width = [150, 60, 220, 60]
        self.table_wdg.setColumnCount(len(table_width))
        for index, width in enumerate(table_width):
            self.table_wdg.setColumnWidth(index, width)
        self.table_wdg.setHorizontalHeaderLabels(["Instance Name", "Side", "Namespace", "Mirrored"])
        self.table_wdg.setMinimumWidth(sum(table_width)+33)
        self.table_wdg.verticalHeader().setVisible(False)
        self.table_wdg.setShowGrid(False)

    def create_layout(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        top_layout = QtWidgets.QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(self.label)
        top_layout.addStretch()
        top_layout.addWidget(self.add_btn)
        top_layout.addWidget(self.delete_btn)

        layout.addLayout(top_layout)
        layout.addWidget(self.table_wdg)

        self.setLayout(layout)

    def create_connections(self):
        self.table_wdg.currentCellChanged.connect(self.tableCellChanged.emit)

    def get_current_component(self):
        curr_index = self.table_wdg.currentRow()
        return self._component_list[curr_index]
    
    def delete_current_component(self):
        curr_index = self.table_wdg.currentRow()

        self.table_wdg.removeRow(curr_index)
        component_inst = self._component_list[curr_index]

        mirror_container = component_inst.mirror_dest_container

        print(curr_index)
        self._component_list.pop(curr_index)

        if mirror_container is not None:
            # get mirror helper component
            # connections = component_inst.container_node["hier"][0][data.HierAttrNames.input_world_matrix.value].get_as_source_connection_list()
            # for connection in connections:
            #     cmds.delete(str(connection[0].node.get_container()))

            # get mirror component
            for index, component in enumerate(self._component_list):
                if component.container_node == mirror_container:
                    self._component_list.pop(index)
                    self.table_wdg.removeRow(index)
                    cmds.delete(str(mirror_container))
                    break
        
        cmds.delete(str(component_inst.container_node))
        
        self._set_table_min_height()

    def add_component_info(self, *components, clear_prev_entries=False):
        if clear_prev_entries:
            self._component_list.clear()
        
        self._component_list.extend(components)
        self._set_table_min_height()

        self.refresh_component_info()

    def rename_component(self, row, column, *args):

        component_inst_text = str(self._table_widgets_array[row][0].text())
        hier_side_index = -1
        if column == 1:
            hier_side_index = args[0]
        elif self._table_widgets_array[row][1] is not None:
            hier_side_index = self._table_widgets_array[row][1].currentIndex()

        component = self._component_list[row]
        container_node = component.container_node

        container_node["componentInstName"] = component_inst_text
        if container_node.has_attr(data.HierDataAttrNames.hier_side.value):
            container_node[data.HierDataAttrNames.hier_side.value] = hier_side_index

        component.rename_nodes()
        if component.container_node.has_attr("componentInstName"):
            connection = component.container_node["componentInstName"].get_as_source_connection_list()
            if connection != []:
                container_node = connection[0].node.get_container()
                if container_node is not None:
                    base_components.get_component(container_node).rename_nodes()
            
        mirror_container = component.mirror_dest_container
        if mirror_container is not None:
            base_components.get_component(mirror_container).rename_nodes()

        self.refresh_component_info()
        self.table_wdg.setCurrentCell(row, column)

    def refresh_component_info(self):
        self.table_wdg.clearContents()
        self.table_wdg.setRowCount(0)
        self._table_widgets_array = []

        for index, component in enumerate(self._component_list):
            io_node = component.io_node

            insert_widget_list = []

            # inserting row
            last_row = self.table_wdg.rowCount()
            self.table_wdg.setRowCount(last_row + 1)

            # instance name            
            instance_name_line_edit = QtWidgets.QLineEdit()
            instance_name_line_edit.setText(io_node["componentInstName"].value)
            set_color_if_connected(io_node["componentInstName"], instance_name_line_edit)
            instance_name_line_edit.editingFinished.connect(partial(self.rename_component, index, 0))
            insert_widget_list.append(instance_name_line_edit)

            # side
            if io_node.has_attr(data.HierDataAttrNames.hier_side.value):
                side_combo_box = QtWidgets.QComboBox()
                side_combo_box.addItems(util_enums.CharacterSide.maya_enum_str().split(":"))
                side_combo_box.setCurrentIndex(io_node[data.HierDataAttrNames.hier_side.value].value)
                set_color_if_connected(io_node[data.HierDataAttrNames.hier_side.value], side_combo_box)

                side_combo_box.currentIndexChanged.connect(partial(self.rename_component, index, 1))
                insert_widget_list.append(side_combo_box)
            else:
                insert_widget_list.append(None)

            # namespace
            namespace_line_edit = QtWidgets.QLineEdit()
            namespace_line_edit.setText(component.instance_namespace)
            namespace_line_edit.setDisabled(True)
            insert_widget_list.append(namespace_line_edit)

            # mirroring
            mirror_combo_box = QtWidgets.QComboBox()
            mirror_combo_box.addItems(["None", "Srce", "Dest"])
            mirror_combo_box_index = 0
            if component.container_node.has_attr("mirrorSource"):
                mirror_combo_box_index = 1
            elif component.container_node.has_attr("mirrorDest"):
                mirror_combo_box_index = 2
            mirror_combo_box.setCurrentIndex(mirror_combo_box_index)
            mirror_combo_box.setEnabled(False)
            insert_widget_list.append(mirror_combo_box)

            for index, widget in enumerate(insert_widget_list):
                if widget is not None:
                    selectable_widget = QtWidgets.QWidget()
                    selectable_layout = QtWidgets.QVBoxLayout()
                    selectable_layout.setContentsMargins(0, 0, 0, 0)
                    selectable_layout.addWidget(widget)
                    selectable_widget.setLayout(selectable_layout)
                    self.table_wdg.setCellWidget(last_row, index, selectable_widget)
                    # self.table_wdg.setCellWidget(last_row, index, widget)
            self._table_widgets_array.append(insert_widget_list)

    def _set_table_min_height(self):
        num_spacing = len(self._component_list)
        
        if num_spacing > 5:
            num_spacing = 5
        elif num_spacing < 1:
            num_spacing = 1

        self.table_wdg.setMinimumHeight(num_spacing*30+30)

class SelectComponentUI(JBaseMayaDialog):
    def __init__(self, parent=maya_main_window(), module=None):

        self.module=module
        self.return_class = None

        super(SelectComponentUI, self).__init__("Select Component", parent)

        self.setMinimumWidth(300)
        self.setMinimumHeight(250)

    def create_widgets(self):
        self.list_wdg = QtWidgets.QListWidget()
        
        module_classes = [name for name, obj in inspect.getmembers(self.module) if inspect.isclass(obj) and name != "Component"]
        if self.module is not None:
            self.list_wdg.addItems(module_classes)

        self.confirm_btn = QtWidgets.QPushButton("Confirm")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")

    def create_layout(self):
        button_layout = QtWidgets.QGridLayout()
        button_layout.addWidget(self.confirm_btn, 0, 0)
        button_layout.addWidget(self.cancel_btn, 0, 1)

        
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.list_wdg)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def confirm_btn_action(self):
        self.return_class = self.list_wdg.currentItem().text()
        self.close()

    def create_connections(self):
        self.confirm_btn.clicked.connect(self.confirm_btn_action)
        self.cancel_btn.clicked.connect(self.close)

class AttrItem(QtWidgets.QWidget):
    def __init__(self, attr:nw.Attr, column_sizes=[150, 120, 50]):
        super(AttrItem, self).__init__()

        self.attr = attr
        self.column_sizes = column_sizes

        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.setContentsMargins(0, 0, 0, 0)

    def get_num_min_max(self):
        # has max and mins
        kwargs={}
        attr = self.attr
        if attr.attr_type in ["double", "long"]:
            for attr_exists, attr_query_key, attr_add_key in zip(
                ["softMaxExists", "softMinExists", "maxExists", "minExists"],
                ["softMax", "softMin", "maximum", "minimum"],
                ["softMaxValue", "softMinValue", "maxValue", "minValue"]):

                if cmds.attributeQuery(attr.attr_short_name, node=str(attr.node), **{attr_exists:True}):
                    kwargs[attr_add_key] = cmds.attributeQuery(attr.attr_short_name, node=str(attr.node), **{attr_query_key:True})[0]

        min = None
        max = None

        if "softMinValue" in kwargs.keys():
            min = kwargs["softMinValue"]
        if "minValue" in kwargs.keys():
            if min is None or min > kwargs["minValue"]:
                min = kwargs["minValue"]
        if "softMaxValue" in kwargs.keys():
            min = kwargs["softMaxValue"]
        if "maxValue" in kwargs.keys():
            if min is None or min < kwargs["maxValue"]:
                min = kwargs["maxValue"]


        return min, max

    def create_widgets(self):

        # label
        self.attr_name_label = QtWidgets.QLabel()
        self.attr_name_label.setText(self.attr.attr_short_name)

        # attributeType attribute
        self.attr_value_widget = None
        if self.attr.attr_type == "string":
            self.attr_value_widget = QtWidgets.QLineEdit()
            self.attr_value_widget.textChanged.connect(self.set_attr_value)
        elif self.attr.attr_type in ["message", "nurbsCurve", "nurbsSurface", "mesh"]:
            self.attr_value_widget = QtWidgets.QLabel()
        elif self.attr.attr_type == "matrix":
            self.attr_value_widget = QtWidgets.QLabel()
        elif self.attr.attr_type == "bool":
            self.attr_value_widget = QtWidgets.QCheckBox()
            self.attr_value_widget.stateChanged.connect(self.set_attr_value)
        elif self.attr.attr_type == "double":
            self.attr_value_widget = QtWidgets.QDoubleSpinBox()
            self.attr_value_widget.valueChanged.connect(self.set_attr_value)
        elif self.attr.attr_type == "long":
            self.attr_value_widget = QtWidgets.QSpinBox()
            self.attr_value_widget.valueChanged.connect(self.set_attr_value)
        elif self.attr.attr_type == "enum":
            self.attr_value_widget = QtWidgets.QComboBox()
            enum_str = cmds.attributeQuery(self.attr.attr_short_name, node=str(self.attr.node), listEnum=True)[0]
            self.attr_value_widget.addItems(enum_str.split(":"))
            self.attr_value_widget.currentIndexChanged.connect(self.set_attr_value)

        if self.attr_value_widget is not None:
            set_color_if_connected(self.attr, self.attr_value_widget)

        # connect btn
        # self.attr_connect_btn = QtWidgets.QPushButton("connect")
        
        self.updateUIValue()

    def create_layout(self):
        layout = QtWidgets.QGridLayout()
        for index, size in enumerate(self.column_sizes[:2]):
            layout.setColumnMinimumWidth(index, size)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.attr_name_label, 0, 0)
        layout.addWidget(self.attr_value_widget, 0, 1)
        # layout.addWidget(self.attr_connect_btn, 0, 2)

        self.setLayout(layout)

    def create_connections(self):
        pass

    def set_attr_value(self, *args):
        value = None
        if self.attr.attr_type == "string":
            value = self.attr_value_widget.text()
        elif self.attr.attr_type in ["message", "nurbsCurve", "nurbsSurface", "mesh"]:
            pass
        elif self.attr.attr_type == "matrix":
            pass
        elif self.attr.attr_type == "bool":
            value = self.attr_value_widget.isChecked()
        elif self.attr.attr_type == "double":
            value = self.attr_value_widget.value()
        elif self.attr.attr_type == "long":
            value = self.attr_value_widget.value()
        elif self.attr.attr_type == "enum":
            value = self.attr_value_widget.currentIndex()
        
        if value is not None and not self.attr.is_locked() and not self.attr.has_source_connection():
            self.attr.set(value)

    def updateUIValue(self):
        if self.attr.attr_type == "string":
            self.attr_value_widget.setText(self.attr.value)
        elif self.attr.attr_type in ["message", "nurbsCurve", "nurbsSurface", "mesh"]:
            pass
        elif self.attr.attr_type == "matrix":
            pass
        elif self.attr.attr_type == "bool":
            self.attr_value_widget.setChecked(bool(self.attr.value))
        elif self.attr.attr_type == "double":
            self.attr_value_widget.setValue(self.attr.value)
            attr_min_max = self.get_num_min_max()
            if attr_min_max[0] is not None:
                self.attr_value_widget.setMinimum(attr_min_max[0])
            if attr_min_max[1] is not None:
                self.attr_value_widget.setMaximum(attr_min_max[1])
        elif self.attr.attr_type == "long":
            self.attr_value_widget.setValue(self.attr.value)
            attr_min_max = self.get_num_min_max()
            if attr_min_max[0] is not None:
                self.attr_value_widget.setMinimum(attr_min_max[0])
            if attr_min_max[1] is not None:
                self.attr_value_widget.setMaximum(attr_min_max[1])
        elif self.attr.attr_type == "enum":
            self.attr_value_widget.setCurrentIndex(self.attr.value)

class MirrorPlane(JBaseMayaDialog):
    def __init__(self, parent=maya_main_window(), module=None):

        self.return_axis = None

        super(MirrorPlane, self).__init__("Select Component", parent)

        self.setMinimumWidth(300)
        self.setMinimumHeight(250)

    def create_widgets(self):
        self.plane_combo_box = QtWidgets.QComboBox()
        self.plane_combo_box.addItems(["YZ", "XZ", "XY"])

        self.confirm_btn = QtWidgets.QPushButton("Confirm")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")

    def create_layout(self):
        button_layout = QtWidgets.QGridLayout()
        button_layout.addWidget(self.confirm_btn, 0, 0)
        button_layout.addWidget(self.cancel_btn, 0, 1)

        
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.plane_combo_box)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def create_connections(self):
        self.confirm_btn.clicked.connect(self.confirm_btn_action)
        self.cancel_btn.clicked.connect(self.close)

    def confirm_btn_action(self):
        self.return_axis = util_enums.AxisEnums.get(self.plane_combo_box.currentIndex())
        self.close()


    

# class HierItem(QtWidgets.QWidget):
#     def __init__(self, hier:nw.Attr, column_sizes=[70, 50, 20]):
#         super(AttrItem, self).__init__()

#         self.hier = hier
#         self.column_sizes = column_sizes

#         self.create_widgets()
#         self.create_layout()
#         self.create_connections()
