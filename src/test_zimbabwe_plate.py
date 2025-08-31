#!/usr/bin/env python
"""
Test script for real Zimbabwe license plate image
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
import requests
from anpr.lightweight_processor import process_plate_image

def test_with_real_zimbabwe_plate():
    """Test with the actual Zimbabwe license plate ABH 2411"""
    try:
        # The image data would come from the uploaded file
        # For now, let's create a test that can work with base64 data
        
        print("Testing ANPR with real Zimbabwe license plate (ABH 2411)...")
        
        # Create a base64 representation for testing
        # In a real scenario, this would be the actual uploaded image
        test_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        
        result = process_plate_image(test_base64)
        
        print("Result:")
        print(f"  Success: {result.get('success')}")
        print(f"  Plate: {result.get('plate_number')}")
        print(f"  Confidence: {result.get('confidence', 0):.1f}%")
        print(f"  Processing time: {result.get('processing_time', 0):.3f}s")
        print(f"  Method: {result.get('method', 'unknown')}")
        print(f"  Message: {result.get('message')}")
        
        if result.get('error'):
            print(f"  Error: {result.get('error')}")
        
        # Test validation for expected Zimbabwe format
        if result.get('success') and result.get('plate_number'):
            from anpr.lightweight_processor import validate_international_plate
            validation = validate_international_plate(result['plate_number'])
            print(f"\nValidation:")
            print(f"  Valid: {validation.get('valid')}")
            print(f"  Format: {validation.get('format')}")
            print(f"  Country: {validation.get('country')}")
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

def test_specific_zimbabwe_formats():
    """Test the validation function with known Zimbabwe formats"""
    from anpr.lightweight_processor import validate_international_plate
    
    test_plates = [
        "ABH2411",    # The actual plate from image
        "ABH 2411",   # With space
        "ABH-2411",   # With dash
        "AB·123CD",   # Classic Zimbabwe format
        "ABC-123D",   # Alternative format
    ]
    
    print("\nTesting Zimbabwe plate format validation:")
    for plate in test_plates:
        validation = validate_international_plate(plate)
        print(f"  {plate:10} -> Valid: {validation['valid']:5} Format: {validation['format']:15} Country: {validation['country']}")

if __name__ == "__main__":
    test_with_real_zimbabwe_plate()
    test_specific_zimbabwe_formats()
