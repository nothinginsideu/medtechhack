import openpyxl
import typing
from app.parsers.base import BaseParser, ParsedItem, detect_currency
import re

class ExcelParser(BaseParser):
    def parse(self) -> typing.List[ParsedItem]:
        import os
        ext = os.path.splitext(self.file_path)[1].lower()
        
        rows_data = []
        if ext == ".xls":
            import xlrd
            wb = xlrd.open_workbook(self.file_path)
            sheet = wb.sheet_by_index(0)
            rows_data = [sheet.row_values(i) for i in range(sheet.nrows)]
        else:
            import openpyxl
            wb = openpyxl.load_workbook(self.file_path, data_only=True)
            sheet = wb.active
            rows_data = list(sheet.iter_rows(values_only=True))
        
        items = []
        
        # Auto-detect columns
        name_idx = -1
        price_idx = -1
        header_currency = "KZT"
        
        # Поиск заголовков
        for row_idx, row in enumerate(rows_data[:30]):
            for col_idx, cell in enumerate(row):
                if isinstance(cell, str):
                    val = cell.lower()
                    if "наименование" in val or "услуга" in val:
                        name_idx = col_idx
                    if ("цена" in val or "стоимость" in val or "тенге" in val or "граждан" in val) and price_idx == -1:
                        price_idx = col_idx
                        header_currency = detect_currency(val, self.file_path)
            
            if name_idx != -1 and price_idx != -1:
                break
                
        # Фоллбэк: если заголовки не найдены, ищем колонку с длинным текстом и колонку с числами
        if name_idx == -1 or price_idx == -1:
            name_idx, price_idx = 1, 4 # Дефолт для Клиники 8
            header_currency = detect_currency("", self.file_path)
            
        for i, row in enumerate(rows_data):
            if i < 3: # Пропускаем хидеры
                continue
                
            if len(row) > max(name_idx, price_idx):
                name_cell = row[name_idx]
                price_cell = row[price_idx]
                
                if name_cell and isinstance(name_cell, str) and len(name_cell.strip()) > 5:
                    try:
                        # Очистка цены и определение валюты
                        cell_str = str(price_cell)
                        cell_currency = detect_currency(cell_str)
                        currency = cell_currency if cell_currency != "KZT" else header_currency
                        
                        price_str = cell_str.replace(" ", "").replace(",", ".").replace("тг", "").replace("kzt", "").replace("₸", "").replace("$", "").replace("usd", "").replace("rub", "").replace("руб", "").strip()
                        price_val = float(price_str)
                        
                        if currency == "KZT" and price_val < 100:
                            continue
                        
                        item = ParsedItem(
                            service_name_raw=name_cell.strip(),
                            price_resident_kzt=price_val,
                            currency_original=currency,
                            service_code_source=str(row[0]) if row[0] else None
                        )
                        item.validate_prices()
                        items.append(item)
                    except ValueError:
                        continue
                        
        return items

