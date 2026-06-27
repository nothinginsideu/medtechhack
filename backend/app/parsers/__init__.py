from app.parsers.excel import ExcelParser
from app.parsers.word import WordParser
from app.parsers.pdf import PDFParser
from app.parsers.docling_parser import DoclingParser
import os

def get_parser(file_path: str, config: dict):
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in [".xlsx", ".xls"]:
        return ExcelParser(file_path, config)
    elif ext == ".docx":
        return DoclingParser(file_path, config)
    elif ext == ".pdf":
        return DoclingParser(file_path, config)
    else:
        raise ValueError(f"Неподдерживаемый формат файла: {ext}")
