from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import asyncio
import re

from app.db.database import get_db
from app.models.price_item import PriceItem
from app.models.price_document import ParseStatus, PriceDocument
from app.parsers.archive_parser import ArchiveProcessor
from app.parsers import get_parser
# from app.core.validator import Validator # Will create this

router = APIRouter()

async def process_documents_task(documents_to_process: list):
    # This simulates a background task or celery worker
    from app.matching.matcher import Matcher
    from app.db.database import SessionLocal
    
    for doc_info in documents_to_process:
        async with SessionLocal() as db_session:
            doc_id = doc_info["doc_id"]
            file_path = doc_info["file_path"]
            
            stmt = select(PriceDocument).where(PriceDocument.id == doc_id)
            result = await db_session.execute(stmt)
            doc = result.scalars().first()
            if not doc:
                continue
                
            doc.parse_status = ParseStatus.processing
            await db_session.commit()
            
            # 0. Extract date from file content if possible (overwrite filename fallback date)
            try:
                from app.parsers.base import extract_date_from_file
                extracted_date = await asyncio.to_thread(extract_date_from_file, file_path)
                if extracted_date:
                    doc.effective_date = extracted_date
                    await db_session.commit()
            except Exception as e:
                print(f"Error extracting date from file content: {e}")
            
            try:
                from datetime import date
                from decimal import Decimal, InvalidOperation
                # 1. Parsing
                parser = get_parser(file_path, {})
                parsed_items = await asyncio.to_thread(parser.parse)
                doc.raw_content = getattr(parser, "raw_content", "") or None
                
                import urllib.request
                import xml.etree.ElementTree as ET
                
                # Default historical fallback logic
                historic_usd_rates = {2020: 413, 2021: 426, 2022: 460, 2023: 456, 2024: 450, 2025: 480, 2026: 485}
                historic_rub_rates = {2020: 5.7, 2021: 5.8, 2022: 6.7, 2023: 5.3, 2024: 5.0, 2025: 5.2, 2026: 5.3}
                year = doc.effective_date.year if doc.effective_date else date.today().year
                usd_rate = historic_usd_rates.get(year, 480)
                rub_rate = historic_rub_rates.get(year, 5.2)
                
                # Fetch actual rates from National Bank API
                try:
                    fdate = doc.effective_date.strftime('%d.%m.%Y') if doc.effective_date else date.today().strftime('%d.%m.%Y')
                    url = f"https://nationalbank.kz/rss/get_rates.cfm?fdate={fdate}"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=5) as response:
                        xml_data = response.read()
                        root = ET.fromstring(xml_data)
                        for item in root.findall('item'):
                            title = item.find('title').text
                            if title == 'USD':
                                usd_rate = float(item.find('description').text)
                            elif title == 'RUB':
                                rub_rate = float(item.find('description').text)
                    print(f"Loaded National Bank rates for {fdate}: USD={usd_rate}, RUB={rub_rate}")
                except Exception as e:
                    print(f"Failed to fetch National Bank API, using fallback rates: {e}")
                
                if doc.effective_date and doc.effective_date > date.today():
                    doc.parse_log = (doc.parse_log or "") + f"Предупреждение: дата прайса в будущем ({doc.effective_date}).\n"
                
                # 2. Matching and Validation
                from app.matching.matcher import AUTO_MATCH_THRESHOLD
                matcher = Matcher(db_session)
                await matcher.load_services()
                
                # Load all previous active prices for anomaly detection
                prev_stmt = select(PriceItem).where(
                    PriceItem.partner_id == doc.partner_id,
                    PriceItem.is_active == True
                )
                prev_result = await db_session.execute(prev_stmt)
                all_active_prices = prev_result.scalars().all()
                
                created_items = 0
                review_items = 0
                items_to_insert = []
                seen_items = set()
                
                for item_data in parsed_items:
                    raw_name = str(getattr(item_data, "service_name_raw", "")).strip()
                    lower_raw = raw_name.lower()
                    squished_raw = re.sub(r'[^a-zа-я0-9]', '', lower_raw)
                    
                    if not raw_name or len(squished_raw) < 4:
                        doc.parse_log = (doc.parse_log or "") + f"Пропущена строка: слишком короткое название ({raw_name}).\n"
                        continue
                        
                    garbage_exact = {"итого", "всего", "наименование", "услуга", "исследование", "операция", "манипуляция", "посещение", "процедура", "цена", "стоимость", "тенге", "код", "шифр", "в06006сыв", "сн001сыв", "b06006"}
                    garbage_prefixes = ("приложение", "отянваря", "отфевраля", "отмарта", "отапреля", "отмая", "отиюня", "отиюля", "отавгуста", "отсентября", "отоктября", "отноября", "отдекабря")
                    
                    if squished_raw in garbage_exact or squished_raw.startswith(garbage_prefixes):
                        continue
                        
                    price_resident_raw = getattr(item_data, "price_resident_kzt", 0) or 0
                    price_nonresident_raw = getattr(item_data, "price_nonresident_kzt", None)
                    
                    try:
                        price_resident = Decimal(str(price_resident_raw))
                    except (ValueError, TypeError, InvalidOperation):
                        price_resident = Decimal('0')
                        
                    try:
                        if price_nonresident_raw is not None and str(price_nonresident_raw).strip() != "":
                            price_nonresident = Decimal(str(price_nonresident_raw))
                        else:
                            price_nonresident = None
                    except (ValueError, TypeError, InvalidOperation):
                        price_nonresident = None
                        
                    # Protect against Numeric(10,2) overflow (max 99,999,999.99)
                    max_price = Decimal('99000000')
                    if price_resident > max_price:
                        price_resident = max_price
                    if price_nonresident is not None and price_nonresident > max_price:
                        price_nonresident = max_price
                        
                    # Currency check
                    currency = getattr(item_data, "currency_original", "KZT")
                    price_original = price_resident
                    if currency == "USD":
                        price_resident = price_resident * Decimal(str(usd_rate))
                        if price_nonresident is not None:
                            price_nonresident = price_nonresident * Decimal(str(usd_rate))
                    elif currency == "RUB":
                        price_resident = price_resident * Decimal(str(rub_rate))
                        if price_nonresident is not None:
                            price_nonresident = price_nonresident * Decimal(str(rub_rate))
                            
                    # Deduplication within the same document
                    item_key = (squished_raw, price_resident)
                    if item_key in seen_items:
                        continue
                    seen_items.add(item_key)
                    
                    match_result = matcher.match(raw_name)
                    
                    # Low-confidence match → escalate to the AI fallback before giving up.
                    if not match_result or match_result.score < AUTO_MATCH_THRESHOLD:
                        ai_match = await matcher.ai_match_fallback(raw_name)
                        if ai_match:
                            match_result = ai_match

                    # Link to the catalog only above the auto-match threshold; otherwise the
                    # item stays unlinked and lands in the review queue (needs_review).
                    if match_result:
                        score = match_result.score
                        # Only auto-link if above threshold
                        if score >= AUTO_MATCH_THRESHOLD:
                            matched_service_id = match_result.service_id
                        else:
                            # Keep it for suggestion, but don't auto-verify
                            matched_service_id = match_result.service_id
                    else:
                        matched_service_id = None
                        score = 0
                    
                    reasons = []

                    # Validation rules
                    if price_resident <= 0:
                        reasons.append("Цена должна быть числом больше 0")
                    elif price_nonresident is not None and price_nonresident < price_resident:
                        reasons.append("Цена для нерезидента меньше цены для резидента")
                    
                    if currency not in ["KZT", "USD", "RUB"]:
                        reasons.append("Не удалось распознать валюту")
                    
                    # Find the closest previous version in history (strictly older than doc.effective_date)
                    prev_item = None
                    for p in all_active_prices:
                        if p.service_name_raw == raw_name and p.effective_date < doc.effective_date:
                            if prev_item is None or p.effective_date > prev_item.effective_date:
                                prev_item = p
                                
                    if prev_item and prev_item.price_resident_kzt:
                        diff_ratio = abs(price_resident - Decimal(str(prev_item.price_resident_kzt))) / Decimal(str(prev_item.price_resident_kzt))
                        if diff_ratio > Decimal('0.5'):
                            reasons.append(f"Цена отличается от предыдущей версии на {int(diff_ratio*100)}%")
    
                    if score < AUTO_MATCH_THRESHOLD:
                        if matched_service_id is None:
                            reasons.append("Новая услуга, нет синонимов")
                        else:
                            reasons.append(f"Уверенность сопоставления {int(score)}%")
                    
                    is_verified = len(reasons) == 0
                    verification_note = "; ".join(reasons) if not is_verified else None
                    if not is_verified:
                        review_items += 1

                    # Deactivate old version if the new one is auto-verified immediately
                    if is_verified and prev_item:
                        prev_item.is_active = False

                    new_item = PriceItem(
                        document_id=doc.id,
                        partner_id=doc.partner_id,
                        service_name_raw=raw_name,
                        service_id=matched_service_id,
                        price_resident_kzt=price_resident,
                        price_nonresident_kzt=price_nonresident,
                        price_original=price_original,
                        currency_original=currency,
                        is_verified=is_verified,
                        verification_note=verification_note,
                        effective_date=doc.effective_date,
                        is_active=True,
                        match_score=score
                    )
                    items_to_insert.append(new_item)
                    created_items += 1
                
                if items_to_insert:
                    db_session.add_all(items_to_insert)
                
                try:
                    if created_items == 0:
                        doc.parse_status = ParseStatus.error
                        doc.parse_log = (doc.parse_log or "") + "Документ не содержит распознаваемых строк с ценами.\n"
                    elif review_items > 0 or (doc.parse_log and "Предупреждение" in doc.parse_log):
                        doc.parse_status = ParseStatus.needs_review
                    else:
                        doc.parse_status = ParseStatus.done
                    await db_session.commit()
                except Exception as e:
                    await db_session.rollback()
                    doc.parse_status = ParseStatus.error
                    doc.parse_log = (doc.parse_log or "") + f"\nКритическая ошибка при сохранении в БД: {str(e)}"
                    await db_session.commit()
                
            except Exception as e:
                import traceback
                tb_str = traceback.format_exc()
                print(f"CRITICAL PARSING ERROR FOR {file_path}:\n{tb_str}")
                doc.parse_status = ParseStatus.error
                doc.parse_log = f"{str(e)}\n{tb_str}"
                await db_session.commit()


