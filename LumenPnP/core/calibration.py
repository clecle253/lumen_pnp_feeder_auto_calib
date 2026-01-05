import time
import re
import traceback
from org.openpnp.model import Location, Part, Configuration
from javax.swing import JOptionPane

class PocketCalibrator:
    """
    Calibrates the 'Part Offset' of a feeder by visually detecting the pocket.
    Uses the VisionStore and custom VisionEngine.
    """
    def __init__(self, machine):
        self.machine = machine
        from LumenPnP.core.vision_store import VisionStore
        from LumenPnP.core.vision_core import VisionEngine
        self.store = VisionStore()
        self.engine = VisionEngine()
        
    def calibrate_feeder(self, feeder, callback=None):
        """
        Calibrate the pocket position for a single feeder.
        Updates feeder.partOffset.
        """
        try:
            if callback: callback("Calibrating pocket for " + feeder.getName())
            
            # 1. Get Part info
            part = feeder.getPart()
            if not part:
                if callback: callback("Skipping: No part assigned.")
                return False
                
            # 2. Lookup Vision Profile
            # Try Part ID first
            profile_name = self.store.get_mapping(part.getId())
            if not profile_name:
                # Try Part Name (fallback)
                profile_name = self.store.get_mapping(part.getName())
                
            if not profile_name:
                if callback: callback("No Vision Mapping found for Part: " + str(part.getName()))
                return False
                
            profile = self.store.get_profile(profile_name)
            if not profile:
                if callback: callback("Profile '" + str(profile_name) + "' not found!")
                return False

            if callback: callback("Using Profile: " + str(profile.name))

            # 3. Determine Search Location (Feeder + Current Offset)
            feeder_loc = feeder.getLocation()
            current_offset = feeder.getOffset()
            
            search_loc = feeder_loc
            if current_offset:
                search_loc = search_loc.add(current_offset)
                
            # Move Camera
            head = self.machine.getDefaultHead()
            cam = head.getDefaultCamera()
            if not cam:
                if callback: callback("Error: No camera found.")
                return False

            if callback: callback("Moving to search location...")
            head.moveToSafeZ()
            cam.moveTo(search_loc)
            time.sleep(0.5) # Settle
            
            # 4. Capture & Process
            if callback: callback("Analysing image...")
            img = cam.capture()
            # process_image returns: found, center, res_img, stats, res_img_bin
            found, center, _, _, _ = self.engine.process_image(img, profile)
            
            if not found or not center:
                if callback: callback("Vision failed: Part not found.")
                return False
                
            # 5. Calculate Offset (Pixels -> Millimeters)
            # Center is in Pixels (0,0 at TopLeft)
            # We need deviation from Image Center
            img_w = img.getWidth()
            img_h = img.getHeight()
            center_x = img_w / 2.0
            center_y = img_h / 2.0
            
            dx_px = center.x - center_x
            dy_px = center.y - center_y
            
            # Get Units Per Pixel (Location object with X, Y)
            units_per_pixel = cam.getUnitsPerPixel()
            upp_x = units_per_pixel.getX()
            upp_y = units_per_pixel.getY()
            
            # Calculate world delta
            # Assuming standard OpenPnP setup
            # Delta World X = Pixel Delta X * UPP X
            # Delta World Y = -Pixel Delta Y * UPP Y (Image Y is inverted vs World Y)
            
            dx_mm = dx_px * upp_x
            dy_mm = -dy_px * upp_y
            
            # New Part Location (Absolute)
            found_world_x = search_loc.getX() + dx_mm
            found_world_y = search_loc.getY() + dy_mm
            
            # Offset = Part - FeederBase
            # We want the offset relative to the Feeder base location.
            new_offset_x = found_world_x - feeder_loc.getX()
            new_offset_y = found_world_y - feeder_loc.getY()
            
            from org.openpnp.model import Location
            # Preserve Z/Rotation from existing offset
            old_z = current_offset.getZ() if current_offset else 0.0
            old_rot = current_offset.getRotation() if current_offset else 0.0
            
            final_offset = Location(feeder_loc.getUnits(), new_offset_x, new_offset_y, old_z, old_rot)
            
            if callback: 
                callback("Found! Delta: X=%.3f, Y=%.3f" % (dx_mm, dy_mm))
                # callback("New Offset: X=%.3f, Y=%.3f" % (new_offset_x, new_offset_y))
            
            # 6. Update Feeder
            feeder.setOffset(final_offset)
            feeder.setEnabled(True)
            
            return True

        except Exception as e:
            if callback: 
                callback("Pocket Calibration Error: " + str(e))
            import traceback
            traceback.print_exc()
            return False


