"""
Broadcast utility for boom gate WebSocket updates
"""
import asyncio
import logging
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


async def broadcast_gate_status_update():
    """Broadcast current gate status to all connected WebSocket clients"""
    try:
        from .models import main_gate
        from .sound_system import sound_system
        
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning("No channel layer configured for WebSocket broadcast")
            return False
        
        # Get current status
        status = main_gate.get_status()
        status['sound_enabled'] = sound_system.sound_enabled
        
        # Broadcast to all connected clients
        await channel_layer.group_send(
            "boom_gate_main",
            {
                'type': 'gate_status_update',
                'data': status
            }
        )
        
        logger.info(f"Broadcasted gate status: {status['state']}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to broadcast gate status: {str(e)}")
        return False


async def trigger_gate_via_websocket(command, **kwargs):
    """Send gate command via WebSocket to all connected clients"""
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.warning("No channel layer configured for WebSocket commands")
            return False
        
        # Send command to all connected clients
        await channel_layer.group_send(
            "boom_gate_main",
            {
                'type': 'gate_command',
                'command': command,
                'data': kwargs
            }
        )
        
        logger.info(f"Sent WebSocket gate command: {command}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send WebSocket gate command: {str(e)}")
        return False


def broadcast_gate_status_sync():
    """Synchronous wrapper for broadcasting gate status"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(broadcast_gate_status_update())
        
        loop.close()
        return result
        
    except Exception as e:
        logger.error(f"Error in sync broadcast: {str(e)}")
        return False


def trigger_gate_websocket_sync(command, **kwargs):
    """Synchronous wrapper for triggering gate via WebSocket"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(trigger_gate_via_websocket(command, **kwargs))
        
        loop.close()
        return result
        
    except Exception as e:
        logger.error(f"Error in sync WebSocket trigger: {str(e)}")
        return False
