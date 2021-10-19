import sys

from . FloListenerImpl import FloListenerImpl

source_file = None
try:
    source_file = sys.argv[1]
except IndexError:
    pass

if source_file is not None:
    FloListenerImpl.loadModule(source_file)
else:
    FloListenerImpl.repl()