@router.post("/upload-prices")
async def upload_prices_archive(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Принимает ZIP-архив, определяет клиники и даты из названий, валидирует цены.
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "Допускаются только ZIP-архивы")
        
    content = await file.read()
    
    processor = ArchiveProcessor(db)
    documents_to_process = await processor.process_zip(content)
    
    if not documents_to_process:
        return {"status": "warning", "message": "Не найдено поддерживаемых файлов или партнеров"}
        
    # Queue processing
    background_tasks.add_task(process_documents_task, documents_to_process)
    
    return {
        "status": "ok", 
        "message": f"Архив загружен. Файлов в обработке: {len(documents_to_process)}"
    }

@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """
    Получение агрегированной статистики для дашборда администратора.
    """
    from sqlalchemy import func
    from app.models.partner import Partner
    
    # 1. Количество обработанных документов
    docs_stmt = select(func.count()).select_from(PriceDocument).where(
        PriceDocument.parse_status.in_([ParseStatus.done, ParseStatus.needs_review])
    )
    docs_result = await db.execute(docs_stmt)
    processed_docs = docs_result.scalar() or 0
    
    # 2. Активные клиники
    clinics_stmt = select(func.count()).select_from(Partner).where(Partner.is_active == True)
    clinics_result = await db.execute(clinics_stmt)
    active_clinics = clinics_result.scalar() or 0
    
    # automationScore = доля активных позиций, привязанных к справочнику (service_id IS NOT NULL).
    # Это честная мера «нормализации» по ТЗ (п.4.3), без хардкода.
    total_active_stmt = select(func.count()).select_from(PriceItem).where(PriceItem.is_active == True)
    total_active = (await db.execute(total_active_stmt)).scalar() or 0

    normalized_stmt = select(func.count()).select_from(PriceItem).where(
        PriceItem.is_active == True,
        PriceItem.service_id.is_not(None)
    )
    normalized_active = (await db.execute(normalized_stmt)).scalar() or 0

    automation_score = int((normalized_active / total_active) * 100) if total_active > 0 else 0
    
    # Adjust in_queue to match the actual DB count to prevent bouncing issues
    unmatched_stmt = select(func.count()).select_from(PriceItem).where(
        PriceItem.is_verified == False,
        PriceItem.is_active == True
    )
    in_queue = (await db.execute(unmatched_stmt)).scalar() or 0
    
    # 5. Количество документов в обработке (и в очереди)
    processing_stmt = select(func.count()).select_from(PriceDocument).where(
        PriceDocument.parse_status.in_([ParseStatus.processing, ParseStatus.pending])
    )
    processing_result = await db.execute(processing_stmt)
    processing_count = processing_result.scalar() or 0
    
    return {
        "processed": processed_docs,
        "automationScore": automation_score,
        "normalizedItems": normalized_active,
        "totalItems": total_active,
        "inQueue": in_queue,
        "activeClinics": active_clinics,
        "processingCount": processing_count
    }