class SlotCalibrator:
    FIDUCIAL_PART_NAME = "Fiducial-1mm"

    def __init__(self, machine):
        self.machine = machine

    def run_calibration(self, feeders, log_callback, progress_callback, stop_event):
        """
        Run slot calibration on the provided list of feeders.
        
        Args:
            feeders: List of Feeder objects to calibrate
            log_callback: Function to call for logging (msg)
            progress_callback: Function to call for progress (current, total)
            stop_event: threading.Event to check for cancellation
        """
        log_callback("--- Starting Slot Calibration ---")
        
        # Instantiate PocketCalibrator
        pocket_calibrator = PocketCalibrator(self.machine)
        
        
        # 1. Validate Vision Setup
        try:
            fiducial_part = self._get_fiducial_part(log_callback)
            if not fiducial_part.getPackage():
                msg = "The Part '" + fiducial_part.getName() + "' has no Package assigned.\n"
                msg += "Vision cannot work without a footprint.\n"
                msg += "Please configure Vision/Footprint settings in the Parts tab."
                log_callback("STOPPING: " + msg)
                JOptionPane.showMessageDialog(None, msg, "Configuration Needed", JOptionPane.WARNING_MESSAGE)
                return
        except Exception as e:
            log_callback("CRITICAL: Vision Part setup failed: " + str(e))
            return

        # 2. Sort Feeders
        try:
            feeders.sort(key=self._get_slot_number)
            log_callback("Sorted feeders by slot number.")
        except Exception as e:
            log_callback("Warning: Sorting failed, using default order. " + str(e))

        total = len(feeders)
        log_callback("Calibrating " + str(total) + " feeders...")
        
        updated_count = 0
        
        for i, feeder in enumerate(feeders):
            # Check for cancellation
            if stop_event.is_set():
                log_callback("Calibration STOPPED by user.")
                break
                
            progress_callback(i, total)
            
            f_name = str(feeder.getName()) if feeder.getName() else "Unnamed"
            log_callback(">>> [" + str(i+1) + "/" + str(total) + "] Calibrating: " + f_name)
            
            try:
                # Get Target Location
                current_loc = feeder.getLocation()
                if hasattr(feeder, 'getSlot'):
                    slot = feeder.getSlot()
                    if slot:
                        current_loc = slot.getLocation()
                        # log_callback("  Using Slot Location.")
                
                # Check for 0,0,0
                if current_loc.x == 0 and current_loc.y == 0:
                    log_callback("  SKIP: Location is 0,0,0")
                    continue
                    
                # Vision Check
                # log_callback("  Locating fiducial...")
                found_loc = None
                
                try:
                    fiducial_locator = self.machine.getFiducialLocator()
                    if not fiducial_locator:
                         log_callback("  ERROR: No FiducialLocator on machine.")
                         continue
                         
                    found_loc = fiducial_locator.getFiducialLocation(current_loc, fiducial_part)
                except Exception as ev:
                    log_callback("  Vision Error: " + str(ev))
                    found_loc = None
                    
                if found_loc:
                    log_callback("  Fiducial FOUND at: X=" + str(round(found_loc.x, 3)) + ", Y=" + str(round(found_loc.y, 3)))
                    
                    # Update Location
                    base_loc = feeder.getLocation()
                    new_base_loc = Location(base_loc.units, found_loc.x, found_loc.y, base_loc.z, base_loc.rotation)
                    
                    if hasattr(feeder, 'getSlot') and feeder.getSlot():
                        slot = feeder.getSlot()
                        slot.setLocation(new_base_loc)
                        log_callback("  UPDATED Slot Location.")
                    else:
                        feeder.setLocation(new_base_loc)
                        log_callback("  UPDATED Feeder Location.")
                        
                        log_callback("  UPDATED Feeder Location.")
                        
                    updated_count += 1
                    
                    # 3. Pocket Calibration (Auto)
                    # Only if Slot was found and updated? Yes, otherwise we might be searching in the void.
                    log_callback("  > Attempting Pocket Calibration...")
                    # We pass a silent callback for non-critical failures, or just reuse log?
                    # Reuse log but maybe prefix?
                    pocket_success = pocket_calibrator.calibrate_feeder(feeder, callback=lambda m: log_callback("    [Pocket] " + m))
                    if pocket_success:
                        updated_count += 1 # Count pockets too? Or track separately?
                        log_callback("  > Pocket Calibrated.")
                    else:
                        log_callback("  > Pocket Calibration Skipped/Failed (See details above).")
                        
                else:
                    log_callback("  FAILED to locate fiducial.")
                    
            except Exception as e:
                log_callback("  AXIS/SYSTEM ERROR: " + str(e))
                traceback.print_exc()

        # Finish
        progress_callback(total, total)
        log_callback("--- Calibration Complete ---")
        log_callback("Updated " + str(updated_count) + " / " + str(total) + " feeders.")
        
        # Save changes
        try:
            if updated_count > 0:
                log_callback("Saving configuration...")
                Configuration.get().save()
                log_callback("Configuration saved.")
        except Exception as e:
            log_callback("Error saving config: " + str(e))

    def _get_fiducial_part(self, log_fn):
        config = Configuration.get()
        part = config.getPart(self.FIDUCIAL_PART_NAME)
        if part:
            return part
            
        all_parts = config.getParts()
        for p in all_parts:
            if p.name == self.FIDUCIAL_PART_NAME:
                return p
                
        # Create if missing
        log_fn("Creating new Fiducial Part: " + self.FIDUCIAL_PART_NAME)
        new_part = Part(self.FIDUCIAL_PART_NAME)
        new_part.setId(self.FIDUCIAL_PART_NAME)
        new_part.setName(self.FIDUCIAL_PART_NAME)
        config.addPart(new_part)
        
        msg = "Ref Fiducial Part created. Please configure Vision Settings for '" + self.FIDUCIAL_PART_NAME + "'."
        JOptionPane.showMessageDialog(None, msg, "Setup Required", JOptionPane.WARNING_MESSAGE)
        return new_part

    def _get_slot_number(self, feeder):
        name = str(feeder.getName())
        match = re.search(r'Slot:\s*(\d+)', name, re.IGNORECASE)
        if match:
            return int(match.group(1))
        if name.isdigit():
            return int(name)
        m2 = re.search(r'\((\d+)\)', name)
        if m2:
            return int(m2.group(1))
        return 999999
