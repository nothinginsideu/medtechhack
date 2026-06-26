import docx
import typing
from app.parsers.base import BaseParser, ParsedItem
import re

class WordParser(BaseParser):
    def parse(self) -> typing.List[ParsedItem]:
        doc = docx.Document(self.file_path)
        items = []
        
        # Чаще всего прайсы в Word лежат в таблицах
        for table in doc.tables:
            for i, row in enumerate(table.rows):
                # Пропускаем шапку (грубо)
                if i == 0 and self.config.get("has_header", True):
                    continue
                
                cells = row.cells
                if len(cells) >= 2:
                    name_cell = cells[0].text.strip()
                    price_cell = cells[-1].text.strip() # Цена обычно в последней колонке
                    
                    if name_cell:
                        try:
                            price_val = float(str(price_cell).replace(" ", "").replace(",", "."))
                            item = ParsedItem(
                                service_name_raw=name_cell,
                                price_resident_kzt=price_val
                            )
                            item.validate_prices()
                            items.append(item)
                        except ValueError:
                            continue
                        
        return items
