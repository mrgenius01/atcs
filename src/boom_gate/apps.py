from django.apps import AppConfig


class BoomGateConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'boom_gate'
    verbose_name = 'Boom Gate System'
    
    def ready(self):
        """Initialize boom gate system when Django starts"""
        try:
            # Initialize sound system
            from .sound_system import sound_system
            sound_system.load_sounds()
            
            # Initialize gate
            from .models import main_gate
            main_gate.set_operational(True)
            
            print("🚧 Boom Gate System initialized successfully")
            
        except Exception as e:
            print(f"⚠️ Boom Gate System initialization warning: {e}")
            # Don't fail Django startup if boom gate has issues
