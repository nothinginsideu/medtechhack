from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_db
from app.models.partner import Partner

router = APIRouter()

from typing import Optional
from sqlalchemy.orm import joinedload

@router.get("/")
async def get_partners(
    city: Optional[str] = None,
    status: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Возвращает список всех клиник (партнеров) с опциональной фильтрацией
    """
    stmt = select(Partner)
    
    if city:
        stmt = stmt.where(Partner.city.ilike(f"%{city}%"))
    if status is not None:
        stmt = stmt.where(Partner.is_active == status)
        
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

@router.get("/{partner_id}/services")
async def get_partner_services(partner_id: int, db: AsyncSession = Depends(get_db)):
    """
    Возвращает полный актуальный прайс-лист конкретного партнера.
    """
    from app.models.price_item import PriceItem
    
    stmt = select(Partner).where(Partner.id == partner_id)
    result = await db.execute(stmt)
    partner = result.scalars().first()
    
    if not partner:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Партнер не найден")
        
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
            "price_resident": float(p.price_resident_kzt) if p.price_resident_kzt else 0,
            "price_nonresident": float(p.price_nonresident_kzt) if p.price_nonresident_kzt else 0,
            "price_original": float(p.price_original) if p.price_original else 0,
            "currency_original": p.currency_original.value if p.currency_original else "KZT",
            "date": p.effective_date.strftime("%d %b %Y") if p.effective_date else None
        })
        
    # Find the maximum date among active services
    effective_date_val = None
    if prices:
        valid_dates = [p.effective_date for p in prices if p.effective_date]
        if valid_dates:
            effective_date_val = max(valid_dates).strftime("%Y-%m-%d")

    return {
        "partner": {
            "id": partner.id,
            "name": partner.name,
            "city": partner.city,
            "address": partner.address,
            "bin": partner.bin,
            "is_verified": partner.is_verified,
            "verification_date": partner.verification_date.strftime("%Y-%m-%d %H:%M:%S") if partner.verification_date else None,
            "effective_date": effective_date_val
        },
        "services": price_list
    }

@router.post("/{partner_id}/verify")
async def verify_partner(partner_id: int, db: AsyncSession = Depends(get_db)):
    """
    Ручная верификация клиники оператором.
    """
    from datetime import datetime
    from fastapi import HTTPException
    
    stmt = select(Partner).where(Partner.id == partner_id)
    result = await db.execute(stmt)
    partner = result.scalars().first()
    
    if not partner:
        raise HTTPException(status_code=404, detail="Клиника не найдена")
        
    partner.is_verified = True
    partner.verification_date = datetime.now()
    
    await db.commit()
    await db.refresh(partner)
    
    return {
        "status": "ok",
        "message": f"Клиника '{partner.name}' успешно верифицирована",
        "is_verified": partner.is_verified,
        "verification_date": partner.verification_date.strftime("%Y-%m-%d %H:%M:%S")
    }
