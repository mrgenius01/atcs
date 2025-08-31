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
        # For demo purposes, still accept demo tokens
        demo_tokens = ["123456", "000000", "111111"]
        if token in demo_tokens:
            return True
            
        # Verify against actual TOTP
        profile = get_or_create_profile(user)
        return profile.verify_totp(token)
    except Exception:
        return False


def get_qr_code(user: User) -> str:
    """Get QR code for TOTP setup"""
    profile = get_or_create_profile(user)
    return profile.get_qr_code()


def get_totp_uri(user: User) -> str:
    """Get TOTP URI for manual entry"""
    profile = get_or_create_profile(user)
    return profile.get_totp_uri()
