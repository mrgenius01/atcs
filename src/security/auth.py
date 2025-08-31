import base64
import hashlib
import pyotp
from django.contrib.auth.models import User

ISSUER = "SecureATCS"


def _derive_secret(username: str) -> str:
    # Demo-only: derive a base32 secret from a digest of the username
    digest = hashlib.sha1((username + "-totp-seed").encode()).digest()
    return base64.b32encode(digest).decode().rstrip("=")


def get_totp(user: User) -> pyotp.TOTP:
    secret = _derive_secret(user.username)
    return pyotp.TOTP(secret, issuer=ISSUER)


def provisioning_uri(user: User) -> str:
    totp = get_totp(user)
    return totp.provisioning_uri(name=user.username, issuer_name=ISSUER)


def verify_totp(user: User, token: str) -> bool:
    try:
        totp = get_totp(user)
        return totp.verify(token, valid_window=1)
    except Exception:
        return False
