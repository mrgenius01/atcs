# Lightweight plate detector stub (replaces OpenCV)
from typing import List, Tuple

def detect_plate_regions(image_data: dict) -> List[Tuple[int,int,int,int]]:
    """Simulate plate detection returning bounding boxes (x,y,w,h)"""
    if not image_data.get("processed"):
        return []
    
    # Return simulated plate region based on image dimensions
    w, h = image_data.get("width", 100), image_data.get("height", 100)
    # Assume plate is in center-bottom area (typical for vehicles)
    plate_w, plate_h = min(w//3, 120), min(h//8, 30)
    plate_x = (w - plate_w) // 2
    plate_y = h - plate_h - 10
    
    return [(plate_x, plate_y, plate_w, plate_h)]
