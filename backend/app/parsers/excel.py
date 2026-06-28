import openpyxl
import typing
from app.parsers.base import BaseParser, ParsedItem, detect_currency, parse_price
from decimal import Decimal, InvalidOperation
import re

class ExcelParser(BaseParser):
    def parse(self) -> typing.List[ParsedItem]:
        import os
        ext = os.path.splitext(self.file_path)[1].lower()
        
        sheets_rows = []
        if ext == ".xls":
            import xlrd
            wb = xlrd.open_workbook(self.file_path)
            for sheet in wb.sheets():
                sheets_rows.append((sheet.name, [sheet.row_values(i) for i in range(sheet.nrows)]))
        else:
            wb = openpyxl.load_workbook(self.file_path, data_only=True)
            for sheet in wb.worksheets:
                sheets_rows.append((sheet.title, list(sheet.iter_rows(values_only=True))))
        
        items = []
        raw_lines = []
        
        for sheet_name, rows_data in sheets_rows:
            name_idx = -1
            price_idx = -1
            nonresident_idx = -1
            code_idx = 0
            header_row = 0
            header_currency = detect_currency("", self.file_path)

            for row_idx, row in enumerate(rows_data[:40]):
                raw_lines.append(" | ".join("" if c is None else str(c) for c in row))
                for col_idx, cell in enumerate(row):
                    if not isinstance(cell, str):
                        continue
                    val = cell.lower()
                    if any(word in val for word in ["код", "шифр", "code"]) and code_idx == 0:
                        code_idx = col_idx
                    if any(word in val for word in ["наименование", "название", "услуга", "исследование"]):
                        name_idx = col_idx
                    if "нерезидент" in val or "иностранец" in val:
                        nonresident_idx = col_idx
                    if nonresident_idx != col_idx and any(word in val for word in ["цена", "стоимость", "тенге", "тг", "резидент"]):
                        if price_idx == -1 and "нерезидент" not in val:
                            price_idx = col_idx
                            header_currency = detect_currency(val, self.file_path)

                if name_idx != -1 and price_idx != -1:
                    header_row = row_idx
                    break

            if name_idx == -1 or price_idx == -1:
                continue

            for row in rows_data[header_row + 1:]:
                if len(row) <= max(name_idx, price_idx, nonresident_idx, code_idx):
                    continue

                name_cell = row[name_idx]
                if not isinstance(name_cell, str) or len(name_cell.strip()) < 5:
                    continue
                if name_cell.strip().lower() in {"итого", "всего", "наименование", "услуга"}:
                    continue

                cell_currency = detect_currency(str(row[price_idx]))
                currency = cell_currency if cell_currency != "KZT" else header_currency
                price_val = None
                actual_price_idx = price_idx
                for offset in range(5):
                    if price_idx + offset < len(row):
                        p_val = parse_price(row[price_idx + offset], currency)
                        if p_val is not None:
                            price_val = p_val
                            actual_price_idx = price_idx + offset
                            break
                
                if price_val is None:
                    continue

                nonresident_val = None
                if nonresident_idx != -1:
                    for offset in range(5):
                        if nonresident_idx + offset < len(row) and (nonresident_idx + offset) != actual_price_idx:
                            n_val = parse_price(row[nonresident_idx + offset], currency)
                            if n_val is not None:
                                nonresident_val = n_val
                                break

                try:
                    item = ParsedItem(
                        service_name_raw=name_cell.strip(),
                        price_resident_kzt=price_val,
                        price_nonresident_kzt=nonresident_val,
                        currency_original=currency,
                        service_code_source=str(row[code_idx]).strip() if row[code_idx] else None
                    )
                    item.validate_prices()
                    items.append(item)
                except (ValueError, InvalidOperation):
                    continue
                        
        self.raw_content = "\n".join(raw_lines)
        return items
