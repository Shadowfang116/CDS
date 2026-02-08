"""Encryption service for webhook secrets using Fernet."""
import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings


def _get_encryption_key() -> bytes:
    """Get or derive encryption key from config."""
    if settings.INTEGRATIONS_ENCRYPTION_KEY:
        # If provided, use it directly (should be base64-encoded Fernet key)
        try:
            return base64.urlsafe_b64decode(settings.INTEGRATIONS_ENCRYPTION_KEY.encode())
        except Exception:
            # If not valid base64, derive from it
            pass
    
    # Derive from APP_SECRET_KEY
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"bank_diligence_webhook_secret",
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.APP_SECRET_KEY.encode()))
    return key


def encrypt_string(plaintext: str) -> str:
    """
    Encrypt a string (webhook secret).
    Returns base64-encoded ciphertext.
    Raises ValueError if cryptography is not available.
    """
    try:
        key = _get_encryption_key()
        f = Fernet(key)
        encrypted = f.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    except ImportError:
        raise ValueError("cryptography library is required for webhook secret encryption")
    except Exception as e:
        raise ValueError(f"Encryption failed: {str(e)}")


def decrypt_string(ciphertext: str) -> str:
    """
    Decrypt a string (webhook secret).
    Raises ValueError if decryption fails.
    """
    try:
        key = _get_encryption_key()
        f = Fernet(key)
        encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode())
        decrypted = f.decrypt(encrypted_bytes)
        return decrypted.decode()
    except ImportError:
        raise ValueError("cryptography library is required for webhook secret decryption")
    except Exception as e:
        raise ValueError(f"Decryption failed: {str(e)}")


def generate_secret() -> str:
    """Generate a random webhook secret (32 bytes, base64-encoded)."""
    import secrets
    secret_bytes = secrets.token_bytes(32)
    return base64.urlsafe_b64encode(secret_bytes).decode()


def get_secret_preview(secret: str) -> str:
    """Get last 4 characters of secret for display."""
    return secret[-4:] if len(secret) >= 4 else secret

