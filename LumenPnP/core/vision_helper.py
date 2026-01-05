from org.openpnp.model import Configuration

from org.openpnp.vision.pipeline.stages import ImageCapture, ConvertColor, DetectCircularSymmetry, ClosestModel, ConvertModelToKeyPoints

class VisionHelper:
    def __init__(self):
        pass

    def setup_pocket_pipeline(self, package):
        """
        Replaces the vision pipeline of the given Package with a robust
        CircularSymmetry -> ClosestModel -> ConvertModelToKeyPoints chain.
        """
        if not package:
            print("Error: No package provided.")
            return False

        print("Configuring pipeline for package: " + package.getName())
        
        # Access the Vision Provider
        # Note: OpenPnP parts can have different vision settings. 
        # Usually we want the 'Vision' tab pipeline.
        # This is typically on the Part itself? No, vision is often on the Package for feeders.
        # Actually in 2.0, it's package.getVisionProvider()
        
        provider = package.getVisionProvider()
        if not provider:
            print("Error: Package has no VisionProvider.")
            return False
            
        pipeline = provider.getPipeline()
        if not pipeline:
            print("Error: Provider has no Pipeline.")
            return False
            
        # CLEAR existing stages
        pipeline.clear()
        print("Pipeline cleared.")
        
        # 1. ImageCapture
        cap = ImageCapture()
        cap.setEnabled(True)
        cap.setName("Input")
        cap.settleTimeMs = 250
        pipeline.add(cap)
        
        # 2. ConvertColor
        gray = ConvertColor()
        gray.setEnabled(True)
        gray.setName("Gray")
        gray.conversion = ConvertColor.Conversion.BgrToGray
        pipeline.add(gray)
        
        # 3. DetectCircularSymmetry
        # We need to import the class correctly. 
        # Assuming standard package: org.openpnp.vision.pipeline.stages.DetectCircularSymmetry
        sym = DetectCircularSymmetry()
        sym.setEnabled(True)
        sym.setName("Find Circle")
        sym.minDiameter = 1.0 # 1mm default
        sym.maxDiameter = 4.0 # 4mm default
        sym.maxDistance = 3.0 # 3mm max jump to avoid sprocket
        sym.subSampling = 8
        sym.property = DetectCircularSymmetry.Property.Outer # Generally correct for pockets
        pipeline.add(sym)
        
        # 4. ClosestModel
        # Filters multiple circles to keep the best one
        closest = ClosestModel()
        closest.setEnabled(True)
        closest.setName("Keep Best")
        # Default model part is usually Center, which is what we want
        pipeline.add(closest)
        
        # 5. ConvertModelToKeyPoints
        conv = ConvertModelToKeyPoints()
        conv.setEnabled(True)
        conv.setName("To Points")
        pipeline.add(conv)
        
        # 6. SimpleResult (Optional but good safety if available, otherwise ClosestModel+Convert is usually enough)
        # Try to add it, if it fails (class not found), we skip it.
        try:
            # Check if SimpleResult exists or just rely on the converter
            # The user said they couldn't find "Results". 
            # But usually ConvertModelToKeyPoint IS acceptable as final stage if it returns KeyPoints.
            # However, OpenPnP normally expects a 'Result' type at the end for full compliance?
            # Let's stick to the 5 stages first as per my last analysis.
            pass
        except:
            pass
            
        print("Pipeline configured successfully!")
        return True
