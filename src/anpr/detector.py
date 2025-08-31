import cv2
import numpy as np
import re
import logging
from typing import List, Tuple, Optional, Dict
import time

logger = logging.getLogger(__name__)

class LicensePlateDetector:
    def __init__(self):
        """Initialize the license plate detector with cascade classifiers"""
        self.plate_cascade = None
        self.init_cascade_classifier()
    
    def init_cascade_classifier(self):
        """Initialize OpenCV cascade classifier for license plate detection"""
        try:
            # Try to load pre-trained cascade classifier for Russian license plates
            # You can download from: https://github.com/opencv/opencv/tree/master/data/haarcascades
            cascade_path = cv2.data.haarcascades + 'haarcascade_russian_plate_number.xml'
            self.plate_cascade = cv2.CascadeClassifier(cascade_path)
            
            if self.plate_cascade.empty():
                logger.warning("Cascade classifier not loaded, using contour-based detection")
                self.plate_cascade = None
        except Exception as e:
            logger.warning(f"Could not load cascade classifier: {e}")
            self.plate_cascade = None

def detect_plate_regions_contour(image: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """
    Detect potential license plate regions using contour analysis
    Returns list of (x, y, width, height) bounding boxes
    """
    try:
        print(f"🔍 CONTOUR DETECTION: Starting contour analysis on image {image.shape}")
        
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            print(f"✓ CONTOUR: Converted BGR to grayscale")
        else:
            gray = image.copy()
            print(f"✓ CONTOUR: Image already grayscale")
        
        # Apply bilateral filter to reduce noise while preserving edges
        filtered = cv2.bilateralFilter(gray, 11, 17, 17)
        print(f"✓ CONTOUR: Applied bilateral filter")
        
        # Find edges using Canny
        edges = cv2.Canny(filtered, 30, 200)
        edge_count = np.count_nonzero(edges)
        print(f"✓ CONTOUR: Canny edge detection found {edge_count} edge pixels")
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        print(f"✓ CONTOUR: Found {len(contours)} total contours")
        
        plate_candidates = []
        filtered_contours = 0
        
        print(f"🔍 CONTOUR: Analyzing {len(contours)} contours for plate characteristics...")
        
        for i, contour in enumerate(contours):
            # Calculate contour area and bounding rectangle
            area = cv2.contourArea(contour)
            if area < 500:  # Skip very small contours
                continue
            
            filtered_contours += 1
            
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h
            
            print(f"  Contour {i+1}: area={area:.0f}, bbox=({x},{y},{w},{h}), aspect={aspect_ratio:.2f}")
            
            # License plates typically have aspect ratio between 2:1 and 6:1
            if 2.0 <= aspect_ratio <= 6.0 and area > 800:
                # Calculate extent (area ratio)
                rect_area = w * h
                extent = area / rect_area if rect_area > 0 else 0
                
                # Check if contour approximation gives 4-sided polygon (rectangular)
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                print(f"    ✓ Good aspect ratio! extent={extent:.2f}, corners={len(approx)}")
                
                # Additional validation
                if (extent > 0.4 and  # Reasonable fill ratio
                    len(approx) >= 4 and  # At least 4 corners
                    w > 80 and h > 20 and  # Minimum size
                    w < gray.shape[1] * 0.9 and h < gray.shape[0] * 0.3):  # Maximum size
                    
                    print(f"    🎯 PLATE CANDIDATE: Adding to candidates list!")
                    plate_candidates.append((x, y, w, h, area))
                else:
                    reason = []
                    if extent <= 0.4: reason.append(f"low extent ({extent:.2f})")
                    if len(approx) < 4: reason.append(f"not rectangular ({len(approx)} corners)")
                    if w <= 80 or h <= 20: reason.append(f"too small ({w}x{h})")
                    if w >= gray.shape[1] * 0.9 or h >= gray.shape[0] * 0.3: reason.append(f"too large ({w}x{h})")
                    print(f"    ❌ Rejected: {', '.join(reason)}")
            else:
                reason = "bad aspect ratio" if not (2.0 <= aspect_ratio <= 6.0) else "too small area"
                print(f"    ❌ Rejected: {reason}")
        
        print(f"✓ CONTOUR: Processed {filtered_contours} contours above size threshold")
        print(f"🎯 CONTOUR: Found {len(plate_candidates)} plate candidates")
        
        # Sort by area (largest first) and return top candidates
        plate_candidates.sort(key=lambda x: x[4], reverse=True)
        
        final_candidates = [(x, y, w, h) for x, y, w, h, _ in plate_candidates[:5]]
        print(f"📋 CONTOUR: Returning top {len(final_candidates)} candidates: {final_candidates}")
        
        return final_candidates
        
    except Exception as e:
        logger.error(f"Error in contour-based detection: {e}")
        return []

def detect_plate_regions_cascade(detector: LicensePlateDetector, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """
    Detect license plates using Haar cascade classifier
    """
    try:
        print(f"🔍 CASCADE DETECTION: Starting cascade analysis on image {image.shape}")
        
        if detector.plate_cascade is None:
            print("❌ CASCADE: No cascade classifier loaded")
            return []
        
        print("✓ CASCADE: Cascade classifier available")
        
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            print("✓ CASCADE: Converted to grayscale")
        else:
            gray = image.copy()
            print("✓ CASCADE: Image already grayscale")
        
        # Detect plates using cascade
        print("🔍 CASCADE: Running detectMultiScale...")
        plates = detector.plate_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 20),
            maxSize=(400, 100)
        )
        
        print(f"✓ CASCADE: Detection complete, found {len(plates)} plates")
        
        if len(plates) > 0:
            for i, (x, y, w, h) in enumerate(plates):
                print(f"  Plate {i+1}: bbox=({x},{y},{w},{h}), area={w*h}")
        
        return [(x, y, w, h) for x, y, w, h in plates]
        
    except Exception as e:
        logger.error(f"Error in cascade detection: {e}")
        return []

