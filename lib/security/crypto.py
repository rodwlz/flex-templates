"""Fernet encryption/decryption for vault secrets."""
import json
from cryptography.fernet import Fernet, InvalidToken


def generate_key() -> str:
    """Generate a new Fernet key (URL-safe base64, 32 bytes)."""
    return Fernet.generate_key().decode()


def encrypt(data: dict, key: str) -> str:
    """Encrypt a dict to a string."""
    try:
        fernet = Fernet(key.encode())
        plaintext = json.dumps(data)
        ciphertext = fernet.encrypt(plaintext.encode())
        return ciphertext.decode()
    except (ValueError, TypeError) as e:
        raise RuntimeError(f"Encryption failed: {e}")


def decrypt(blob: str, key: str) -> dict:
    """Decrypt a string to a dict."""
    try:
        fernet = Fernet(key.encode())
        plaintext = fernet.decrypt(blob.encode()).decode()
        return json.loads(plaintext)
    except InvalidToken:
        raise RuntimeError("Invalid encryption key — cannot decrypt vault")
    except (ValueError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Decryption failed: {e}")
