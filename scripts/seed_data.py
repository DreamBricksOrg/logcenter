import asyncio, random
from bson import ObjectId
from src.db.utils import get_db
from src.core.security import hash_secret
from src.util.helpers import utcnow_iso

async def main():
    db = await get_db()
    # 1) Criar projeto
    proj = {
        "name": "Projeto Demo",
        "code": "demo-project",
        "description": "Projeto de demonstração",
        "config": {"exportFields": ["data.userId", "data.endpoint"]}
    }
    res_proj = await db["projects"].insert_one(proj)
    project_id = res_proj.inserted_id

    # 2) Criar usuário admin
    salt, pwd = hash_secret("adminpass")
    admin = {
        "email": "admin@example.com",
        "password_salt": salt,
        "password_hash": pwd,
        "role": "admin"
    }
    await db["users"].insert_one(admin)

    # 3) Gerar logs de exemplo
    levels = ["INFO", "WARN", "ERROR"]
    endpoints = ["/api/foo", "/api/bar", "/api/baz"]
    users = ["user1", "user2", "user3", "user4", "user5"]
    for i in range(50):
        log = {
            "uploadedAt": utcnow_iso(),
            "timestamp": utcnow_iso(),
            "status": f"{200 + random.randint(0, 5)} OK",
            "level": random.choice(levels),
            "message": f"Log de teste #{i}",
            "tags": ["env:test", f"user:{random.choice(users)}"],
            "data": {
                "userId": random.choice(users),
                "endpoint": random.choice(endpoints)
            },
            "request_id": f"req-{i}",
            "project_id": project_id
        }
        await db["logs"].insert_one(log)
    print("Seed completed: 1 project, 1 admin, 50 logs inserted.")

if __name__ == "__main__":
    asyncio.run(main())
