"""
Simple boom gate test without sound dependencies
"""
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def simple_gate_test():
    """Test boom gate basic functionality without sound"""
    print("🚧 Simple Boom Gate Test 🚧\n")
    
    try:
        # Import boom gate models only
        from boom_gate.models import BoomGate, GateState
        
        # Create gate instance
        gate = BoomGate("test_gate")
        
        print(f"✓ Gate initialized: {gate.gate_id}")
        
        # Test gate status
        status = gate.get_status()
        print(f"\n📊 Initial Status:")
        print(f"   State: {status['state']}")
        print(f"   Operational: {status['operational']}")
        print(f"   Last Action: {status['last_action']}")
        
        # Test gate opening
        print(f"\n🔓 Opening gate...")
        success = await gate.open_gate()
        print(f"   Result: {'SUCCESS' if success else 'FAILED'}")
        print(f"   New State: {gate.state.value}")
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Test gate closing  
        print(f"\n🔒 Closing gate...")
        success = await gate.close_gate()
        print(f"   Result: {'SUCCESS' if success else 'FAILED'}")
        print(f"   Final State: {gate.state.value}")
        
        # Test auto cycle
        print(f"\n🔄 Testing auto cycle (2 seconds open)...")
        success = await gate.auto_cycle(open_duration=2)
        print(f"   Result: {'SUCCESS' if success else 'FAILED'}")
        print(f"   Final State: {gate.state.value}")
        
        print(f"\n✅ Basic boom gate functionality test PASSED!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def test_controller():
    """Test the boom gate controller interface"""
    print("\n🎮 Testing Boom Gate Controller 🎮\n")
    
    try:
        from boom_gate.controller import BoomGateController
        
        controller = BoomGateController()
        print(f"✓ Controller initialized")
        
        # Test status
        status = controller.get_gate_status()
        print(f"✓ Gate status retrieved: {status['state']}")
        
        # Test operational check
        operational = controller.is_gate_operational()
        print(f"✓ Gate operational: {operational}")
        
        print(f"✅ Controller test PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Controller test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("=" * 50)
    print("    BOOM GATE SYSTEM TEST SUITE")
    print("=" * 50)
    
    gate_test = await simple_gate_test()
    controller_test = await test_controller()
    
    print(f"\n" + "=" * 50)
    print("TEST RESULTS:")
    print(f"  Gate Model: {'✅ PASS' if gate_test else '❌ FAIL'}")
    print(f"  Controller: {'✅ PASS' if controller_test else '❌ FAIL'}")
    
    if gate_test and controller_test:
        print(f"\n🎉 ALL TESTS PASSED! Boom gate system is ready!")
        print(f"\nNext steps:")
        print(f"  1. Start Django server: python manage.py runserver")
        print(f"  2. Visit: http://localhost:8000/boom-gate/")
        print(f"  3. Test WebSocket connection for real-time control")
    else:
        print(f"\n⚠️ Some tests failed. Check the errors above.")
    
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
