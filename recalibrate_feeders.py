# OpenPnP Script: Recalibrate All Feeders
# Description: Recalibrates all enabled feeders by locating their fiducials and updating coordinates.
# Author: Assistant

# Standard Imports
from org.openpnp.model import Location, Part
from org.openpnp.util import VisionUtils
from org.openpnp.spi import VisionProvider
import time

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# Name of the Part to use for fiducial recognition.
# You MUST have a part with this name defined in OpenPnP (Parts tab).
FIDUCIAL_PART_NAME = "Fiducial-1mm" 

# Substring to filter feeders. Only feeders containing this string will be calibrated.
# Set to "" to calibrate ALL enabled feeders.
FEEDER_NAME_FILTER = "" 

# ==============================================================================
# SCRIPT LOGIC
# ==============================================================================


# Validating 'gui' available for logging
if 'gui' not in globals():
    print("WARNING: 'gui' object not found. Logs might be lost in background threads.")

def log_to_console(message):
    """Logs to the Scripting Console in a thread-safe way."""
    try:
        if 'gui' in globals():
            gui.getScriptingConsole().appendString(str(message) + "\n")
        else:
            print(str(message))
    except:
        print(str(message))

log_to_console("--- Starting Feeder Calibration Script ---")


def create_fiducial_part(config):
    try:
        from org.openpnp.model import Part
        from javax.swing import JOptionPane
        
        print("Creating new Fiducial Part: " + FIDUCIAL_PART_NAME)
        new_part = Part(FIDUCIAL_PART_NAME)
        new_part.setId(FIDUCIAL_PART_NAME)
        new_part.setName(FIDUCIAL_PART_NAME)
        # new_part.setDescription("Auto-created") # Removed: attribute not available in this version
        
        config.addPart(new_part)
        
        msg = "The script created a new Part named '" + FIDUCIAL_PART_NAME + "'.\n"
        msg += "Please go to the 'Parts' tab, find this part, and configure its VISION settings.\n"
        msg += "(Vision tab -> Enable Vision -> Pipeline).\n"
        msg += "Once configured, re-run this script."
        
        print("WARNING: " + msg.replace("\n", " "))
        JOptionPane.showMessageDialog(None, msg, "Feeder Calibration - Setup Required", JOptionPane.WARNING_MESSAGE)
        
        return new_part
    except Exception as e:
        print("Error creating part: " + str(e))
        raise e

def get_fiducial_part():
    try:
        from org.openpnp.model import Configuration
        config = Configuration.get()
        
        # 1. Try exact ID lookup
        part = config.getPart(FIDUCIAL_PART_NAME)
        if part:
            return part
            
        # 2. If not found, search by Name
        all_parts = config.getParts()
        for p in all_parts:
            if p.name == FIDUCIAL_PART_NAME:
                return p
        
        # 3. If still not found, CREATE IT
        print("Fiducial Part '" + FIDUCIAL_PART_NAME + "' NOT FOUND. Auto-creating...")
        return create_fiducial_part(config)

    except Exception as e:
         print("Error looking up/creating part: " + str(e))
         raise e

