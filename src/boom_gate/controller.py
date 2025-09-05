"""
Boom Gate Control Interface
Main interface for controlling the boom gate system
"""
import asyncio
import logging
from .models import main_gate, GateState
from .sound_system import sound_system
from .consumers import send_gate_command

logger = logging.getLogger(__name__)


class BoomGateController:
    """Main controller for boom gate operations"""
    
    def __init__(self):
        self.gate = main_gate
        self.sound = sound_system
    
    async def open_gate_for_transaction(self, transaction_id=None, vehicle_plate=None):
        """
        Open gate for successful transaction
        Called from ANPR system when payment is successful
        """
        logger.info(f"Opening gate for transaction {transaction_id}, vehicle {vehicle_plate}")
        
        try:
            # Send WebSocket command to open gate
            success = await send_gate_command('auto_cycle', open_duration=5)
            
            if success:
                logger.info(f"Gate opened successfully for vehicle {vehicle_plate}")
                return True
            else:
                logger.error(f"Failed to open gate for vehicle {vehicle_plate}")
                return False
                
        except Exception as e:
            logger.error(f"Error opening gate for transaction: {str(e)}")
            return False
    
    async def emergency_close(self):
        """Emergency gate close"""
        try:
            await send_gate_command('emergency_stop')
            logger.warning("Emergency gate close activated")
            return True
        except Exception as e:
            logger.error(f"Emergency close error: {str(e)}")
            return False
    
    def get_gate_status(self):
        """Get current gate status"""
        return self.gate.get_status()
    
    def is_gate_operational(self):
        """Check if gate is operational"""
        return self.gate.is_operational
    
    def toggle_sound_effects(self):
        """Toggle sound effects on/off"""
        return self.sound.toggle_sound()


# Global controller instance
boom_gate_controller = BoomGateController()


# Convenience functions for use in other modules
async def open_gate_for_successful_payment(transaction_id, vehicle_plate):
    """
    Convenience function to open gate after successful payment
    Use this from the ANPR/payment processing code
    """
    return await boom_gate_controller.open_gate_for_transaction(
        transaction_id=transaction_id,
        vehicle_plate=vehicle_plate
    )


def get_gate_status():
    """Get current gate status"""
    return boom_gate_controller.get_gate_status()


async def emergency_stop_gate():
    """Emergency stop gate"""
    return await boom_gate_controller.emergency_close()
