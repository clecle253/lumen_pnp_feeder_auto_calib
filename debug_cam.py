from org.openpnp.model import Configuration
import json

def inspect():
    try:
        config = Configuration.get()
        machine = config.getMachine()
        head = machine.getDefaultHead()
        cam = head.getDefaultCamera()
        
        print("Camera Object: " + str(cam))
        # print("Class: " + str(cam.getClass())) # Avoiding getName call just in case
        
        if hasattr(cam, "getBrightness"):
            val = cam.getBrightness()
            print("\n--- getBrightness() ---")
            print("Value: " + str(val))
            print("Type: " + str(type(val)))
            # print("TypeClass: " + str(val.getClass()))
            
            # If it's a Property object, it might have .set() or .setValue()
            for d in dir(val):
                if "set" in d.lower():
                    print("PROP: " + d)

        # Also check CapturePropertyHolder if helpful
        # if hasattr(cam, "getCaptureProperties"): ...

    except Exception as e:
        print("Error: " + str(e))

inspect()
