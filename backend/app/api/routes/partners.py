from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db
from app.models.partner import Partner

router = APIRouter()

@router.get("/")
async def get_partners(db: AsyncSession = Depends(get_db)):
    """
    Возвращает список всех клиник (партнеров)
    """
    stmt = select(Partner)
    result = await db.execute(stmt)
    partners = result.scalars().all()
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "city": p.city,
            "address": p.address,
            "phone": p.contact_phone,
            "email": p.contact_email
        }
        for p in partners
    ]
