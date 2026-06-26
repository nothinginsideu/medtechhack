from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

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
    Поиск по эталонным услугам и возврат цен в клиниках. Возвращает полные данные партнера для модалки.
    """
    norm_query = Normalizer.normalize_text(q)
    
    # Используем ILIKE для простого поиска, но на фронтенде убрали моки, так что пустой поиск не сломается.
    # В идеале здесь должен быть полнотекстовый поиск PostgreSQL или RapidFuzz по синонимам.
    # Для целей MVP ILIKE по нормализованному запросу работает адекватно (если нормализация не вернула пустую строку).
    if not norm_query:
        return []

    stmt = select(Service).where(Service.name_ru.ilike(f"%{norm_query}%")).options(
        joinedload(Service.price_items).joinedload(PriceItem.document),
        joinedload(Service.price_items).joinedload(PriceItem.partner)
    )
    
    result = await db.execute(stmt)
    services = result.unique().scalars().all()
    
    response = []
    for svc in services:
        prices = []
        for p_item in svc.price_items:
            if not p_item.is_active:
                continue
            
            partner = p_item.partner
            prices.append({
                "partner_id": partner.id,
                "partner_name": partner.name,
                "partner_address": partner.address,
                "partner_city": partner.city,
                "partner_bin": partner.bin,
                "partner_phone": partner.contact_phone,
                "price_resident": p_item.price_resident_kzt,
                "price_nonresident": p_item.price_nonresident_kzt,
                "price_original": p_item.price_original,
                "currency_original": p_item.currency_original.value if p_item.currency_original else "KZT",
                "original_name": p_item.service_name_raw,
                "date": p_item.effective_date.strftime("%d %b %Y") if p_item.effective_date else None
            })
            
        if prices: # Только услуги, у которых есть хотя бы одна активная цена
            response.append({
                "service_id": svc.id,
                "name": svc.name_ru,
                "specialty": svc.specialty,
                "prices": sorted(prices, key=lambda x: x["price_resident"] if x["price_resident"] else float('inf'))
            })
        
    return response

@router.get("/partner/{partner_id}")
async def get_partner_details(partner_id: int, db: AsyncSession = Depends(get_db)):
    """
    Получение всех актуальных цен для конкретного партнера (для модалки прайс-листа).
    """
    from app.models.partner import Partner
    stmt = select(Partner).where(Partner.id == partner_id)
    result = await db.execute(stmt)
    partner = result.scalars().first()
    
    if not partner:
        return None
        
    price_stmt = select(PriceItem).where(
        PriceItem.partner_id == partner_id,
        PriceItem.is_active == True
    ).options(joinedload(PriceItem.service))
    
    price_result = await db.execute(price_stmt)
    prices = price_result.scalars().all()
    
    price_list = []
    for p in prices:
        price_list.append({
            "service_name": p.service.name_ru if p.service else p.service_name_raw,
            "specialty": p.service.specialty if p.service else "Общее",
            "price_resident": p.price_resident_kzt,
            "price_nonresident": p.price_nonresident_kzt,
            "price_original": p.price_original,
            "currency_original": p.currency_original.value if p.currency_original else "KZT",
            "date": p.effective_date.strftime("%d %b %Y") if p.effective_date else None
        })
        
    return {
        "id": partner.id,
        "name": partner.name,
        "address": partner.address,
        "city": partner.city,
        "bin": partner.bin,
        "phone": partner.contact_phone,
        "email": partner.contact_email,
        "price_list": price_list
    }
