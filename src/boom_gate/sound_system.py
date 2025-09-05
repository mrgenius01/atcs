"""
Sound System for Boom Gate
Handles all audio effects for gate operations
"""
import pygame
import asyncio
import logging
import os
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class SoundSystem:
    def __init__(self):
        self.initialized = False
        self.sound_enabled = True
        self.sounds = {}
        self.current_channel = None
        self.sound_dir = Path(__file__).parent / "sounds"
        
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.initialized = True
            logger.info("Sound system initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize sound system: {str(e)}")
            self.sound_enabled = False
    
    def load_sounds(self):
        """Load all sound effects"""
        if not self.initialized:
            return
            
        sound_files = {
            "motor_start": "motor_start.wav",
            "motor_run": "motor_run.wav", 
            "motor_stop": "motor_stop.wav",
            "warning_beep": "warning_beep.wav",
            "gate_open": "gate_open.wav",
            "gate_close": "gate_close.wav",
            "error_sound": "error_sound.wav"
        }
        
        # Create sounds directory if it doesn't exist
        self.sound_dir.mkdir(exist_ok=True)
        
        for sound_name, filename in sound_files.items():
            sound_path = self.sound_dir / filename
            
            # Create placeholder sound files if they don't exist
            if not sound_path.exists():
                self._create_placeholder_sound(sound_path, sound_name)
            
            try:
                self.sounds[sound_name] = pygame.mixer.Sound(str(sound_path))
                logger.info(f"Loaded sound: {sound_name}")
            except Exception as e:
                logger.error(f"Failed to load sound {sound_name}: {str(e)}")
    
    def _create_placeholder_sound(self, sound_path, sound_name):
        """Create a simple placeholder sound using pygame"""
        if not self.initialized:
            return
            
        try:
            # Generate simple sound based on type
            sample_rate = 22050
            duration = 0.5  # seconds
            
            if sound_name in ["motor_start", "motor_run", "motor_stop"]:
                # Low frequency motor sound
                frequency = 120
                duration = 1.0 if sound_name == "motor_run" else 0.5
            elif sound_name == "warning_beep":
                # High pitched beep
                frequency = 800
                duration = 0.3
            elif sound_name in ["gate_open", "gate_close"]:
                # Mechanical sound
                frequency = 200
                duration = 0.8
            else:
                # Error sound
                frequency = 400
                duration = 0.2
            
            # Create simple sine wave
            import numpy as np
            frames = int(duration * sample_rate)
            arr = np.sin(2 * np.pi * frequency * np.linspace(0, duration, frames))
            arr = (arr * 32767).astype(np.int16)
            arr = np.repeat(arr.reshape(frames, 1), 2, axis=1)
            
            # Save as wav file
            pygame.sndarray.make_sound(arr).set_volume(0.3)
            
            # Create a simple click sound for now (pygame doesn't easily save to file)
            logger.info(f"Created placeholder for {sound_name}")
            
        except Exception as e:
            logger.error(f"Failed to create placeholder sound {sound_name}: {str(e)}")
    
    def play_sound(self, sound_name, loop=False):
        """Play a sound effect"""
        if not self.sound_enabled or not self.initialized:
            return
            
        if sound_name not in self.sounds:
            logger.warning(f"Sound {sound_name} not found")
            return
            
        try:
            if loop:
                self.current_channel = self.sounds[sound_name].play(-1)
            else:
                self.sounds[sound_name].play()
            logger.debug(f"Playing sound: {sound_name}")
        except Exception as e:
            logger.error(f"Failed to play sound {sound_name}: {str(e)}")
    
    def stop_sound(self):
        """Stop currently playing looped sound"""
        if self.current_channel:
            try:
                self.current_channel.stop()
                self.current_channel = None
            except Exception as e:
                logger.error(f"Failed to stop sound: {str(e)}")
    
    def stop_all_sounds(self):
        """Stop all sounds"""
        if self.initialized:
            try:
                pygame.mixer.stop()
                self.current_channel = None
            except Exception as e:
                logger.error(f"Failed to stop all sounds: {str(e)}")
    
    async def play_gate_opening_sequence(self):
        """Play complete gate opening sound sequence"""
        if not self.sound_enabled:
            return
            
        try:
            # Warning beeps
            for _ in range(3):
                self.play_sound("warning_beep")
                await asyncio.sleep(0.5)
            
            # Motor start
            self.play_sound("motor_start")
            await asyncio.sleep(0.5)
            
            # Motor running (looped)
            self.play_sound("motor_run", loop=True)
            await asyncio.sleep(2.0)
            
            # Motor stop
            self.stop_sound()
            self.play_sound("motor_stop")
            await asyncio.sleep(0.5)
            
            # Gate open confirmation
            self.play_sound("gate_open")
            
        except Exception as e:
            logger.error(f"Error in gate opening sequence: {str(e)}")
    
    async def play_gate_closing_sequence(self):
        """Play complete gate closing sound sequence"""
        if not self.sound_enabled:
            return
            
        try:
            # Warning beeps
            for _ in range(2):
                self.play_sound("warning_beep")
                await asyncio.sleep(0.5)
            
            # Motor start
            self.play_sound("motor_start")
            await asyncio.sleep(0.5)
            
            # Motor running (looped)
            self.play_sound("motor_run", loop=True)
            await asyncio.sleep(2.0)
            
            # Motor stop
            self.stop_sound()
            self.play_sound("motor_stop")
            await asyncio.sleep(0.5)
            
            # Gate close confirmation
            self.play_sound("gate_close")
            
        except Exception as e:
            logger.error(f"Error in gate closing sequence: {str(e)}")
    
    def play_error_sound(self):
        """Play error sound"""
        if self.sound_enabled:
            self.play_sound("error_sound")
    
    def set_volume(self, volume=0.7):
        """Set master volume (0.0 to 1.0)"""
        if self.initialized:
            try:
                for sound in self.sounds.values():
                    sound.set_volume(volume)
            except Exception as e:
                logger.error(f"Failed to set volume: {str(e)}")
    
    def toggle_sound(self):
        """Toggle sound on/off"""
        self.sound_enabled = not self.sound_enabled
        if not self.sound_enabled:
            self.stop_all_sounds()
        logger.info(f"Sound {'enabled' if self.sound_enabled else 'disabled'}")
        return self.sound_enabled


# Global sound system instance
sound_system = SoundSystem()

# Load sounds on import
try:
    sound_system.load_sounds()
except Exception as e:
    logger.error(f"Failed to load sounds on import: {str(e)}")
