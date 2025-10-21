import asyncio
from db.utils import get_db

import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))


async def main():
    db = await get_db()
    # Índice em project_id e timestamp (descendente)
    await db["logs"].create_index([("project_id", 1), ("timestamp", -1)])
    # Índice em level e timestamp (descendente)
    await db["logs"].create_index([("level", 1), ("timestamp", -1)])
    # Índice em data.userId (para filtros frequentes em data.*)
    await db["logs"].create_index([("data.userId", 1)])
    print("Indexes created.")

if __name__ == "__main__":
    asyncio.run(main())