"""
Boom Gate Model
Handles boom gate state and operations
"""
import asyncio
import logging
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class GateState(Enum):
    CLOSED = "closed"
    OPENING = "opening"
    OPEN = "open"
    CLOSING = "closing"
    ERROR = "error"


class BoomGate:
    def __init__(self, gate_id="main_gate"):
        self.gate_id = gate_id
        self.state = GateState.CLOSED
        self.last_action_time = datetime.now()
        self.is_operational = True
        self.operation_duration = 3  # seconds for full open/close cycle
        
    def get_status(self):
        """Get current gate status"""
        return {
            "gate_id": self.gate_id,
            "state": self.state.value,
            "last_action": self.last_action_time.isoformat(),
            "operational": self.is_operational
        }
    
    async def open_gate(self):
        """Open the boom gate"""
        if not self.is_operational:
            logger.error(f"Gate {self.gate_id} is not operational")
            return False
            
        if self.state in [GateState.OPEN, GateState.OPENING]:
            logger.info(f"Gate {self.gate_id} already open or opening")
            return True
            
        logger.info(f"Opening gate {self.gate_id}")
        self.state = GateState.OPENING
        self.last_action_time = datetime.now()
        
        # Simulate gate opening duration
        await asyncio.sleep(self.operation_duration)
        
        self.state = GateState.OPEN
        logger.info(f"Gate {self.gate_id} opened successfully")
        return True
    
    async def close_gate(self):
        """Close the boom gate"""
        if not self.is_operational:
            logger.error(f"Gate {self.gate_id} is not operational")
            return False
            
        if self.state in [GateState.CLOSED, GateState.CLOSING]:
            logger.info(f"Gate {self.gate_id} already closed or closing")
            return True
            
        logger.info(f"Closing gate {self.gate_id}")
        self.state = GateState.CLOSING
        self.last_action_time = datetime.now()
        
        # Simulate gate closing duration
        await asyncio.sleep(self.operation_duration)
        
        self.state = GateState.CLOSED
        logger.info(f"Gate {self.gate_id} closed successfully")
        return True
    
    async def auto_cycle(self, open_duration=5):
        """Automatically open gate and close after specified duration"""
        try:
            # Open the gate
            await self.open_gate()
            
            # Keep gate open for specified duration
            await asyncio.sleep(open_duration)
            
            # Close the gate
            await self.close_gate()
            
            return True
            
        except Exception as e:
            logger.error(f"Error in auto cycle for gate {self.gate_id}: {str(e)}")
            self.state = GateState.ERROR
            return False
    
    def emergency_stop(self):
        """Emergency stop - immediately set to closed state"""
        logger.warning(f"Emergency stop activated for gate {self.gate_id}")
        self.state = GateState.CLOSED
        self.last_action_time = datetime.now()
    
    def set_operational(self, operational=True):
        """Set gate operational status"""
        self.is_operational = operational
        logger.info(f"Gate {self.gate_id} operational status: {operational}")


# Global gate instance
main_gate = BoomGate("main_gate")
