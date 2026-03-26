from __future__ import annotations
import os
import hmac
import base64
import hashlib
from typing import Tuple, Optional

from core.config import settings

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def gen_salt(n_bytes: int = 16) -> str:
    return base64.b64encode(os.urandom(n_bytes)).decode("utf-8")

def pbkdf2_hash(secret: str, salt_b64: str, iterations: int = 200_000) -> str:
    salt = base64.b64decode(salt_b64.encode("utf-8"))
    dk = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations)
    return base64.b64encode(dk).decode("utf-8")

def hash_secret(secret: str) -> Tuple[str, str]:
    """Retorna (salt_b64, hash_b64)."""
    salt = gen_salt()
    h = pbkdf2_hash(secret, salt)
    return salt, h

def verify_secret(secret: str, salt_b64: str, hash_b64: str) -> bool:
    calc = pbkdf2_hash(secret, salt_b64)
    return hmac.compare_digest(calc, hash_b64)

def _get_master_key() -> bytes:
    """
    Chave mestra do ambiente, em base64, com 32 bytes (AES-256). SECRET_KEY
    """
    b64u = settings.SECRET_KEY
    if not b64u:
        raise RuntimeError("Missing env SECRET_KEY")
    pad = '=' * (-len(b64u) % 4)
    key = base64.urlsafe_b64decode((b64u + pad).encode("utf-8"))

    if len(key) != 32:
        raise RuntimeError(
            f"SECRET_KEY must decode to 32 bytes, got {len(key)}"
        )
    return key

def encrypt_secret(plaintext: str, aad: Optional[bytes] = None) -> Tuple[str, str]:
    """
    Retorna (nonce_b64, ciphertext_b64) usando AES-GCM.
    """
    key = _get_master_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), aad)
    return base64.b64encode(nonce).decode("utf-8"), base64.b64encode(ct).decode("utf-8")

def decrypt_secret(nonce_b64: str, ciphertext_b64: str, aad: Optional[bytes] = None) -> str:
    key = _get_master_key()
    aesgcm = AESGCM(key)
    nonce = base64.b64decode(nonce_b64)
    ct = base64.b64decode(ciphertext_b64)
    pt = aesgcm.decrypt(nonce, ct, aad)
    return pt.decode("utf-8")
