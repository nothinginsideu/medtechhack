import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import typing
import re
from app.parsers.base import BaseParser, ParsedItem, detect_currency, parse_price, PRICE_PATTERN
from decimal import Decimal, InvalidOperation
import io

class PDFParser(BaseParser):
    def parse(self) -> typing.List[ParsedItem]:
        items = []
        doc = fitz.open(self.file_path)
        
        # 1. Попробуем извлечь текст напрямую (текстовый PDF), группируя слова по Y-координате
        extracted_text = ""
        for page in doc:
            words = page.get_text("words")
            words.sort(key=lambda w: (round(w[1]/5), w[0])) # Группировка с шагом ~5 пикселей
            lines_dict = {}
            for w in words:
                y = round(w[1]/5)
                lines_dict.setdefault(y, []).append(w[4])
            for y in sorted(lines_dict.keys()):
                extracted_text += " ".join(lines_dict[y]) + "\n"
            
        # Если текста мало, скорее всего это скан (нужен OCR)
        if len(extracted_text.strip()) < 100:
            extracted_text = ""
            for i, page in enumerate(doc):
                if i >= 3: # Limit OCR to first 3 pages for speed
                    break
                pix = page.get_pixmap(dpi=100)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                # Tesseract OCR
                text = pytesseract.image_to_string(img, lang="rus+eng")
                extracted_text += text + "\n"

        self.raw_content = extracted_text
                
        # Простой построчный парсер из извлеченного текста
        lines = extracted_text.split('\n')
        
        file_currency = detect_currency("", self.file_path)
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Remove row number from the beginning of the line before extracting prices
            line = re.sub(r'^\d{1,4}[\s.)]+', '', line)
            
            # Detect currency from line or filename
            line_currency = detect_currency(line)
            currency = line_currency if line_currency != "KZT" else file_currency
                
            # Находим все числа, похожие на цены
            prices_str = [match.group(1) for match in PRICE_PATTERN.finditer(line)]
            valid_prices = []
            for p in prices_str:
                try:
                    val = parse_price(p, currency)
                    if val is not None:
                        valid_prices.append(val)
                except (ValueError, InvalidOperation):
                    pass
            
            if valid_prices:
                price_val = valid_prices[0]
                nonresident_val = valid_prices[1] if len(valid_prices) > 1 else None
                
                # Формируем имя услуги, вырезая все найденные цены
                name_raw = line
                for p in prices_str:
                    name_raw = name_raw.replace(p, "")
                
                # Очистка названия
                name_raw = re.sub(r'\s{2,}', ' ', name_raw).strip()
                name_raw = re.sub(r'^\d+[\s.)]*', '', name_raw) # Удаляем порядковый номер
                
                # Фильтруем мусор
                if len(name_raw) < 5:
                    continue
                    
                # Услуга должна содержать хотя бы одну букву
                if not re.search(r'[а-яА-Яa-zA-Z]', name_raw):
                    continue
                    
                # Отсекаем явные заголовки
                lower_name = name_raw.lower()
                if "утвержден" in lower_name or "приказ" in lower_name or "директор" in lower_name:
                    continue
                    
                try:
                    item = ParsedItem(
                        service_name_raw=name_raw,
                        price_resident_kzt=price_val,
                        price_nonresident_kzt=nonresident_val,
                        currency_original=currency
                    )
                    item.validate_prices()
                    items.append(item)
                except ValueError:
                    # Fallback to resident price only
                    try:
                        item = ParsedItem(
                            service_name_raw=name_raw,
                            price_resident_kzt=price_val,
                            currency_original=currency
                        )
                        item.validate_prices()
                        items.append(item)
                    except Exception:
                        pass

        return items
