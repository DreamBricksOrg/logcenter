import hmac
import hashlib
import secrets
from typing import Optional, Dict, Any
from bson import ObjectId
from db.utils import get_db
from core.config import settings
from core.security import verify_secret

ADMIN_KEY_SEPARATOR = "."

def _hmac_admin_key(secret_key: str, rnd: str) -> str:
    return hmac.new(secret_key.encode(), rnd.encode(), hashlib.sha256).hexdigest()

async def generate_admin_key(secret_key: Optional[str] = None) -> str:
    secret_key = secret_key or settings.SECRET_KEY
    rnd = secrets.token_hex(16)
    mac = _hmac_admin_key(secret_key, rnd)
    return f"{rnd}{ADMIN_KEY_SEPARATOR}{mac}"

async def is_admin_key(key: str, secret_key: Optional[str] = None) -> bool:
    secret_key = secret_key or settings.SECRET_KEY
    if ADMIN_KEY_SEPARATOR not in key:
        return False
    try:
        rnd, mac = key.split(ADMIN_KEY_SEPARATOR, 1)
    except ValueError:
        return False
    expected = _hmac_admin_key(secret_key, rnd)
    return hmac.compare_digest(mac, expected)

async def login_admin(email: str, password: str) -> Optional[str]:
    db = await get_db()
    user = await db["users"].find_one({"email": email.lower().strip()})
    if not user:
        return None
    if user.get("role") != "admin":
        return None
    salt = user.get("password_salt")
    hsh = user.get("password_hash")
    if not (salt and hsh and verify_secret(password, salt, hsh)):
        return None
    return await generate_admin_key()

async def validate_project_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    from core.security import verify_secret
    db = await get_db()
    async for p in db["projects"].find({}, {"_id": 1, "code": 1, "api_key_salt": 1, "api_key_hash": 1}):
        salt = p.get("api_key_salt")
        hsh = p.get("api_key_hash")
        if salt and hsh and verify_secret(api_key, salt, hsh):
            return {
                "project_id": str(p["_id"]),
                "project_code": p["code"],
                "role": "client"
            }
    return None