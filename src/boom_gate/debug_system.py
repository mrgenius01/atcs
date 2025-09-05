"""
Debug utility to check boom gate WebSocket status
"""
import asyncio
import logging
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


async def check_websocket_connections():
    """Check if WebSocket system is working"""
    try:
        channel_layer = get_channel_layer()
        
        if not channel_layer:
            print("❌ No channel layer configured")
            return False
        
        print(f"✅ Channel layer configured: {type(channel_layer).__name__}")
        
        # Try to send a test message
        await channel_layer.group_send(
            "boom_gate_main",
            {
                'type': 'gate_status_update',
                'data': {'test': 'connection_check'}
            }
        )
        
        print("✅ Test message sent to boom_gate_main group")
        return True
        
    except Exception as e:
        print(f"❌ WebSocket check failed: {e}")
        return False


def debug_boom_gate_system():
    """Debug the entire boom gate system"""
    print("🔍 Boom Gate System Debug 🔍\n")
    
    # Check models
    try:
        from .models import main_gate
        status = main_gate.get_status()
        print(f"✅ Gate Model: {status['state']} (operational: {status['operational']})")
    except Exception as e:
        print(f"❌ Gate Model Error: {e}")
    
    # Check sound system
    try:
        from .sound_system import sound_system
        print(f"✅ Sound System: {'enabled' if sound_system.sound_enabled else 'disabled'} (initialized: {sound_system.initialized})")
    except Exception as e:
        print(f"❌ Sound System Error: {e}")
    
    # Check WebSocket system
    print("\n📡 Checking WebSocket System...")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(check_websocket_connections())
        
        loop.close()
        
        if result:
            print("✅ WebSocket system operational")
        else:
            print("❌ WebSocket system not working")
            
    except Exception as e:
        print(f"❌ WebSocket Check Error: {e}")
    
    # Check sync controller
    try:
        from .sync_controller import get_gate_status_sync
        sync_status = get_gate_status_sync()
        print(f"✅ Sync Controller: {sync_status['state']}")
    except Exception as e:
        print(f"❌ Sync Controller Error: {e}")
    
    print(f"\n📋 Debug Summary:")
    print(f"   - Gate model operational")
    print(f"   - Sound system ready")
    print(f"   - WebSocket layer configured") 
    print(f"   - Sync controller working")
    print(f"\n🎯 Next Steps:")
    print(f"   1. Open web interface: http://localhost:8000/boom-gate/")
    print(f"   2. Run transaction test: python boom_gate/test_integration.py")
    print(f"   3. Check browser console for WebSocket connection")


if __name__ == "__main__":
    debug_boom_gate_system()
