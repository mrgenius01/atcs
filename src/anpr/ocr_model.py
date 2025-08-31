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
    """Enhanced preprocessing of ROI for better OCR accuracy"""
    try:
        # Convert to grayscale if needed
        if len(roi_image.shape) == 3:
            gray = cv2.cvtColor(roi_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi_image.copy()
        
        # Resize image if too small (OCR works better on larger images)
        height, width = gray.shape
        if width < 200 or height < 50:
            scale_factor = max(200 / width, 50 / height)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Apply bilateral filter to reduce noise while preserving edges
        filtered = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        # Apply Gaussian blur to reduce fine noise
        blurred = cv2.GaussianBlur(filtered, (3, 3), 0)
        
        # Sharpen the image to enhance text edges
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(blurred, -1, kernel)
        
        # Apply adaptive thresholding for better text separation
        binary = cv2.adaptiveThreshold(
            sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Morphological operations to clean up text
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # Optional: Apply dilation to make text bolder (helps with thin fonts)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        processed = cv2.dilate(processed, kernel, iterations=1)
        
        return processed
    except Exception as e:
        logger.error(f"Error in ROI preprocessing: {e}")
        return roi_image

def validate_plate_text(text: str) -> Tuple[bool, str]:
    """Validate and clean detected text as license plate"""
    if not text:
        return False, ""
    
    # Handle Unicode characters and normalize
    import unicodedata
    
    # Normalize Unicode characters (convert special chars to ASCII equivalents)
    text = unicodedata.normalize('NFKD', text)
    
    # Replace common OCR misreadings and special characters
    text_replacements = {
        '·': ' ',     # Middle dot to space
        '•': ' ',     # Bullet to space  
        '‧': ' ',     # Hyphenation point to space
        '−': '-',     # Minus sign to hyphen
        '–': '-',     # En dash to hyphen
        '—': '-',     # Em dash to hyphen
        'О': 'O',     # Cyrillic O to Latin O
        'А': 'A',     # Cyrillic A to Latin A
        'В': 'B',     # Cyrillic B to Latin B
        'Е': 'E',     # Cyrillic E to Latin E
        'Н': 'H',     # Cyrillic H to Latin H
        'І': 'I',     # Cyrillic I to Latin I
        'Р': 'P',     # Cyrillic P to Latin P
        'С': 'C',     # Cyrillic C to Latin C
        'Т': 'T',     # Cyrillic T to Latin T
        'Х': 'X',     # Cyrillic X to Latin X
        '0': 'O',     # Sometimes 0 is misread as O in plates
        '1': 'I',     # Sometimes 1 is misread as I
    }
    
    for old_char, new_char in text_replacements.items():
        text = text.replace(old_char, new_char)
    
    # Convert to uppercase
    text = text.upper()
    
    # Extract alphanumeric characters and spaces/hyphens
    # Keep structure for format recognition
    structured_text = re.sub(r'[^A-Z0-9\s\-]', '', text)
    
    # Create cleaned version (no spaces/hyphens for validation)
    cleaned = re.sub(r'[^A-Z0-9]', '', structured_text)
    
    # International license plate patterns (more comprehensive)
    patterns = [
        # European formats
        r'^[A-Z]{2}[0-9]{2}[A-Z]{3}$',        # EU standard: AB12CDE
        r'^[A-Z]{1,2}[0-9]{3,4}[A-Z]{1,2}$',  # General EU: A123BC, AB1234C
        
        # UK formats  
        r'^[A-Z][0-9]{1,3}[A-Z]{3}$',         # UK format: A123BCD
        r'^[A-Z]{2}[0-9]{2}[A-Z]{3}$',        # UK current: AB12CDE
        
        # US/Canada formats
        r'^[A-Z]{2,3}[0-9]{3,4}$',            # US state: ABC1234
        r'^[0-9]{3}[A-Z]{3}$',                # US numeric: 123ABC
        
        # Zimbabwe/African formats
        r'^[A-Z]{2,3}[0-9]{3,4}[A-Z]{0,2}$',  # ZW: AB1234C, ABC123D
        
        # Generic international
        r'^[A-Z]{1,3}[0-9]{1,4}[A-Z]{0,3}$',  # General: ABC123D
        r'^[0-9]{1,4}[A-Z]{1,4}[0-9]{0,4}$',  # Mixed: 123ABC456
        r'^[A-Z]{1,2}[0-9]{4,6}$',            # Simple: AB123456
        r'^[0-9]{4,6}[A-Z]{1,2}$',            # Reverse: 123456AB
    ]
    
    # Check length (typical plates are 4-9 characters)
    if len(cleaned) < 4 or len(cleaned) > 9:
        return False, structured_text.strip()
    
    # Check against patterns
    for pattern in patterns:
        if re.match(pattern, cleaned):
            return True, structured_text.strip()
    
    # If no exact pattern match but reasonable format, still accept
    has_letters = bool(re.search(r'[A-Z]', cleaned))
    has_numbers = bool(re.search(r'[0-9]', cleaned))
    
    if has_letters and has_numbers and 4 <= len(cleaned) <= 9:
        return True, structured_text.strip()
    
    return False, structured_text.strip()
    
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