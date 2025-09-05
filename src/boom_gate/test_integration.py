"""
Test boom gate integration between transaction and WebSocket
"""
import requests
import json
import time

def test_transaction_boom_gate():
    """Test boom gate trigger from transaction processing"""
    print("🚧 Testing Transaction → Boom Gate Integration 🚧\n")
    
    base_url = "http://localhost:8000"
    
    # Test transaction processing with boom gate trigger
    print("1. Simulating vehicle transaction with boom gate trigger...")
    try:
        # Simulate ANPR transaction
        transaction_payload = {
            "plate_number": "TEST-BOOM-123",
            "confidence": 0.95,
            "location": "Main Toll Plaza",
            "toll_amount": 2.50
        }
        
        print(f"   Processing transaction for plate: {transaction_payload['plate_number']}")
        
        response = requests.post(
            f"{base_url}/api/process-vehicle-transaction/",
            json=transaction_payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Transaction successful: {data.get('success')}")
            print(f"   ✓ Transaction ID: {data.get('transaction_id')}")
            print(f"   ✓ Boom gate triggered: {data.get('boom_gate_triggered', False)}")
            print(f"   ✓ Status: {data.get('status')}")
            
            if data.get('success'):
                print("\n   🎵 You should now hear boom gate sounds!")
                print("   🚪 Check the web interface - the gate should be moving!")
                print(f"   ⏳ Gate will stay open for 5 seconds...")
                
                # Wait for gate operation to complete
                time.sleep(7)
                
                # Check final gate status
                status_response = requests.get(f"{base_url}/boom-gate/status/")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    final_state = status_data['data']['state']
                    print(f"   ✓ Final gate state: {final_state}")
                
            else:
                print(f"   ⚠️ Transaction failed: {data.get('message')}")
                
        else:
            print(f"   ❌ Transaction failed: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Transaction test error: {e}")
    
    print("\n" + "="*60)
    
    # Test direct API boom gate trigger
    print("\n2. Testing direct boom gate API trigger...")
    try:
        api_payload = {
            "command": "open",
            "transaction_id": "api_test_002",
            "vehicle_plate": "API-TEST-456",
            "open_duration": 3
        }
        
        print(f"   Triggering gate for plate: {api_payload['vehicle_plate']}")
        
        response = requests.post(
            f"{base_url}/boom-gate/control/",
            json=api_payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ API trigger successful: {data.get('success')}")
            print(f"   ✓ Message: {data.get('message')}")
            
            print("\n   🎵 You should hear boom gate sounds again!")
            print("   🚪 Gate should be operating via API trigger!")
            
            time.sleep(5)
            
        else:
            print(f"   ❌ API trigger failed: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ API test error: {e}")
    
    print("\n" + "="*60)
    print("🎉 Integration test completed!")
    print("\nWhat should happen:")
    print("  1. 🔊 Motor sounds during both tests")
    print("  2. 🚪 Visual gate movement in web interface")
    print("  3. ✅ Successful transaction processing")
    print("  4. 🔄 Gate opens and closes automatically")
    print("="*60)

if __name__ == "__main__":
    print("Make sure:")
    print("1. Django server is running (python manage.py runserver)")
    print("2. Or Daphne server is running (daphne -p 8000 asgi:application)")
    print("3. Boom gate web interface is open: http://localhost:8000/boom-gate/")
    print("4. A vehicle is registered in the system for testing")
    print()
    
    input("Press Enter to start integration test...")
    test_transaction_boom_gate()
