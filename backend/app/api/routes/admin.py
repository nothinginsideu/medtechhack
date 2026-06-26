from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.db.database import get_db
from app.models.price_item import PriceItem
from app.models.price_document import ParseStatus

router = APIRouter()

@router.get("/unmatched")
async def get_unmatched_items(db: AsyncSession = Depends(get_db)):
    """
    Получение списка позиций прайса, которые ИИ не смог сопоставить (уверенность < 85%) 
    или где зафиксирована аномалия.
    """
    stmt = select(PriceItem).where(
        (PriceItem.is_verified == False) &
        (
            (PriceItem.match_score < 85.0) | 
            (PriceItem.verification_note != None) # Аномалии помечаются заметкой
        )
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    response = []
    for item in items:
        response.append({
            "id": item.id,
            "raw_name": item.service_name_raw,
            "suggested_service_id": item.service_id,
            "confidence": item.match_score,
            "price": item.price_resident_kzt,
            "status": "anomaly" if item.verification_note else "unmatched",
            "note": item.verification_note
        })
    return response

@router.post("/match/{item_id}")
async def match_item(item_id: int, service_id: int, db: AsyncSession = Depends(get_db)):
    """
    Ручное подтверждение оператором связи позиции прайса с эталонной услугой.
    """
    stmt = select(PriceItem).where(PriceItem.id == item_id)
    result = await db.execute(stmt)
    item = result.scalars().first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Позиция не найдена")
        
    item.service_id = service_id
    item.is_verified = True
    item.verification_note = "Ручное сопоставление оператором"
    
    await db.commit()
    return {"status": "ok", "message": "Связь подтверждена"}
