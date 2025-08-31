from src.security.encryption import encrypt, decrypt

def test_encrypt_decrypt_roundtrip():
    data = b"secret"
    blob = encrypt(data)
    assert blob != data
    plain = decrypt(blob)
    assert plain == data
