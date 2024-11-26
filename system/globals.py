import os
import sys

USING_PY3 = sys.version_info.major >= 3

AUTO_RIGGING_DIR = os.environ['J_Auto_RIGGING_DIR']

ATTR_WITH_CHILDREN = ["compound", "double3", "double2"]

IO_NODE_NAME = "interface"