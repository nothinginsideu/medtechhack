from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from typing import Optional, List

from app.db.database import get_db
from app.models.service import Service
from app.models.price_item import PriceItem
from app.models.partner import Partner

router = APIRouter()

@router.get("/")
async def get_services(
    category: Optional[str] = Query(None, description="Фильтрация по категории услуги"),
    db: AsyncSession = Depends(get_db)
):
    """
    Список услуг справочника с фильтрацией по категории.
    """
    stmt = select(Service).where(Service.is_active == True)
    if category:
        stmt = stmt.where(Service.category.ilike(f"%{category}%"))
        
    result = await db.execute(stmt)
    services = result.scalars().all()
    
    return [
        {
            "id": s.id,
            "name": s.name_ru,
            "category": s.category,
            "specialty": s.specialty,
            "code": s.code,
            "icd_code": s.icd_code
        }
        for s in services
    ]

@router.get("/{service_id}/partners")
async def get_service_partners(
    service_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Список партнёров, оказывающих услугу, с ценами.
    """
    # Проверяем существование услуги
    svc_stmt = select(Service).where(Service.id == service_id, Service.is_active == True)
    svc_result = await db.execute(svc_stmt)
    service = svc_result.scalars().first()
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")
        
    # Ищем активные цены клиник для этой услуги
    price_stmt = (
        select(PriceItem)
        .where(
            PriceItem.service_id == service_id,
            PriceItem.is_active == True
        )
        .options(joinedload(PriceItem.partner))
    )
    
    price_result = await db.execute(price_stmt)
    price_items = price_result.scalars().all()
    
    partners_list = []
    for item in price_items:
        partner = item.partner
        if not partner or not partner.is_active:
            continue
            
        partners_list.append({
            "partner_id": partner.id,
            "partner_name": partner.name,
            "partner_city": partner.city,
            "partner_address": partner.address,
            "price_resident": float(item.price_resident_kzt) if item.price_resident_kzt is not None else None,
            "price_nonresident": float(item.price_nonresident_kzt) if item.price_nonresident_kzt is not None else None,
            "currency": item.currency_original.value if item.currency_original else "KZT",
            "effective_date": item.effective_date.strftime("%Y-%m-%d") if item.effective_date else None
        })
        
    # Сортируем от дешевых цен к дорогим
    partners_list = sorted(partners_list, key=lambda x: x["price_resident"] if x["price_resident"] is not None else float('inf'))
    
    return {
        "service": {
            "id": service.id,
            "name": service.name_ru,
            "category": service.category
        },
        "partners": partners_list
    }