def detect_plate_regions(image: np.ndarray, detector: LicensePlateDetector = None) -> List[Tuple[int, int, int, int]]:
    """
    Combined approach: use both cascade and contour-based detection
    """
    all_regions = []
    
    # Try cascade detection first
    if detector and detector.plate_cascade is not None:
        cascade_regions = detect_plate_regions_cascade(detector, image)
        all_regions.extend(cascade_regions)
    
    # Add contour-based detection results
    contour_regions = detect_plate_regions_contour(image)
    all_regions.extend(contour_regions)
    
    # Remove duplicates and overlapping regions
    filtered_regions = []
    for region in all_regions:
        x, y, w, h = region
        is_duplicate = False
        
        for existing in filtered_regions:
            ex, ey, ew, eh = existing
            
            # Check for significant overlap
            overlap_x = max(0, min(x + w, ex + ew) - max(x, ex))
            overlap_y = max(0, min(y + h, ey + eh) - max(y, ey))
            overlap_area = overlap_x * overlap_y
            
            current_area = w * h
            existing_area = ew * eh
            
            # If overlap is more than 50% of either region, consider it duplicate
            if (overlap_area > 0.5 * current_area or 
                overlap_area > 0.5 * existing_area):
                is_duplicate = True
                break
        
        if not is_duplicate:
            filtered_regions.append(region)
    
    return filtered_regions[:3]  # Return top 3 unique candidates

def enhance_plate_roi(roi: np.ndarray) -> np.ndarray:
    """
    Enhance the ROI for better OCR performance
    """
    try:
        # Convert to grayscale if needed
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi.copy()
        
        # Resize if too small
        if gray.shape[1] < 200:
            scale_factor = 200 / gray.shape[1]
            new_width = int(gray.shape[1] * scale_factor)
            new_height = int(gray.shape[0] * scale_factor)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
        
        return blurred
        
    except Exception as e:
        logger.error(f"Error enhancing ROI: {e}")
        return roi

