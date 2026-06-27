import re
import typing
from decimal import Decimal
from app.parsers.base import BaseParser, ParsedItem, detect_currency

class DoclingParser(BaseParser):
    def parse(self) -> typing.List[ParsedItem]:
        from docling.document_converter import DocumentConverter
        
        converter = DocumentConverter()
        result = converter.convert(self.file_path)
        markdown_content = result.document.export_to_markdown()
        
        items = []
        lines = markdown_content.split("\n")
        
        in_table = False
        current_table_headers = []
        current_table_rows = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if in_table:
                if line.startswith("|"):
                    current_table_rows.append(line)
                else:
                    # Table ended, parse it
                    if current_table_headers and current_table_rows:
                        items.extend(self._parse_markdown_table(current_table_headers, current_table_rows))
                    in_table = False
                    current_table_headers = []
                    current_table_rows = []
            else:
                # Detect table start: a line starting with | followed by a separator line
                if line.startswith("|") and i + 1 < len(lines) and re.match(r'^\|\s*[:-]-+[:-]\s*\|', lines[i+1].strip()):
                    in_table = True
                    current_table_headers = [cell.strip() for cell in line.split("|")[1:-1]]
                    # Skip the separator line
                    i += 1
            i += 1
            
        # If file ended while still in a table
        if in_table and current_table_headers and current_table_rows:
            items.extend(self._parse_markdown_table(current_table_headers, current_table_rows))
            
        return items

    def _parse_markdown_table(self, headers: typing.List[str], rows: typing.List[str]) -> typing.List[ParsedItem]:
        parsed_items = []
        
        # Find indexes of key columns
        name_idx = -1
        code_idx = -1
        price_res_idx = -1
        price_nonres_idx = -1
        
        # Normalize headers for matching
        norm_headers = [h.lower() for h in headers]
        
        # Try to find currency indicators in headers and/or filename
        header_text = " ".join(norm_headers)
        header_currency = detect_currency(header_text, self.file_path)
        
        # 1. Look for service name column
        for idx, h in enumerate(norm_headers):
            if any(word in h for word in ["наименование", "услуга", "исследование", "название", "описание", "name", "service"]):
                if not any(code_word in h for code_word in ["код", "шифр", "code", "id", "№", "article"]):
                    name_idx = idx
                    break
        # Fallback for name: first text column that doesn't look like code or price
        if name_idx == -1 and len(headers) >= 2:
            for idx, h in enumerate(norm_headers):
                if not any(word in h for word in ["код", "шифр", "id", "№", "цена", "стоимость", "прайс", "price", "resident", "резидент", "нерезидент"]):
                    name_idx = idx
                    break
            if name_idx == -1:
                name_idx = 0 # Default to first column
                
        # 2. Look for code column
        for idx, h in enumerate(norm_headers):
            if any(word in h for word in ["код", "шифр", "id", "№", "code"]):
                code_idx = idx
                break
                
        # 3. Look for resident price column
        for idx, h in enumerate(norm_headers):
            if "нерезидент" not in h and any(word in h for word in ["резидент", "resident"]):
                price_res_idx = idx
                break
        if price_res_idx == -1:
            for idx, h in enumerate(norm_headers):
                if "нерезидент" not in h and any(word in h for word in ["стоимость", "цена", "прайс", "price", "kzt", "тенге", "тг"]):
                    price_res_idx = idx
                    break
            
        # 4. Look for non-resident price column
        for idx, h in enumerate(norm_headers):
            if any(word in h for word in ["нерезидент", "non-resident", "nonresident", "иностранец"]):
                price_nonres_idx = idx
                break
                
        # Parse rows
        for row in rows:
            cells = [cell.strip() for cell in row.split("|")[1:-1]]
            if len(cells) < len(headers):
                continue
                
            # Service Name
            service_name = cells[name_idx] if name_idx < len(cells) else ""
            if not service_name or service_name.lower() in ["наименование", "услуга", "всего", "итого", "---"]:
                continue
                
            # Clean service name
            service_name = re.sub(r'^\d+[\s.)]*', '', service_name).strip() # Remove numbering
            
            # Service Code
            service_code = cells[code_idx] if (code_idx != -1 and code_idx < len(cells)) else ""
            
            # Price resident
            price_res_val = Decimal('0')
            threshold = Decimal('100') if header_currency == "KZT" else Decimal('1.0')
            if price_res_idx != -1 and price_res_idx < len(cells):
                price_res_val = self._clean_price(cells[price_res_idx])
            else:
                # Fallback: look for the first cell that parses as a float >= threshold
                for idx, cell in enumerate(cells):
                    if idx != name_idx and idx != code_idx:
                        val = self._clean_price(cell)
                        if val >= threshold:
                            price_res_val = val
                            price_res_idx = idx
                            break
                            
            # Price non-resident
            price_nonres_val = Decimal('0')
            if price_nonres_idx != -1 and price_nonres_idx < len(cells):
                price_nonres_val = self._clean_price(cells[price_nonres_idx])
                
            # Detect currency for the row
            price_cell_text = cells[price_res_idx] if (price_res_idx != -1 and price_res_idx < len(cells)) else ""
            cell_currency = detect_currency(price_cell_text)
            currency = cell_currency if cell_currency != "KZT" else header_currency
                
            # Skip header replication rows or empty rows
            if not service_name or len(service_name) < 3:
                continue
            if not re.search(r'[а-яА-Яa-zA-Z]', service_name):
                continue
            if price_res_val <= Decimal('0') and price_nonres_val <= Decimal('0'):
                continue
                
            # Attempt to instantiate ParsedItem with non-resident validation
            try:
                item = ParsedItem(
                    service_name_raw=service_name,
                    price_resident_kzt=price_res_val if price_res_val > Decimal('0') else None,
                    price_nonresident_kzt=price_nonres_val if price_nonres_val > Decimal('0') else None,
                    currency_original=currency,
                    service_code_source=service_code if service_code else None
                )
                item.validate_prices()
                parsed_items.append(item)
            except (ValueError, TypeError):
                # Validation fallback: omit invalid non-resident price
                try:
                    item = ParsedItem(
                        service_name_raw=service_name,
                        price_resident_kzt=price_res_val if price_res_val > Decimal('0') else None,
                        currency_original=currency,
                        service_code_source=service_code if service_code else None
                    )
                    parsed_items.append(item)
                except Exception:
                    continue
            
        return parsed_items

    def _clean_price(self, price_str: str) -> Decimal:
        # Extract first numeric sequence, ignore whitespace/currencies
        match = re.search(r'\b([1-9]\d{0,2}(?:\s?\d{3})*(?:[.,]\d{1,2})?)\b', price_str)
        if match:
            try:
                val_str = match.group(1).replace(" ", "").replace(",", ".")
                return Decimal(val_str)
            except (ValueError, ArithmeticError):
                pass
        return Decimal('0')

