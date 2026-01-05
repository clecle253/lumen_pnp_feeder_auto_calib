import json
import os

class VisionProfile:
    METHODS = ["RECT", "CIRCLE"]
    
    def __init__(self, name="Default"):
        self.name = name
        self.method = "RECT" # RECT or CIRCLE
        # Pre-processing
        self.brightness = 0 # -100 to 100 (Software)
        self.contrast = 0   # -100 to 100 (Software)
        
        # Hardware
        self.camera_brightness = -1 # -1 = Ignore/Default. Range often -100 to 100 or 0-255 depending on cam
        
        self.threshold_min = 100
        self.threshold_max = 255
        self.invert = False
        self.blur_size = 0 # 0 = Off
        
        # Masking
        self.mask_type = "NONE" # NONE, CIRCLE, RECT
        self.mask_width = 600   # For Rect (Width) or Circle (Diameter)
        self.mask_height = 600  # For Rect (Height)
        
        # Filter Sizes (in pixels)
        self.min_area = 100
        self.max_area = 10000
        self.min_width = 10
        self.max_width = 800
        self.min_height = 10
        self.max_height = 800
        # For Circle
        self.min_diameter = 10
        self.max_diameter = 500

    def to_dict(self):
        return {
            "name": self.name,
            "method": self.method,
            "brightness": self.brightness,
            "contrast": self.contrast,
            "camera_brightness": self.camera_brightness,
            "threshold_min": self.threshold_min,
            "threshold_max": self.threshold_max,
            "invert": self.invert,
            "blur_size": self.blur_size,
            "mask_type": self.mask_type,
            "mask_width": self.mask_width,
            "mask_height": self.mask_height,
            "min_area": self.min_area,
            "max_area": self.max_area,
            "min_width": self.min_width,
            "max_width": self.max_width,
            "min_height": self.min_height,
            "max_height": self.max_height,
            "min_diameter": self.min_diameter,
            "max_diameter": self.max_diameter
        }

    @staticmethod
    def from_dict(data):
        p = VisionProfile(data.get("name", "Unknown"))
        p.method = data.get("method", "RECT")
        p.brightness = data.get("brightness", 0)
        p.contrast = data.get("contrast", 0)
        p.camera_brightness = data.get("camera_brightness", -1)
        p.threshold_min = data.get("threshold_min", 100)
        p.threshold_max = data.get("threshold_max", 255)
        p.invert = data.get("invert", False)
        p.blur_size = data.get("blur_size", 0)
        p.mask_type = data.get("mask_type", "NONE")
        p.mask_width = data.get("mask_width", 600)
        p.mask_height = data.get("mask_height", 600)
        p.min_area = data.get("min_area", 100)
        p.max_area = data.get("max_area", 10000)
        p.min_width = data.get("min_width", 10)
        p.max_width = data.get("max_width", 800)
        p.min_height = data.get("min_height", 10)
        p.max_height = data.get("max_height", 800)
        p.min_diameter = data.get("min_diameter", 10)
        p.max_diameter = data.get("max_diameter", 500)
        return p

class VisionStore:
    def __init__(self, storage_dir=None):
        if storage_dir is None:
            # Default to user home + .lumen_pnp
            home = os.path.expanduser("~")
            self.storage_dir = os.path.join(home, ".lumen_pnp")
        else:
            self.storage_dir = storage_dir
            
        if not os.path.exists(self.storage_dir):
            try:
                os.makedirs(self.storage_dir)
            except:
                pass
                
        self.config_file = os.path.join(self.storage_dir, "lumen_vision_profiles.json")
        self.profiles = {} # name -> VisionProfile
        self.load()
        
    def save_profile(self, profile):
        self.profiles[profile.name] = profile
        self.save()

    def delete_profile(self, name):
        if name in self.profiles:
            del self.profiles[name]
            self.save()

    # --- Mappings (PartID/FeederID -> ProfileName) ---
    def get_mapping(self, item_id):
        # item_id could be Part.id or Feeder.name
        return self.mappings.get(str(item_id))

    def set_mapping(self, item_id, profile_name):
        self.mappings[str(item_id)] = profile_name
        self.save()
        
    def load(self):
        self.profiles = {}
        self.mappings = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    for item in data.get("profiles", []):
                        p = VisionProfile.from_dict(item)
                        self.profiles[p.name] = p
                    self.mappings = data.get("mappings", {})
            except Exception as e:
                print("Error loading vision profiles: " + str(e))
        
        # Ensure at least one default profile
        if not self.profiles:
            default_rect = VisionProfile("Default Rect")
            self.save_profile(default_rect)

    def get_profile(self, name):
        return self.profiles.get(name)

    def get_all_profiles(self):
        return list(self.profiles.values())

    def save(self):
        data = {
            "profiles": [p.to_dict() for p in self.profiles.values()],
            "mappings": self.mappings
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print("Error saving vision profiles: " + str(e))
