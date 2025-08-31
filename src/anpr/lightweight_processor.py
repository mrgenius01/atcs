# Lightweight ANPR processing (no OpenCV dependency for now)
import re
import time
import random
from typing import Dict


def process_plate_image(img_bytes: bytes) -> Dict[str, any]:
    """
    Simulate ANPR processing pipeline
    In production, this would use OpenCV + EasyOCR/Tesseract
    """
    start_time = time.time()
    
    try:
        # Simulate processing delay
        time.sleep(0.2)
        
        # Generate realistic Zimbabwe plate
        letters1 = random.choice(['AB', 'AC', 'AD', 'AE', 'AF', 'AG'])
        numbers = random.randint(1000, 9999)
        letters2 = random.choice(['CD', 'CE', 'CF', 'CG', 'CH', 'CI'])
        detected_text = f"{letters1}·{numbers}{letters2}"
        
        # Simulate confidence based on "image quality"
        base_confidence = 0.75 + (random.random() * 0.2)  # 75-95%
        
        # Zimbabwe plate validation
        validation = validate_zimbabwe_plate(detected_text)
        
        processing_time = time.time() - start_time
        
        return {
            "success": validation["valid"],
            "detected_text": detected_text,
            "validation": validation,
            "processing_time": processing_time
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "processing_time": time.time() - start_time
        }


def validate_zimbabwe_plate(plate_text: str) -> Dict[str, any]:
    """Validate Zimbabwe license plate format"""
    if not plate_text:
        return {"valid": False, "confidence": 0.0}
    
    # Zimbabwe patterns
    patterns = [
        r'^[A-Z]{2}[\s·-]?\d{4}[A-Z]{2}$',  # AB·1234CD
        r'^[A-Z]{3}[\s·-]?\d{3,4}$',        # ABC·123
    ]
    
    cleaned = re.sub(r'[^\w\s·-]', '', plate_text.upper().strip())
    
    for pattern in patterns:
        if re.match(pattern, cleaned):
            return {
                "valid": True,
                "confidence": 0.85 + (random.random() * 0.1),  # 85-95%
                "format": "zimbabwe_standard",
                "cleaned_plate": cleaned
            }
    
    return {"valid": False, "confidence": 0.3}
