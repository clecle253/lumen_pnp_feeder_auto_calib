import threading
import sys
import os

import threading
import sys
import os
from org.openpnp.model import Configuration

# Robust Path Detection for Jython/OpenPnP
script_dir = None
try:
    # Try standard __file__ (works in most contexts)
    script_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # __file__ not defined in Jython exec() context
    print("WARN: __file__ not defined, trying fallbacks...")
    
    # Fallback 1: Specific path for User's Remote Setup (Windows)
    remote_path_win = r"P:\ICane\projets\ICane\electronique\pnp_script"
    
    # Fallback 2: Specific path for User's Remote Setup (Linux/Pi - pcloud_script)
    remote_path_linux_1 = "/home/clecle253/.openpnp2/scripts/pcloud_script"
    # Fallback 3: Possible alternative name (pnp_script)
    remote_path_linux_2 = "/home/clecle253/.openpnp2/scripts/pnp_script"
    
    # Fallback 4: Default OpenPnP scripts folder
    default_path = os.path.join(Configuration.get().getConfigurationDirectory().getAbsolutePath(), "scripts")
    
    if os.path.exists(remote_path_win):
        script_dir = remote_path_win
    elif os.path.exists(remote_path_linux_1):
        script_dir = remote_path_linux_1
    elif os.path.exists(remote_path_linux_2):
        script_dir = remote_path_linux_2
    else:
        script_dir = default_path

print("Script directory (resolved): " + script_dir)

if script_dir not in sys.path:
    print("Adding script directory to sys.path")
    sys.path.append(script_dir)
else:
    print("Script directory already in sys.path")

try:
    if os.path.exists(script_dir):
        print("Contents of " + script_dir + ": " + str(os.listdir(script_dir)))
        # Check for LumenPnP folder specifically
        lp_path = os.path.join(script_dir, "LumenPnP")
        if os.path.exists(lp_path):
             print("LumenPnP folder found. Contents: " + str(os.listdir(lp_path)))
        else:
             print("ERROR: LumenPnP folder NOT found in script_dir!")
except Exception as e:
    print("Error listing dir: " + str(e))

import LumenPnP.gui.lumen_gui
import LumenPnP.core.kicad_importer
# Force reload to pick up changes without restarting OpenPnP
reload(LumenPnP.core.kicad_importer)
reload(LumenPnP.gui.lumen_gui)
from LumenPnP.gui.lumen_gui import LumenPnPGUI

def launch():
    """Launch the LumenPnP plugin GUI"""
    gui_thread = threading.Thread(target=lambda: LumenPnPGUI(machine, gui).run())
    gui_thread.daemon = True
    gui_thread.start()
    print("LumenPnP Plugin launched successfully!")

# Auto-launch when script is executed
launch()
