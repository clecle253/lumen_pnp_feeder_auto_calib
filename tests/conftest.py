import os
import sys

# The plugin runs inside OpenPnP (Jython); its pure-logic modules are tested here with Python 3.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
