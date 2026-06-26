import docx
import typing
from app.parsers.base import BaseParser, ParsedItem
import re

class WordParser(BaseParser):
    def parse(self) -> typing.List[ParsedItem]:
        doc = docx.Document(self.file_path)
        items = []
        
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
