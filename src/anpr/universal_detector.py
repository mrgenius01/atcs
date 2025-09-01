"""
Enhanced Universal License Plate Detection
Uses multiple detection strategies for better accuracy
"""
import cv2
import numpy as np
import logging
from typing import List, Tuple, Optional, Dict

logger = logging.getLogger(__name__)

class UniversalPlateDetector:
    def __init__(self):
        """Initialize universal plate detector with multiple strategies"""
        self.strategies = [
            self.detect_by_contours,
            self.detect_by_edges_and_morphology, 
            self.detect_by_color_filtering,
            self.detect_by_text_regions
        ]
    
    def detect_by_contours(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Enhanced contour-based detection"""
        try:
            print("🔍 UNIVERSAL: Strategy 1 - Contour-based detection")
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            print(f"✓ UNIVERSAL: Converted to grayscale, shape: {gray.shape}")
            
            # Multiple edge detection approaches
            edges1 = cv2.Canny(gray, 50, 200)
            edges2 = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 30, 150)
            edges = cv2.bitwise_or(edges1, edges2)
            edge_pixels = np.count_nonzero(edges)
            print(f"✓ UNIVERSAL: Combined edge detection, {edge_pixels} edge pixels")
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            print(f"✓ UNIVERSAL: Found {len(contours)} contours")
            
            candidates = []
            h, w = gray.shape
            analyzed_contours = 0
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 500:  # Skip small areas
                    continue
                
                analyzed_contours += 1
                x, y, cw, ch = cv2.boundingRect(contour)
                aspect_ratio = cw / ch
                
                print(f"  Contour {analyzed_contours}: area={area:.0f}, bbox=({x},{y},{cw},{ch}), aspect={aspect_ratio:.2f}")
                
                # License plates worldwide typically have these characteristics:
                # - Aspect ratio between 1.5:1 and 6:1 (relaxed for various orientations)
                # - Not too small or too large relative to image
                # - Rectangular shape
                if (1.5 <= aspect_ratio <= 6.0 and 
                    cw > 80 and ch > 20 and
                    cw < w * 0.8 and ch < h * 0.4):
                    
                    # Check how well the contour fits a rectangle
                    rect_area = cw * ch
                    extent = area / rect_area if rect_area > 0 else 0
                    
                    if extent > 0.4:  # Reasonable fill ratio
                        candidates.append((x, y, cw, ch, area * extent))
            
            # Sort by score (area * extent)
            candidates.sort(key=lambda x: x[4], reverse=True)
            return [(x, y, w, h) for x, y, w, h, _ in candidates[:5]]
            
        except Exception as e:
            logger.error(f"Contour detection error: {e}")
            return []
    
    def detect_by_edges_and_morphology(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detection using edge enhancement and morphological operations"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # Enhance edges
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 30, 200)
            
            # Morphological operations to connect text regions
            kernel_horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
            kernel_vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))
            
            # Close horizontal gaps (connect letters)
            morph = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_horizontal)
            # Clean vertical noise
            morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel_vertical)
            
            # Find contours in processed image
            contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            candidates = []
            h, w = gray.shape
            
            for contour in contours:
                x, y, cw, ch = cv2.boundingRect(contour)
                aspect_ratio = cw / ch
                
                if (2.5 <= aspect_ratio <= 5.5 and 
                    cw > 100 and ch > 25 and
                    cw < w * 0.7 and ch < h * 0.3):
                    candidates.append((x, y, cw, ch))
            
            return candidates[:3]
            
        except Exception as e:
            logger.error(f"Morphology detection error: {e}")
            return []
    
    def detect_by_color_filtering(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detection using color filtering for common plate colors"""
        try:
            if len(image.shape) != 3:
                return []
            
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            candidates = []
            
            # Define color ranges for common license plate colors
            color_ranges = [
                # White plates
                {"lower": np.array([0, 0, 200]), "upper": np.array([180, 30, 255])},
                # Yellow plates (like Zimbabwe)
                {"lower": np.array([20, 100, 100]), "upper": np.array([30, 255, 255])},
                # Blue plates  
                {"lower": np.array([100, 150, 50]), "upper": np.array([130, 255, 255])},
            ]
            
            for color_range in color_ranges:
                mask = cv2.inRange(hsv, color_range["lower"], color_range["upper"])
                
                # Morphological operations
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area < 1000:
                        continue
                    
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / h
                    
                    if 2.0 <= aspect_ratio <= 6.0 and w > 80 and h > 20:
                        candidates.append((x, y, w, h))
            
            return candidates[:3]
            
        except Exception as e:
            logger.error(f"Color detection error: {e}")
            return []
    
    def detect_by_text_regions(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detection using text region analysis"""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
            
            # Apply adaptive threshold to highlight text
            thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                         cv2.THRESH_BINARY_INV, 11, 2)
            
            # Find text-like regions
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            # Connect nearby text regions horizontally
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
            connected = cv2.morphologyEx(morph, cv2.MORPH_CLOSE, horizontal_kernel)
            
            contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            candidates = []
            h, w = gray.shape
            
            for contour in contours:
                x, y, cw, ch = cv2.boundingRect(contour)
                aspect_ratio = cw / ch
                
                # Look for text-like regions
                if (2.0 <= aspect_ratio <= 8.0 and 
                    cw > 60 and ch > 15 and
                    cw < w * 0.9 and ch < h * 0.4):
                    
                    # Check density of text in region
                    roi = thresh[y:y+ch, x:x+cw]
                    white_pixels = cv2.countNonZero(roi)
                    total_pixels = cw * ch
                    density = white_pixels / total_pixels if total_pixels > 0 else 0
                    
                    # License plates should have reasonable text density
                    if 0.1 <= density <= 0.7:
                        candidates.append((x, y, cw, ch))
            
            return candidates[:3]
            
        except Exception as e:
            logger.error(f"Text region detection error: {e}")
            return []
    
    def detect_plates(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Run all detection strategies and combine results"""
        all_candidates = []
        
        for strategy in self.strategies:
            try:
                candidates = strategy(image)
                all_candidates.extend(candidates)
            except Exception as e:
                logger.warning(f"Strategy {strategy.__name__} failed: {e}")
        
        # Remove duplicates and overlapping regions
        filtered = self._remove_overlaps(all_candidates)
        return filtered[:5]  # Return top 5 candidates
    
    def _remove_overlaps(self, candidates: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """Remove overlapping bounding boxes"""
        if not candidates:
            return []
        
        # Sort by area (larger first)
        candidates = sorted(candidates, key=lambda x: x[2] * x[3], reverse=True)
        
        filtered = []
        for candidate in candidates:
            x1, y1, w1, h1 = candidate
            
            overlaps = False
            for existing in filtered:
                x2, y2, w2, h2 = existing
                
                # Calculate overlap
                overlap_x = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
                overlap_y = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
                overlap_area = overlap_x * overlap_y
                
                area1 = w1 * h1
                area2 = w2 * h2
                
                # If overlap is significant, skip this candidate
                if overlap_area > 0.3 * min(area1, area2):
                    overlaps = True
                    break
            
            if not overlaps:
                filtered.append(candidate)
        
        return filtered
