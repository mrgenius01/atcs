# Real OpenCV-based OCR for license plates
import cv2
import numpy as np
import easyocr
from typing import Optional, Tuple, List
import re
import logging

logger = logging.getLogger(__name__)

class PlateOCRModel:
    def __init__(self):
        """Initialize EasyOCR reader for multiple languages"""
        try:
            # Initialize with English and common languages for international plates
            self.reader = easyocr.Reader(['en', 'fr', 'de', 'es', 'it'], gpu=False)
            self.loaded = True
            logger.info("EasyOCR model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load EasyOCR model: {e}")
            self.loaded = False
            self.reader = None

def load_model(path: str = None):
    """Load the OCR model"""
    return PlateOCRModel()

def preprocess_roi(roi_image: np.ndarray) -> np.ndarray:
    """Preprocess ROI for better OCR accuracy"""
    try:
        # Convert to grayscale if needed
        if len(roi_image.shape) == 3:
            gray = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi_image.copy()
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Apply adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        return processed
    except Exception as e:
        logger.error(f"Error in ROI preprocessing: {e}")
        return roi_image

def validate_plate_text(text: str) -> Tuple[bool, str]:
    """Validate and clean detected text as license plate"""
    if not text:
        return False, ""
    
    # Clean the text: remove spaces, convert to uppercase
    cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
    
    # Common international license plate patterns
    patterns = [
        r'^[A-Z]{1,3}[0-9]{1,4}[A-Z]{0,3}$',  # General pattern: ABC123D
        r'^[A-Z]{2}[0-9]{2}[A-Z]{3}$',        # EU format: AB12CDE
        r'^[A-Z][0-9]{1,3}[A-Z]{3}$',         # UK format: A123BCD
        r'^[0-9]{1,3}[A-Z]{1,3}[0-9]{1,4}$', # Mixed format: 123ABC456
        r'^[A-Z]{1,2}[0-9]{4,6}$',            # Simple format: AB1234
        r'^[0-9]{4,6}[A-Z]{1,2}$',            # Reverse format: 1234AB
    ]
    
    # Check length (typical plates are 4-8 characters)
    if len(cleaned) < 4 or len(cleaned) > 8:
        return False, cleaned
    
    # Check against patterns
    for pattern in patterns:
        if re.match(pattern, cleaned):
            return True, cleaned
    
    return False, cleaned

def infer_plate_text(model: PlateOCRModel, roi_bounds: tuple, image: np.ndarray = None) -> Optional[str]:
    """Extract text from license plate ROI using real OCR"""
    if not model or not model.loaded:
        logger.error("OCR model not loaded")
        return None
    
    try:
        # Extract ROI from image if provided
        if image is not None and roi_bounds:
            x, y, w, h = roi_bounds
            roi = image[y:y+h, x:x+w]
        else:
            logger.error("No image or ROI bounds provided")
            return None
        
        # Preprocess the ROI
        processed_roi = preprocess_roi(roi)
        
        # Use EasyOCR to detect text
        results = model.reader.readtext(processed_roi)
        
        if not results:
            logger.warning("No text detected in ROI")
            return None
        
        # Find the best candidate text
        best_text = ""
        best_confidence = 0.0
        
        for (bbox, text, confidence) in results:
            # Validate if this looks like a license plate
            is_valid, cleaned_text = validate_plate_text(text)
            
            if is_valid and confidence > best_confidence and confidence > 0.5:
                best_text = cleaned_text
                best_confidence = confidence
        
        if best_text and best_confidence > 0.5:
            logger.info(f"Detected plate: {best_text} (confidence: {best_confidence:.2f})")
            return best_text
        else:
            logger.warning(f"No valid plate detected. Best attempt: {best_text} (confidence: {best_confidence:.2f})")
            return None
            
    except Exception as e:
        logger.error(f"Error in OCR inference: {e}")
        return None