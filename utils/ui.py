import maya.OpenMayaUI as omui
import maya.cmds as cmds

from PySide2 import QtCore
from PySide2 import QtWidgets
from shiboken2 import wrapInstance
import abc
from enum import Enum

import system.globals as globals


def maya_main_window():
    """Return the Maya main window"""
    main_window_ptr = omui.MQtUtil.mainWindow()
    if globals.USING_PY3:
        return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)
    else:
        return wrapInstance(long(main_window_ptr), QtWidgets.QWidget)
    
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
    def __init__(self, widget=None, frame_style=QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Sunken, orientation:JWidgetLayoutOrientation=JWidgetLayoutOrientation.verticle):
        super(JBorderWidget, self).__init__()
        if widget is not None:
            self.widget = widget


        self.setFrameStyle(frame_style)
        self.layout=None
        if orientation==JWidgetLayoutOrientation.horizontal:
            self.layout=QtWidgets.QHBoxLayout()
        else:
            self.layout=QtWidgets.QVBoxLayout()
        if widget is not None:
            self.layout.addWidget(self.widget)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.layout)