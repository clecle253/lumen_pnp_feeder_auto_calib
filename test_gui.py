"""
Test script to verify LumenPnP GUI works standalone
(without OpenPnP machine object)
"""

import sys
sys.path.insert(0, r"c:\Users\cleme\Desktop\open pnp plugin")

# Mock machine and gui objects for testing
class MockMachine:
    def getFeeders(self):
        return []

class MockGUI:
    pass

# Import and launch
from LumenPnP.gui.main_window import LumenPnPGUI

machine = MockMachine()
gui = MockGUI()

app = LumenPnPGUI(machine, gui)
app.run()
