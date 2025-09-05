# 🚧 Boom Gate System

A Python-based boom gate simulation with sound effects for the Secure ATCS (Automatic Toll Collection System).

## Features

- **Real-time Control**: WebSocket-based boom gate control
- **Sound Effects**: Realistic motor sounds, warning beeps, and gate operation audio
- **Visual Simulation**: CSS-animated gate representation
- **Auto Cycle**: Automatic open/close sequence after successful payments
- **Emergency Stop**: Safety feature for immediate gate control
- **Status Monitoring**: Real-time gate status and activity logging

## Components

### Core Modules

- `models.py` - Boom gate state management and operations
- `sound_system.py` - pygame-based audio engine for realistic sounds
- `consumers.py` - WebSocket consumer for real-time gate control
- `controller.py` - Main interface for ANPR system integration
- `views.py` - Django views for gate control panel
- `routing.py` - WebSocket URL routing

### Installation

1. Install required packages:
```bash
pip install pygame channels channels-redis
```

2. Add to Django `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    # ... other apps
    'channels',
    'boom_gate',
]
```

3. Configure ASGI in `settings.py`:
```python
ASGI_APPLICATION = "asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}
```

4. Include URLs in main `urls.py`:
```python
path("boom-gate/", include('boom_gate.urls')),
```

### Usage

#### Web Interface
Access the boom gate control panel at: `http://localhost:8000/boom-gate/`

#### Integration with ANPR System
The boom gate automatically opens when a payment is successful:

```python
from boom_gate.controller import open_gate_for_successful_payment

# Called automatically after successful transaction
await open_gate_for_successful_payment(
    transaction_id="12345",
    vehicle_plate="ABC-123D"
)
```

#### WebSocket Commands

Connect to: `ws://localhost:8000/ws/boom-gate/`

Available commands:
```json
{"command": "open_gate"}
{"command": "close_gate"}  
{"command": "auto_cycle", "open_duration": 5}
{"command": "emergency_stop"}
{"command": "toggle_sound"}
{"command": "get_status"}
```

#### Sound Effects

The system includes realistic audio:
- Motor start/run/stop sounds
- Warning beeps before operation
- Gate confirmation sounds
- Error notifications

Audio can be toggled on/off via the web interface or API.

### Configuration

#### Sound Settings
- Sounds are automatically generated if not present
- Volume can be adjusted programmatically
- Sound system gracefully degrades if pygame unavailable

#### Gate Timing
- Default operation duration: 3 seconds
- Auto-close delay: 5 seconds (configurable)
- Emergency stop: Immediate

### Security Features

- WebSocket authentication via Django auth middleware
- Emergency stop capability
- Operational status monitoring
- Audit logging for all gate operations

### Development

#### Running the System
```bash
# Start Django with ASGI support
python manage.py runserver
```

#### Testing WebSocket Connection
```javascript
const socket = new WebSocket('ws://localhost:8000/ws/boom-gate/');
socket.onopen = () => console.log('Connected');
socket.send('{"command": "get_status"}');
```

### Integration Points

The boom gate system integrates with:

1. **ANPR Processing** - Automatic gate opening after successful payments
2. **Dashboard System** - Real-time status monitoring
3. **Audit System** - Gate operation logging
4. **Security Module** - Authentication and access control

### Architecture

```
┌─────────────────┐    WebSocket    ┌──────────────────┐
│   Web Interface │ ◄─────────────► │ Django Channels  │
└─────────────────┘                 └──────────────────┘
                                             │
                                             ▼
┌─────────────────┐                 ┌──────────────────┐
│  ANPR System    │────────────────►│  Gate Controller │
└─────────────────┘                 └──────────────────┘
                                             │
                                             ▼
┌─────────────────┐                 ┌──────────────────┐
│  Sound System   │◄────────────────│   Gate Model     │
└─────────────────┘                 └──────────────────┘
```

This boom gate system provides a fun and interactive enhancement to the toll collection system with realistic sound effects and smooth WebSocket-based control! 🔊🚪
