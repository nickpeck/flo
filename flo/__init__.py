"""Flo language runtime
"""
import platform
import sys

# version check
maj_ver, min_ver, patchlevel = platform.python_version_tuple()
if int(maj_ver) < 3 or int(min_ver) < 7:
    raise Exception("Python version >= 3.7 is required")
