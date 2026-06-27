from app.parsers.excel import ExcelParser
from app.parsers.word import WordParser
from app.parsers.pdf import PDFParser
from app.parsers.docling_parser import DoclingParser
from app.parsers.base import BaseParser
import os
import typing
from app.parsers.base import ParsedItem

class HybridParser(BaseParser):
    def __init__(self, file_path: str, config: dict, primary_parser_class):
        super().__init__(file_path, config)
        self.primary_parser_class = primary_parser_class

    def parse(self) -> typing.List[ParsedItem]:
        try:
            # First try the lightweight parser
            primary_parser = self.primary_parser_class(self.file_path, self.config)
            items = primary_parser.parse()
            
            # If we extracted some items, assume it worked well enough
            if len(items) > 5:
                return items
        except Exception:
            pass
            
        # Fallback to the heavy parser
        fallback_parser = DoclingParser(self.file_path, self.config)
        return fallback_parser.parse()

def get_parser(file_path: str, config: dict):
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in [".xlsx", ".xls"]:
        return ExcelParser(file_path, config)
    elif ext == ".docx":
        return HybridParser(file_path, config, WordParser)
    elif ext == ".pdf":
        return HybridParser(file_path, config, PDFParser)
    else:
        raise ValueError(f"Неподдерживаемый формат файла: {ext}")
