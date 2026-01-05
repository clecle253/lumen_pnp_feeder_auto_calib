import csv
import os
from org.openpnp.model import Configuration

class MappingStore:
    """
    Manages the mapping between Part Name patterns and Vision/Template Part IDs.
    Stored in 'lumen_pocket_map.csv' in the configuration directory.
    Format: pattern,vision_part_id
    """
    
    def __init__(self):
        self.config_dir = Configuration.get().getConfigurationDirectory().getAbsolutePath()
        self.file_path = os.path.join(self.config_dir, "lumen_pocket_map.csv")
        self.mappings = [] # List of dicts: {'pattern': str, 'vision_part_id': str}
        self.load()

    def load(self):
        """Load mappings from CSV"""
        self.mappings = []
        if not os.path.exists(self.file_path):
            return

        try:
            with open(self.file_path, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        self.mappings.append({
                            'pattern': row[0].strip(),
                            'vision_part_id': row[1].strip()
                        })
        except Exception as e:
            print("Error loading mapping file: " + str(e))

    def save(self):
        """Save mappings to CSV"""
        try:
            with open(self.file_path, 'w') as f: # Jython 2.7 csv module handles simple ASCII fine
                # write manually to ensure no newline issues across platforms if using csv module
                for m in self.mappings:
                    f.write(m['pattern'] + "," + m['vision_part_id'] + "\n")
        except Exception as e:
            print("Error saving mapping file: " + str(e))

    def add_mapping(self, pattern, vision_part_id):
        """Add or update a mapping"""
        # Check if update
        for m in self.mappings:
            if m['pattern'] == pattern:
                m['vision_part_id'] = vision_part_id
                self.save()
                return
        
        # New
        self.mappings.append({'pattern': pattern, 'vision_part_id': vision_part_id})
        self.save()

    def remove_mapping(self, pattern):
        """Remove a mapping by pattern"""
        self.mappings = [m for m in self.mappings if m['pattern'] != pattern]
        self.save()

    def get_vision_part_id(self, part_name):
        """
        Find the Vision Part ID for a given Part Name.
        Checks for:
        1. Exact Match
        2. Substring Match (Pattern is in Part Name)
        Returns None if no match.
        """
        if not part_name:
            return None
            
        # Priority 1: Exact Match
        for m in self.mappings:
            if m['pattern'] == part_name:
                return m['vision_part_id']
                
        # Priority 2: Substring Match (Longest pattern wins?)
        # For now, first match. Sorted by length descending could be better.
        for m in self.mappings:
            if m['pattern'] in part_name:
                return m['vision_part_id']
                
        return None
