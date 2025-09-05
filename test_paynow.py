#!/usr/bin/env python
"""
Test script to check Paynow SDK response attributes
"""
import os
import sys
import django

# Add the src directory to Python path
sys.path.insert(0, '/src')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from paynow import Paynow

def test_paynow_attributes():
    """Test what attributes are available on Paynow response"""
    try:
        paynow = Paynow('19347', '53f73fa2-89cb-4e3e-94cd-f0c6badd9f6a', 'http://example.com/result/', 'http://example.com/return/')
        
        # Create a test payment
        payment = paynow.create_payment('TEST123', 'test@example.com')
        payment.add('Test Item', 1.0)
        
        print("Paynow SDK loaded successfully")
        print(f"Payment object type: {type(payment)}")
        print(f"Payment attributes: {dir(payment)}")
        
        # Don't actually send the payment, just test the object structure
        print("\nPaynow client attributes:")
        print(dir(paynow))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_paynow_attributes()
