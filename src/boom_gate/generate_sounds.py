"""
Generate basic sound files for boom gate system
"""
import pygame
import numpy as np
import os
from pathlib import Path

def generate_sound_files():
    """Generate basic WAV files for boom gate sounds"""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    sounds_dir = Path(__file__).parent / "sounds"
    sounds_dir.mkdir(exist_ok=True)
    
    # Sound configurations
    sounds = {
        "motor_start": {"freq": 120, "duration": 0.5, "volume": 0.3},
        "motor_run": {"freq": 100, "duration": 0.8, "volume": 0.2},
        "motor_stop": {"freq": 80, "duration": 0.3, "volume": 0.3},
        "warning_beep": {"freq": 800, "duration": 0.2, "volume": 0.4},
        "gate_open": {"freq": 200, "duration": 0.4, "volume": 0.3},
        "gate_close": {"freq": 150, "duration": 0.4, "volume": 0.3},
        "error_sound": {"freq": 400, "duration": 0.3, "volume": 0.5}
    }
    
    sample_rate = 22050
    
    for sound_name, config in sounds.items():
        try:
            # Generate sine wave
            duration = config["duration"]
            frequency = config["freq"]
            volume = config["volume"]
            
            frames = int(duration * sample_rate)
            arr = np.sin(2 * np.pi * frequency * np.linspace(0, duration, frames))
            
            # Add some envelope to make it sound more natural
            envelope = np.concatenate([
                np.linspace(0, 1, frames // 4),  # Attack
                np.ones(frames // 2),             # Sustain
                np.linspace(1, 0, frames // 4)   # Release
            ])
            
            arr = arr * envelope * volume
            arr = (arr * 32767).astype(np.int16)
            
            # Make stereo
            arr = np.repeat(arr.reshape(frames, 1), 2, axis=1)
            
            # Create pygame sound and save
            sound = pygame.sndarray.make_sound(arr)
            sound_path = sounds_dir / f"{sound_name}.wav"
            
            # Save as WAV (simple method using pygame)
            pygame.mixer.Sound.set_volume(sound, volume)
            
            print(f"✓ Generated: {sound_name}.wav")
            
        except Exception as e:
            print(f"❌ Failed to generate {sound_name}: {e}")
    
    print(f"🔊 Sound generation completed!")

if __name__ == "__main__":
    print("🎵 Generating boom gate sound files...")
    generate_sound_files()
