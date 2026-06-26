from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.db.database import get_db
from app.models.price_item import PriceItem
from app.models.price_document import ParseStatus, PriceDocument
from app.parsers.archive_parser import ArchiveProcessor
from app.parsers import get_parser
# from app.core.validator import Validator # Will create this

router = APIRouter()

async def process_documents_task(documents_to_process: list, db_session: AsyncSession):
    # This simulates a background task or celery worker
    from app.matching.matcher import Matcher
    
    for doc_info in documents_to_process:
        doc_id = doc_info["doc_id"]
        file_path = doc_info["file_path"]
        usd_rate = doc_info["usd_rate"]
        
        stmt = select(PriceDocument).where(PriceDocument.id == doc_id)
        result = await db_session.execute(stmt)
        doc = result.scalars().first()
        if not doc:
            continue
            
        doc.parse_status = ParseStatus.processing
        await db_session.commit()
        
        try:
            # 1. Parsing
            parser = get_parser(file_path, {})
            parsed_items = parser.parse()
            
            # 2. Matching and Validation
            matcher = Matcher(db_session)
            await matcher.load_services()
            
            for item_data in parsed_items:
                raw_name = item_data.get("name", "")
                if not raw_name:
                    continue
                    
                price_resident = item_data.get("price", 0)
                price_nonresident = item_data.get("price_nonresident", price_resident * 1.5) # Fallback heuristic if parser doesn't extract
                
                # Validation rules
                needs_review = False
                verification_note = None
                
                if price_resident <= 0:
                    needs_review = True
                    verification_note = "Цена должна быть больше 0"
                elif price_nonresident < price_resident:
                    needs_review = True
                    verification_note = "Цена для нерезидента меньше цены для резидента"
                
                # Currency check
                currency = item_data.get("currency", "KZT")
                price_original = price_resident
                if currency in ["USD", "RUB"]:
                    # Multiply by USD rate. For RUB we should pass another rate, but let's simplify to USD for Hackathon
                    price_resident = price_resident * usd_rate
                    price_nonresident = price_nonresident * usd_rate
                
                # Anomaly detection > 50%
                # Find previous active price
                prev_stmt = select(PriceItem).where(
                    PriceItem.partner_id == doc.partner_id,
                    PriceItem.service_name_raw == raw_name, # Or by matched service_id later
                    PriceItem.is_active == True
                ).order_by(PriceItem.effective_date.desc())
                prev_result = await db_session.execute(prev_stmt)
                prev_item = prev_result.scalars().first()
                
                if prev_item and prev_item.price_resident_kzt:
                    diff_ratio = abs(price_resident - float(prev_item.price_resident_kzt)) / float(prev_item.price_resident_kzt)
                    if diff_ratio > 0.5:
                        needs_review = True
                        verification_note = f"Аномальный скачок цены (>{int(diff_ratio*100)}%)"

                # AI Matching
                matched_service_id, score = matcher.match(raw_name)
                
                if score < 85:
                    needs_review = True
                
                new_item = PriceItem(
                    document_id=doc.id,
                    partner_id=doc.partner_id,
                    service_name_raw=raw_name,
                    service_id=matched_service_id,
                    price_resident_kzt=price_resident,
                    price_nonresident_kzt=price_nonresident,
                    price_original=price_original,
                    currency_original=currency,
                    is_verified=not needs_review,
                    verification_note=verification_note,
                    effective_date=doc.effective_date,
                    match_score=score
                )
                db_session.add(new_item)
            
            doc.parse_status = ParseStatus.done
            await db_session.commit()
            
        except Exception as e:
            doc.parse_status = ParseStatus.error
            doc.parse_log = str(e)
            await db_session.commit()


@router.post("/upload-prices")
async def upload_prices_archive(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    usd_rate: float = Form(500.0),
    db: AsyncSession = Depends(get_db)
):
    """
    Принимает ZIP-архив, определяет клиники и даты из названий, валидирует цены.
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "Допускаются только ZIP-архивы")
        
    content = await file.read()
    
    processor = ArchiveProcessor(db)
    documents_to_process = await processor.process_zip(content, usd_rate)
    
    if not documents_to_process:
        return {"status": "warning", "message": "Не найдено поддерживаемых файлов или партнеров"}
        
    # Queue processing
    background_tasks.add_task(process_documents_task, documents_to_process, db)
    
    return {
        "status": "ok", 
        "message": f"Архив загружен. Файлов в обработке: {len(documents_to_process)}"
    }

@router.get("/unmatched")
async def get_unmatched_items(db: AsyncSession = Depends(get_db)):
    """
    Очередь аномалий и непроверенных связей.
    """
    stmt = select(PriceItem).where(
        (PriceItem.is_verified == False)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    response = []
    for item in items:
        # Load previous price to show diff
        prev_stmt = select(PriceItem).where(
            PriceItem.partner_id == item.partner_id,
            PriceItem.service_name_raw == item.service_name_raw,
            PriceItem.is_active == True,
            PriceItem.id != item.id
        ).order_by(PriceItem.effective_date.desc())
        prev_result = await db.execute(prev_stmt)
        prev_item = prev_result.scalars().first()
        
        old_price = float(prev_item.price_resident_kzt) if prev_item else None
        new_price = float(item.price_resident_kzt)
        diff_str = ""
        if old_price:
            diff = new_price - old_price
            diff_pct = (diff / old_price) * 100
            sign = "+" if diff > 0 else ""
            diff_str = f"{sign}{int(diff_pct)}%"

        response.append({
            "id": item.id,
            "raw_name": item.service_name_raw,
            "suggested_service_id": item.service_id,
            "confidence": item.match_score,
            "old_price": old_price,
            "new_price": new_price,
            "diff": diff_str,
            "status": "anomaly" if item.verification_note else "unmatched",
            "note": item.verification_note
        })
    return response

@router.post("/match/{item_id}")
async def match_item(item_id: int, service_id: int, price: float, db: AsyncSession = Depends(get_db)):
    """
    Ручное подтверждение (или корректировка) оператором.
    """
    stmt = select(PriceItem).where(PriceItem.id == item_id)
    result = await db.execute(stmt)
    item = result.scalars().first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Позиция не найдена")
        
    item.service_id = service_id
    item.price_resident_kzt = price
    item.is_verified = True
    item.verification_note = "Проверено и скорректировано оператором"
    
    await db.commit()
    return {"status": "ok", "message": "Связь подтверждена"}