def detect_and_recognize_plate(image_data, detector: LicensePlateDetector = None) -> Optional[Dict]:
    """
    Main function to detect and recognize license plates using enhanced universal detection
    """
    start_time = time.time()
    
    try:
        from .preprocess import preprocess_image
        from .ocr_model import load_model, infer_plate_text
        from .universal_detector import UniversalPlateDetector
        
        # Initialize detectors
        if detector is None:
            detector = LicensePlateDetector()
        
        universal_detector = UniversalPlateDetector()
        
        # Load OCR model
        ocr_model = load_model()
        if not ocr_model or not ocr_model.loaded:
            logger.error("OCR model failed to load")
            return {
                'error': 'OCR model not available',
                'plate': None,
                'confidence': 0.0,
                'processing_time': time.time() - start_time
            }
        
        # Handle different input types
        if isinstance(image_data, str):
            # Base64 encoded image
            from .preprocess import preprocess_image
            processed_result = preprocess_image(image_data)
            if processed_result.get('error'):
                logger.error(f"Preprocessing failed: {processed_result['error']}")
                return {
                    'error': processed_result['error'],
                    'plate': None,
                    'confidence': 0.0,
                    'processing_time': time.time() - start_time
                }
            original_image = processed_result.get('original')
        else:
            # Direct numpy array
            original_image = image_data
        
        if original_image is None:
            return {
                'error': 'Image processing failed',
                'plate': None,
                'confidence': 0.0,
                'processing_time': time.time() - start_time
            }
        
        logger.info(f"Processing image shape: {original_image.shape}")
        print(f"🔍 DETECTION: Processing image shape: {original_image.shape}")
        
        # Try universal detection first (enhanced multi-strategy approach)
        regions = universal_detector.detect_plates(original_image)
        print(f"🔍 DETECTION: Universal detector found {len(regions)} regions")
        
        # Fallback to cascade detection if universal detection fails
        if not regions:
            regions = detect_plate_regions_cascade(detector, original_image)
            print(f"🔍 DETECTION: Cascade detector found {len(regions)} regions")
        
        # Final fallback to contour detection
        if not regions:
            regions = detect_plate_regions_contour(original_image)
            print(f"🔍 DETECTION: Contour detector found {len(regions)} regions")
        
        if not regions:
            logger.warning("No plate regions detected by any method")
            print("❌ DETECTION: No plate regions detected by any method")
            return {
                'error': 'No license plate detected',
                'plate': None,
                'confidence': 0.0,
                'processing_time': time.time() - start_time
            }
        
        logger.info(f"Found {len(regions)} potential plate regions")
        print(f"🎯 DETECTION: Found {len(regions)} potential plate regions to analyze")
        
        # Try OCR on each detected region
        best_result = None
        best_confidence = 0.0
        
        for i, (x, y, w, h) in enumerate(regions):
            try:
                # Extract and enhance ROI
                roi = original_image[y:y+h, x:x+w]
                enhanced_roi = enhance_plate_roi(roi)
                
                logger.info(f"Processing region {i+1}: size {w}x{h} at ({x},{y})")
                print(f"🔍 DETECTION: Processing region {i+1}/{len(regions)}: size {w}x{h} at ({x},{y})")
                
                # Perform OCR
                detected_text = infer_plate_text(ocr_model, (0, 0, enhanced_roi.shape[1], enhanced_roi.shape[0]), enhanced_roi)
                
                if detected_text:
                    # Estimate confidence based on text characteristics and region size
                    confidence = estimate_plate_confidence(detected_text, w * h)
                    
                    logger.info(f"Region {i+1}: '{detected_text}' (confidence: {confidence:.2f})")
                    print(f"✅ DETECTION: Region {i+1} result: '{detected_text}' (confidence: {confidence:.2f})")
                    
                    if confidence > best_confidence:
                        best_result = {
                            'plate': detected_text,
                            'confidence': confidence,
                            'region': (x, y, w, h),
                            'processing_time': time.time() - start_time
                        }
                        best_confidence = confidence
                        print(f"🏆 DETECTION: New best result: '{detected_text}' (confidence: {confidence:.2f})")
                else:
                    logger.info(f"Region {i+1}: No text detected")
                    print(f"❌ DETECTION: Region {i+1}: No text detected")
                        
            except Exception as e:
                logger.error(f"Error processing region {i+1}: {e}")
                print(f"💥 DETECTION: Error processing region {i+1}: {e}")
                continue
        
        if best_result:
            logger.info(f"Best detection: '{best_result['plate']}' (confidence: {best_result['confidence']:.2f})")
            return best_result
        else:
            return {
                'error': 'No valid license plate text detected',
                'plate': None,
                'confidence': 0.0,
                'processing_time': time.time() - start_time
            }
        
    except Exception as e:
        logger.error(f"Detection failed: {e}")
        return {
            'error': f"Detection failed: {str(e)}",
            'plate': None,
            'confidence': 0.0,
            'processing_time': time.time() - start_time
        }

def estimate_plate_confidence(text: str, region_area: int) -> float:
    """
    Estimate confidence based on text characteristics and region size
    """
    if not text:
        return 0.0
    
    confidence = 0.5  # Base confidence
    
    # Length check (typical plates are 4-8 characters)
    if 4 <= len(text) <= 8:
        confidence += 0.2
    
    # Character composition check
    has_letters = bool(re.search(r'[A-Z]', text))
    has_numbers = bool(re.search(r'[0-9]', text))
    
    if has_letters and has_numbers:
        confidence += 0.2
    
    # Region size bonus
    if region_area > 2000:
        confidence += 0.1
    
    return min(confidence, 1.0)
