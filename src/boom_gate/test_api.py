"""
Test boom gate integration with Django
Run this after starting the Django server
"""
import requests
import json
import time

def test_boom_gate_api():
    """Test boom gate via API endpoints"""
    base_url = "http://localhost:8000"
    
    print("🚧 Testing Boom Gate API Integration 🚧\n")
    
    # Test 1: Get gate status
    print("1. Testing gate status...")
    try:
        response = requests.get(f"{base_url}/boom-gate/status/")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Status: {data['data']['state']}")
            print(f"   ✓ Operational: {data['data']['operational']}")
        else:
            print(f"   ❌ Status check failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Status check error: {e}")
    
    print()
    
    # Test 2: Open gate via API
    print("2. Testing gate opening via API...")
    try:
        payload = {
            "command": "open",
            "transaction_id": "test_001", 
            "vehicle_plate": "TEST-123",
            "open_duration": 3
        }
        
        response = requests.post(
            f"{base_url}/boom-gate/control/",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Gate command sent: {data['message']}")
            
            # Wait a moment for operation to complete
            print("   ⏳ Waiting for gate operation to complete...")
            time.sleep(4)
            
            # Check status after operation
            status_response = requests.get(f"{base_url}/boom-gate/status/")
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"   ✓ Final status: {status_data['data']['state']}")
            
        else:
            print(f"   ❌ Gate open failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Gate open error: {e}")
    
    print()
    
    # Test 3: Test emergency stop
    print("3. Testing emergency stop...")
    try:
        payload = {"command": "emergency_stop"}
        
        response = requests.post(
            f"{base_url}/boom-gate/control/",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Emergency stop: {data['message']}")
        else:
            print(f"   ❌ Emergency stop failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Emergency stop error: {e}")
    
    print("\n" + "="*50)
    print("🎉 API Test completed!")
    print("If successful, you should have heard motor sounds!")
    print("="*50)

if __name__ == "__main__":
    print("Make sure Django server is running on http://localhost:8000")
    input("Press Enter to start testing...")
    test_boom_gate_api()
