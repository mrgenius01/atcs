"""
Test script for boom gate system
Run this to test boom gate functionality without full Django setup
"""
import asyncio
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_boom_gate():
    """Test boom gate basic functionality"""
    print("🚧 Testing Boom Gate System 🚧\n")
    
    try:
        # Import boom gate components
        from boom_gate.models import BoomGate, GateState
        from boom_gate.sound_system import SoundSystem
        
        # Create gate instance
        gate = BoomGate("test_gate")
        sound = SoundSystem()
        
        print(f"✓ Gate initialized: {gate.gate_id}")
        print(f"✓ Sound system initialized: {sound.initialized}")
        
        # Test gate status
        status = gate.get_status()
        print(f"\n📊 Initial Status:")
        print(f"   State: {status['state']}")
        print(f"   Operational: {status['operational']}")
        
        # Test gate opening
        print(f"\n🔓 Opening gate...")
        success = await gate.open_gate()
        print(f"   Result: {'SUCCESS' if success else 'FAILED'}")
        print(f"   New State: {gate.state.value}")
        
        # Test auto cycle
        print(f"\n🔄 Testing auto cycle (3 seconds open)...")
        success = await gate.auto_cycle(open_duration=3)
        print(f"   Result: {'SUCCESS' if success else 'FAILED'}")
        print(f"   Final State: {gate.state.value}")
        
        # Test sound system
        print(f"\n🔊 Testing sound system...")
        if sound.sound_enabled:
            print("   Playing test sound...")
            # sound.play_sound("warning_beep")  # Uncomment if pygame is available
            print("   ✓ Sound system ready")
        else:
            print("   ⚠️ Sound system disabled")
        
        print(f"\n✅ Boom gate system test completed successfully!")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure Django and boom_gate modules are properly configured")
    except Exception as e:
        print(f"❌ Test failed: {e}")

async def test_sound_only():
    """Test just the sound system"""
    print("🔊 Testing Sound System Only 🔊\n")
    
    try:
        from boom_gate.sound_system import SoundSystem
        
        sound = SoundSystem()
        print(f"Sound system initialized: {sound.initialized}")
        print(f"Sound enabled: {sound.sound_enabled}")
        
        if sound.initialized and sound.sound_enabled:
            print("Playing warning beep sequence...")
            await sound.play_gate_opening_sequence()
            
        print("✅ Sound test completed!")
        
    except Exception as e:
        print(f"❌ Sound test failed: {e}")

if __name__ == "__main__":
    print("Choose test to run:")
    print("1. Full boom gate test")
    print("2. Sound system only")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(test_boom_gate())
    elif choice == "2":
        asyncio.run(test_sound_only())
    else:
        print("Invalid choice. Running full test...")
        asyncio.run(test_boom_gate())
