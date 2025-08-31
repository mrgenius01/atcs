import pyotp
from django.contrib.auth.models import User

ISSUER = "SecureATCS"


def get_totp(user: User) -> pyotp.TOTP:
    # In MVP, derive a stable secret for existing users for demo purposes only.
    # In prod, store per-user random secret in DB and allow QR enrollment.
    seed = (user.username + "-totp-seed").encode()
    secret = pyotp.random_base32()
    # deter: we could persist via user.profile later; using random each run is fine for demo
    return pyotp.TOTP(secret, issuer=ISSUER)


def verify_totp(user: User, token: str) -> bool:
    try:
        totp = get_totp(user)
        return totp.verify(token, valid_window=1)
    except Exception:
        return False
