from __future__ import annotations
import os
import hmac
import base64
import hashlib
from typing import Tuple

def gen_salt(n_bytes: int = 16) -> str:
    return base64.b64encode(os.urandom(n_bytes)).decode("utf-8")

def pbkdf2_hash(secret: str, salt_b64: str, iterations: int = 200_000) -> str:
    salt = base64.b64decode(salt_b64.encode("utf-8"))
    dk = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations)
    return base64.b64encode(dk).decode("utf-8")

def hash_secret(secret: str) -> Tuple[str, str]:
    """
    Retorna (salt_b64, hash_b64)
    """
    salt = gen_salt()
    h = pbkdf2_hash(secret, salt)
    return salt, h

def verify_secret(secret: str, salt_b64: str, hash_b64: str) -> bool:
    calc = pbkdf2_hash(secret, salt_b64)
    return hmac.compare_digest(calc, hash_b64)
