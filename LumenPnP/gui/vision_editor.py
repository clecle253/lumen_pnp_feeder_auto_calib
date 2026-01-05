import threading
import time
from javax.swing import JFrame, JPanel, JButton, JLabel, JList, JScrollPane, JSplitPane, JTextField, JCheckBox, JComboBox, DefaultListModel, BorderFactory, SwingConstants, ImageIcon, JOptionPane, JSlider, BoxLayout, Box, JToggleButton, ButtonGroup, SwingUtilities
from java.lang import Runnable
from java.awt import BorderLayout, Dimension, Color, Image, Font, GridLayout, FlowLayout, BasicStroke, RenderingHints
from java.awt.image import BufferedImage
from java.awt.event import ActionListener, MouseAdapter, WindowAdapter
from javax.swing.event import ListSelectionListener, ChangeListener

from LumenPnP.core.vision_store import VisionStore, VisionProfile
from LumenPnP.core.vision_core import VisionEngine
from org.openpnp.util import OpenCvUtils

class VisionEditor:
    def __init__(self, machine, parent_window=None):
        self.machine = machine
        self.store = VisionStore()
        self.current_profile = None
        self.engine = VisionEngine()
        self.running = False
        self.stop_event = threading.Event()
        self.loading_ui = False
        
        # Click-to-Move State
        self.last_raw_w = 0
        # Click-to-Move State
        self.last_raw_w = 0
        self.last_raw_h = 0
        
        # Tool Mode: 'move' or 'measure'
        self.tool_mode = 'move'
        self.measure_p1 = None # (x, y) raw
        self.measure_p2 = None # (x, y) raw
        
        # Original Camera State (for Restore)
        self.orig_cam_state = None
        self._capture_original_cam_state()

        
        self.window = JFrame("LumenPnP Custom Vision Editor")
        # Maximize Window
        self.window.setExtendedState(JFrame.MAXIMIZED_BOTH)
            
        # UI Components
        self.setup_ui()
        
        self.window.setVisible(True)
        self.window.setDefaultCloseOperation(JFrame.DO_NOTHING_ON_CLOSE)
        
        class CloseListener(WindowAdapter):
            def __init__(self, parent): self.parent = parent
            def windowClosing(self, e):
                self.parent.close()
                
        self.window.addWindowListener(CloseListener(self))
        
        # Start Live Loop (Paused by default? or Auto-start?)
        self.start_live_view()

    def _capture_original_cam_state(self):
        try:
            head = self.machine.getDefaultHead()
            cam = head.getDefaultCamera()
            prop = None
            if hasattr(cam, "getBrightness"):
                prop = cam.getBrightness()
            elif hasattr(cam, "getDevice"):
                dev = cam.getDevice()
                if hasattr(dev, "getBrightness"):
                     prop = dev.getBrightness()
            
            if prop:
                 val = 0
                 is_auto = False
                 if hasattr(prop, "getValue"): val = int(prop.getValue())
                 if hasattr(prop, "isAuto"): is_auto = prop.isAuto()
                 self.orig_cam_state = {'value': val, 'auto': is_auto}
        except:
             pass

    def setup_ui(self):

        # 1. Left Panel: Profile List
        left_panel = JPanel(BorderLayout())
        left_panel.setPreferredSize(Dimension(200, 0))
        left_panel.setBorder(BorderFactory.createTitledBorder("Profiles"))
        
        self.list_model = DefaultListModel()
        self.profile_list = JList(self.list_model)
        self.profile_list.addListSelectionListener(lambda e: self.on_profile_selected())
        
        scroll_list = JScrollPane(self.profile_list)
        left_panel.add(scroll_list, BorderLayout.CENTER)
        
        btn_panel = JPanel(GridLayout(1, 2))
        btn_add = JButton("New", actionPerformed=self.on_add_profile)
        btn_del = JButton("Delete", actionPerformed=self.on_delete_profile)
        btn_panel.add(btn_add)
        btn_panel.add(btn_del)
        left_panel.add(btn_panel, BorderLayout.SOUTH)
        
        # 2. Center Panel: Camera View
        center_panel = JPanel(BorderLayout())
        center_panel.setBorder(BorderFactory.createTitledBorder("Camera View"))
        
        self.lbl_image = JLabel("Waiting for Camera...", SwingConstants.CENTER)
        self.lbl_image.setOpaque(True)
        self.lbl_image.setBackground(Color.BLACK)
        self.lbl_image.setForeground(Color.WHITE)
        
        # Click-to-Move Listener
        class VisionMouseListener(MouseAdapter):
            def __init__(self, parent): self.parent = parent
            def mouseClicked(self, e): self.parent.on_camera_click(e)
            
        self.lbl_image.addMouseListener(VisionMouseListener(self))
        center_panel.add(self.lbl_image, BorderLayout.CENTER)
        
        # Info Overlay Label
        self.lbl_info = JLabel("Status: -")
        self.lbl_info.setForeground(Color.BLUE)
        self.lbl_info.setFont(Font("Serif", Font.BOLD, 16))
        
        # Path Label (South, small)
        self.lbl_path = JLabel("Config: ...")
        
        top_info_panel = JPanel(BorderLayout())
        top_info_panel.add(self.lbl_info, BorderLayout.CENTER)
        top_info_panel.add(self.lbl_path, BorderLayout.SOUTH)
        
        center_panel.add(top_info_panel, BorderLayout.NORTH)
        
        cam_ctrl_panel = JPanel(FlowLayout())
        self.chk_live = JCheckBox("Live View", True)
        self.chk_binary = JCheckBox("Show Threshold (Debug)", False)
        cam_ctrl_panel.add(self.chk_live)
        cam_ctrl_panel.add(self.chk_binary)
        
        # Tool Toggles
        self.btn_move = JToggleButton("Move", True)
        self.btn_measure = JToggleButton("Measure", False)
        
        grp = ButtonGroup()
        grp.add(self.btn_move)
        grp.add(self.btn_measure)
        
        def on_tool_change(e):
            if self.btn_move.isSelected():
                self.tool_mode = 'move'
                self.measure_p1 = None
                self.measure_p2 = None
                self.lbl_measure_val.setText("Dist: -")
            else:
                self.tool_mode = 'measure'
                self.measure_p1 = None
                self.measure_p2 = None
                self.lbl_measure_val.setText("Dist: -")
                
        self.btn_move.addActionListener(on_tool_change)
        self.btn_measure.addActionListener(on_tool_change)
        
        self.btn_move.addActionListener(on_tool_change)
        self.btn_measure.addActionListener(on_tool_change)
        
        cam_ctrl_panel.add(Box.createHorizontalStrut(10))
        cam_ctrl_panel.add(self.btn_move)
        cam_ctrl_panel.add(self.btn_measure)
        
        self.lbl_measure_val = JLabel("  Dist: -  ")
        self.lbl_measure_val.setFont(Font("Monospaced", Font.BOLD, 12))
        cam_ctrl_panel.add(self.lbl_measure_val)
        
        cam_ctrl_panel.add(Box.createHorizontalStrut(10))
        
        btn_capture = JButton("Force Capture", actionPerformed=lambda e: self.capture_frame())
        cam_ctrl_panel.add(btn_capture)
        center_panel.add(cam_ctrl_panel, BorderLayout.SOUTH)
        
        # 3. Right Panel: Settings
        right_panel = JPanel()
        # Use GridLayout for the form: 0 rows (auto), 2 columns (Label, Field)
        # We need a wrapper panel to prevent it from stretching vertically if we use Border/Box context, 
        # but inside the split pane, a simple JPanel with standard layout might be tricky.
        # Let's use a nice vertical Box layout but with a specialized form panel inside.
        
        right_panel.setLayout(BorderLayout())
        right_panel.setPreferredSize(Dimension(300, 0))
        right_panel.setBorder(BorderFactory.createTitledBorder("Settings"))

        # Form Container
        form_panel = JPanel(GridLayout(0, 2, 5, 10)) # 2 cols, hgap 5, vgap 10
        form_panel.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10))
        
        # Name
        form_panel.add(JLabel("Name:"))
        self.txt_name = JTextField()
        form_panel.add(self.txt_name)
        
        # Method
        form_panel.add(JLabel("Method:"))
        self.cmb_method = JComboBox(VisionProfile.METHODS)
        self.cmb_method.addActionListener(lambda e: self.save_ui_to_profile())
        form_panel.add(self.cmb_method)

        # Brightness / Contrast
        form_panel.add(JLabel("Brightness:"))
        self.sld_bright = JSlider(-100, 100, 0)
        self.sld_bright.addChangeListener(lambda e: self.save_ui_to_profile())
        form_panel.add(self.sld_bright)
        
        form_panel.add(JLabel("Contrast:"))
        self.sld_contrast = JSlider(-100, 100, 0)
        self.sld_contrast.addChangeListener(lambda e: self.save_ui_to_profile())
        form_panel.add(self.sld_contrast)
        
        # Hardware Brightness
        form_panel.add(JLabel("Camera Brightness (-1=Def):"))
        self.sld_cam_bright = JSlider(-100, 100, -1)
        # We apply immediately for visual feedback
        self.sld_cam_bright.addChangeListener(lambda e: self.on_cam_brightness_change())
        form_panel.add(self.sld_cam_bright)
        
        # Masking
        form_panel.add(JLabel("Mask Type:"))
        self.cmb_mask = JComboBox(["NONE", "RECT", "CIRCLE"])
        self.cmb_mask.addActionListener(lambda e: self.save_ui_to_profile())
        form_panel.add(self.cmb_mask)
        
        form_panel.add(JLabel("Mask W/Dia:"))
        self.txt_mask_w = JTextField("600")
        form_panel.add(self.txt_mask_w)
        
        form_panel.add(JLabel("Mask Height:"))
        self.txt_mask_h = JTextField("600")
        form_panel.add(self.txt_mask_h) # Ignored if Circle

        # Threshold Min
        form_panel.add(JLabel("Threshold Min:"))
        self.sld_min = JSlider(0, 255, 100)
        self.sld_min.addChangeListener(lambda e: self.save_ui_to_profile())
        form_panel.add(self.sld_min)
        
        # Threshold Max
        form_panel.add(JLabel("Threshold Max:"))
        self.sld_max = JSlider(0, 255, 255)
        self.sld_max.addChangeListener(lambda e: self.save_ui_to_profile())
        form_panel.add(self.sld_max)
        
        # Invert
        form_panel.add(JLabel("Invert Colors:"))
        self.chk_invert = JCheckBox("", actionPerformed=lambda e: self.save_ui_to_profile())
        form_panel.add(self.chk_invert)
        
        # Dimensions
        form_panel.add(JLabel("Min Area:"))
        self.txt_min_area = JTextField("500")
        form_panel.add(self.txt_min_area)
        
        form_panel.add(JLabel("Max Area:"))
        self.txt_max_area = JTextField("50000")
        form_panel.add(self.txt_max_area)
        
        form_panel.add(JLabel("Min Width:"))
        self.txt_min_w = JTextField("10")
        form_panel.add(self.txt_min_w)
        
        form_panel.add(JLabel("Max Width:"))
        self.txt_max_w = JTextField("500")
        form_panel.add(self.txt_max_w)
        
        form_panel.add(JLabel("Min Height:"))
        self.txt_min_h = JTextField("10")
        form_panel.add(self.txt_min_h)
        
        form_panel.add(JLabel("Max Height:"))
        self.txt_max_h = JTextField("500")
        form_panel.add(self.txt_max_h)
        
        # Apply Button (South of Right Panel)
        btn_apply = JButton("Apply & Save", actionPerformed=lambda e: self.save_ui_to_profile())
        
        # Add to Right Panel
        # We put form_panel in a wrapper to keep it at the top
        top_wrapper = JPanel(BorderLayout())
        top_wrapper.add(form_panel, BorderLayout.NORTH)
        
        right_panel.add(top_wrapper, BorderLayout.CENTER)
        right_panel.add(btn_apply, BorderLayout.SOUTH)

        # Split Panes
        split_right = JSplitPane(JSplitPane.HORIZONTAL_SPLIT, center_panel, right_panel)
        split_right.setResizeWeight(0.7)
        
        split_main = JSplitPane(JSplitPane.HORIZONTAL_SPLIT, left_panel, split_right)
        self.window.add(split_main, BorderLayout.CENTER)
        
        # Listeners for TextFields to auto-update?
        # Maybe just use the "Apply" button for the text fields to avoid lag
        
        # Auto-select first
        self.refresh_list(select_first=True)
        self.lbl_path.setText("Config: " + str(self.store.config_file))

    def refresh_list(self, select_first=False):
        self.list_model.clear()
        profiles = self.store.get_all_profiles()
        first = None
        for i, p in enumerate(profiles):
            self.list_model.addElement(p.name)
            if i==0: first = p.name
            
        if select_first and first:
            self.profile_list.setSelectedValue(first, True)
        
        # precise selection if possible?

    def on_profile_selected(self):
        name = self.profile_list.getSelectedValue()
        if not name: return
        if not name: return
        self.current_profile = self.store.get_profile(name)
        # FORCE UI Update
        self.profile_to_ui(self.current_profile)
        self.window.revalidate()
        self.window.repaint()

    def profile_to_ui(self, p):
        if not p: return
        self.loading_ui = True
        try:
            self.txt_name.setText(p.name)
            self.cmb_method.setSelectedItem(p.method)
            
            self.sld_bright.setValue(int(getattr(p, 'brightness', 0)))
            self.sld_contrast.setValue(int(getattr(p, 'contrast', 0)))
            
            # Hardware
            cam_br = int(getattr(p, 'camera_brightness', -1))
            self.sld_cam_bright.setValue(cam_br)
            
            self.cmb_mask.setSelectedItem(getattr(p, 'mask_type', "NONE"))
            self.txt_mask_w.setText(str(getattr(p, 'mask_width', 600)))
            self.txt_mask_h.setText(str(getattr(p, 'mask_height', 600)))
            
            self.sld_min.setValue(int(p.threshold_min))
            self.sld_max.setValue(int(p.threshold_max))
            self.chk_invert.setSelected(p.invert)
            self.txt_min_area.setText(str(p.min_area))
            self.txt_max_area.setText(str(p.max_area))
            self.txt_min_w.setText(str(p.min_width))
            self.txt_max_w.setText(str(p.max_width))
            self.txt_min_h.setText(str(p.min_height))
            self.txt_max_h.setText(str(p.max_height))
        finally:
            self.loading_ui = False

    def save_ui_to_profile(self):
        if self.loading_ui: return
        if not self.current_profile: return
        try:
            p = self.current_profile
            # Name change? tricky. handle later.
            p.method = self.cmb_method.getSelectedItem()
            
            p.brightness = self.sld_bright.getValue()
            p.contrast = self.sld_contrast.getValue()
            
            p.camera_brightness = self.sld_cam_bright.getValue()
            
            p.mask_type = self.cmb_mask.getSelectedItem()
            p.mask_width = int(self.txt_mask_w.getText())
            p.mask_height = int(self.txt_mask_h.getText())
            
            p.threshold_min = self.sld_min.getValue()
            p.threshold_max = self.sld_max.getValue()
            p.invert = self.chk_invert.isSelected()
            
            p.min_area = int(self.txt_min_area.getText())
            p.max_area = int(self.txt_max_area.getText())
            p.min_width = int(self.txt_min_w.getText())
            p.max_width = int(self.txt_max_w.getText())
            p.min_height = int(self.txt_min_h.getText())
            p.max_height = int(self.txt_max_h.getText())
            
            self.store.save_profile(p)
            self.lbl_info.setText("Settings Saved for: " + p.name)
            # Reload to ensure consistency?
            self.current_profile = self.store.get_profile(p.name)
        except Exception as e:
            self.lbl_info.setText("Error saving profile: " + str(e))

    def on_cam_brightness_change(self):
        # Update profile and set camera prop
        # if not self.chk_live.isSelected(): return 
        
        val = self.sld_cam_bright.getValue()
        if self.current_profile:
             self.current_profile.camera_brightness = val
        
        # Apply to Camera
        try:
            head = self.machine.getDefaultHead()
            cam = head.getDefaultCamera()
            
            # Helper to set property
            def set_prop(prop, value):
                # Try to disable auto if exists
                if hasattr(prop, "setAuto"):
                    try: prop.setAuto(False)
                    except: pass
                # Set Value
                if hasattr(prop, "setValue"):
                    prop.setValue(int(value))
            
            if hasattr(cam, "getBrightness"):
                # Use the PropertyHolder
                set_prop(cam.getBrightness(), val)
            elif hasattr(cam, "getDevice"):
                # Fallback to Device if method missing on Cam wrapper (rare but possible)
                dev = cam.getDevice()
                if hasattr(dev, "getBrightness"):
                     set_prop(dev.getBrightness(), val)
                     
        except Exception as e:
             self.lbl_image.setText("Cam Control Error: " + str(e))
             
    def on_add_profile(self, e):
        name = JOptionPane.showInputDialog(self.window, "Enter Profile Name:")
        if name:
            new_p = VisionProfile(name)
            self.store.save_profile(new_p)
            self.refresh_list()
            self.profile_list.setSelectedValue(name, True)

    def on_delete_profile(self, e):
        name = self.profile_list.getSelectedValue()
        if name:
            self.store.delete_profile(name)
            self.refresh_list()

    def start_live_view(self):
        self.running = True
        t = threading.Thread(target=self.live_loop)
        t.start()

    def live_loop(self):
        # DEBUG: Check if thread starts
        print("DEBUG: Thread Started")
        def update_start(): self.lbl_image.setText("DEBUG: Thread Started")
        try: SwingUtilities.invokeLater(update_start)
        except: pass
        
        while self.running and self.window.isVisible():
            try:
                if self.chk_live.isSelected():
                    # DEBUG: capturing
                    # def update_cap(): self.lbl_image.setText("DEBUG: Capturing...")
                    # SwingUtilities.invokeLater(update_cap)
                    self.capture_frame()
            except Exception as e:
                print("Live Loop Error: " + str(e))
                def update_err(): self.lbl_image.setText("Loop Error: " + str(e))
                try: SwingUtilities.invokeLater(update_err)
                except: pass
            time.sleep(0.2) # 5 FPS

    def capture_frame(self):
        try:
            head = self.machine.getDefaultHead()
            if not head:
                 self.lbl_image.setText("No Head Found")
                 return
                 
            cam = head.getDefaultCamera()
            if not cam:
                 self.lbl_image.setText("No Camera Found on Head")
                 return
            
            # Capture
            try:
                img = cam.capture()
            except Exception as e:
                self.lbl_image.setText("Capture Exception: " + str(e))
                return
                
            if not img:
                 self.lbl_image.setText("Camera Capture Failed (None)")
                 return

            # Process if profile selected
            if self.current_profile:
                try:
                    # engine returns found, center, res_img (color), stats, res_img_bin (annotated)
                    found, center, res_img, stats, res_img_bin = self.engine.process_image(img, self.current_profile)
                    
                    if self.chk_binary.isSelected():
                        final_img = res_img_bin
                    else:
                        final_img = res_img
                    
                    if found and center:
                         self.lbl_info.setText("FOUND: X=%.2f Y=%.2f Area=%d" % (center.x, center.y, stats.get('area', 0)))
                    else:
                         self.lbl_info.setText("Not Found")
                except Exception as e:
                    self.lbl_image.setText("Vision Process Error: " + str(e))
                    return
            else:
                final_img = img
            
            if not final_img:
                 self.lbl_image.setText("Processing Failed (None)")
                 return

            # Update State
            self.last_raw_w = final_img.getWidth()
            self.last_raw_h = final_img.getHeight()
            
            # Display
            width = self.lbl_image.getWidth()
            height = self.lbl_image.getHeight()
            
            if width > 0 and height > 0:
                 try:
                     # 1. Scale Image
                     scaled = final_img.getScaledInstance(width, height, Image.SCALE_FAST)
                     
                     # 2. Draw to BufferedImage
                     bimg = BufferedImage(width, height, BufferedImage.TYPE_INT_RGB)
                     g = bimg.createGraphics()
                     
                     try:
                         g.drawImage(scaled, 0, 0, None)
                         
                         # 3. Draw Overlay
                         if self.tool_mode == 'measure' and (self.measure_p1 or self.measure_p2):
                            g.setColor(Color.RED)
                            g.setStroke(BasicStroke(2))
                            
                            iw_raw = self.last_raw_w
                            ih_raw = self.last_raw_h
                            if iw_raw > 0 and ih_raw > 0:
                                sx = float(width) / float(iw_raw)
                                sy = float(height) / float(ih_raw)
                                
                                def to_screen(p):
                                    return (int(p[0] * sx), int(p[1] * sy))
                                
                                def draw_cross(p, color):
                                     s = to_screen(p)
                                     g.setColor(color)
                                     sz = 10
                                     g.drawLine(s[0]-sz, s[1], s[0]+sz, s[1])
                                     g.drawLine(s[0], s[1]-sz, s[0], s[1]+sz)
                                     return s
                                
                                s1 = None
                                if self.measure_p1:
                                     s1 = draw_cross(self.measure_p1, Color.RED)
                                     
                                if self.measure_p2:
                                     s2 = draw_cross(self.measure_p2, Color.GREEN)
                                     
                                     g.setColor(Color.YELLOW)
                                     g.drawLine(s1[0], s1[1], s2[0], s2[1])
                                     
                                     import math
                                     dx = self.measure_p1[0] - self.measure_p2[0]
                                     dy = self.measure_p1[1] - self.measure_p2[1]
                                     dist_px = math.sqrt(dx*dx + dy*dy)
                                     
                                     g.setColor(Color.WHITE)
                                     g.setFont(Font("SansSerif", Font.BOLD, 14))
                                     g.drawString("%.2f px" % dist_px, s2[0]+15, s2[1])
                                     self.lbl_measure_val.setText("Dist: %.2f px" % dist_px)
                                else:
                                     self.lbl_measure_val.setText("Dist: -")
                            elif self.tool_mode != 'measure':
                                 self.lbl_measure_val.setText("Dist: -")
                     finally:
                         g.dispose()
                     
                     icon = ImageIcon(bimg)
                 except Exception as e:
                     self.lbl_image.setText("Draw Error: " + str(e))
                     return
            else:
                 icon = ImageIcon(final_img)
                 
            self.lbl_image.setIcon(icon)
            self.lbl_image.setText("")
            
        except Exception as e:
            self.lbl_image.setText("Camera Error: " + str(e))
            print("Capture Frame Error: " + str(e))
            
    def on_camera_click(self, e):
        """Handle click on camera feed"""
        if self.last_raw_w == 0 or self.last_raw_h == 0: return

        # 1. Get Click Coordinates
        click_x = e.getX()
        click_y = e.getY()
        
        # 2. Get Label Dimensions
        lbl_w = self.lbl_image.getWidth()
        lbl_h = self.lbl_image.getHeight()
        
        if lbl_w == 0 or lbl_h == 0: return
        
        # 3. Calculate Scale/Offsets
        # Used 'ImageIcon' centers the image in Label?
        # Default JLabel is center aligned if text, but icon?
        # We need to be careful. The ImageIcon is set on the Label.
        # Usually centered by default if we used standard JLabel ctor or setHorizontalAlignment.
        # Check defaults: initialized SwingConstants.CENTER.
        
        icon = self.lbl_image.getIcon()
        if not icon: return
        
        icon_w = icon.getIconWidth()
        icon_h = icon.getIconHeight()
        
        off_x = (lbl_w - icon_w) / 2
        off_y = (lbl_h - icon_h) / 2
        
        # Relative to Image
        rel_x = click_x - off_x
        rel_y = click_y - off_y
        
        if rel_x < 0 or rel_x >= icon_w or rel_y < 0 or rel_y >= icon_h:
            return # Clicked outside
            
        # Un-Scale to Raw
        scale_x = float(self.last_raw_w) / float(icon_w)
        scale_y = float(self.last_raw_h) / float(icon_h)
        
        raw_x = rel_x * scale_x
        raw_y = rel_y * scale_y
        
        if self.tool_mode == 'measure':
             if self.measure_p1 and self.measure_p2:
                 # Reset
                 self.measure_p1 = (raw_x, raw_y)
                 self.measure_p2 = None
             elif not self.measure_p1:
                 self.measure_p1 = (raw_x, raw_y)
             else:
                 self.measure_p2 = (raw_x, raw_y)
             
             # Force repaint (capture frame will see new points)
             if not self.chk_live.isSelected():
                 self.capture_frame()
                 
             return

        # ---- MOVE MODE ----
        
        # 3. Calculate Center of Image (Raw)
        center_raw_x = self.last_raw_w / 2.0
        center_raw_y = self.last_raw_h / 2.0
        
        delta_raw_x = raw_x - center_raw_x
        delta_raw_y = raw_y - center_raw_y
        
        # 6. Convert to Millimeters
        try:
            head = self.machine.getDefaultHead()
            cam = head.getDefaultCamera()
            upp = cam.getUnitsPerPixel()
            
            # X Move
            move_x = delta_raw_x * upp.getX()
            
            # Y Move: Top-Left Image -> Bottom-Left Machine
            # Down on image (+Y) = Down on machine (-Y)
            move_y = delta_raw_y * upp.getY() * -1.0 # Assuming standard OpenPnP setup
            
            # Execute Move
            from org.openpnp.model import Location
            loc = cam.getLocation()
            new_loc = Location(loc.getUnits(), loc.getX() + move_x, loc.getY() + move_y, loc.getZ(), loc.getRotation())
            
            def move_task():
                try:
                    speed = self.machine.getSpeed()
                    cam.moveTo(new_loc, speed)
                    self.lbl_info.setText("Moved: %.2f, %.2f" % (move_x, move_y))
                except Exception as ex:
                    self.lbl_info.setText("Move Error: " + str(ex))
            
            threading.Thread(target=move_task).start()
            
        except Exception as ex:
            self.lbl_info.setText("Click Error: " + str(ex))

    def close(self):
        self.running = False
        
        # Restore Camera State
        if self.orig_cam_state:
            try:
                head = self.machine.getDefaultHead()
                cam = head.getDefaultCamera()
                
                val = int(self.orig_cam_state.get('value', 0))
                is_auto = self.orig_cam_state.get('auto', False)
                
                def set_prop(prop):
                    if hasattr(prop, "setAuto"):
                        try: prop.setAuto(is_auto)
                        except: pass
                    
                    if not is_auto and hasattr(prop, "setValue"):
                        prop.setValue(val)
                        
                if hasattr(cam, "getBrightness"):
                    set_prop(cam.getBrightness())
                elif hasattr(cam, "getDevice"):
                     dev = cam.getDevice()
                     if hasattr(dev, "getBrightness"):
                         set_prop(dev.getBrightness())
            except:
                pass
            
            # Prevent double restore
            self.orig_cam_state = None
                
        self.window.dispose()
