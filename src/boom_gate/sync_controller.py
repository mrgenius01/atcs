"""
Simple boom gate trigger for Django views
Works without WebSocket dependencies
"""
import logging
import threading
import asyncio
from .models import main_gate
from .sound_system import sound_system

logger = logging.getLogger(__name__)


def trigger_gate_sync(transaction_id, vehicle_plate, open_duration=5):
    """
    Synchronous boom gate trigger for Django views
    Runs the gate operation in a background thread
    """
    def run_gate_operation():
        """Run gate operation with its own event loop"""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def gate_sequence():
                """Complete gate operation sequence"""
                try:
                    logger.info(f"Opening boom gate for transaction {transaction_id}, plate {vehicle_plate}")
                    
                    # Play opening sound sequence
                    if sound_system.sound_enabled:
                        await sound_system.play_gate_opening_sequence()
                    
                    # Open gate
                    success = await main_gate.open_gate()
                    if not success:
                        logger.error("Failed to open gate")
                        return False
                    
                    # Keep open for specified duration
                    logger.info(f"Gate open, waiting {open_duration} seconds...")
                    await asyncio.sleep(open_duration)
                    
                    # Play closing sound sequence  
                    if sound_system.sound_enabled:
                        await sound_system.play_gate_closing_sequence()
                    
                    # Close gate
                    success = await main_gate.close_gate()
                    if success:
                        logger.info(f"Boom gate cycle completed for {vehicle_plate}")
                        return True
                    else:
                        logger.error("Failed to close gate")
                        return False
                        
                except Exception as e:
                    logger.error(f"Error in gate sequence: {str(e)}")
                    return False
            
            # Run the gate sequence
            result = loop.run_until_complete(gate_sequence())
            return result
            
        except Exception as e:
            logger.error(f"Error in gate operation thread: {str(e)}")
            return False
        finally:
            try:
                loop.close()
            except:
                pass
    
    try:
        # Start gate operation in background thread
        gate_thread = threading.Thread(
            target=run_gate_operation,
            name=f"BoomGate-{transaction_id}",
            daemon=True
        )
        gate_thread.start()
        
        logger.info(f"Boom gate operation started for transaction {transaction_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to start boom gate operation: {str(e)}")
        return False


def get_gate_status_sync():
    """Get current gate status synchronously"""
    try:
        return main_gate.get_status()
    except Exception as e:
        logger.error(f"Error getting gate status: {str(e)}")
        return {
            'gate_id': 'main_gate',
            'state': 'error',
            'operational': False,
            'error': str(e)
        }


def emergency_stop_sync():
    """Emergency stop gate synchronously"""
    try:
        main_gate.emergency_stop()
        sound_system.stop_all_sounds()
        sound_system.play_error_sound()
        logger.warning("Emergency stop activated")
        return True
    except Exception as e:
        logger.error(f"Error in emergency stop: {str(e)}")
        return False
