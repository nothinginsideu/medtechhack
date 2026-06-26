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
