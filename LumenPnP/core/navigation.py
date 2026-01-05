from org.openpnp.model import Configuration, Location
from java.awt.image import BufferedImage
from java.awt import Graphics2D, Color, Image
from javax.imageio import ImageIO
from java.io import File
import math
import os
import time

class MapNavigator:
    def __init__(self, machine):
        self.machine = machine
        self.config_dir = Configuration.get().getConfigurationDirectory().getAbsolutePath()
        self.map_path = os.path.join(self.config_dir, "machine_map.png")
        self.metadata_path = os.path.join(self.config_dir, "machine_map.properties")
        
        # Default machine limits (should be retrieved from axes in a real scenario, but defaults are safer for now)
        # LumenPnP typical size? Let's assume 500x500 or read from soft limits if possible.
        # For now, we'll try to determine from axes or utilize user input/defaults
        self.min_x = 0
        self.max_x = 420 # mm
        self.min_y = 0
        self.max_y = 400 # mm
        
        # Load metadata if exists to restore coordinate mapping
        self.image_width = 0
        self.image_height = 0
        self._load_metadata()

    def scan_bed(self, log_val, progress_callback, stop_event):
        """
        Scans the machine bed by saving tiles to disk, then stitching them.
        """
        camera = self.machine.getDefaultHead().getDefaultCamera()
        if not camera:
            raise Exception("No default camera found")

        # 1. Setup Directories
        temp_dir = os.path.join(self.config_dir, "lumen_scan_temp")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        # Clear old tiles?
        # for f in os.listdir(temp_dir):
        #    os.remove(os.path.join(temp_dir, f))

        # 2. Camera & Grid Setup
        upp_x = camera.getUnitsPerPixel().x
        upp_y = camera.getUnitsPerPixel().y
        
        if upp_x == 0 or upp_y == 0:
            raise Exception("Camera UnitsPerPixel is not calibrated (0).")
            
        try:
            fmt = camera.getFormat()
            # Dynamic dimension parsing (Regex fallback)
            w = 0; h = 0
            if hasattr(fmt, 'width'): w = fmt.width
            elif hasattr(fmt, 'getWidth'): w = fmt.getWidth()
            elif hasattr(fmt, 'getWidthPixels'): w = fmt.getWidthPixels()
            
            if hasattr(fmt, 'height'): h = fmt.height
            elif hasattr(fmt, 'getHeight'): h = fmt.getHeight()
            elif hasattr(fmt, 'getHeightPixels'): h = fmt.getHeightPixels()
            
            if w == 0 or h == 0:
                import re
                fmt_str = str(fmt)
                m = re.search(r'(\d+)\s*x\s*(\d+)', fmt_str)
                if m:
                    w = int(m.group(1)); h = int(m.group(2))
                    log_val("DEBUG: Parsed dimensions: " + str(w) + "x" + str(h))

            if w == 0 or h == 0: raise Exception("No camera dimensions.")
            
            fov_width = w * upp_x
            fov_height = h * upp_y
        except Exception as e:
            log_val("Error getting format: " + str(e))
            raise e

        overlap = 0.1 
        step_x = fov_width * (1.0 - overlap)
        step_y = fov_height * (1.0 - overlap)
        
        cols = int(math.ceil((self.max_x - self.min_x) / step_x))
        rows = int(math.ceil((self.max_y - self.min_y) / step_y))
        
        log_val("Grid: " + str(cols) + " cols x " + str(rows) + " rows")
        
        total_steps = cols * rows
        current_step = 0
        
        original_loc = camera.getLocation()
        
        # 3. SCAN LOOP (Move & Save Only)
        try:
            log_val("Starting Scan Loop (Saving to " + temp_dir + ")...")
            
            for r in range(rows):
                center_y = self.max_y - (r * step_y) - (fov_height / 2)
                if center_y < self.min_y: center_y = self.min_y + (fov_height/2) 
                
                for c in range(cols):
                    if stop_event.is_set(): return

                    progress_callback(current_step, total_steps)
                    current_step += 1
                    
                    center_x = self.min_x + (c * step_x) + (fov_width / 2)
                    if center_x > self.max_x: center_x = self.max_x - (fov_width/2)

                    # Move
                    target = Location(original_loc.units, center_x, center_y, original_loc.z, 0)
                    camera.moveTo(target, self.machine.getSpeed())
                    
                    # Settle
                    time.sleep(0.5) # Increased to reduce motion blur
                    
                    # Capture
                    img = camera.capture()
                    
                    # Save Tile
                    tile_name = "tile_{}_{}.png".format(r, c)
                    tile_path = os.path.join(temp_dir, tile_name)
                    ImageIO.write(img, "png", File(tile_path))
                    
                    # log_val("Saved " + tile_name)
                    
        except Exception as e:
            log_val("Scan Logic Error: " + str(e))
            raise e

        # 4. POST-PROCESSING (Stitch)
        log_val("Scan Complete. Stitching Map...")
        self._stitch_map(temp_dir, rows, cols, w, h, upp_x, upp_y, overlap, log_val, stop_event)

    def _stitch_map(self, temp_dir, rows, cols, cam_w, cam_h, upp_x, upp_y, overlap, log_val, stop_event):
        # Calculate final size
        total_width_mm = self.max_x - self.min_x
        total_height_mm = self.max_y - self.min_y
        
        # Scale factor (0.1 = 10%)
        # To scale down by 10, we sample every 10th pixel.
        step_sample = 10
        
        final_w = int((total_width_mm / upp_x) / step_sample)
        final_h = int((total_height_mm / upp_y) / step_sample)
        
        log_val("Stitching into Image: " + str(final_w) + "x" + str(final_h) + " (Manual Raster Mode)")
        
        try:
            # Create Master Image 
            result_image = BufferedImage(final_w, final_h, BufferedImage.TYPE_INT_RGB)
            
            # Note: We do NOT use Graphics2D at all to avoid freezing.
            
            fov_width = cam_w * upp_x
            fov_height = cam_h * upp_y
            step_x = fov_width * (1.0 - overlap)
            step_y = fov_height * (1.0 - overlap)

            log_val("Starting Stitch Loop (Pixel-by-Pixel)...")
            
            for r in range(rows):
                log_val("Stitching Row " + str(r+1) + "/" + str(rows))
                
                center_y = self.max_y - (r * step_y) - (fov_height / 2)
                if center_y < self.min_y: center_y = self.min_y + (fov_height/2) 
                
                for c in range(cols):
                    if stop_event.is_set():
                        log_val("Stitching Aborted")
                        return

                    center_x = self.min_x + (c * step_x) + (fov_width / 2)
                    if center_x > self.max_x: center_x = self.max_x - (fov_width/2)
                    
                    # Tile Logic
                    tile_name = "tile_{}_{}.png".format(r, c)
                    tile_path = os.path.join(temp_dir, tile_name)
                    f_tile = File(tile_path)
                    
                    if f_tile.exists():
                        try:
                            img_tile = ImageIO.read(f_tile)
                            tile_w = img_tile.getWidth()
                            tile_h = img_tile.getHeight()
                            
                            # Calculate Base Global Position for this tile's Top-Left (Scaled)
                            # Raw Global Pos (TopLeft) = Center - (FOV/2)
                            # Transformed by Scale
                            
                            raw_tl_x = (center_x - self.min_x - (fov_width/2)) / upp_x
                            raw_tl_y = (self.max_y - (center_y + (fov_height/2))) / upp_y
                                                        
                            base_dest_x = int(raw_tl_x / step_sample)
                            base_dest_y = int(raw_tl_y / step_sample)
                            
                            # Manual Subsampling Loop
                            # Iterate over tile pixels with Step
                            # Python loops are slow, but robust against drawing freeze?
                            # Optimization: Reading full array is awkward in Jython. 
                            # We will try pixel get/set first. If too slow, optimize later.
                            
                            for ty in range(0, tile_h, step_sample):
                                for tx in range(0, tile_w, step_sample):
                                    # Get Source Pixel
                                    rgb = img_tile.getRGB(tx, ty)
                                    
                                    # Dest Coords
                                    dx = base_dest_x + (tx / step_sample)
                                    dy = base_dest_y + (ty / step_sample)
                                    
                                    # Bounds Check
                                    if dx >= 0 and dx < final_w and dy >= 0 and dy < final_h:
                                        result_image.setRGB(dx, dy, rgb)
                                        
                        except Exception as e_tile:
                            log_val("Error processing tile " + tile_name + ": " + str(e_tile))
                            
                    # Trigger GC explicitly occasionally?
                    # System.gc() 
            
            # Save Master Map
            log_val("Saving final map...")
            ImageIO.write(result_image, "png", File(self.map_path))
            
            # Save Metadata
            self._save_metadata(final_w, final_h, self.min_x, self.max_x, self.min_y, self.max_y)
            self.image_width = final_w
            self.image_height = final_h
            
            log_val("Map Stitched & Saved Successfully.")
            
        except Exception as e:
            log_val("Stitching Failed: " + str(e))
            raise e

    def get_map_file(self):
        f = File(self.map_path)
        if f.exists():
            return self.map_path
        return None

    def pixel_to_machine(self, px, py):
        """Convert Image Pixel coordinates to Machine Coordinates (mm)"""
        # X is easy: MinX + (px * Range / Width)
        # Y is flipped: MaxY - (py * Range / Height)
        
        range_x = self.max_x - self.min_x
        range_y = self.max_y - self.min_y
        
        mm_x = self.min_x + (px / float(self.image_width)) * range_x
        mm_y = self.max_y - (py / float(self.image_height)) * range_y
        
        return (mm_x, mm_y)

    def _save_metadata(self, w, h, ex_min_x, ex_max_x, ex_min_y, ex_max_y):
        props = str(w)+","+str(h)+","+str(ex_min_x)+","+str(ex_max_x)+","+str(ex_min_y)+","+str(ex_max_y)
        with open(self.metadata_path, 'w') as f:
            f.write(props)
            
    def _load_metadata(self):
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, 'r') as f:
                data = f.read().split(',')
                if len(data) == 6:
                    self.image_width = int(data[0])
                    self.image_height = int(data[1])
                    self.min_x = float(data[2])
                    self.max_x = float(data[3])
                    self.min_y = float(data[4])
                    self.max_y = float(data[5])
