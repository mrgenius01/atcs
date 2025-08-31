#!/usr/bin/env python
"""
Test script for ANPR functionality
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
from anpr.lightweight_processor import process_plate_image

def test_with_sample_image():
    """Test with a simple colored rectangle as a license plate simulation"""
    try:
        import cv2
        import numpy as np
        from PIL import Image
        import io
        
        # Create a simple test image with text-like patterns
        # This simulates a license plate
        test_image = np.zeros((100, 300, 3), dtype=np.uint8)
        test_image.fill(255)  # White background
        
        # Add some black rectangles to simulate text
        cv2.rectangle(test_image, (20, 30), (40, 70), (0, 0, 0), -1)  # Letter-like shape
        cv2.rectangle(test_image, (60, 30), (80, 70), (0, 0, 0), -1)  # Letter-like shape
        cv2.rectangle(test_image, (100, 30), (120, 70), (0, 0, 0), -1)  # Number-like shape
        cv2.rectangle(test_image, (140, 30), (160, 70), (0, 0, 0), -1)  # Number-like shape
        cv2.rectangle(test_image, (180, 30), (200, 70), (0, 0, 0), -1)  # Number-like shape
        cv2.rectangle(test_image, (220, 30), (240, 70), (0, 0, 0), -1)  # Letter-like shape
        cv2.rectangle(test_image, (260, 30), (280, 70), (0, 0, 0), -1)  # Letter-like shape
        
        # Convert to PIL Image
        pil_image = Image.fromarray(cv2.cvtColor(test_image, cv2.COLOR_BGR2RGB))
        
        # Convert to base64
        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        img_data = f"data:image/png;base64,{img_base64}"
        
        print("Testing ANPR with simulated license plate image...")
        result = process_plate_image(img_data)
        
        print("Result:")
        print(f"  Success: {result.get('success')}")
        print(f"  Plate: {result.get('plate_number')}")
        print(f"  Confidence: {result.get('confidence', 0):.1f}%")
        print(f"  Processing time: {result.get('processing_time', 0):.3f}s")
        print(f"  Method: {result.get('method', 'unknown')}")
        print(f"  Message: {result.get('message')}")
        
        if result.get('error'):
            print(f"  Error: {result.get('error')}")
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_with_sample_image()