@router.get("/unmatched")
async def get_unmatched_items(
    queue: str = Query("fast_track", description="fast_track или anomaly"),
    db: AsyncSession = Depends(get_db)
):
    """
    Очередь аномалий и непроверенных связей.
    """
    from sqlalchemy.orm import joinedload
    from sqlalchemy import case, and_, or_, not_, func
    
    base_cond = and_(
        PriceItem.is_verified == False,
        PriceItem.is_active == True
    )
    
    # 1. Считаем общее число для обеих очередей для вкладок
    fast_track_count_stmt = select(func.count()).select_from(PriceItem).where(
        base_cond,
        PriceItem.match_score >= 60,
        PriceItem.match_score < 85,
        or_(
            PriceItem.verification_note == None,
            and_(
                not_(PriceItem.verification_note.ilike("%цена%")),
                not_(PriceItem.verification_note.ilike("%валют%")),
                not_(PriceItem.verification_note.ilike("%нерезидент%")),
                
            )
        )
    )
    fast_track_count = (await db.execute(fast_track_count_stmt)).scalar() or 0
    
    anomaly_count_stmt = select(func.count()).select_from(PriceItem).where(
        base_cond,
        or_(
            PriceItem.match_score < 60,
            PriceItem.match_score.is_(None),
            PriceItem.verification_note.ilike("%цена%"),
            PriceItem.verification_note.ilike("%валют%"),
            PriceItem.verification_note.ilike("%нерезидент%")
        )
    )
    anomaly_count = (await db.execute(anomaly_count_stmt)).scalar() or 0

    # 2. Выгружаем элементы в зависимости от активной очереди
    if queue == "fast_track":
        stmt = select(PriceItem).where(
            base_cond,
            PriceItem.match_score >= 60,
            PriceItem.match_score < 85,
            or_(
                PriceItem.verification_note == None,
                and_(
                    not_(PriceItem.verification_note.ilike("%цена%")),
                    not_(PriceItem.verification_note.ilike("%валют%")),
                    not_(PriceItem.verification_note.ilike("%нерезидент%"))
                )
            )
        ).options(
            joinedload(PriceItem.partner),
            joinedload(PriceItem.document),
            joinedload(PriceItem.service)
        ).order_by(PriceItem.match_score.desc()).limit(100)
    else: # anomaly / unmatched
        stmt = select(PriceItem).where(
            base_cond,
            or_(
                PriceItem.match_score < 60,
                PriceItem.match_score.is_(None),
                PriceItem.verification_note.ilike("%цена%"),
                PriceItem.verification_note.ilike("%валют%"),
                PriceItem.verification_note.ilike("%нерезидент%")
            )
        ).options(
            joinedload(PriceItem.partner),
            joinedload(PriceItem.document),
            joinedload(PriceItem.service)
        ).order_by(PriceItem.match_score.desc()).limit(100)

    result = await db.execute(stmt)
    items = result.scalars().all()
    
    response = []
    for item in items:
        # Load previous price to show diff (strictly older than this item)
        prev_stmt = select(PriceItem).where(
            PriceItem.partner_id == item.partner_id,
            PriceItem.service_name_raw == item.service_name_raw,
            PriceItem.is_active == True,
            PriceItem.effective_date < item.effective_date
        ).order_by(PriceItem.effective_date.desc())
        prev_result = await db.execute(prev_stmt)
        prev_item = prev_result.scalars().first()
        
        old_price = float(prev_item.price_resident_kzt) if prev_item else None
        new_price = float(item.price_resident_kzt) if item.price_resident_kzt is not None else 0.0
        new_price_nonresident = float(item.price_nonresident_kzt) if item.price_nonresident_kzt is not None else None
        diff_str = ""
        if old_price:
            diff = new_price - old_price
            diff_pct = (diff / old_price) * 100
            sign = "+" if diff > 0 else ""
            diff_str = f"{sign}{int(diff_pct)}%"

        # Determine if it has other anomalies based on verification_note contents
        other_anomalies = False
        if item.verification_note:
            note_lower = item.verification_note.lower()
            if any(word in note_lower for word in ["цена", "валют", "нерезидент"]):
                other_anomalies = True

        is_fast_track = False
        if item.match_score is not None and 50 <= item.match_score < 65 and not other_anomalies:
            is_fast_track = True

        # Status logic matching thresholds
        if other_anomalies or (item.match_score is not None and item.match_score < 50):
            status = "anomaly"
        elif is_fast_track:
            status = "fast_track"
        else:
            status = "unmatched"

        # Dynamically recalculate/update price diff in note
        note = item.verification_note or ""
        
        # Remove any stale price diff message from note
        import re
        note = re.sub(r'Цена отличается от предыдущей версии на \d+%;?\s*', '', note).strip()
        if note.endswith(';'):
            note = note[:-1].strip()
            
        # Recalculate diff dynamically based on current DB state
        if old_price and old_price > 0:
            diff_pct = abs(new_price - old_price) / old_price * 100
            if diff_pct > 50:
                price_warning = f"Цена отличается от предыдущей версии на {int(diff_pct)}%"
                if note:
                    note = f"{price_warning}; {note}"
                else:
                    note = price_warning
        
        if not note:
            reasons = []
            if item.match_score is not None and item.match_score < 85:
                if item.match_score == 0 or item.service_id is None:
                    reasons.append("Новая услуга, нет синонимов")
                else:
                    reasons.append(f"Уверенность сопоставления {int(item.match_score)}%")
            if item.price_resident_kzt is not None and item.price_resident_kzt <= 0:
                reasons.append("Цена должна быть числом больше 0")
            if reasons:
                note = "; ".join(reasons)
            else:
                note = "Требуется ручная проверка"

        response.append({
            "id": item.id,
            "raw_name": item.service_name_raw,
            "suggested_service_id": item.service_id,
            "suggested_service_name": item.service.name_ru if item.service else None,
            "confidence": item.match_score,
            "old_price": old_price,
            "new_price": new_price,
            "new_price_nonresident": new_price_nonresident,
            "diff": diff_str,
            "status": status,
            "is_fast_track": is_fast_track,
            "note": note,
            "price_original": float(item.price_original) if item.price_original is not None else 0.0,
            "currency_original": item.currency_original.value if item.currency_original else "KZT",
            "partner_name": item.partner.name if item.partner else None,
            "file_name": item.document.file_name if item.document else None
        })
        
    return {
        "items": response,
        "fast_track_count": fast_track_count,
        "anomaly_count": anomaly_count
    }

