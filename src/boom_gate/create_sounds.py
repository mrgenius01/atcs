"""
Create simple placeholder sound files
"""
import wave
import struct
import math

def create_simple_wav(filename, frequency, duration, sample_rate=22050):
    """Create a simple sine wave WAV file"""
    with wave.open(filename, 'w') as wav_file:
        # Set parameters
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        # Generate sine wave
        for i in range(int(sample_rate * duration)):
            # Calculate sine wave value
            value = math.sin(2 * math.pi * frequency * i / sample_rate)
            # Convert to 16-bit integer
            data = struct.pack('<h', int(value * 30000))
            wav_file.writeframes(data)

def create_all_sounds():
    """Create all boom gate sound files"""
    sounds_dir = "boom_gate/sounds"
    
    sounds = {
        "motor_start.wav": (120, 0.5),
        "motor_run.wav": (100, 0.8),
        "motor_stop.wav": (80, 0.3),
        "warning_beep.wav": (800, 0.2),
        "gate_open.wav": (200, 0.4),
        "gate_close.wav": (150, 0.4),
        "error_sound.wav": (400, 0.3)
    }
    
    for filename, (freq, duration) in sounds.items():
        filepath = f"{sounds_dir}/{filename}"
        try:
            create_simple_wav(filepath, freq, duration)
            print(f"✓ Created: {filename}")
        except Exception as e:
            print(f"❌ Failed to create {filename}: {e}")
    
    print("🔊 All sound files created!")

if __name__ == "__main__":
    print("🎵 Creating boom gate sound files...")
    create_all_sounds()
