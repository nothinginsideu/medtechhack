import openpyxl
import typing
from app.parsers.base import BaseParser, ParsedItem
import re

class ExcelParser(BaseParser):
    def parse(self) -> typing.List[ParsedItem]:
        wb = openpyxl.load_workbook(self.file_path, data_only=True)
        sheet = wb.active
        
        items = []
        name_col = self.config.get("name_col", "A")
        price_col = self.config.get("price_col", "B")
        skip_rows = self.config.get("skip_rows", 1)
        
        for i, row in enumerate(sheet.iter_rows()):
            if i < skip_rows:
                continue
                
            # openpyxl col indices are 0-based in iter_rows, but config gives 'A', 'B'
            # Convert 'A' to 0, 'B' to 1
            name_idx = ord(name_col.upper()) - 65
            price_idx = ord(price_col.upper()) - 65
            
            if len(row) > max(name_idx, price_idx):
                name_val = row[name_idx].value
                price_val = row[price_idx].value
                
                name_cell = row[name_idx].value
                price_cell = row[price_idx].value
                
                if name_cell and isinstance(name_cell, str) and name_cell.strip():
                    try:
                        price_val = float(str(price_cell).replace(" ", "").replace(",", "."))
                        
                        item = ParsedItem(
                            service_name_raw=name_cell,
                            price_resident_kzt=price_val,
                            service_code_source=str(row[0]) if row[0] else None
                        )
                        # Прогоняем валидацию
                        item.validate_prices()
                        items.append(item)
                    except ValueError:
                        continue
                    
        return items
