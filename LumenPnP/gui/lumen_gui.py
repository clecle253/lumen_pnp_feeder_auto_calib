# -*- coding: utf-8 -*-
"""
Main GUI Window for LumenPnP Plugin
Tkinter-based interface with tabbed layout
"""

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext
except ImportError:
    # Jython compatibility - use Swing instead
    print("Tkinter not available, using Swing")
    import javax.swing as swing
    USE_SWING = True
else:
    USE_SWING = False


class LumenPnPGUI:
    """Main GUI window for LumenPnP plugin"""
    
    def __init__(self, machine, openpnp_gui):
        """
        Initialize the GUI
        
        Args:
            machine: OpenPnP machine object
            openpnp_gui: OpenPnP GUI object
        """
        self.machine = machine
        self.openpnp_gui = openpnp_gui
        self.window = None
        
    def run(self):
        """Create and run the GUI"""
        print("LumenPnPGUI.run() called")
        try:
            if USE_SWING:
                from javax.swing import SwingUtilities
                from java.lang import Runnable
                
                class CreateGuiRunnable(Runnable):
                    def run(r_self):
                        try:
                            self._create_swing_gui()
                        except Exception as e:
                            print("CRITICAL ERROR creating Swing GUI: " + str(e))
                            import traceback
                            traceback.print_exc()

                print("Scheduling GUI creation on EDT...")
                SwingUtilities.invokeLater(CreateGuiRunnable())
            else:
                self._create_tkinter_gui()
        except Exception as e:
             print("Error in run(): " + str(e))
             import traceback
             traceback.print_exc()
    
    def _create_tkinter_gui(self):
        """Create Tkinter-based GUI"""
        self.window = tk.Tk()
        self.window.title("LumenPnP Plugin")
        self.window.geometry("1200x900")
        
        # Create main container
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=0)
        
        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Create tabs
        self.calibration_tab = self._create_calibration_tab()
        self.kicad_tab = self._create_kicad_tab()
        self.navigation_tab = self._create_navigation_tab()
        
        self.notebook.add(self.calibration_tab, text="Feeder Calibration")
        self.notebook.add(self.kicad_tab, text="KiCad Import")
        self.notebook.add(self.navigation_tab, text="Fast Travel")
        
        # Create log panel (shared across all tabs)
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add initial log message
        self.log("LumenPnP Plugin initialized successfully")
        self.log("Machine: " + str(self.machine))
        
        # Start GUI loop
        self.window.mainloop()
    
    def _create_calibration_tab(self):
        """Create the Feeder Calibration tab"""
        tab = ttk.Frame(self.notebook, padding="10")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        
        # Title
        title = ttk.Label(tab, text="Feeder Calibration", font=("Arial", 14, "bold"))
        title.grid(row=0, column=0, pady=(0, 10), sticky=tk.W)
        
        # Feeder list frame
        list_frame = ttk.LabelFrame(tab, text="Feeders", padding="5")
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Feeder listbox with scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.feeder_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, selectmode=tk.EXTENDED)
        self.feeder_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.config(command=self.feeder_listbox.yview)
        
        # Populate feeder list (placeholder)
        self._populate_feeder_list()
        
        # Button frame
        button_frame = ttk.Frame(tab)
        button_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(button_frame, text="Scan Feeders", command=self._scan_feeders).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Calibrate Slots", command=self._calibrate_slots).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Calibrate Pockets (WIP)", command=self._calibrate_pockets, state=tk.DISABLED).grid(row=0, column=2, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(tab, mode='determinate')
        self.progress.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        return tab
    
    def _create_kicad_tab(self):
        """Create the KiCad Import tab with File Selection and Validation Table"""
        from javax.swing import JPanel, JLabel, JButton, JTextField, JTable, JScrollPane, BorderFactory, Box, BoxLayout, JFileChooser, JComboBox
        from javax.swing.table import DefaultTableModel
        from java.awt import BorderLayout, GridLayout, Color, Dimension
        
        panel = JPanel(BorderLayout())
        
        # -- TOP PANEL: File Selection --
        file_panel = JPanel(GridLayout(3, 3, 5, 5))
        file_panel.setBorder(BorderFactory.createTitledBorder("Files"))
        
        self.txt_bom = JTextField()
        self.txt_top = JTextField()
        self.txt_bot = JTextField()
        
        # Load saved paths
        saved_paths = self._load_kicad_paths()
        if saved_paths:
            self.txt_bom.setText(saved_paths.get("bom", ""))
            self.txt_top.setText(saved_paths.get("top", ""))
            self.txt_bot.setText(saved_paths.get("bot", ""))

        def pick_file(field):
            fc = JFileChooser()
            if field.getText():
                from java.io import File
                fc.setCurrentDirectory(File(field.getText()).getParentFile())
            ret = fc.showOpenDialog(self.window)
            if ret == JFileChooser.APPROVE_OPTION:
                field.setText(fc.getSelectedFile().getAbsolutePath())
        
        file_panel.add(JLabel("BOM (.csv):")); file_panel.add(self.txt_bom); file_panel.add(JButton("Browse", actionPerformed=lambda e: pick_file(self.txt_bom)))
        file_panel.add(JLabel("Top (.pos):")); file_panel.add(self.txt_top); file_panel.add(JButton("Browse", actionPerformed=lambda e: pick_file(self.txt_top)))
        file_panel.add(JLabel("Bottom (.pos):")); file_panel.add(self.txt_bot); file_panel.add(JButton("Browse", actionPerformed=lambda e: pick_file(self.txt_bot)))
        
        top_container = JPanel(BorderLayout())
        top_container.add(file_panel, BorderLayout.CENTER)
        top_container.add(JButton("Process Files", actionPerformed=lambda e: self._process_kicad_files()), BorderLayout.SOUTH)
        
        panel.add(top_container, BorderLayout.NORTH)
        
        # -- CENTER PANEL: Validation Table --
        # Columns: Ref, CMP_ID, Value, Side, Status, Action
        self.kicad_cols = ["Ref", "CMP_ID", "Value", "Side", "Status", "Action"]
        self.kicad_table_model = DefaultTableModel(self.kicad_cols, 0)
        self.kicad_table = JTable(self.kicad_table_model)
        
        # Scroll pane
        table_scroll = JScrollPane(self.kicad_table)
        table_scroll.setBorder(BorderFactory.createTitledBorder("Validation"))
        panel.add(table_scroll, BorderLayout.CENTER)
        
        # -- BOTTOM PANEL: Actions --
        action_panel = JPanel(GridLayout(1, 2, 10, 10))
        action_panel.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10))
        
        btn_gen = JButton("Generate Board", actionPerformed=lambda e: self._generate_board())
        btn_gen.setBackground(Color(100, 255, 100))
        
        action_panel.add(JLabel("Review discrepancies above before generating."))
        action_panel.add(btn_gen)
        
        panel.add(action_panel, BorderLayout.SOUTH)
        
        return panel

    def _process_kicad_files(self):
        """Parse files and populate table"""
        from LumenPnP.core.kicad_importer import KiCadImporter
        
        bom_path = self.txt_bom.getText()
        top_path = self.txt_top.getText()
        bot_path = self.txt_bot.getText()
        
        if not bom_path or (not top_path and not bot_path):
            self.log("Please select BOM and at least one POS file.")
            return

        # Save paths for next time
        self._save_kicad_paths(bom_path, top_path, bot_path)
            
        self.importer = KiCadImporter()
        
        # Parse BOM
        err = self.importer.parse_bom(bom_path)
        if err:
            self.log("Error parsing BOM: " + err)
            return
            
        # Parse POS
        if top_path: self.importer.parse_pos(top_path)
        if bot_path: self.importer.parse_pos(bot_path)
        
        # Reconcile
        self.kicad_data = self.importer.reconcile()
        
        # Sort Data: Errors first, then by Ref
        # Priority: MISSING_BOM/ID -> 0, OK -> 1
        def sort_key(item):
            prio = 1 if item['status'] == 'OK' else 0
            # Split Ref to sort naturally (C1, C2, C10...)
            import re
            match = re.match(r"([A-Za-z]+)(\d+)", item['ref'])
            if match:
                ref_tuple = (match.group(1), int(match.group(2)))
            else:
                ref_tuple = (item['ref'], 0)
            return (prio, ref_tuple)
            
        self.kicad_data.sort(key=sort_key)
        
        # Update Table (Clear first)
        self.kicad_table_model.setRowCount(0)
        
        for item in self.kicad_data:
            row = [
                item['ref'],
                item['cmp_id'],
                item['value'],
                item['side'],
                item['status'],
                item['action']
            ]
            self.kicad_table_model.addRow(row)
            
        # Apply Custom Renderer for Highlighting
        from javax.swing.table import DefaultTableCellRenderer
        from java.awt import Color, Component
        
        class StatusCellRenderer(DefaultTableCellRenderer):
            def getTableCellRendererComponent(self, table, value, isSelected, hasFocus, row, col):
                c = super(StatusCellRenderer, self).getTableCellRendererComponent(table, value, isSelected, hasFocus, row, col)
                
                # Get Status from column 4
                status = table.getValueAt(row, 4)
                
                # Reset standard Colors first
                if isSelected:
                    c.setBackground(table.getSelectionBackground())
                    c.setForeground(table.getSelectionForeground())
                else:
                    # Harmonious Dark Theme
                    c.setBackground(Color(45, 45, 48)) # VSCode-like Dark Gray
                    
                    if status != "OK":
                        c.setForeground(Color(255, 140, 0)) # Dark Orange (User Preference)
                    else:
                        c.setForeground(Color(220, 220, 220)) # Off-White for Normal
                
                return c
        
        renderer = StatusCellRenderer()
        for i in range(self.kicad_table.getColumnCount()):
            self.kicad_table.getColumnModel().getColumn(i).setCellRenderer(renderer)
            
        self.log("Processed " + str(len(self.kicad_data)) + " items.")

    def _generate_board(self):
        """Create OpenPnP Board from Validated Data"""
        from javax.swing import JOptionPane
        from org.openpnp.model import Configuration, Board, Placement, Location, Part, Package
        from org.openpnp.model import LengthUnit
        
        # 1. Gather Data from Table
        model = self.kicad_table_model
        rows = model.getRowCount()
        
        valid_items = []
        parts_to_create = set()
        
        for i in range(rows):
            # Columns: Ref, CMP_ID, Value, Side, Status, Action
            action = model.getValueAt(i, 5)
            status = model.getValueAt(i, 4)
            cmp_id = model.getValueAt(i, 1)
            ref = model.getValueAt(i, 0)
            
            if action != "Import":
                continue
                
            if not cmp_id:
                self.log("Skipping " + str(ref) + " (No CMP_ID)")
                continue
                
            # Check if Part exists
            part = Configuration.get().getPart(cmp_id)
            if not part:
                parts_to_create.add(cmp_id)
                
            # Get original data coordinates
            # Note: Table values might not be enough
            valid_items.append({
                "ref": ref,
                "cmp_id": cmp_id,
                "x": float(self._get_original_data(ref, 'x')),
                "y": float(self._get_original_data(ref, 'y')),
                "rot": float(self._get_original_data(ref, 'rot')),
                "side": str(self._get_original_data(ref, 'side')),
                # Ensure value comes from the table in case user edited it?
                # Actually, user edits are not yet supported in table, stick to model/original
                "value": model.getValueAt(i, 2)
            })

        if not valid_items:
            self.log("No valid items to import.")
            return

        # 2. Confirmation Popup
        import os
        bom_path = self.txt_bom.getText()
        default_name = os.path.splitext(os.path.basename(bom_path))[0] if bom_path else "Imported Board"
        
        board_name = JOptionPane.showInputDialog(self.window, "Enter Board Name:", default_name)
        
        if not board_name:
            self.log("Generation Cancelled (No Name).")
            return
            
        config = Configuration.get()
        existing_boards = config.getBoards()
        name_conflict = False
        for b in existing_boards:
            if b.getName() == board_name:
                name_conflict = True
                break
        
        if name_conflict:
            resp = JOptionPane.showConfirmDialog(self.window, 
                "A Board with this name already exists.\nCreate anyway?", 
                "Duplicate Board Name", 
                JOptionPane.YES_NO_OPTION,
                JOptionPane.WARNING_MESSAGE)
            if resp != JOptionPane.YES_OPTION:
                self.log("Generation Cancelled.")
                return

        # 3. Execution
        self.log("Starting Generation...")
        try:
            # Create Missing Parts & Packages
            for pid in parts_to_create:
                self.log("Creating Part/Package: " + str(pid))
                
                # Create Package
                pkg = config.getPackage(pid)
                if not pkg:
                    pkg = Package(pid)
                    config.addPackage(pkg)
                
                # Create new Part
                new_part = Part(pid)
                
                # We need to find the value from one of the items
                val_desc = next((x['value'] for x in valid_items if x['cmp_id'] == pid), "")
                if not val_desc: val_desc = str(pid) # Fallback to ID if no value
                
                # Use Name field for the Description/Value (as requested)
                new_part.setName(val_desc)
                new_part.setPackage(pkg)
                
                config.addPart(new_part)
                
            # Create Board
            import java.io.File
            board = Board()
            board.setName(board_name)
            
            # Fix Save Error: Assign a File to the board
            # OpenPnP expects boards to be saved in specific files usually
            config_dir = None
            try:
                # Based on user logs, getResourceDirectory() needs args. 
                # getConfigurationDirectory() is usually the one for the root config folder.
                config_dir = Configuration.get().getConfigurationDirectory()
            except AttributeError:
                self.log("WARN: Configuration.getConfigurationDirectory() not found. Falling back to relative path.")
                pass
            
            if config_dir:
                board_file = java.io.File(config_dir, "boards/" + board_name.replace(" ", "_").replace(":", "") + ".board.xml")
            else:
                board_file = java.io.File("boards/" + board_name.replace(" ", "_").replace(":", "") + ".board.xml")
            
            # Make sure parent directory exists 
            if not board_file.getParentFile().exists():
                 board_file.getParentFile().mkdirs()
                 
            board.setFile(board_file)
            
            # Add Placements
            count = 0
            for item in valid_items:
                pl = Placement(item['ref'])
                
                # Get Part
                part = config.getPart(item['cmp_id'])
                pl.setPart(part)
                
                # Location
                x = item['x']
                y = item['y']
                rot = item['rot']
                
                loc = Location(LengthUnit.Millimeters, x, y, 0.0, rot)
                pl.setLocation(loc)
                
                # Set Side
                try:
                    side_str = item['side'].lower()
                    
                    # Robustly find the Side enum
                    # OpenPnP side enum location varies by version
                    side_enum = None
                    try:
                        side_enum = Location.Side
                    except:
                        try:
                             from org.openpnp.model import BoardLocation
                             side_enum = BoardLocation.Side
                        except:
                             try:
                                 from org.openpnp.model import BoardSide
                                 side_enum = BoardSide
                             except:
                                 self.log("ERROR: Could not find Side enum (Location.Side, BoardLocation.Side, or BoardSide)")
                    
                    if side_enum:
                        if "bottom" in side_str:
                            pl.setSide(side_enum.Bottom)
                        else:
                            pl.setSide(side_enum.Top)
                    else:
                         self.log("WARN: setSide skipped - enum not found")
                   
                except Exception as e:
                    self.log("WARN: Failed to set side for " + item['ref'] + ": " + str(e))
                
                board.addPlacement(pl)
                count += 1
            
            config.addBoard(board)
            config.save()
            
            self.log("Success! Created Board '" + board_name + "' with " + str(count) + " placements.")
            JOptionPane.showMessageDialog(self.window, "Board Created Successfully!")
            
        except Exception as e:
            self.log("Error generating board: " + str(e))
            import traceback
            traceback.print_exc()

    def _get_original_data(self, ref, field):
        """Helper to get X/Y/Rot from the source data (since table might not have it all)"""
        # We stored self.kicad_data in _process_kicad_files
        if hasattr(self, 'kicad_data'):
            for item in self.kicad_data:
                if item['ref'] == ref:
                    return item.get(field, 0)
        return 0

    
    def _load_kicad_paths(self):
        """Load last used paths from file"""
        import os
        from org.openpnp.model import Configuration
        
        config_dir = Configuration.get().getConfigurationDirectory().getAbsolutePath()
        prefs_file = os.path.join(config_dir, "lumenpnp_kicad.properties")
        
        if not os.path.exists(prefs_file):
            return None
            
        paths = {}
        try:
            with open(prefs_file, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, val = line.strip().split('=', 1)
                        paths[key] = val
            return paths
        except:
            return None

    def _save_kicad_paths(self, bom, top, bot):
        """Save paths to file"""
        import os
        from org.openpnp.model import Configuration
        
        config_dir = Configuration.get().getConfigurationDirectory().getAbsolutePath()
        prefs_file = os.path.join(config_dir, "lumenpnp_kicad.properties")
        
        try:
            with open(prefs_file, 'w') as f:
                f.write("bom=" + bom + "\n")
                f.write("top=" + top + "\n")
                f.write("bot=" + bot + "\n")
        except Exception as e:
            self.log("Error saving paths: " + str(e))

    def _create_navigation_tab(self):
        from javax.swing import JPanel, JLabel, JButton, JScrollPane, BorderFactory, Box, BoxLayout, SwingConstants, ImageIcon
        from java.awt import BorderLayout, Dimension, Color, Cursor, Image
        from java.awt.event import MouseAdapter
        
        panel = JPanel(BorderLayout())
        
        # -- MAP DISPLAY (Center) --
        self.map_label = JLabel("No Map Loaded", SwingConstants.CENTER)
        self.map_label.setOpaque(True)
        self.map_label.setBackground(Color.DARK_GRAY)
        self.map_label.setForeground(Color.WHITE)
        self.map_label.setHorizontalAlignment(SwingConstants.CENTER)
        
        # Mouse Listener for Click-to-Move
        class MapMouseListener(MouseAdapter):
            def __init__(self, parent): self.parent = parent
            def mouseClicked(self, e): self.parent._on_map_clicked(e.getX(), e.getY())
                
        self.map_label.addMouseListener(MapMouseListener(self))
        self.map_label.setCursor(Cursor.getPredefinedCursor(Cursor.CROSSHAIR_CURSOR))
        
        self.map_scroll = JScrollPane(self.map_label)
        panel.add(self.map_scroll, BorderLayout.CENTER)
        
        # -- CONTROL BAR (Top) --
        control_bar = JPanel()
        control_bar.setBorder(BorderFactory.createEmptyBorder(5, 5, 5, 5))
        
        btn_scan = JButton("Full Machine Scan", actionPerformed=lambda e: self._start_machine_scan())
        btn_reload = JButton("Reload Map", actionPerformed=lambda e: self._reload_map())
        
        control_bar.add(btn_scan)
        control_bar.add(btn_reload)
        control_bar.add(JLabel("  (Click on map to move machine)"))
        
        panel.add(control_bar, BorderLayout.NORTH)
        
        # Try to load map on init
        # threading.Thread(target=self._reload_map).start() # Don't block init
        
        return panel

    def _on_map_clicked(self, x, y):
        """Handle click on map -> Move machine"""
        if not hasattr(self, 'navigator'):
             from LumenPnP.core.navigation import MapNavigator
             self.navigator = MapNavigator(self.machine)
             
        if not self.map_label.getIcon():
            self.log("No map loaded. Please Scan first.")
            return
            
        try:
            # Calculate Display Offsets (Centering)
            icon = self.map_label.getIcon()
            icon_w = icon.getIconWidth()
            icon_h = icon.getIconHeight()
            
            label_w = self.map_label.getWidth()
            label_h = self.map_label.getHeight()
            
            offset_x = max(0, (label_w - icon_w) / 2)
            offset_y = max(0, (label_h - icon_h) / 2)
            
            # Adjust Click Coordinates
            adj_x = x - offset_x
            adj_y = y - offset_y
            
            # Check if click is valid (inside image)
            if adj_x < 0 or adj_x >= icon_w or adj_y < 0 or adj_y >= icon_h:
                # Clicked in the grey padding
                return

            # Apply Scale to adjusted coordinates
            scale = getattr(self, 'display_scale', 1.0)
            real_x = adj_x / scale
            real_y = adj_y / scale
            
            mm_x, mm_y = self.navigator.pixel_to_machine(real_x, real_y)
            
            self.log("Map Click: " + str(x) + "," + str(y) + 
                     " (Adj: " + str(int(adj_x)) + "," + str(int(adj_y)) + 
                     " @ " + str(round(scale,2)) + ") -> " + 
                     str(round(mm_x,1)) + ", " + str(round(mm_y,1)))
            
            from org.openpnp.model import Location
            head = self.machine.getDefaultHead()
            camera = head.getDefaultCamera()
            
            current_loc = camera.getLocation()
            target = Location(current_loc.units, mm_x, mm_y, current_loc.z, current_loc.rotation)
            
            def move_task():
                try:
                    speed = self.machine.getSpeed()
                    camera.moveTo(target, speed)
                    self.log("Move Complete.")
                except Exception as e:
                    self.log("Move Error: " + str(e))
            
            import threading
            threading.Thread(target=move_task).start()
            
        except Exception as e:
            self.log("Navigation Error: " + str(e))

    def _start_machine_scan(self):
        """Run the bed scan"""
        import threading
        from LumenPnP.core.navigation import MapNavigator
        
        self.log("Starting Full Bed Scan (This may take a while)...")
        
        def run_scan():
            try:
                if not hasattr(self, 'navigator'):
                    self.navigator = MapNavigator(self.machine)
                    
                stop_evt = threading.Event() 
                self.navigator.scan_bed(self.log, self._update_progress, stop_evt)
                self._reload_map()
                
            except Exception as e:
                self.log("Scan Failed: " + str(e))
                import traceback
                traceback.print_exc()
        
        t = threading.Thread(target=run_scan)
        t.start()

    def _reload_map(self):
        """Load map image from disk and display it"""
        from javax.swing import ImageIcon
        from java.awt import Image
        from LumenPnP.core.navigation import MapNavigator
        
        try:
             if not hasattr(self, 'navigator'):
                self.navigator = MapNavigator(self.machine)
                
             path = self.navigator.get_map_file()
             if path:
                 self.log("Loading map: " + path)
                 icon = ImageIcon(path)
                 
                 orig_w = icon.getIconWidth()
                 orig_h = icon.getIconHeight()
                 max_w = 1000
                 max_h = 700
                 
                 scale = 1.0
                 if orig_w > max_w or orig_h > max_h:
                     w_ratio = float(max_w) / float(orig_w)
                     h_ratio = float(max_h) / float(orig_h)
                     scale = min(w_ratio, h_ratio)
                     
                 self.display_scale = scale
                 
                 if scale < 1.0:
                     new_w = int(orig_w * scale)
                     new_h = int(orig_h * scale)
                     img_scaled = icon.getImage().getScaledInstance(new_w, new_h, Image.SCALE_SMOOTH)
                     icon = ImageIcon(img_scaled)
                     self.log("Map Scaled by " + str(round(scale, 2)))
                 
                 self.map_label.setIcon(icon)
                 self.map_label.setText("") 
                 
                 # Auto-Resize Window to fit new map
                 try:
                     # Get current window size
                     cur_w = self.window.getWidth()
                     cur_h = self.window.getHeight()
                     
                     # Target content size
                     target_w = icon.getIconWidth() + 60 # + Sidebars/Padding
                     target_h = icon.getIconHeight() + 350 # + Header + Log Panel (Increased from 200)
                     
                     # Don't shrink below minimum
                     target_w = max(1200, target_w)
                     target_h = max(900, target_h)
                     
                     # Don't grow beyond screen (heuristic)
                     target_w = min(1900, target_w)
                     target_h = min(1000, target_h)
                     
                     if target_w > cur_w or target_h > cur_h:
                         self.window.setSize(target_w, target_h)
                         self.log("Window resized to " + str(target_w) + "x" + str(target_h))
                         
                 except Exception as e_resize:
                     self.log("Resize error: " + str(e_resize))

             else:
                 self.map_label.setText("No Map Found")
                 
        except Exception as e:
            self.log("Error loading map: " + str(e))


    def _populate_feeder_list(self):
        """Populate the feeder list from machine configuration"""
        try:
            feeders = self.machine.getFeeders()
            self.feeder_listbox.delete(0, tk.END)
            
            for feeder in feeders:
                if feeder.isEnabled():
                    name = str(feeder.getName()) if feeder.getName() else "Unnamed"
                    self.feeder_listbox.insert(tk.END, name)
            
            self.log("Loaded " + str(self.feeder_listbox.size()) + " feeders")
        except Exception as e:
            self.log("Error loading feeders: " + str(e))
    
    def _update_slot_ui(self, slot_id, feeder=None, part_name=""):
        """Update the visual state of a slot widget"""
        if slot_id not in self.slot_widgets:
            return
            
        widget = self.slot_widgets[slot_id]
        lbl_name = widget.getClientProperty("lbl_name")
        from java.awt import Color
        
        if feeder:
            active_bg = Color(200, 255, 200) # Light Green for active
            widget.setBackground(active_bg)
            # IMPORTANT: Update original_bg so deselection reverts to Green, not Gray
            widget.putClientProperty("original_bg", active_bg)
            
            # Construct label text
            # User Preference: Show Part Name if available
            final_text = ""
            
            # Be paranoid about part_name
            if part_name and part_name != "Unnamed Part" and part_name != "Unknown":
                final_text = str(part_name)
            else:
                 # Fallback to feeder name if no part assigned
                 f_name = feeder.getName()
                 final_text = str(f_name) if f_name else "Unnamed Feeder"
            
            # Optional: Add abbreviated Slot ID or Feeder ID if needed, but User wanted just Part Name
            
            lbl_name.setText(" " + final_text)
            self.feeder_map[slot_id] = feeder
            
            # Enable Inline Buttons
            btn_f = widget.getClientProperty("btn_f")
            btn_p = widget.getClientProperty("btn_p")
            
            if btn_f:
                btn_f.setVisible(True)
                # Remove old listeners to prevent stacking? 
                # Jython makes removeActionListener tricky if we used lambdas.
                # Better: clean all, then add.
                for l in btn_f.getActionListeners(): btn_f.removeActionListener(l)
                btn_f.addActionListener(lambda e, f=feeder: self._move_to_feeder_slot(f))
                
            if btn_p:
                btn_p.setVisible(True)
                for l in btn_p.getActionListeners(): btn_p.removeActionListener(l)
                btn_p.addActionListener(lambda e, f=feeder: self._move_to_feeder_pocket(f))
            
        else:
            widget.setBackground(widget.getClientProperty("original_bg"))
            lbl_name.setText(" Empty")
            
            # Hide Buttons
            btn_f = widget.getClientProperty("btn_f")
            if btn_f: btn_f.setVisible(False)
            
            btn_p = widget.getClientProperty("btn_p")
            if btn_p: btn_p.setVisible(False)

    def _scan_feeders(self):
        try:
            from java.awt import Color
            from LumenPnP.core.navigation import MapNavigator
            from LumenPnP.core.calibration import SlotCalibrator, PocketCalibrator
            from LumenPnP.core.kicad_importer import KiCadImporter

            import re
            
            try:
                from LumenPnP.gui.vision_editor import VisionEditor
            except ImportError:
                 self.log("Warning: VisionEditor could not be imported. 'Vision Editor' button might fail.")
                 # VisionEditor = None # Optional: handle missing class
                 
            
            self.log("Scanning feeders...")
            
            self.feeder_map = {} # Reset map
            
            # Reset visual state
            for slot_id, widget in self.slot_widgets.items():
                widget.setBackground(Color(240, 240, 240)) # Gray
                widget.putClientProperty("original_bg", Color(240, 240, 240))
                lbl = widget.getClientProperty("lbl_name")
                lbl.setText(" Empty")
                lbl.setForeground(Color.GRAY)
            
            feeders = self.machine.getFeeders()
            found_count = 0
            
            # Regex to find slot ID:
            # 1. "Slot 12" or "Slot: 12" (Preferred)
            # 2. "(12)"
            # 3. Just digits at the START or END of string if distinct?
            
            for feeder in feeders:
                name = str(feeder.getName())
                if not feeder.isEnabled():
                    continue
                
                # Try to extract slot id
                slot_id = None
                
                # Check "Slot X" pattern first
                m_slot = re.search(r'Slot\D*(\d+)', name, re.IGNORECASE)
                if m_slot:
                     slot_id = int(m_slot.group(1))
                else:
                    # Fallback: Check for (X) pattern
                    m_paren = re.search(r'\((\d+)\)', name)
                    if m_paren:
                        slot_id = int(m_paren.group(1))
                    else:
                        # Fallback: Check for digits, but ignore if it looks like part size (0402, 0603)
                        m_digit = re.search(r'(\d+)', name)
                        if m_digit:
                             candidate = int(m_digit.group(1))
                             # Heuristic: If > 50, probably not a slot ID (unless high slots used)
                             if candidate <= 50:
                                 slot_id = candidate
                
                if slot_id:
                     if 1 <= slot_id <= 50:
                         # VALID MAPPING
                         part_name = ""
                         part = feeder.getPart()
                         if part:
                             # Try Name first, then ID
                             p_name = part.getName()
                             if not p_name:
                                 p_name = part.getId()
                             
                             part_name = str(p_name) if p_name else "Unnamed Part"
                         
                         self._update_slot_ui(slot_id, feeder, part_name)
                         found_count += 1
            
            self.log("Scan complete. Found " + str(found_count) + " feeders.")
            
        except Exception as e:
            self.log("Error scanning feeders: " + str(e))
    
    def _calibrate_slots(self):
        """Start slot calibration process"""
        self.log("Starting slot calibration...")
        # TODO: Integrate calibration logic
        self.log("Calibration not yet implemented - use existing script for now")
    
    def _calibrate_pockets(self):
        """Start pocket calibration process"""
        self.log("Starting pocket calibration...")
        # TODO: Implement pocket calibration
    
    def _create_swing_gui(self):
        """Create Swing-based GUI (fallback for Jython)"""
        from javax.swing import JFrame, JTabbedPane, JPanel, JTextArea, JScrollPane, JLabel, JButton, JList, DefaultListModel, BorderFactory, JSplitPane, SwingConstants
        from java.awt import BorderLayout, GridLayout, FlowLayout, Dimension, Color, Font
        
        self.window = JFrame("LumenPnP Plugin")
        self.window.setSize(1200, 900)
        self.window.setLayout(BorderLayout())
        
        # Tabs
        self.notebook = JTabbedPane()
        
        self.notebook.addTab("Calibration", self._create_calibration_panel())
        
        # KiCad Tab
        kicad_panel = self._create_kicad_tab()
        
        # Navigation Tab
        nav_panel = self._create_navigation_tab()
        
        self.notebook.addTab("KiCad Import", kicad_panel)
        self.notebook.addTab("Fast Travel", nav_panel)
        
        self.window.add(self.notebook, BorderLayout.CENTER)
        
        # Log Panel (South)
        log_panel = JPanel(BorderLayout())
        log_panel.setBorder(BorderFactory.createTitledBorder("Log"))
        log_panel.setPreferredSize(Dimension(800, 150))
        
        self.log_area = JTextArea()
        self.log_area.setEditable(False)
        self.log_area.setFont(Font("Monospaced", Font.PLAIN, 12))
        log_scroll = JScrollPane(self.log_area)
        log_panel.add(log_scroll, BorderLayout.CENTER)
        
        self.window.add(log_panel, BorderLayout.SOUTH)
        
        self.window.setVisible(True)

    def _create_calibration_panel(self):
        from javax.swing import JPanel, JLabel, JButton, BorderFactory, JSplitPane, Box, BoxLayout, JScrollPane, SwingConstants
        from java.awt import BorderLayout, GridLayout, Dimension, Color, Component, Font, FlowLayout, Insets
        from java.awt.event import MouseAdapter
        
        panel = JPanel(BorderLayout())
        panel.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10))
        
        # -- CENTER PANEL (Visual Feeder Banks) --
        # Layout: [Left Bank (26-50)]  [ Spacer ]  [Right Bank (25-1)]
        visual_panel = JPanel(GridLayout(1, 3, 20, 0)) # 1 Row, 3 Cols (Banks + Center spacer)
        
        # Helper to create a bank panel
        def create_bank_panel(title):
            p = JPanel(GridLayout(25, 1, 0, 2)) # 25 rows, 1 col, 2px gap
            p.setBorder(BorderFactory.createTitledBorder(title))
            return p
            
        self.left_bank_ui = create_bank_panel("Left Bank (26-50)")
        self.right_bank_ui = create_bank_panel("Right Bank (1-25)")
        
        # Store slot widgets in a dictionary: slot_id -> component
        self.slot_widgets = {}
        self.selected_feeder_name = None
        self.feeder_map = {} # slot_id -> feeder_object
        
        # Create Slot UI Helper
        class SlotMouseListener(MouseAdapter):
            def __init__(self, slot_id, parent):
                self.slot_id = slot_id
                self.parent = parent
            def mouseClicked(self, e):
                self.parent._on_slot_clicked(self.slot_id, e.getSource())

        def create_slot_widget(slot_id):
            p = JPanel(BorderLayout())
            p.setBorder(BorderFactory.createLineBorder(Color.LIGHT_GRAY))
            # ... (truncated for brevity in actual tool call if needed, but here replacing logic)
            p.setBackground(Color(240, 240, 240)) # Default Gray
            p.setPreferredSize(Dimension(150, 24)) # Slightly Taller for buttons
            
            lbl_id = JLabel(" " + str(slot_id) + " ", SwingConstants.CENTER)
            lbl_id.setPreferredSize(Dimension(30, 24))
            lbl_id.setBorder(BorderFactory.createMatteBorder(0, 0, 0, 1, Color.LIGHT_GRAY))
            
            lbl_name = JLabel(" Empty", SwingConstants.LEFT)
            lbl_name.setFont(lbl_name.getFont().deriveFont(10.0))
            
            p.add(lbl_id, BorderLayout.WEST)
            p.add(lbl_name, BorderLayout.CENTER)
            
            # Inline Buttons Panel (Right)
            btn_panel = JPanel(FlowLayout(FlowLayout.RIGHT, 0, 0))
            btn_panel.setOpaque(False)
            
            # Helper for mini button
            def make_mini_btn(txt, tip, bg):
                b = JButton(txt)
                b.setMargin(Insets(0,2,0,2))
                b.setFont(Font("SansSerif", Font.BOLD, 9))
                b.setPreferredSize(Dimension(20, 22))
                b.setToolTipText(tip)
                b.setBackground(bg)
                b.setFocusable(False)
                # Prevent click passing to parent slot widget (partially)
                return b

            btn_f = make_mini_btn("F", "Go to Feeder Slot", Color(220, 220, 220))
            btn_p = make_mini_btn("P", "Go to Pocket", Color(200, 230, 255))
            
            # Init Hidden/Disabled
            btn_f.setVisible(False)
            btn_p.setVisible(False)
            
            btn_panel.add(btn_f)
            btn_panel.add(btn_p)
            
            p.add(btn_panel, BorderLayout.EAST)
            
            # Add interaction
            p.addMouseListener(SlotMouseListener(slot_id, self))
            
            # Store references
            p.putClientProperty("lbl_name", lbl_name)
            p.putClientProperty("original_bg", Color(240, 240, 240))
            p.putClientProperty("btn_f", btn_f)
            p.putClientProperty("btn_p", btn_p)
            
            self.slot_widgets[slot_id] = p
            return p

        # Populate Left Bank: 26 (Top) -> 50 (Bottom)
        for i in range(26, 51):
            self.left_bank_ui.add(create_slot_widget(i))
            
        # Populate Right Bank: 25 (Top) -> 1 (Bottom)
        for i in range(25, 0, -1):
            self.right_bank_ui.add(create_slot_widget(i))
            
        visual_panel.add(self.left_bank_ui)
        visual_panel.add(JPanel()) # Spacer
        visual_panel.add(self.right_bank_ui)
        
        # ScrollPane for the visual map (in case screens are small)
        map_scroll = JScrollPane(visual_panel)
        map_scroll.getVerticalScrollBar().setUnitIncrement(16)
        
        # -- RIGHT PANEL (Actions) --
        action_panel = JPanel()
        action_panel.setLayout(BoxLayout(action_panel, BoxLayout.Y_AXIS))
        action_panel.setBorder(BorderFactory.createTitledBorder("Actions"))
        action_panel.setPreferredSize(Dimension(200, 0))
        
        def make_button(text, action, color=None):
            btn = JButton(text, actionPerformed=action)
            btn.setMaximumSize(Dimension(180, 40))
            btn.setAlignmentX(Component.CENTER_ALIGNMENT)
            if color: btn.setBackground(color)
            return btn
            
        action_panel.add(Box.createVerticalStrut(20))
        action_panel.add(make_button("Scan Feeders", lambda e: self._scan_feeders()))
        action_panel.add(Box.createVerticalStrut(10))
        
        self.btn_cal_general = make_button("General Calibration", lambda e: self._start_general_calibration())
        action_panel.add(self.btn_cal_general)
        action_panel.add(Box.createVerticalStrut(10))
        
        self.btn_cal_selected = make_button("Calibrate Selected", lambda e: self._start_selected_calibration())
        self.btn_cal_selected.setEnabled(False)
        action_panel.add(self.btn_cal_selected)
        action_panel.add(Box.createVerticalStrut(10))
        
        self.btn_edit_map = make_button("Edit Vision Mapping", lambda e: self._open_mapping_editor())
        action_panel.add(self.btn_edit_map)
        action_panel.add(Box.createVerticalStrut(10))
        
        self.btn_cal_pocket = make_button("Calibrate Pocket", lambda e: self._calibrate_selected_pocket())
        self.btn_cal_pocket.setEnabled(False)
        action_panel.add(self.btn_cal_pocket)
        action_panel.add(Box.createVerticalStrut(10))



        self.btn_vision_editor = make_button("Vision Editor (NEW)", lambda e: self._open_vision_editor(), Color(255, 200, 100))
        action_panel.add(self.btn_vision_editor)
        action_panel.add(Box.createVerticalStrut(10))
        
        self.btn_goto_feeder = make_button("Go to Feeder", lambda e: self._move_to_selected_feeder())
        self.btn_goto_feeder.setEnabled(False)
        action_panel.add(self.btn_goto_feeder)
        
        self.btn_goto_pocket = make_button("Go to Pocket", lambda e: self._move_to_selected_pocket())
        self.btn_goto_pocket.setEnabled(False)
        action_panel.add(self.btn_goto_pocket)
        
        
        action_panel.add(Box.createVerticalGlue())
        
        self.stop_btn = make_button("STOP", lambda e: self._stop_calibration(), Color(255, 100, 100))
        self.stop_btn.setEnabled(False)
        action_panel.add(self.stop_btn)
        action_panel.add(Box.createVerticalStrut(20))

        # Main Split
        split = JSplitPane(JSplitPane.HORIZONTAL_SPLIT, map_scroll, action_panel)
        split.setResizeWeight(0.8)
        split.setDividerLocation(0.8)
        
        panel.add(split, BorderLayout.CENTER)
        return panel

    def _on_slot_clicked(self, slot_id, widget):
        from java.awt import Color
        
        # Check if slot has a feeder
        if slot_id not in self.feeder_map:
            self.log("Slot " + str(slot_id) + " is empty.")
            return

        # Reset previous selection visual
        if hasattr(self, 'selected_widget') and self.selected_widget:
            orig = self.selected_widget.getClientProperty("original_bg")
            self.selected_widget.setBackground(orig)

        # Set new selection
        self.selected_widget = widget
        self.selected_slot_id = slot_id
        self.selected_feeder = self.feeder_map[slot_id]
        
        # Highlight (Cyan)
        widget.setBackground(Color(173, 216, 230))
        
        self.btn_cal_selected.setEnabled(True)
        self.btn_cal_pocket.setEnabled(True)

        self.btn_goto_feeder.setEnabled(True)
        self.btn_goto_pocket.setEnabled(True)
            
        if hasattr(self, 'btn_cal_pocket'):
            self.btn_cal_pocket.setEnabled(True)
            
        self.log("Selected Slot " + str(slot_id) + ": " + self.selected_feeder.getName())

    def _start_selected_calibration(self):
        """Start calibration for the selected feeder only"""
        import threading
        from LumenPnP.core.calibration import SlotCalibrator
        
        if not hasattr(self, 'selected_feeder') or not self.selected_feeder:
            self.log("ERROR: No feeder selected!")
            from javax.swing import JOptionPane
            JOptionPane.showMessageDialog(self.window, "Please select a green slot first.", "No Selection", JOptionPane.WARNING_MESSAGE)
            return

        feeder_name = self.selected_feeder.getName()
        self.log("Starting Calibration for: " + str(feeder_name))
        
        self.stop_btn.setEnabled(True)
        self.stop_event = threading.Event()
        
        # Create a single-item list
        target_feeders = [self.selected_feeder]
        
        def run_task():
            try:
                calibrator = SlotCalibrator(self.machine)
                calibrator.run_calibration(
                    target_feeders, 
                    log_callback=self.log,
                    progress_callback=self._update_progress,
                    stop_event=self.stop_event
                )
            except Exception as e:
                self.log("Error in calibration thread: " + str(e))
                import traceback
                traceback.print_exc()
            finally:
                self.stop_btn.setEnabled(False)
                self.log("Calibration finished.")

        t = threading.Thread(target=run_task)
        t.start()

    def _move_to_selected_feeder(self):
        """Move camera to the currently selected feeder's Slot"""
        if not hasattr(self, 'selected_feeder') or not self.selected_feeder:
            return
        self._move_to_feeder_slot(self.selected_feeder)

    def _move_to_feeder_slot(self, feeder):
        try:
            if not feeder: return
            location = feeder.getLocation()
            
            # Use Slot location if available (Base)
            if hasattr(feeder, 'getSlot') and feeder.getSlot():
                 location = feeder.getSlot().getLocation()
            
            self._move_camera_to(location)
        except Exception as e:
            self.log("Error moving to feeder: " + str(e))

    def _move_to_selected_pocket(self):
        """Move camera to the selected feeder's Pocket"""
        if not hasattr(self, 'selected_feeder') or not self.selected_feeder:
            return
        self._move_to_feeder_pocket(self.selected_feeder)

    def _move_to_feeder_pocket(self, feeder):
        """Move camera to the feeder's Pocket Location (Base + Offset)"""
        try:
            if not feeder: return
            location = feeder.getLocation() # Usually Base
            
            # Add Offset if exists
            offset = feeder.getOffset()
            if offset:
                location = location.add(offset)
            
            self._move_camera_to(location)
            
        except Exception as e:
            self.log("Error moving to pocket: " + str(e))

    def _move_camera_to(self, location):
        """Helper to move camera to a location with Safe Z"""
        try:
            head = self.machine.getDefaultHead()
            
            # 1. Safe Z Move first
            head.moveToSafeZ()
            
            # 2. Get Safe Z from Camera
            safe_z = 0.0
            camera = head.getDefaultCamera()
            if camera:
                safe_z = camera.getLocation().getZ()
            
            # 3. Move to target X/Y with Safe Z
            from org.openpnp.model import Location
            target_loc = Location(location.getUnits(), location.getX(), location.getY(), safe_z, location.getRotation())
            
            speed = self.machine.getSpeed()
            self.log("Moving to: %.2f, %.2f" % (target_loc.getX(), target_loc.getY()))
            camera.moveTo(target_loc, speed)
            
        except Exception as e:
            self.log("Move Error: " + str(e))

    def _start_general_calibration(self):
        """Start the calibration in a background thread"""
        import threading
        from LumenPnP.core.calibration import SlotCalibrator
        
        self.log("Starting General Calibration...")
        self.stop_btn.setEnabled(True)
        self.stop_event = threading.Event()
        
        def run_task():
            try:
                calibrator = SlotCalibrator(self.machine)
                
                # Get all feeders (since it's general calibration)
                # In future we can filter based on list selection
                feeders = []
                all_feeders = self.machine.getFeeders()
                for feeder in all_feeders:
                    if feeder.isEnabled():
                        feeders.append(feeder)
                
                calibrator.run_calibration(
                    feeders, 
                    log_callback=self.log,
                    progress_callback=self._update_progress,
                    stop_event=self.stop_event
                )
            except Exception as e:
                self.log("Error in calibration thread: " + str(e))
                import traceback
                traceback.print_exc()
            finally:
                self.stop_btn.setEnabled(False)
                self.log("Background thread finished.")

        t = threading.Thread(target=run_task)
        t.start()
        
    def _calibrate_selected_pocket(self):
        """Calibrate pocket for the selected feeder"""
        import threading
        from LumenPnP.core.calibration import PocketCalibrator
        
        if not hasattr(self, 'selected_feeder') or not self.selected_feeder:
            return

        feeder_name = self.selected_feeder.getName()
        self.log("Starting Pocket Calibration for " + feeder_name)
        self.stop_btn.setEnabled(True)
        
        def run_task():
            try:
                calibrator = PocketCalibrator(self.machine)
                success = calibrator.calibrate_feeder(self.selected_feeder, callback=self.log)
                
                if success:
                    self.log("Pocket calibration successful.")
                    from javax.swing import JOptionPane
                    # JOptionPane.showMessageDialog(self.window, "Pocket Calibrated Successfully!")
                else:
                    self.log("Pocket calibration failed.")
                    
            except Exception as e:
                self.log("Error: " + str(e))
                import traceback
                traceback.print_exc()
            finally:
                self.stop_btn.setEnabled(False)
        
        t = threading.Thread(target=run_task)
        t.start()



    def _open_vision_editor(self):
        from LumenPnP.gui.vision_editor import VisionEditor
        editor = VisionEditor(self.machine, self.window)

    def _stop_calibration(self):
        self.log("Stopping...")
        if hasattr(self, 'stop_event'):
            self.stop_event.set()
    
    def _update_progress(self, current, total):
        # Could update a progress bar here
        pass

    def log(self, message):
        """Add message to log panel"""
        print(message) # Always print to console
        if hasattr(self, 'log_area'):
            from javax.swing import SwingUtilities
            from java.lang import Runnable
            
            # Thread-safe GUI update
            class LogRunnable(Runnable):
                def run(r_self):
                    self.log_area.append(str(message) + "\n")
                    self.log_area.setCaretPosition(self.log_area.getDocument().getLength())
            
            SwingUtilities.invokeLater(LogRunnable())
            
        elif hasattr(self, 'log_text'):
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)

    def _open_mapping_editor(self):
        try:
            print("Opening Mapping Editor...")
            """Open the Vision Mapping Editor Dialog
            Allows linking a specific Part (OpenPnP ID) to a custom Vision Profile.
            """
            from javax.swing import JDialog, JTable, JScrollPane, JButton, JTextField, JComboBox, JLabel, JPanel, BorderFactory, BoxLayout, JOptionPane
            from javax.swing.table import DefaultTableModel
            from java.awt import BorderLayout, FlowLayout, GridLayout, Dimension, Color
            from LumenPnP.core.vision_store import VisionStore
            from org.openpnp.model import Configuration
            
            # Dialog Setup
            dialog = JDialog(self.window, "Vision Mapping Editor", True) # Modal
            dialog.setSize(800, 600)
            dialog.setLayout(BorderLayout(10, 10))
            
            # Data Store
            store = VisionStore()
            
            # -- Table --
            column_names = ["Part ID / Pattern", "Vision Profile"]
            table_model = DefaultTableModel(column_names, 0)
            table = JTable(table_model)
            scroll = JScrollPane(table)
            dialog.add(scroll, BorderLayout.CENTER)
            
            # Populate Table from existing mappings
            if store.mappings:
                for part_id, profile_name in store.mappings.items():
                    table_model.addRow([part_id, profile_name])
                
            # -- Input Panel --
            input_main = JPanel(GridLayout(3, 1, 5, 5))
            input_main.setBorder(BorderFactory.createTitledBorder("Assign Profile to Part"))
            
            # Row 1: Part Selection
            row1 = JPanel(FlowLayout(FlowLayout.LEFT))
            combo_part = JComboBox()
            combo_part.setEditable(True) 
            
            # Populate with OpenPnP Parts
            all_parts = Configuration.get().getParts()
            sorted_parts_id = [p.getId() for p in all_parts]
            sorted_parts_id.sort()
            
            for pid in sorted_parts_id:
                combo_part.addItem(pid)
                
            row1.add(JLabel("Select Part:"))
            row1.add(combo_part)
            input_main.add(row1)
            
            # Row 2: Profile Selection
            row2 = JPanel(FlowLayout(FlowLayout.LEFT))
            combo_profile = JComboBox()
            
            # Populate with Vision Profiles
            profiles = store.get_all_profiles()
            for p in profiles:
                combo_profile.addItem(p.name)
                
            row2.add(JLabel("Select Vision Profile:"))
            row2.add(combo_profile)
            input_main.add(row2)
            
            # Row 3: Buttons
            row3 = JPanel(FlowLayout(FlowLayout.CENTER))
            btn_save = JButton("Save Mapping")
            btn_del = JButton("Delete Mapping")
            btn_close = JButton("Close")
            
            row3.add(btn_save)
            row3.add(btn_del)
            row3.add(btn_close)
            input_main.add(row3)
            
            dialog.add(input_main, BorderLayout.SOUTH)
            
            # -- Helpers --
            def refresh_table():
                while table_model.getRowCount() > 0:
                    table_model.removeRow(0)
                
                if store.mappings:
                    for part_id, profile_name in store.mappings.items():
                        table_model.addRow([part_id, profile_name])

            def on_save(event):
                part_id = str(combo_part.getSelectedItem()).strip()
                profile_name = str(combo_profile.getSelectedItem())
                
                if not part_id:
                    JOptionPane.showMessageDialog(dialog, "Please select a Part.")
                    return
                if not profile_name:
                    JOptionPane.showMessageDialog(dialog, "Please select a Profile.")
                    return
                    
                store.set_mapping(part_id, profile_name)
                refresh_table()
                self.log("Mapped Part '" + part_id + "' to Profile '" + profile_name + "'")
                
            def on_delete(event):
                row = table.getSelectedRow()
                if row < 0:
                    JOptionPane.showMessageDialog(dialog, "Select a row to delete.")
                    return
                    
                part_id = table_model.getValueAt(row, 0)
                
                # Remove from store
                if part_id in store.mappings:
                    del store.mappings[part_id]
                    store.save()
                    
                refresh_table()
                self.log("Deleted mapping for: " + part_id)

            def on_table_click(event):
                row = table.getSelectedRow()
                if row >= 0:
                    part = table_model.getValueAt(row, 0)
                    prof = table_model.getValueAt(row, 1)
                    combo_part.setSelectedItem(part)
                    combo_profile.setSelectedItem(prof)

            # Listeners
            btn_save.addActionListener(on_save)
            btn_del.addActionListener(on_delete)
            btn_close.addActionListener(lambda e: dialog.dispose())
            table.getSelectionModel().addListSelectionListener(lambda e: on_table_click(None) if not e.getValueIsAdjusting() else None)
            
            dialog.setVisible(True)
        except Exception as e:
            self.log("Error opening Mapping Editor: " + str(e))
            import traceback
            traceback.print_exc()
