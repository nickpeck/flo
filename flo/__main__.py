import sys

from . FloListenerImpl import FloListenerImpl

if __name__ == "__main__":
    file = sys.argv[1]
    FloListenerImpl.loadModule(file)