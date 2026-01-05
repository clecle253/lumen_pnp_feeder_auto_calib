from org.opencv.core import Mat, Scalar, Point, Size, MatOfPoint, Rect
from org.opencv.imgproc import Imgproc
from org.opencv.imgcodecs import Imgcodecs
from org.openpnp.util import OpenCvUtils
from java.awt.image import BufferedImage
import math

class VisionEngine:
    def __init__(self):
        pass

    def process_image(self, buffered_image, profile):
        """
        Processes a BufferedImage using the given VisionProfile.
        Returns:
            found (bool): True if target found
            center (Point): Center of the target (in pixel coords) or None
            annotated_image (BufferedImage): Image with drawing for debug
            stats (dict): Info about the found target (area, w, h)
        """
        # Convert BufferedImage to Mat
        mat_src = OpenCvUtils.toMat(buffered_image)
        
        # Determine ROI (maybe center crop? for now execute on full image)
        
        # 1. Pre-Processing (Brightness / Contrast)
        mat_src_processed = Mat()
        if hasattr(profile, 'brightness') or hasattr(profile, 'contrast'):
            # alpha = 1.0 + (contrast / 100.0)
            # beta = brightness
            alpha = 1.0 + (getattr(profile, 'contrast', 0) / 100.0)
            beta = float(getattr(profile, 'brightness', 0))
            mat_src.convertTo(mat_src_processed, -1, alpha, beta)
        else:
            mat_src.copyTo(mat_src_processed)
            
        # 1.5 Masking
        # Apply mask to mat_src_processed
        mask_type = getattr(profile, 'mask_type', "NONE")
        if mask_type != "NONE":
            mask = Mat.zeros(mat_src.size(), mat_src.type())
            # White ROI
            cx, cy = int(mat_src.width()/2), int(mat_src.height()/2)
            mw = int(getattr(profile, 'mask_width', 600))
            mh = int(getattr(profile, 'mask_height', 600))
            
            color_white = Scalar(255, 255, 255)
            
            if mask_type == "RECT":
                x = cx - mw/2
                y = cy - mh/2
                Imgproc.rectangle(mask, Rect(int(x), int(y), int(mw), int(mh)), color_white, -1)
            elif mask_type == "CIRCLE":
                radius = int(mw/2)
                Imgproc.circle(mask, Point(cx, cy), radius, color_white, -1)
                
            # Combine src with mask
            mat_masked = Mat()
            from org.opencv.core import Core
            Core.bitwise_and(mat_src_processed, mask, mat_masked)
            mat_src_processed = mat_masked
        
        # 2. Convert to Gray
        mat_gray = Mat()
        Imgproc.cvtColor(mat_src_processed, mat_gray, Imgproc.COLOR_BGR2GRAY)
        
        # 2. Blur (Optional)
        if profile.blur_size > 0:
            k = profile.blur_size | 1 # Ensure odd
            Imgproc.GaussianBlur(mat_gray, mat_gray, Size(k, k), 0)
            
        # 3. Threshold
        mat_bin = Mat()
        type_thresh = Imgproc.THRESH_BINARY
        if profile.invert:
            type_thresh = Imgproc.THRESH_BINARY_INV
            
        Imgproc.threshold(mat_gray, mat_bin, float(profile.threshold_min), float(profile.threshold_max), type_thresh)
        
        # 4. Find Contours
        contours = [] # Java List of MatOfPoint
        hierarchy = Mat()
        # openpnp uses a wrapped list, we might need a distinct ArrayList
        from java.util import ArrayList
        contours = ArrayList()
        
        Imgproc.findContours(mat_bin, contours, hierarchy, Imgproc.RETR_EXTERNAL, Imgproc.CHAIN_APPROX_SIMPLE)
        
        best_candidate = None
        best_score = -1
        img_center_x = mat_src.width() / 2
        img_center_y = mat_src.height() / 2
        
        stat_found = {}
        
        # Prepare annotation mat (color)
        mat_draw = Mat()
        if mat_src.channels() == 1:
            Imgproc.cvtColor(mat_src, mat_draw, Imgproc.COLOR_GRAY2BGR)
        else:
            mat_src.copyTo(mat_draw)
            
        # Prepare Debug Binary Mat (Colorized for annotation)
        mat_draw_bin = Mat()
        Imgproc.cvtColor(mat_bin, mat_draw_bin, Imgproc.COLOR_GRAY2BGR)
            
        ColorGreen = Scalar(0, 255, 0)
        ColorRed = Scalar(0, 0, 255)
        ColorBlue = Scalar(255, 0, 0)

                
        for i, contour in enumerate(contours):
            # Calculate metrics
            area = Imgproc.contourArea(contour)
            rect = Imgproc.boundingRect(contour)
            x, y, w, h = rect.x, rect.y, rect.width, rect.height
            cx = x + w/2
            cy = y + h/2
            
            # Check filters
            valid = True
            
            if area < profile.min_area or area > profile.max_area:
                valid = False
            
            if valid and profile.method == "RECT":
                if w < profile.min_width or w > profile.max_width: valid = False
                if h < profile.min_height or h > profile.max_height: valid = False
            
            elif valid and profile.method == "CIRCLE":
                angle_ratio = w / h if h != 0 else 0
                diameter = w
                if diameter < profile.min_diameter or diameter > profile.max_diameter: valid = False
            
            if not valid:
                 # Draw rejected (Red)
                 Imgproc.rectangle(mat_draw, rect, ColorRed, 1)
                 Imgproc.rectangle(mat_draw_bin, rect, ColorRed, 1)
                 continue

            # Check distance from center (we usually want the center-most one for pockets)
            dist = math.sqrt((cx - img_center_x)**2 + (cy - img_center_y)**2)
            
            # Scoring: Prioritize Center closeness mostly
            # Score = 1000 - dist
            score = 10000 - dist
            
            if score > best_score:
                best_score = score
                best_candidate = rect
                stat_found = {
                    "x": x, "y": y, "w": w, "h": h, "area": area,
                    "cx": cx, "cy": cy
                }
                
        # Draw Best (Green)
        if best_candidate:
            Imgproc.rectangle(mat_draw, best_candidate, ColorGreen, 2)
            Imgproc.rectangle(mat_draw_bin, best_candidate, ColorGreen, 2)
            # Draw Crosshair
            cx, cy = int(stat_found["cx"]), int(stat_found["cy"])
            Imgproc.line(mat_draw, Point(cx-10, cy), Point(cx+10, cy), ColorGreen, 2)
            Imgproc.line(mat_draw, Point(cx, cy-10), Point(cx, cy+10), ColorGreen, 2)
            
            Imgproc.line(mat_draw_bin, Point(cx-10, cy), Point(cx+10, cy), ColorGreen, 2)
            Imgproc.line(mat_draw_bin, Point(cx, cy-10), Point(cx, cy+10), ColorGreen, 2)
            
            final_center = Point(cx, cy)
            found = True
        else:
            final_center = None
            found = False
            
        # Draw Threshold overlay? (Maybe faint blue for debugging B&W?)
        # For now just return the detection drawing
        
        # Convert result back to BufferedImage
        res_image = OpenCvUtils.toBufferedImage(mat_draw)
        res_image_bin = OpenCvUtils.toBufferedImage(mat_draw_bin)
        
        # Cleanup
        # mat_src.release() # Be careful with releasing java-managed mats? OpenPnP Utils usually handles it?
        
        return found, final_center, res_image, stat_found, res_image_bin # Return annotated bin
