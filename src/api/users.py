from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from bson import ObjectId
from db.utils import get_db
from models.user import UserCreate, UserUpdate, UserOut, UserListResponse
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


@router.get("/", response_model=UserListResponse)
async def list_users(
    principal=Depends(require_principal),

    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=9, ge=1, le=100),

    email: Optional[str] = Query(default=None, description="Filtra por email (regex, case-insensitive)"),
    name: Optional[str] = Query(default=None, description="Filtra por name (regex, case-insensitive)"),
    role: Optional[str] = Query(default=None, description="admin|client"),
    project_code: Optional[str] = Query(default=None, description="Usuários que tenham este project_code em project_codes"),
):
    if principal["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")

    db = await get_db()

    query: dict = {}

    if email:
        query["email"] = {"$regex": email, "$options": "i"}

    if name:
        query["name"] = {"$regex": name, "$options": "i"}

    if role:
        if role not in ("admin", "client"):
            raise HTTPException(status_code=422, detail="role must be 'admin' or 'client'")
        query["role"] = role

    if project_code:
        query["project_codes"] = project_code

    projection = {"email": 1, "name": 1, "role": 1, "project_codes": 1}

    total = await db["users"].count_documents(query)

    cursor = (
        db["users"]
        .find(query, projection)
        .sort([("email", 1)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    docs = await cursor.to_list(length=page_size)

    items = []
    for u in docs:
        items.append({
            "_id": str(u["_id"]),
            "email": u["email"],
            "name": u["name"],
            "role": u["role"],
            "project_codes": u.get("project_codes", []) or [],
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
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
