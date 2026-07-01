import asyncio
from app.database.requests import select_muscle_group

async def check():
    groups = await select_muscle_group()
    items = list(groups)
    print(f"Groups count: {len(items)}")
    for g in items:
        print(f"  - {g.id}: {g.name}")

asyncio.run(check())
