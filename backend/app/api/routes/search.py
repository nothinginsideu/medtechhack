from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from typing import List

from app.db.database import get_db
from app.models.service import Service
from app.models.price_item import PriceItem
from app.matching.normalizer import Normalizer

router = APIRouter()

@router.get("/search")
async def search_services(
    q: str = Query(..., min_length=2, description="Поисковой запрос (например: анализ крови)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Поиск по эталонным услугам и возврат цен в клиниках.
    """
    norm_query = Normalizer.normalize_text(q)
    
    # Очень простой ILIKE поиск по эталонному справочнику
    stmt = select(Service).where(Service.name_ru.ilike(f"%{norm_query}%")).options(
        joinedload(Service.price_items).joinedload(PriceItem.document)
    )
    
    result = await db.execute(stmt)
    services = result.unique().scalars().all()
    
    response = []
    for svc in services:
        prices = []
        for p_item in svc.price_items:
            # Подтягиваем инфу о партнере
            partner = p_item.partner
            prices.append({
                "partner_id": partner.id,
                "partner_name": partner.name,
                "price": p_item.price_resident_kzt,
                "price_nonresident": p_item.price_nonresident_kzt,
                "original_name": p_item.service_name_raw,
                "date": p_item.effective_date.strftime("%d %b %Y") if p_item.effective_date else None
            })
            
        response.append({
            "service_id": svc.id,
            "name": svc.name_ru,
            "specialty": svc.specialty,
            "prices": sorted(prices, key=lambda x: x["price"] if x["price"] else float('inf'))
        })
        
    return response
