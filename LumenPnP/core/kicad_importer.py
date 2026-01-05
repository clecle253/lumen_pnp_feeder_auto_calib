# -*- coding: utf-8 -*-
import csv
import re
import os

class KiCadImporter:
    def __init__(self):
        self.bom_data = {} # Ref -> {cmp_id, val, pkg, manufacturer...}
        self.placements = [] # List of {ref, x, y, rot, side, status, ...}

    def parse_bom(self, file_path):
        """
        Parse BOM CSV.
        Expected Header like: "Reference","Value","CMP_ID","Manufacturer_Name","Manufacturer_Part_Number","Qté"
        """
        self.bom_data = {}
        if not os.path.exists(file_path):
            return "File not found: " + file_path
            
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                
            import csv
            reader = csv.reader(lines)
            
            header_found = False
            col_map = {}
            
            # print("DEBUG: Parsing BOM " + file_path)
            
            for row in reader:
                if not row: continue
                
                # Check for Header
                # We look for "Reference" and ("CMP_ID" or "Value")
                # Normalize header names for check
                row_norm = [c.strip().replace('"', '') for c in row]
                
                if not header_found:
                    # Heuristic to find header row
                    if "Reference" in row_norm and ("CMP_ID" in row_norm or "Value" in row_norm):
                        header_found = True
                        # Map headers
                        for i, name in enumerate(row_norm):
                            col_map[name] = i
                        # print("DEBUG: Header found: " + str(col_map))
                        continue
                
                if not header_found:
                    continue
                    
                # Parse Data
                def get_val(name):
                    if name in col_map:
                        return row[col_map[name]].strip()
                    return ""
                
                refs_str = get_val("Reference")
                cmp_id = get_val("CMP_ID")
                val = get_val("Value")
                
                # Split refs "C1, C2"
                refs = [r.strip() for r in refs_str.split(',')]
                
                for r in refs:
                    if r:
                        # Normalize Ref to Upper Case for matching
                        r_key = r.upper()
                        self.bom_data[r_key] = {
                            "cmp_id": cmp_id,
                            "value": val,
                            "original_row": row
                        }
                            
        except Exception as e:
             return "Exception parsing BOM: " + str(e)
                        
        return None # Success

    def parse_pos(self, file_path, side_override=None):
        """
        Parse .pos file.
        Format is fixed width/space separated.
        # Ref     Val       Package      PosX       PosY       Rot  Side
        """
        if not file_path or not os.path.exists(file_path):
            return "File not found"

        with open(file_path, 'r') as f:
            lines = f.readlines()
            
        # Regex to interpret the line
        # C4 0.1uF Package 134.7750 -64.7105 -90.0000 top
        # Ref is always first. 
        # But wait, Val and Package can contain spaces? "1uF 25V"
        # The user example: 
        # C4        0.1uF               C_0603_...      134.7750 ...
        # It looks like wide whitespace separation.
        
        parsed_count = 0
        for line in lines:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
                
            # Split by whitespace
            parts = line.split()
            if len(parts) < 6:
                continue
                
            # Structure usually: Ref (0), Val (1), Pkg (2), PosX (-4), PosY (-3), Rot (-2), Side (-1)
            # BUT Val and Pkg might be split if they contain spaces.
            # User example:
            # C13       22uF_10V_NP         C_0603...
            # Validation seems to use underscores for spaces in user provided example, ensuring no spaces in Val?
            # User wrote: "1uF 25V" in BOM, but ".pos" example shows "22uF_10V_NP".
            # KiCad POS export usually replaces spaces with underscores or quotes strings.
            # Assuming safe whitespace splitting for X, Y, Rot, Side (last 4 columns).
            
            # Safe logic:
            try:
                ref = parts[0]
                side = parts[-1]
                rot = float(parts[-2])
                pos_y = float(parts[-3])
                pos_x = float(parts[-4])
                
                # Debug specific ref
                # if "IC5" in ref:
                #    print("DEBUG: POS found IC5 -> X:" + str(pos_x) + " Y:" + str(pos_y))
                
                self.placements.append({
                    "ref": ref,
                    "x": pos_x,
                    "y": pos_y,
                    "rot": rot,
                    "side": side,
                    "source": "pos"
                })
                parsed_count += 1
            except ValueError as e:
                # print("DEBUG: Error parsing POS line: '" + line + "' -> " + str(e))
                continue
            
        # print("DEBUG: Parsed " + str(parsed_count) + " placements from " + file_path)
        return None

    def reconcile(self):
        """
        Merge BOM and POS data.
        Returns a list of dicts for the GUI table.
        """
        results = []
        
        # 1. Iterate Placements (from POS)
        for p in self.placements:
            ref = p['ref']
            item = {
                "ref": ref,
                "x": p['x'],
                "y": p['y'],
                "rot": p['rot'],
                "side": p['side'],
                "cmp_id": "",
                "value": "",
                "status": "OK",
                "action": "Import"
            }
            
            # Find in BOM
            ref_key = ref.upper()
            if ref_key in self.bom_data:
                bom_entry = self.bom_data[ref_key]
                item['cmp_id'] = bom_entry.get('cmp_id', '')
                item['value'] = bom_entry.get('value', '')
                
                if not item['cmp_id']:
                    item['status'] = "MISSING_ID" # In BOM but no CMP_ID?
                else:
                    item['status'] = "OK"
            else:
                item['status'] = "MISSING_BOM" # In POS but not in BOM
                item['action'] = "Ignore" # Default to ignore? Or Warn?
            
            results.append(item)
            
        # 2. Check for BOM items not in POS (optional, maybe user wants to know?)
        # For now, we only care about what we physically place.
        
        return results

