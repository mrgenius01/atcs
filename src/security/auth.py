import pyotp
from django.contrib.auth.models import User

ISSUER = "SecureATCS"


def get_or_create_profile(user):
    """Get or create user profile with TOTP secret"""
    from dashboard.models import UserProfile
    profile, created = UserProfile.objects.get_or_create(user=user)
    if created or not profile.totp_secret:
        profile.generate_totp_secret()
    return profile


def verify_totp(user: User, token: str) -> bool:
    """Verify TOTP token against user's secret"""
    try:
        if not token:
            return False
            
        # Verify against actual TOTP only (no more dummy tokens)
        profile = get_or_create_profile(user)
        
        # If TOTP is not enabled, always return False for token verification
        if not profile.totp_enabled:
            return False
            
        return profile.verify_totp(token)
    except Exception as e:
        return False


def get_qr_code(user: User) -> str:
    """Get QR code for TOTP setup"""
    profile = get_or_create_profile(user)
    return profile.get_qr_code()


def get_totp_uri(user: User) -> str:
    """Get TOTP URI for manual entry"""
    profile = get_or_create_profile(user)
    return profile.get_totp_uri()