def calibrate_feeders():
    print("\n--- 1. Listing Feeders ---")
    feeders = machine.getFeeders()
    print("Total feeders found: " + str(len(feeders)))
    
    enabled_feeders = []
    for feeder in feeders:
        f_name = str(feeder.name) if feeder.name else "Unnamed"
        # Try getId() if id attribute access fails/is None
        try:
            f_id = str(feeder.getId())
        except:
             f_id = str(feeder.id) if hasattr(feeder, 'id') and feeder.id else "NoID"

        print(" - Found Feeder: " + f_name + " (ID: " + f_id + ") Enabled: " + str(feeder.enabled))
        
        if feeder.enabled:
            # Check filter
            if FEEDER_NAME_FILTER and FEEDER_NAME_FILTER not in f_name:
                continue
            enabled_feeders.append(feeder)

    # SORTING: Sort feeders by slot number (extracted from name) to optimize travel path
    import re
    def get_slot_number(feeder):
        name = str(feeder.getName())
        
        # Log entry for debugging regex
        # log_to_console("Inspecting: " + name)

        # The log shows names like: "002280155359531020383330 (Slot: 37)"
        # Previous regex r'\d+' caught the start ID.
        # We need to capture the specific "Slot: X" number.
        
        # Try finding "Slot: <number>" case insensitive
        match = re.search(r'Slot:\s*(\d+)', name, re.IGNORECASE)
        
        num = 999999
        if match:
            num = int(match.group(1)) # Group 1 is the number
        else:
             # Fallback: check if the name itself is just a number (e.g. "12")
             if name.isdigit():
                 num = int(name)
             # Fallback 2: Check for "(<number>)" if "Slot:" is missing
             else:
                 m2 = re.search(r'\((\d+)\)', name)
                 if m2:
                     num = int(m2.group(1))
        
        # log_to_console("  -> Parsed Slot: " + str(num))
        return num

    try:
        enabled_feeders.sort(key=get_slot_number)
        log_to_console("Sorted feeders by slot number.")
        
        # Log the order for verification
        log_to_console("Processing Order:")
        for f in enabled_feeders:
             log_to_console(" - " + f.getName())
             
    except Exception as e:
        log_to_console("Warning: Could not sort feeders. processing in default order. " + str(e))

    log_to_console("--- Feeder Scan Complete. " + str(len(enabled_feeders)) + " feeders selected for calibration ---")

    if len(enabled_feeders) == 0:
        log_to_console("No enabled feeders found matching filter. Warning: Exiting.")
        return

    # 2. Validate Vision Setup
    log_to_console("\n--- 2. Vision Setup ---")

    try:
        fiducial_part = get_fiducial_part()
        
        # Check if we just created it (description check or name)
        # Better: Check if it has a Package (footprint) assigned.
        # If no package, vision cannot work (usually).
        if not fiducial_part.getPackage():
             from javax.swing import JOptionPane
             msg = "The Part '" + fiducial_part.getName() + "' has no Package assigned.\n"
             msg += "This means Vision cannot work.\n"
             msg += "Please go to the Parts tab, assign a Package, and configure Vision/Footprint settings."
             print("STOPPING: " + msg.replace("\n", " "))
             JOptionPane.showMessageDialog(None, msg, "Feeder Calibration - Configuration Needed", JOptionPane.WARNING_MESSAGE)
             return

        print("Using Fiducial Part: " + fiducial_part.name)
        
    except Exception as e:
        print("CRITICAL WARNING: Vision 'Part' setup failed. Cannot proceed with CALIBRATION.")
        print("Reason: " + str(e))
        return

    print("\n--- 3. Starting Calibration ---")
    
    updated_count = 0
    count = 0
    for feeder in enabled_feeders:
        f_name = str(feeder.name) if feeder.name else "Unnamed"
        log_to_console(">>> Calibrating Feeder: " + f_name)
        
        try:
            # 2. Get current location (TARGET THE BASE / SLOT LOCATION)
            # User reports 'feeder.getLocation()' moves to Pick Location.
            # We need to find the real 'Slot Location'.
            
            # --- INTROSPECTION DEBUGGING ---
            # Print detailed info for the FIRST feeder to find the right field
            if count == 0:
                log_to_console("--- DEBUG: Feeder Inspection ---")
                log_to_console("  Class: " + str(feeder.getClass()))
                log_to_console("  feeder.getLocation(): " + str(feeder.getLocation()))
                if hasattr(feeder, 'getPickLocation'):
                    log_to_console("  feeder.getPickLocation(): " + str(feeder.getPickLocation()))
                
                # Check for ReferenceFeeder specific fields
                if hasattr(feeder, 'getPartOffset'):
                     # getPartOffset might return Location or string? it returns a Location usually.
                     log_to_console("  feeder.getPartOffset(): " + str(feeder.getPartOffset()))

                # Check for Slot (ReferenceSlotFixedFeeder)
                if hasattr(feeder, 'getSlot'):
                     slot = feeder.getSlot()
                     if slot:
                         log_to_console("  feeder.getSlot().getLocation(): " + str(slot.getLocation()))
                     else:
                         log_to_console("  feeder.getSlot() is None")
                
                log_to_console("--------------------------------")

            # Try to use Slot Location if available, otherwise default to getLocation()
            current_loc = feeder.getLocation()
            if hasattr(feeder, 'getSlot'):
                slot = feeder.getSlot()
                if slot:
                    current_loc = slot.getLocation()
                    log_to_console("  Using Slot Location: " + str(current_loc))
            
            # log_to_console("  Target Location: " + str(current_loc))
            
            # Validate location is not 0,0,0 (unless enabled)
            if current_loc.x == 0 and current_loc.y == 0:
                 log_to_console("  WARNING: Feeder location is 0,0,0. Skipping motion.")
                 continue
            
            # 3. Perform vision check using standard FiducialLocator method
            # We access the underlying implementation method getFiducialLocation which works for any location.
            log_to_console("  Locating fiducial using FiducialLocator.getFiducialLocation...")
            
            found_loc = None
            try:
                # Look up the FiducialLocator
                fiducial_locator = machine.getFiducialLocator()
                if not fiducial_locator:
                    print("  ERROR: Machine has no FiducialLocator configured.")
                    continue

                # We call the method directly. 
                # Note: getFiducialLocation is public in ReferenceFiducialLocator but not in the Interface.
                # Scripts usually can access it if the underlying object has the method.
                # usage: getFiducialLocation(Location nominalLocation, PartSettingsHolder part)
                found_loc = fiducial_locator.getFiducialLocation(current_loc, fiducial_part)
                
            except Exception as ev:
                 log_to_console("  Moving to " + str(current_loc))
                 found_loc = None

            if found_loc:
                log_to_console("  Fiducial found at: " + str(found_loc))
                
                # ... update location ...
                # Use standard setLocation
                new_loc = Location(found_loc.units, found_loc.x, found_loc.y, current_loc.z, current_loc.rotation)
                
                # Update logic:
                # We found the fiducial at 'found_loc'.
                # Since we targeted the 'Slot Location' (Base), 'found_loc' IS the new 'Slot Location'.
                # We update the feeder's base location directly.
                
                # Create validation log
                base_loc = feeder.getLocation()
                log_to_console("  Old Slot Location: " + str(base_loc))
                
                # Construct new location: 
                # Use found X/Y.
                # Keep original Z and Rotation from the feeder configuration (don't overwrite with vision Z unless intended).
                # Usually vision Z is not reliable for slot Z.
                new_base_loc = Location(base_loc.units, found_loc.x, found_loc.y, base_loc.z, base_loc.rotation)
                
                log_to_console("  New Slot Location: " + str(new_base_loc))
                
                # Apply update
                # Crucial: If we read from Slot, we must WRITE to Slot.
                if hasattr(feeder, 'getSlot') and feeder.getSlot():
                     slot = feeder.getSlot()
                     # Re-verify base_loc is consistent with slot (it should be as we read it)
                     # Apply
                     slot.setLocation(new_base_loc)
                     log_to_console("  UPDATED SLOT Location directly.")
                else:
                     feeder.setLocation(new_base_loc)
                     log_to_console("  UPDATED FEEDER Location.")
                
                updated_count += 1
                
            else:
                log_to_console("  FAILED to locate fiducial for " + feeder.name)
                
        except Exception as e:
            log_to_console("  ERROR processing " + feeder.name + ": " + str(e))
        
        except Exception as e:
            print("  ERROR processing " + feeder.name + ": " + str(e))
        
        count += 1

    log_to_console("--- Calibration Complete ---")
    log_to_console("Processed: " + str(count) + " feeders.")
    log_to_console("Updated:   " + str(updated_count) + " feeders.")

# Main entry point - Executing via Python verify threading (Background Thread) to avoid UI freeze.
# We use gui.getScriptingConsole().appendString() to ensure logs are visible.

log_to_console("Script executed. Starting Python background thread...")

import threading

def run_calibration_task():
    try:
        log_to_console("Background Calibration Task STARTED.")
        
        # Ensure imports are available in this thread scope logic if needed
        # (Jython usually shares global scope, but good to be safe for specific OpenPnP classes)
        
        calibrate_feeders()
        
        from org.openpnp.model import Configuration
        log_to_console("Saving configuration...")
        Configuration.get().save()
        log_to_console("Configuration Saved.")
        log_to_console("Background task COMPLETED.")
        
    except Exception as e:
        import traceback
        traceback.print_exc() # Prints to std err
        log_to_console("FATAL ERROR in Background Task: " + str(e))

# Launch the thread
t = threading.Thread(target=run_calibration_task)
t.start()
