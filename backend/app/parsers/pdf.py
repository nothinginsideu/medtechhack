import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import typing
import re
from app.parsers.base import BaseParser, ParsedItem
import io

class PDFParser(BaseParser):
    def parse(self) -> typing.List[ParsedItem]:
        items = []
        doc = fitz.open(self.file_path)
        
        # 1. Попробуем извлечь текст напрямую (текстовый PDF)
        extracted_text = ""
        for page in doc:
            extracted_text += page.get_text("text") + "\n"
            
        # Если текста мало, скорее всего это скан (нужен OCR)
        if len(extracted_text.strip()) < 100:
            extracted_text = ""
            for page in doc:
                pix = page.get_pixmap(dpi=150)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                # Tesseract OCR
                text = pytesseract.image_to_string(img, lang="rus+eng")
                extracted_text += text + "\n"
                
        # Простой построчный парсер из извлеченного текста
        lines = extracted_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Ищем паттерн: "какой-то текст услуги ... цена"
            # Простой RegEx для вытаскивания цены из конца строки
            match = re.search(r'(.*?)(?:[\s\.]+|)(\d+[\d\s]*)(?:тг|kzt|₸|)$', line, flags=re.IGNORECASE)
            
            if match:
                name_raw = match.group(1).strip()
                price_str = match.group(2).replace(" ", "")
                
                # Фильтруем мусор
                if len(name_raw) < 5 or not price_str.isdigit():
                    continue
                    
                try:
                    price_val = float(price_str)
                    
                    # Игнорируем подозрительно маленькие "цены" (возможно номера страниц)
                    if price_val < 100:
                        continue

                    item = ParsedItem(
                        service_name_raw=name_raw,
                        price_resident_kzt=price_val
                    )
                    item.validate_prices()
                    items.append(item)
                except ValueError:
                    continue

        return items
