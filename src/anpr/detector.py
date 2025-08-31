# Detector stub for plates
# In MVP, we assume the plate ROI is provided or use a simple heuristic.

from typing import List, Tuple

def detect_plate_regions(image) -> List[Tuple[int,int,int,int]]:
    # Return a dummy full-image region
    h, w = image.shape[:2]
    return [(0, 0, w, h)]
