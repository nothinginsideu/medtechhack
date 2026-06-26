import zipfile
import io
import os
import re
from datetime import date
from rapidfuzz import process
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.partner import Partner
from app.models.price_document import PriceDocument, FileFormat, ParseStatus
from app.parsers import get_parser

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
        Извлекает год из имени файла (например, '...прайс 2026.pdf').
        Если год не найден, возвращает текущую дату.
        """
        match = re.search(r'\b(20\d{2})\b', filename)
        if match:
            year = int(match.group(1))
            return date(year, 1, 1)
        return date.today()

    def _find_partner_by_filename(self, filename: str) -> Partner:
        """
        Определяет партнера по имени файла с помощью RapidFuzz.
        """
        if not self.partners:
            return None
        
        partner_names = {p.id: p.name for p in self.partners}
        base_name = os.path.splitext(os.path.basename(filename))[0]
        
        best_match = process.extractOne(base_name, partner_names)
        if best_match and best_match[1] > 60: # Порог уверенности 60%
            partner_id = best_match[2]
            return next((p for p in self.partners if p.id == partner_id), None)
        return None

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
                
                filename = os.path.basename(file_info.filename)
                if not filename:
                    continue

                file_format = self._determine_format(filename)
                if not file_format:
                    continue

                partner = self._find_partner_by_filename(filename)
                if not partner:
                    print(f"Партнер не найден для файла: {filename}")
                    continue

                effective_date = self._extract_date_from_filename(filename)

                temp_dir = "/tmp/medpartners_uploads"
                os.makedirs(temp_dir, exist_ok=True)
                temp_path = os.path.join(temp_dir, filename)
                
                with open(temp_path, "wb") as f:
                    f.write(archive.read(file_info.filename))

                doc = PriceDocument(
                    partner_id=partner.id,
                    file_name=filename,
                    file_format=file_format,
                    effective_date=effective_date,
                    parse_status=ParseStatus.pending
                )
                self.db.add(doc)
                await self.db.commit()
                await self.db.refresh(doc)
                
                documents_to_process.append({
                    "doc_id": doc.id,
                    "file_path": temp_path
                })
                
        return documents_to_process
