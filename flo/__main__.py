import sys

from . FloListenerImpl import FloListenerImpl

try:
    file = sys.argv[1]
    FloListenerImpl.loadModule(file)
except IndexError:
    FloListenerImpl.repl()