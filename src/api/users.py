from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from bson import ObjectId
from db.utils import get_db
from models.user import UserCreate, UserUpdate, UserOut
from core.security import hash_secret
from core.auth import require_principal

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserOut, status_code=201)
async def create_user(payload: UserCreate, principal=Depends(require_principal)):
    if principal["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")

    db = await get_db()
    email = payload.email.lower().strip()

    if await db["users"].find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email already exists")

    salt, hsh = hash_secret(payload.password_plain)
    doc = {
        "email": email,
        "name": payload.name.strip(),
        "role": payload.role,
        "password_salt": salt,
        "password_hash": hsh,
        "project_codes": payload.project_codes or [],
    }

    res = await db["users"].insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return {
        "_id": doc["_id"],
        "email": doc["email"],
        "name": doc["name"],
        "role": doc["role"],
        "project_codes": doc["project_codes"],
    }

@router.get("/", response_model=List[UserOut])
async def list_users(principal=Depends(require_principal)):
    if principal["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")

    db = await get_db()
    cursor = db["users"].find({}, {"email": 1, "name": 1, "role": 1, "project_codes": 1})
    docs = await cursor.to_list(length=1000)

    out: List[UserOut] = []
    for u in docs:
        out.append({
            "_id": str(u["_id"]),
            "email": u["email"],
            "name": u["name"],
            "role": u["role"],
            "project_codes": u.get("project_codes", []),
        })
    return out

@router.patch("/{user_id}", response_model=UserOut)
async def update_user(user_id: str, payload: UserUpdate, principal=Depends(require_principal)):
    if principal["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")

    db = await get_db()
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid id")

    updates = {}
    if payload.name is not None:
        updates["name"] = payload.name.strip()
    if payload.role is not None:
        updates["role"] = payload.role
    if payload.project_codes is not None:
        updates["project_codes"] = payload.project_codes
    if payload.password_plain:
        salt, hsh = hash_secret(payload.password_plain)
        updates["password_salt"] = salt
        updates["password_hash"] = hsh

    if not updates:
        raise HTTPException(status_code=400, detail="No changes")

    res = await db["users"].update_one({"_id": oid}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    u = await db["users"].find_one({"_id": oid}, {"email": 1, "name": 1, "role": 1, "project_codes": 1})
    return {
        "_id": str(u["_id"]),
        "email": u["email"],
        "name": u["name"],
        "role": u["role"],
        "project_codes": u.get("project_codes", []),
    }

@router.delete("/{user_id}", status_code=204)
async def delete_user(user_id: str, principal=Depends(require_principal)):
    if principal["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")

    db = await get_db()
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid id")

    res = await db["users"].delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return None
