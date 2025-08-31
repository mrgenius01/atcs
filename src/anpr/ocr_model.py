# Lightweight OCR stub (replaces TensorFlow)
from typing import Optional
import random

# Zimbabwe plate patterns for simulation
ZIMBABWE_PLATES = [
    "AB·7123CD", "BC·8456EF", "CD·9789GH", "DE·1234IJ", 
    "EF·5678KL", "FG·9012MN", "GH·3456OP", "HI·7890QR"
]

def load_model(path: str):
    """Simulate model loading"""
    return {"loaded": True, "path": path}

def infer_plate_text(model, roi_bounds: tuple) -> Optional[str]:
    """Simulate OCR inference returning Zimbabwe-format plate"""
    if not model or not model.get("loaded"):
        return None
    
    # Simulate 95% accuracy requirement
    if random.random() < 0.95:
        return random.choice(ZIMBABWE_PLATES)
    else:
        # 5% failure rate
        return None