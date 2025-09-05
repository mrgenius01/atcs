"""
WebSocket Consumer for Boom Gate Control
Handles real-time gate commands via WebSocket
"""
import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import main_gate, GateState
from .sound_system import sound_system

logger = logging.getLogger(__name__)


class BoomGateConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gate_group_name = "boom_gate_main"
    
    async def connect(self):
        """Handle WebSocket connection"""
        # Join boom gate group
        await self.channel_layer.group_add(
            self.gate_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"Boom gate WebSocket connected: {self.channel_name}")
        
        # Send initial gate status
        await self.send_gate_status()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Leave boom gate group
        await self.channel_layer.group_discard(
            self.gate_group_name,
            self.channel_name
        )
        logger.info(f"Boom gate WebSocket disconnected: {self.channel_name}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(text_data)
            command = data.get('command')
            
            logger.info(f"Received boom gate command: {command}")
            
            if command == 'open_gate':
                await self.handle_open_gate(data)
            elif command == 'close_gate':
                await self.handle_close_gate(data)
            elif command == 'auto_cycle':
                await self.handle_auto_cycle(data)
            elif command == 'get_status':
                await self.send_gate_status()
            elif command == 'emergency_stop':
                await self.handle_emergency_stop()
            elif command == 'toggle_sound':
                await self.handle_toggle_sound()
            else:
                await self.send_error(f"Unknown command: {command}")
                
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            logger.error(f"Error processing boom gate command: {str(e)}")
            await self.send_error(f"Command processing error: {str(e)}")
    
    async def handle_open_gate(self, data):
        """Handle gate open command"""
        try:
            # Play opening sound sequence
            asyncio.create_task(sound_system.play_gate_opening_sequence())
            
            # Open the gate
            success = await main_gate.open_gate()
            
            if success:
                await self.broadcast_gate_status()
                await self.send_response("Gate opened successfully")
            else:
                sound_system.play_error_sound()
                await self.send_error("Failed to open gate")
                
        except Exception as e:
            logger.error(f"Error opening gate: {str(e)}")
            sound_system.play_error_sound()
            await self.send_error(f"Gate open error: {str(e)}")
    
    async def handle_close_gate(self, data):
        """Handle gate close command"""
        try:
            # Play closing sound sequence
            asyncio.create_task(sound_system.play_gate_closing_sequence())
            
            # Close the gate
            success = await main_gate.close_gate()
            
            if success:
                await self.broadcast_gate_status()
                await self.send_response("Gate closed successfully")
            else:
                sound_system.play_error_sound()
                await self.send_error("Failed to close gate")
                
        except Exception as e:
            logger.error(f"Error closing gate: {str(e)}")
            sound_system.play_error_sound()
            await self.send_error(f"Gate close error: {str(e)}")
    
    async def handle_auto_cycle(self, data):
        """Handle automatic gate cycle command"""
        try:
            open_duration = data.get('open_duration', 5)  # Default 5 seconds
            
            # Start auto cycle with sound effects
            asyncio.create_task(sound_system.play_gate_opening_sequence())
            success = await main_gate.auto_cycle(open_duration)
            
            if success:
                await self.broadcast_gate_status()
                await self.send_response(f"Auto cycle completed (open for {open_duration}s)")
            else:
                sound_system.play_error_sound()
                await self.send_error("Auto cycle failed")
                
        except Exception as e:
            logger.error(f"Error in auto cycle: {str(e)}")
            sound_system.play_error_sound()
            await self.send_error(f"Auto cycle error: {str(e)}")
    
    async def handle_emergency_stop(self):
        """Handle emergency stop command"""
        try:
            main_gate.emergency_stop()
            sound_system.stop_all_sounds()
            sound_system.play_error_sound()
            
            await self.broadcast_gate_status()
            await self.send_response("Emergency stop activated")
            
        except Exception as e:
            logger.error(f"Error in emergency stop: {str(e)}")
            await self.send_error(f"Emergency stop error: {str(e)}")
    
    async def handle_toggle_sound(self):
        """Handle sound toggle command"""
        try:
            sound_enabled = sound_system.toggle_sound()
            status = "enabled" if sound_enabled else "disabled"
            await self.send_response(f"Sound {status}")
            
        except Exception as e:
            logger.error(f"Error toggling sound: {str(e)}")
            await self.send_error(f"Sound toggle error: {str(e)}")
    
    async def send_gate_status(self):
        """Send current gate status"""
        status = main_gate.get_status()
        status['sound_enabled'] = sound_system.sound_enabled
        
        await self.send(text_data=json.dumps({
            'type': 'gate_status',
            'data': status
        }))
    
    async def broadcast_gate_status(self):
        """Broadcast gate status to all connected clients"""
        status = main_gate.get_status()
        status['sound_enabled'] = sound_system.sound_enabled
        
        await self.channel_layer.group_send(
            self.gate_group_name,
            {
                'type': 'gate_status_update',
                'data': status
            }
        )
    
    async def send_response(self, message):
        """Send success response"""
        await self.send(text_data=json.dumps({
            'type': 'response',
            'success': True,
            'message': message
        }))
    
    async def send_error(self, message):
        """Send error response"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'success': False,
            'message': message
        }))
    
    # Group message handlers
    async def gate_status_update(self, event):
        """Handle gate status update from group"""
        await self.send(text_data=json.dumps({
            'type': 'gate_status',
            'data': event['data']
        }))


# Function to send gate command from other parts of the system
async def send_gate_command(command, **kwargs):
    """
    Send gate command via WebSocket
    Usage: await send_gate_command('open_gate')
    """
    from channels.layers import get_channel_layer
    
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.error("No channel layer configured")
        return False
    
    try:
        await channel_layer.group_send(
            "boom_gate_main",
            {
                'type': 'gate_command',
                'command': command,
                'data': kwargs
            }
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send gate command {command}: {str(e)}")
        return False
