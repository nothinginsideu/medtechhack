import docx
import typing
from app.parsers.base import BaseParser, ParsedItem, detect_currency
from decimal import Decimal, InvalidOperation
import re

class WordParser(BaseParser):
    def parse(self) -> typing.List[ParsedItem]:
        doc = docx.Document(self.file_path)
        items = []
        
        file_currency = detect_currency("", self.file_path)
        
        ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'
        for table in doc.tables:
            for i, tr in enumerate(table._tbl.tr_lst):
                # Пропускаем шапку (грубо)
                if i == 0 and self.config.get("has_header", True):
                    continue
                
                cells = tr.tc_lst
                if len(cells) >= 2:
                    name_cell = " ".join("".join(n.text for n in cell.iter(ns) if getattr(n, 'text', None)).strip() for cell in cells[:-1]).strip()
                    price_cell = "".join(n.text for n in cells[-1].iter(ns) if getattr(n, 'text', None)).strip()
                    
                    if name_cell:
                        try:
                            # Detect currency from cell or filename
                            cell_currency = detect_currency(price_cell)
                            currency = cell_currency if cell_currency != "KZT" else file_currency
                            
                            # Clean price cell
                            price_str = str(price_cell).replace(" ", "").replace(",", ".").replace("тг", "").replace("kzt", "").replace("₸", "").replace("$", "").replace("usd", "").replace("rub", "").replace("руб", "").strip()
                            price_val = Decimal(price_str)
                            
                            # Skip if KZT and price < 100
                            if currency == "KZT" and price_val < Decimal('100'):
                                continue
                                
                            item = ParsedItem(
                                service_name_raw=name_cell,
                                price_resident_kzt=price_val,
                                currency_original=currency
                            )
                            item.validate_prices()
                            items.append(item)
                        except (ValueError, InvalidOperation):
                            continue
                        
        return items