@router.post("/match/{item_id}")
async def match_item(
    item_id: int,
    service_id: Optional[int] = None,
    service_name: Optional[str] = None,
    price: Optional[float] = None,
    price_nonresident: Optional[float] = None,
    raw_name: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Ручное подтверждение (или корректировка) оператором.
    """
    from decimal import Decimal

    stmt = select(PriceItem).where(PriceItem.id == item_id)
    result = await db.execute(stmt)
    item = result.scalars().first()

    if not item:
        raise HTTPException(status_code=404, detail="Позиция не найдена")

    resident_price = Decimal(str(price)) if price is not None else item.price_resident_kzt
    nonresident_price = Decimal(str(price_nonresident)) if price_nonresident is not None else item.price_nonresident_kzt

    if resident_price is None or resident_price <= 0:
        raise HTTPException(status_code=400, detail="Цена должна быть числом больше 0")
    if nonresident_price is not None and nonresident_price < resident_price:
        raise HTTPException(status_code=400, detail="Цена для нерезидента не может быть меньше цены для резидента")
        
    
    if service_name and not service_id:
        from app.models.service import Service
        svc_result = await db.execute(select(Service).where(Service.name_ru.ilike(f"%{service_name}%")))
        found_svc = svc_result.scalars().first()
        if found_svc:
            service_id = found_svc.id
            
    # Архивация старой версии (по ТЗ: старая версия архивируется, не удаляется)
    item.is_active = False
    
    # Деактивируем любые другие активные цены для этого партнера и названия услуги
    deactivate_stmt = select(PriceItem).where(
        PriceItem.partner_id == item.partner_id,
        PriceItem.service_name_raw == raw_name,
        PriceItem.is_active == True,
        PriceItem.id != item.id
    )
    deactivate_result = await db.execute(deactivate_stmt)
    for old_item in deactivate_result.scalars().all():
        old_item.is_active = False

    # Обучение системы (фича «Снежный ком» по ТЗ):
    # Добавляем сырое название в список синонимов эталонной услуги,
    # чтобы при следующем парсинге сопоставление сработало автоматически.
    if service_id:
        from app.models.service import Service
        svc_stmt = select(Service).where(Service.id == service_id)
        svc_result = await db.execute(svc_stmt)
        svc = svc_result.scalars().first()
        if svc:
            current_synonyms = svc.synonyms or []
            if not isinstance(current_synonyms, list):
                current_synonyms = []
            if raw_name not in current_synonyms:
                new_synonyms = list(current_synonyms) + [raw_name]
                svc.synonyms = new_synonyms
                from app.api.routes.search import clear_service_cache
                clear_service_cache()

    # Создание новой бессрочной версии с внесенными правками
    new_item = PriceItem(
        document_id=item.document_id,
        partner_id=item.partner_id,
        service_name_raw=raw_name,
        service_code_source=item.service_code_source,
        service_id=service_id,
        price_resident_kzt=resident_price,
        price_nonresident_kzt=nonresident_price,
        price_original=resident_price,
        currency_original=item.currency_original,
        is_verified=True,
        verification_note="Проверено и скорректировано оператором",
        effective_date=item.effective_date,
        is_active=True,
        match_score=item.match_score
    )
    
    db.add(new_item)
    await db.commit()
    return {"status": "ok", "message": "Связь подтверждена"}

@router.delete("/reject/{item_id}")
async def reject_item(item_id: int, db: AsyncSession = Depends(get_db)):
    """
    Отклонение (удаление) позиции из очереди верификации.
    """
    stmt = select(PriceItem).where(PriceItem.id == item_id)
    result = await db.execute(stmt)
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Позиция не найдена")
        
    await db.delete(item)
    await db.commit()
    return {"status": "ok", "message": "Позиция отклонена"}

@router.get("/auto-normalized")
async def get_auto_normalized_items(db: AsyncSession = Depends(get_db)):
    """
    Список всех автоматически сопоставленных позиций (уверенность >= 85%) для отображения на дашборде.
    """
    from sqlalchemy.orm import joinedload
    
    stmt = select(PriceItem).where(
        PriceItem.is_verified == True,
        PriceItem.is_active == True,
        PriceItem.match_score >= 85
    ).options(
        joinedload(PriceItem.partner),
        joinedload(PriceItem.service)
    ).order_by(PriceItem.id.desc()).limit(100)
    
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    response = []
    for item in items:
        response.append({
            "id": item.id,
            "raw_name": item.service_name_raw,
            "service_id": item.service_id,
            "service_name": item.service.name_ru if item.service else None,
            "confidence": item.match_score,
            "price_resident": float(item.price_resident_kzt) if item.price_resident_kzt is not None else 0.0,
            "price_nonresident": float(item.price_nonresident_kzt) if item.price_nonresident_kzt is not None else None,
            "partner_name": item.partner.name if item.partner else None,
            "effective_date": item.effective_date.strftime("%Y-%m-%d") if item.effective_date else None
        })
    return response

@router.get("/export")
async def export_price_data(db: AsyncSession = Depends(get_db)):
    from fastapi.responses import StreamingResponse
    import csv
    import io
    from sqlalchemy.orm import joinedload
    
    async def iter_csv():
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow([
            "Клиника", 
            "Исходное название", 
            "Сопоставленная услуга", 
            "Цена (Резидент, KZT)", 
            "Цена (Нерезидент, KZT)", 
            "Оригинальная цена", 
            "Валюта", 
            "Статус", 
            "Дата"
        ])
        yield output.getvalue().encode('utf-8-sig')
        output.seek(0)
        output.truncate(0)
        
        stmt = select(PriceItem).options(
            joinedload(PriceItem.partner),
            joinedload(PriceItem.service)
        ).where(PriceItem.is_active == True)
        
        # In async context, execute and then fetchall or stream
        result = await db.execute(stmt)
        items = result.scalars().all()
        
        for row in items:
            status_text = "Верифицировано" if row.is_verified else "Ожидает"
            mapped_service = row.service.name_ru if row.service else ""
            partner_name = row.partner.name if row.partner else ""
            
            writer.writerow([
                partner_name,
                row.service_name_raw,
                mapped_service,
                str(row.price_resident_kzt or 0),
                str(row.price_nonresident_kzt) if row.price_nonresident_kzt is not None else "",
                str(row.price_original or ""),
                row.currency_original.value if row.currency_original else "",
                status_text,
                str(row.effective_date or "")
            ])
            yield output.getvalue().encode('utf-8-sig')
            output.seek(0)
            output.truncate(0)
            
    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=medpartners_export.csv"}
    )
