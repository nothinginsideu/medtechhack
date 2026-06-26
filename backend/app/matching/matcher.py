import typing
from app.matching.normalizer import Normalizer
from sqlalchemy.future import select
from app.models.service import Service
import difflib

class MatchResult(typing.NamedTuple):
    service_id: int
    score: float

class Matcher:
    def __init__(self, db_session):
        self.db = db_session
        self.services_cache = []
        self.normalized_services = []
        
    async def load_services(self):
        """Загружаем эталонный справочник в память для быстрого поиска"""
        result = await self.db.execute(select(Service))
        self.services_cache = result.scalars().all()
        
        # Предрасчет нормализованных названий для быстрого fuzzy-поиска
        self.normalized_services = [
            Normalizer.normalize_text(s.name_ru) for s in self.services_cache
        ]
        
    def exact_match(self, text: str) -> MatchResult | None:
        norm_text = Normalizer.normalize_text(text)
        for i, norm_svc in enumerate(self.normalized_services):
            if norm_text == norm_svc:
                return MatchResult(service_id=self.services_cache[i].id, score=100.0)
        return None
        
    def fuzzy_match(self, text: str, threshold: float = 65.0) -> MatchResult | None:
        norm_text = Normalizer.normalize_text(text)
        
        best_score = 0
        best_index = -1
        
        import rapidfuzz
        for i, norm_svc in enumerate(self.normalized_services):
            # token_set_ratio игнорирует лишние слова (например "у взрослых"), 
            # что кардинально повышает точность авто-сопоставления
            score = rapidfuzz.fuzz.token_set_ratio(norm_text, norm_svc)
            if score > best_score:
                best_score = score
                best_index = i
                
        if best_score >= threshold and best_index != -1:
            return MatchResult(service_id=self.services_cache[best_index].id, score=best_score)
                
        return None
        
    def match(self, original_text: str) -> MatchResult | None:
        # Сначала пробуем точное совпадение
        res = self.exact_match(original_text)
        if res:
            return res
            
        # Если не вышло, пробуем нечеткий поиск
        return self.fuzzy_match(original_text)
