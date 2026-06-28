import zipfile
import io
import os
import re
import uuid
from datetime import date
from rapidfuzz import process
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.partner import Partner
from app.models.price_document import PriceDocument, FileFormat, ParseStatus
from app.parsers import get_parser

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/uploads"))

class ArchiveProcessor:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.partners = []

    async def _load_partners(self):
        stmt = select(Partner).where(Partner.is_active == True)
        result = await self.db.execute(stmt)
        self.partners = result.scalars().all()

    def _extract_date_from_filename(self, filename: str) -> date:
        """
        Извлекает дату вступления из имени файла (ДД.ММ.ГГГГ, ГГГГ-ММ-ДД или просто ГГГГ).
        Если дата не найдена, возвращает текущую дату.
        """
        # 1. Поиск DD.MM.YYYY
        match_full = re.search(r'\b(\d{1,2})[./-](\d{1,2})[./-](20\d{2})\b', filename)
        if match_full:
            d, m, y = map(int, match_full.groups())
            try:
                return date(y, m, d)
            except ValueError:
                pass
                
        # 2. Поиск YYYY-MM-DD
        match_iso = re.search(r'\b(20\d{2})[./-](\d{1,2})[./-](\d{1,2})\b', filename)
        if match_iso:
            y, m, d = map(int, match_iso.groups())
            try:
                return date(y, m, d)
            except ValueError:
                pass

        # 3. Поиск просто года
        match_year = re.search(r'\b(20\d{2})\b', filename)
        if match_year:
            year = int(match_year.group(1))
            return date(year, 1, 1)
            
        return date.today()

    def _partner_name_from_filename(self, filename: str) -> str:
        base_name = os.path.splitext(os.path.basename(filename))[0]
        clinic_match = re.search(r'(клиника\s*\d+)', base_name, re.IGNORECASE)
        if clinic_match:
            return re.sub(r'\s+', ' ', clinic_match.group(1)).strip().title()

        cleaned = re.sub(r'\b(прайс|price|лист|год|года|утверждено|от|архив)\b', ' ', base_name, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b20\d{2}\b', ' ', cleaned)
        cleaned = cleaned.replace('_', ' ').replace('-', ' ')
        return re.sub(r'\s+', ' ', cleaned).strip() or base_name

    async def _find_or_create_partner_by_filename(self, filename: str) -> Partner:
        """
        Определяет партнера по имени файла. Если не найден — ищет по БИН в тексте (заглушка)
        или создает нового динамически.
        """
        # Попытка найти БИН в названии (обычно он 12 цифр)
        bin_match = re.search(r'\b(\d{12})\b', filename)
        extracted_bin = bin_match.group(1) if bin_match else None

        partner_name = self._partner_name_from_filename(filename)

        if self.partners:
            partner_names = {p.id: p.name for p in self.partners}
            
            # Сначала пытаемся по названию (требуем практически 100% совпадения, чтобы Клиника 1 и Клиника 2 не сливались)
            best_match = process.extractOne(partner_name, partner_names)
            if best_match and best_match[1] >= 90: 
                partner_id = best_match[2]
                return next((p for p in self.partners if p.id == partner_id), None)
                
            # Если передали БИН и не нашли по имени, ищем по БИН
            if extracted_bin:
                for p in self.partners:
                    if p.bin == extracted_bin:
                        return p
        
        # Если партнер не найден, создаем нового
        new_partner = Partner(
            name=partner_name,
            bin=extracted_bin,
            city="Астана", # Дефолт, если не удалось определить
            is_active=True
        )
        self.db.add(new_partner)
        await self.db.flush()
        await self.db.refresh(new_partner)
        self.partners.append(new_partner)
        return new_partner

    def _safe_storage_path(self, filename: str) -> str:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        safe_name = re.sub(r'[^\w.\- а-яА-ЯёЁ]', '_', filename).strip(" ._")
        return os.path.join(UPLOAD_DIR, f"{uuid.uuid4().hex}_{safe_name}")

    def _determine_format(self, filename: str) -> FileFormat:
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".pdf":
            return FileFormat.pdf
        elif ext == ".docx":
            return FileFormat.docx
        elif ext in [".xlsx", ".xls"]:
            return FileFormat.xlsx
        return None

    async def process_zip(self, zip_content: bytes) -> list:
        """
        Распаковывает ZIP, определяет партнера, дату, создает PriceDocument и возвращает их.
        """
        await self._load_partners()
        documents_to_process = []

        with zipfile.ZipFile(io.BytesIO(zip_content)) as archive:
            for file_info in archive.infolist():
                if file_info.is_dir() or file_info.filename.startswith('__MACOSX') or file_info.filename.startswith('.'):
                    continue
                
                raw_filename = file_info.filename
                # Исправляем кодировку (Mojibake), так как zipfile по умолчанию читает в CP437
                try:
                    raw_filename = raw_filename.encode('cp437').decode('utf-8')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    try:
                        raw_filename = raw_filename.encode('cp437').decode('cp866')
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        pass

                filename = os.path.basename(raw_filename)
                if not filename:
                    continue

                file_format = self._determine_format(filename)
                if not file_format:
                    continue

                partner = await self._find_or_create_partner_by_filename(filename)
                    
                if not partner:
                    print(f"Партнер не найден и не удалось создать: {filename}")
                    continue

                effective_date = self._extract_date_from_filename(filename)

                stored_path = self._safe_storage_path(filename)
                
                with open(stored_path, "wb") as f:
                    f.write(archive.read(file_info.filename))

                doc = PriceDocument(
                    partner_id=partner.id,
                    file_name=filename,
                    file_format=file_format,
                    effective_date=effective_date,
                    parse_status=ParseStatus.pending,
                    parse_log=f"Исходный файл сохранен: {stored_path}\n"
                )
                self.db.add(doc)
                await self.db.commit()
                await self.db.refresh(doc)
                
                documents_to_process.append({
                    "doc_id": doc.id,
                    "file_path": stored_path
                })
                
        return documents_to_process
