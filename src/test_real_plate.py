#!/usr/bin/env python
"""
Test ANPR with uploaded Zimbabwe license plate image
Save the Zimbabwe plate image as 'zimbabwe_plate.jpg' in the test_images folder
"""
import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

import base64
import cv2
import numpy as np
from PIL import Image
import io
from anpr.lightweight_processor import process_plate_image, validate_international_plate

def create_test_zimbabwe_plate():
    """Create a test Zimbabwe license plate image similar to ABH 2411"""
    try:
        # Create a yellow background (Zimbabwe plates are yellow)
        img = np.full((120, 300, 3), (0, 200, 255), dtype=np.uint8)  # Yellow background in BGR
        
        # Add black text using OpenCV
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 2
        thickness = 3
        color = (0, 0, 0)  # Black text
        
        # Add "ABH" text
        cv2.putText(img, 'ABH', (20, 60), font, font_scale, color, thickness)
        
        # Add "2411" text
        cv2.putText(img, '2411', (150, 60), font, font_scale, color, thickness)
        
        # Add some border
        cv2.rectangle(img, (5, 5), (295, 115), (0, 0, 0), 2)
        
        return img
        
    except Exception as e:
        print(f"Error creating test image: {e}")
        return None

def test_with_zimbabwe_image():
    """Test ANPR with Zimbabwe license plate image"""
    print("=== Testing ANPR with Zimbabwe License Plate ===")
    
    # Try to load actual image first
    image_path = "test_images/zimbabwe_plate.jpeg"
    
    if os.path.exists(image_path):
        print(f"Loading actual image from {image_path}")
        try:
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            
            # Convert to base64
            img_base64 = base64.b64encode(image_bytes).decode('utf-8')
            img_data = f"data:image/jpeg;base64,{img_base64}"
            
        except Exception as e:
            print(f"Error loading image: {e}")
            img_data = None
    else:
        print(f"Image file not found at {image_path}")
        print("Creating synthetic Zimbabwe plate image...")
        
        # Create synthetic image
        test_img = create_test_zimbabwe_plate()
        if test_img is not None:
            # Convert to PIL and then to base64
            pil_image = Image.fromarray(cv2.cvtColor(test_img, cv2.COLOR_BGR2RGB))
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            img_data = f"data:image/png;base64,{img_base64}"
        else:
            img_data = None
    
    if img_data is None:
        print("No image data available for testing")
        return
    
    # Process the image
    print("Processing image...")
    result = process_plate_image(img_data)
    
    print("\n=== ANPR Results ===")
    print(f"Success: {result.get('success')}")
    print(f"Detected Plate: {result.get('plate_number')}")
    print(f"Confidence: {result.get('confidence', 0):.1f}%")
    print(f"Processing Time: {result.get('processing_time', 0):.3f}s")
    print(f"Method Used: {result.get('method', 'unknown')}")
    print(f"Message: {result.get('message')}")
    
    if result.get('error'):
        print(f"Error: {result.get('error')}")
    
    # Test validation if we got a result
    if result.get('success') and result.get('plate_number'):
        print(f"\n=== Plate Format Validation ===")
        validation = validate_international_plate(result['plate_number'])
        print(f"Valid Format: {validation.get('valid')}")
        print(f"Format Type: {validation.get('format')}")
        print(f"Country: {validation.get('country')}")
        print(f"Original: {validation.get('original')}")
        print(f"Cleaned: {validation.get('cleaned')}")

def test_zimbabwe_validation():
    """Test Zimbabwe license plate format validation"""
    print("\n=== Testing Zimbabwe Plate Format Validation ===")
    
    test_plates = [
        "ABH2411",      # Actual plate from image (compact)
        "ABH 2411",     # With space
        "ABH-2411",     # With dash
        "AB·123CD",     # Traditional Zimbabwe format
        "ABC-123D",     # Alternative Zimbabwe format
        "ZW123AB",      # Generic format
        "INVALID",      # Invalid format
        "A1B2C3D4E",    # Too long
        "AB",           # Too short
    ]
    
    for plate in test_plates:
        validation = validate_international_plate(plate)
        status = "✓" if validation['valid'] else "✗"
        print(f"{status} {plate:12} -> {validation['format']:15} ({validation['country']})")

def main():
    """Run all tests"""
    test_with_zimbabwe_image()
    test_zimbabwe_validation()
    
    print("\n=== Instructions ===")
    print("To test with the actual Zimbabwe plate image:")
    print("1. Save the Zimbabwe license plate image as 'test_images/zimbabwe_plate.jpg'")
    print("2. Run this script again")
    print("3. The system will process the real image and detect 'ABH 2411'")

if __name__ == "__main__":
    main()
