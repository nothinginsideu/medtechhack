import abc
import typing
from pydantic import BaseModel, Field, field_validator

class ParsedItem(BaseModel):
    service_name_raw: str
    price_resident_kzt: float | None = None
    price_nonresident_kzt: float | None = None
    currency_original: str = "KZT"
    service_code_source: str | None = None
    
    @field_validator('price_resident_kzt')
    def check_price(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Цена должна быть больше 0")
        return v
        
    def validate_prices(self):
        # Если есть обе цены, проверим что нерезидент >= резидент
        if self.price_resident_kzt and self.price_nonresident_kzt:
            if self.price_nonresident_kzt < self.price_resident_kzt:
                raise ValueError("Цена нерезидента не может быть меньше цены резидента")


def detect_currency(text: str = "", filename: str = "") -> str:
    """
    Detects the currency (USD, RUB, or defaults to KZT) from a string and/or filename.
    """
    t_lower = text.lower() if text else ""
    f_lower = filename.lower() if filename else ""
    
    if "$" in t_lower or "usd" in t_lower or "$" in f_lower or "usd" in f_lower or "dollar" in f_lower or "доллар" in f_lower:
        return "USD"
    if "rub" in t_lower or "руб" in t_lower or "rub" in f_lower or "руб" in f_lower or "рубл" in f_lower:
        return "RUB"
    return "KZT"


class BaseParser(abc.ABC):
    """
    Базовый класс для всех парсеров прайс-листов.
    """
    def __init__(self, file_path: str, config: dict):
        self.file_path = file_path
        self.config = config

    @abc.abstractmethod
    def parse(self) -> typing.List[ParsedItem]:
        """
        Парсит файл и возвращает список найденных услуг с ценами.
        """
        pass
