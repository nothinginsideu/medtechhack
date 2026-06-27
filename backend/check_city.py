import asyncio
from sqlalchemy.future import select
from app.db.database import SessionLocal
from app.models.partner import Partner

async def main():
    async with SessionLocal() as db:
        stmt = select(Partner).where(Partner.name.ilike("%Клиника 1%"))
        res = await db.execute(stmt)
        partners = res.scalars().all()
        for p in partners:
            print(f"Partner ID: {p.id} | Name: {p.name} | City: {p.city} | Active: {p.is_active}")

if __name__ == "__main__":
    asyncio.run(main())
