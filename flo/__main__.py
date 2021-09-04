import sys

from . FloListenerImpl import FloListenerImpl

file = sys.argv[1]
FloListenerImpl.loadModule(file)