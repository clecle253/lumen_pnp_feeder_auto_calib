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
        self.window.geometry("900x700")
        
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
            # We must account for the fact that the image might be centered or scaled?
            # Current impl: JLabel contains Icon 1:1. X/Y are relative to Label (which roughly matches Icon if tight)
            
            # Check if click is within image bounds
            icon = self.map_label.getIcon()
            if x > icon.getIconWidth() or y > icon.getIconHeight():
                return
                
            mm_x, mm_y = self.navigator.pixel_to_machine(x, y)
            
            self.log("Map Click: " + str(x) + "," + str(y) + " -> Move To: " + str(round(mm_x,1)) + ", " + str(round(mm_y,1)))
            
            # Move Machine
            from org.openpnp.model import Location
            head = self.machine.getDefaultHead()
            # Get current Z from head? Safe Z?
            current_loc = head.getLocation()
            
            # Create target location (Keep current Z and Rotation)
            target = Location(current_loc.units, mm_x, mm_y, current_loc.z, current_loc.rotation)
            
            # Execute move in thread to not block UI
            def move_task():
                try:
                    head.moveToSafe(target)
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
        # Disable buttons? TODO
        
        def run_scan():
            try:
                if not hasattr(self, 'navigator'):
                    self.navigator = MapNavigator(self.machine)
                    
                stop_evt = threading.Event() # Todo: connect to stop button
                self.navigator.scan_bed(self.log, self._update_progress, stop_evt)
                
                # Reload map after scan
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
                 
                 # Optional: Scale if too huge? 
                 # For now, full RES is better for accuracy. ScrollPane handles scroll.
                 
                 self.map_label.setIcon(icon)
                 self.map_label.setText("") # Remove text
                 self.log("Map loaded.")
             else:
                 self.log("No saved map found.")
                 self.map_label.setText("No Map Found. Click 'Full Machine Scan'.")
                 self.map_label.setIcon(None)
                 
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
            widget.setBackground(Color(200, 255, 200)) # Light Green for active
            
            # Construct label text: "Name (Part)"
            # Paranoid string conversion
            f_name = feeder.getName()
            display_text = str(f_name) if f_name else "Unnamed"
            
            if part_name:
                display_text += " (" + str(part_name) + ")"
                
            lbl_name.setText(" " + display_text)
            self.feeder_map[slot_id] = feeder
        else:
            widget.setBackground(widget.getClientProperty("original_bg"))
            lbl_name.setText(" Empty")
    
    def _scan_feeders(self):
        """Scan feeders for issues before calibration"""
        self.log("Scanning feeders (Logic v2)...")
        try:
            feeders = self.machine.getFeeders()
            found_count = 0
            
            # Reset all slots first
            for i in range(1, 51):
                self._update_slot_ui(i, None)
            
            import re
            
            for feeder in feeders:
                if not feeder.isEnabled():
                    continue
                    
                name = str(feeder.getName())
                # Try to extract slot number from name (e.g. "Slot 1", "Feeder 12", "1")
                # Look for the last integer in the name which is usually the slot ID
                # This could be improved if rigid naming convention is used
                match = re.search(r"(\d+)", name)
                
                if match:
                    # In case of multiple numbers, user might prefer the last one, or first?
                    # Let's assume the number matches a slot ID 1-50
                    potential_id = int(match.group(1))
                    
                    if 1 <= potential_id <= 50:
                        # Get Assigned Part
                        part_name = ""
                        part = feeder.getPart()
                        if part:
                            p_name = part.getName()
                            part_name = str(p_name) if p_name is not None else "Unnamed Part"
                        
                        self._update_slot_ui(potential_id, feeder, part_name)
                        found_count += 1
                        # self.log("DEBUG: Mapped " + name + " to Slot " + str(potential_id))
            
            self.log("Scan complete. Found " + str(found_count) + " active feeders aligned with slots.")
            
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
        self.window.setSize(1000, 700)
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
        from java.awt import BorderLayout, GridLayout, Dimension, Color, Component, Font
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
            p.setBackground(Color(240, 240, 240)) # Default Gray
            p.setPreferredSize(Dimension(150, 20))
            
            lbl_id = JLabel(" " + str(slot_id) + " ", SwingConstants.CENTER)
            lbl_id.setPreferredSize(Dimension(30, 20))
            lbl_id.setBorder(BorderFactory.createMatteBorder(0, 0, 0, 1, Color.LIGHT_GRAY))
            
            lbl_name = JLabel(" Empty", SwingConstants.LEFT)
            lbl_name.setFont(lbl_name.getFont().deriveFont(10.0))
            
            p.add(lbl_id, BorderLayout.WEST)
            p.add(lbl_name, BorderLayout.CENTER)
            
            # Add interaction
            p.addMouseListener(SlotMouseListener(slot_id, self))
            
            # Store references
            p.putClientProperty("lbl_name", lbl_name)
            p.putClientProperty("original_bg", Color(240, 240, 240))
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
        
        self.btn_cal_selected = make_button("Calibrate Selected", lambda e: self.log("Selected Calib - Todo"))
        self.btn_cal_selected.setEnabled(False)
        action_panel.add(self.btn_cal_selected)
        
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
        self.log("Selected Slot " + str(slot_id) + ": " + self.selected_feeder.getName())

    def _scan_feeders(self):
        """Scan feeders and populate the visual map"""
        from java.awt import Color
        from LumenPnP.core.calibration import SlotCalibrator
        import re
        
        self.log("Scanning feeders configuration...")
        self.feeder_map = {} # Reset map
        
        # Reset visual state
        for slot_id, widget in self.slot_widgets.items():
            widget.setBackground(Color(240, 240, 240)) # Gray
            widget.putClientProperty("original_bg", Color(240, 240, 240))
            lbl = widget.getClientProperty("lbl_name")
            lbl.setText(" Empty")
            lbl.setForeground(Color.GRAY)
        
        # Helper method from calibration core logic to parse slot ID
        # We duplicate it slightly here or instantiate the class purely for the helper
        # Simple regex for now is safer/faster than importing the whole class instance logic
        def get_slot_id(name):
             match = re.search(r'Slot:\s*(\d+)', name, re.IGNORECASE)
             if match: return int(match.group(1))
             if name.isdigit(): return int(name)
             m2 = re.search(r'\((\d+)\)', name)
             if m2: return int(m2.group(1))
             return None

        found_count = 0
        feeders = self.machine.getFeeders()
        for feeder in feeders:
            if not feeder.isEnabled():
                continue
                
            name = str(feeder.getName())
            slot_id = get_slot_id(name)
            
            if slot_id and slot_id in self.slot_widgets:
                # Update map
                self.feeder_map[slot_id] = feeder
                found_count += 1
                
                # Update UI
                widget = self.slot_widgets[slot_id]
                widget.setBackground(Color.WHITE)
                widget.putClientProperty("original_bg", Color.WHITE)
                
                lbl = widget.getClientProperty("lbl_name")
                
                # Try to get Part Name
                part_name = "Unknown"
                if feeder.getPart():
                    part_name = feeder.getPart().getName()
                
                lbl.setText(" " + part_name)
                lbl.setForeground(Color.BLACK)
        
        self.log("Scan complete. Mapped " + str(found_count) + " feeders to slots.")

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
