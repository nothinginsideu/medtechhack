from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from typing import Optional, List

from app.db.database import get_db
from app.models.service import Service
from app.models.price_item import PriceItem
from app.matching.normalizer import Normalizer

SERVICE_CACHE = {}

async def get_service_cache(db: AsyncSession) -> dict:
    global SERVICE_CACHE
    if not SERVICE_CACHE:
        stmt = select(Service.id, Service.name_ru, Service.synonyms).where(Service.is_active == True)
        result = await db.execute(stmt)
        for row in result.all():
            svc_id, name, synonyms = row[0], row[1], row[2]
            SERVICE_CACHE[f"{svc_id}_name"] = name
            if synonyms and isinstance(synonyms, list):
                for i, syn in enumerate(synonyms):
                    if syn:
                        SERVICE_CACHE[f"{svc_id}_syn_{i}"] = syn
    return SERVICE_CACHE

router = APIRouter()

@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Возвращает список уникальных специализаций (категорий) из базы."""
    stmt = select(Service.specialty).where(Service.specialty != None).distinct()
    result = await db.execute(stmt)
    specialties = [s for s in result.scalars().all() if s.strip()]
    
    # Map them strictly back to our 4-5 major groups if we want, or just return them directly.
    # The user asked to remove hardcoded mapping, so we return the raw distinct values, 
    # but maybe grouped into top-level unique ones.
    
    return sorted(list(set(specialties)))

@router.get("/search")
async def search_services(
    q: str = Query(..., min_length=2, description="Поисковой запрос (например: анализ крови)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Поиск по эталонным услугам и возврат цен в клиниках. Возвращает полные данные партнера для модалки.
    """
    from sqlalchemy import or_, and_
    import re
    
    # 1. Stop words to ignore for better matching
    STOP_WORDS = {
        'врач', 'врача', 'врачи', 'услуга', 'услуги', 'сдать', 'сделать', 'пройти', 
        'клиника', 'клиники', 'центр', 'анализ', 'анализы', 'цена', 'цены', 'стоимость',
        'руб', 'тенге', 'тг', 'kzt', 'в', 'на', 'и', 'или', 'с', 'по', 'для', 'прием'
    }
    
    # Simple stemmer to strip word endings (Russian plural/case forms)
    def stem_word(word: str) -> str:
        word = word.lower().strip()
        # Remove common Russian case/gender endings if word is long enough
        suffixes = ['ого', 'его', 'ому', 'ему', 'ое', 'ая', 'ои', 'ые', 'ых', 'их', 'ам', 'ям', 'а', 'я', 'о', 'е', 'и', 'ы', 'у', 'ю', 'ом', 'ем', 'ой', 'ей', 'ь']
        for suffix in suffixes:
            if word.endswith(suffix) and len(word) - len(suffix) >= 4:
                return word[:-len(suffix)]
        return word

    # Clean and tokenize query
    clean_query = q.lower()
    raw_words = re.findall(r'[a-zA-Zа-яА-Я0-9-+]+', clean_query)
    
    # Filter stop-words and stem
    words = []
    for w in raw_words:
        if w not in STOP_WORDS:
            stemmed = stem_word(w)
            if len(stemmed) >= 2:
                words.append(stemmed)
                
    # If all words were stop words, fallback to using raw words
    if not words:
        words = [stem_word(w) for w in raw_words if len(w) >= 2]
        
    if not words:
        return []

    # Build logical AND across all search terms. Each term must match either Service name, specialty, or raw item name
    conditions = []
    for word in words:
        conditions.append(
            or_(
                Service.name_ru.ilike(f"%{word}%"),
                Service.specialty.ilike(f"%{word}%"),
                and_(
                    PriceItem.service_name_raw.ilike(f"%{word}%"),
                    PriceItem.is_active == True,
                    PriceItem.is_verified == True
                )
            )
        )

    # Executing search query joining PriceItems (only verified and active)
    stmt = (
        select(Service)
        .join(PriceItem, PriceItem.service_id == Service.id)
        .where(
            and_(
                PriceItem.is_active == True,
                PriceItem.is_verified == True,
                *conditions
            )
        )
        .options(
            joinedload(Service.price_items).joinedload(PriceItem.document),
            joinedload(Service.price_items).joinedload(PriceItem.partner)
        )
    )
    
    result = await db.execute(stmt)
    services = result.unique().scalars().all()
    
    response = []
    for svc in services:
        prices = []
        for p_item in svc.price_items:
            if not p_item.is_active or not p_item.is_verified:
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

    if not response:
        # Fallback to RapidFuzz
        from rapidfuzz import process, fuzz
        
        cache = await get_service_cache(db)
        cutoff = 60 if len(q) <= 5 else 50
        
        def combo_scorer(s1, s2, **kwargs):
            return max(fuzz.WRatio(s1, s2, **kwargs), fuzz.partial_ratio(s1, s2, **kwargs))
            
        matches = process.extract(q, cache, limit=5, scorer=combo_scorer, score_cutoff=cutoff)
        
        if matches:
            matched_ids = list({int(str(m[2]).split('_')[0]) for m in matches})
            
            fallback_stmt = (
                select(Service)
                .join(PriceItem, PriceItem.service_id == Service.id)
                .where(
                    and_(
                        Service.id.in_(matched_ids),
                        PriceItem.is_active == True,
                        PriceItem.is_verified == True
                    )
                )
                .options(
                    joinedload(Service.price_items).joinedload(PriceItem.document),
                    joinedload(Service.price_items).joinedload(PriceItem.partner)
                )
            )
            fallback_result = await db.execute(fallback_stmt)
            fallback_services = fallback_result.unique().scalars().all()
            
            for svc in fallback_services:
                prices = []
                for p_item in svc.price_items:
                    if not p_item.is_active or not p_item.is_verified:
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
                    
                if prices:
                    response.append({
                        "service_id": svc.id,
                        "name": svc.name_ru,
                        "specialty": svc.specialty,
                        "prices": sorted(prices, key=lambda x: x["price_resident"] if x["price_resident"] is not None else float('inf'))
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

@router.get("/partners/{partner_id}/history")
async def get_price_history(
    partner_id: int,
    service_id: Optional[int] = Query(None),
    raw_name: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Получение истории изменения цен для конкретного партнера и услуги.
    """
    stmt = select(PriceItem).where(
        PriceItem.partner_id == partner_id
    )
    
    if service_id is not None:
        stmt = stmt.where(PriceItem.service_id == service_id)
    elif raw_name:
        stmt = stmt.where(PriceItem.service_name_raw.ilike(raw_name.strip()))
    else:
        return []
        
    stmt = stmt.order_by(PriceItem.effective_date.asc())
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    history = []
    seen_dates = set()
    for item in items:
        if not item.effective_date:
            continue
        date_str = item.effective_date.strftime("%Y-%m-%d")
        
        if date_str in seen_dates:
            for h in history:
                if h["date"] == date_str and (item.is_active or not h["is_active"]):
                    h["price"] = float(item.price_resident_kzt) if item.price_resident_kzt is not None else 0
                    h["price_nonresident"] = float(item.price_nonresident_kzt) if item.price_nonresident_kzt is not None else 0
                    h["is_active"] = item.is_active
            continue
            
        seen_dates.add(date_str)
        history.append({
            "date": date_str,
            "year": item.effective_date.year,
            "price": float(item.price_resident_kzt) if item.price_resident_kzt is not None else 0,
            "price_nonresident": float(item.price_nonresident_kzt) if item.price_nonresident_kzt is not None else 0,
            "is_active": item.is_active
        })
        
    return history

from pydantic import BaseModel

class AssistantRequest(BaseModel):
    message: str

@router.post("/search/assistant")
async def chat_assistant(
    payload: AssistantRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Интерактивный медицинский ИИ-ассистент, рекомендующий исследования/врачей по симптомам и находящий цены.
    """
    import google.generativeai as genai
    from app.core.config import settings
    import json
    
    from fastapi import HTTPException

    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="ИИ-Ассистент временно недоступен: отсутствует API-ключ")
        
    genai.configure(api_key=settings.GEMINI_API_KEY)
    
    prompt = f"""
    Ты — умный медицинский ассистент MedPartners.
    Пациент жалуется на симптомы: "{payload.message}"
    
    1. Проанализируй жалобу и кратко опиши, к какому врачу или на какие анализы/исследования ему стоит обратить внимание.
    2. Выдели список из 1-3 ключевых фраз (например: "прием терапевта", "узи брюшной полости", "общий анализ крови") для поиска в нашей базе цен.
    
    Верни ответ строго в формате JSON со следующими полями:
    - "analysis": Краткое описание проблемы и советы на русском языке.
    - "recommendations": Список конкретных рекомендаций (например, "Записаться к терапевту", "Сдать общий анализ крови").
    - "search_queries": Список текстовых запросов для поиска по прайс-листам медицинских услуг (каждый запрос должен быть простым словосочетанием на русском языке, например: ["прием терапевта", "узи"]).
    
    JSON:
    """
    
    try:
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(prompt)
        text_response = response.text.strip()
        
        if text_response.startswith("```json"):
            text_response = text_response[7:]
        if text_response.endswith("```"):
            text_response = text_response[:-3]
        text_response = text_response.strip()
        
        data = json.loads(text_response)
        
        analysis = data.get("analysis", "Не удалось проанализировать симптомы.")
        recommendations = data.get("recommendations", [])
        search_queries = data.get("search_queries", [])
    except Exception as e:
        print(f"Ошибка при работе с Gemini: {e}")
        raise HTTPException(status_code=503, detail="ИИ-Ассистент временно недоступен")
        
    services_found = []
    seen_service_ids = set()
    
    for query in search_queries:
        try:
            results = await search_services(q=query, db=db)
            for res in results:
                srv_id = res.get("service_id")
                if srv_id in seen_service_ids:
                    continue
                seen_service_ids.add(srv_id)
                services_found.append(res)
        except Exception as search_err:
            print(f"Ошибка поиска для '{query}': {search_err}")
            
    return {
        "analysis": analysis,
        "recommendations": recommendations,
        "services": services_found
    }
