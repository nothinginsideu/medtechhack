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
        self.service_mapping = []
        self.ai_disabled = False
        
    async def load_services(self):
        """Загружаем эталонный справочник в память для быстрого поиска"""
        result = await self.db.execute(select(Service))
        self.services_cache = result.scalars().all()
        
        self.normalized_services = []
        self.service_mapping = []
        
        for s in self.services_cache:
            # 1. Добавляем основное название
            norm_name = Normalizer.normalize_text(s.name_ru)
            self.normalized_services.append(norm_name)
            self.service_mapping.append(s)
            
            # 2. Добавляем все синонимы (для фичи «Снежный ком»)
            if s.synonyms and isinstance(s.synonyms, list):
                for syn in s.synonyms:
                    norm_syn = Normalizer.normalize_text(syn)
                    if norm_syn:
                        self.normalized_services.append(norm_syn)
                        self.service_mapping.append(s)
        
    def exact_match(self, text: str) -> MatchResult | None:
        norm_text = Normalizer.normalize_text(text)
        for i, norm_svc in enumerate(self.normalized_services):
            if norm_text == norm_svc:
                return MatchResult(service_id=self.service_mapping[i].id, score=100.0)
        return None
        
    def fuzzy_match(self, text: str, threshold: float = 65.0) -> MatchResult | None:
        norm_text = Normalizer.normalize_text(text)
        
        best_score = 0
        best_index = -1
        
        import rapidfuzz
        import re
        
        stop_words = {'терапия', 'прием', 'исследование', 'анализ', 'услуга', 'консультация', 'осмотр', 'процедура', 'диагностика', 'лечение'}
        text_words = set([w for w in re.findall(r'[a-zа-я0-9]+', norm_text) if w not in stop_words])
        
        for i, norm_svc in enumerate(self.normalized_services):
            # token_set_ratio checks word intersection
            set_score = rapidfuzz.fuzz.token_set_ratio(norm_text, norm_svc)
            # token_sort_ratio penalizes size/length mismatch
            sort_score = rapidfuzz.fuzz.token_sort_ratio(norm_text, norm_svc)
            
            # Weighted combination for high accuracy and low false positives
            score = set_score * 0.6 + sort_score * 0.4
            
            # Penalty logic: if meaningful non-stop words have zero intersection, penalize heavily.
            svc_words = set([w for w in re.findall(r'[a-zа-я0-9]+', norm_svc) if w not in stop_words])
            if text_words and svc_words and not text_words.intersection(svc_words):
                score *= 0.5
            
            if score > best_score:
                best_score = score
                best_index = i
                
        if best_score >= threshold and best_index != -1:
            return MatchResult(service_id=self.service_mapping[best_index].id, score=best_score)
                
        return None
        
    def match(self, original_text: str) -> MatchResult | None:
        # Сначала пробуем точное совпадение
        res = self.exact_match(original_text)
        if res:
            return res
            
        # Если не вышло, пробуем нечеткий поиск
        return self.fuzzy_match(original_text)

    async def ai_match_fallback(self, original_text: str) -> MatchResult | None:
        """
        Использование Gemini для сопоставления сложных синонимов по топ-15 кандидатам от RapidFuzz.
        """
        if self.ai_disabled:
            return None

        from app.core.config import settings
        import google.generativeai as genai
        import json
        import asyncio
        
        if not settings.GEMINI_API_KEY:
            return None
            
        norm_text = Normalizer.normalize_text(original_text)
        if not norm_text:
            return None
            
        # 1. Получаем топ-15 уникальных кандидатов через RapidFuzz
        import rapidfuzz
        candidates_map = {}
        for i, norm_svc in enumerate(self.normalized_services):
            score = rapidfuzz.fuzz.token_set_ratio(norm_text, norm_svc)
            svc = self.service_mapping[i]
            if svc.id not in candidates_map or score > candidates_map[svc.id][1]:
                candidates_map[svc.id] = (svc, score)
                
        candidates = sorted(candidates_map.values(), key=lambda x: x[1], reverse=True)[:15]
        if not candidates:
            return None
            
        # Строим список кандидатов для промпта
        candidates_str = "\n".join([f"- ID: {c[0].id}, Название: {c[0].name_ru}" for c in candidates])
        
        prompt = f"""
        Ты — медицинский эксперт-сопоставитель данных.
        Дано сырое название услуги из прайс-листа клиники: "{original_text}"
        
        Среди следующих 15 услуг из эталонного справочника выбери ту, которая является клиническим синонимом или совпадением (учитывая разные аббревиатуры, языки или формулировки):
        {candidates_str}
        
        Требования:
        - Если точного совпадения или синонима нет, верни null.
        - Если есть, выбери наиболее подходящую.
        
        Ответь строго в формате JSON:
        {{"service_id": <выбранный_ID_или_null>}}
        """
        
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            
            # Run in executor to avoid blocking the event loop
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: model.generate_content(
                    prompt, 
                    generation_config={"response_mime_type": "application/json"}
                )
            )
            
            text_response = response.text.strip()
            data = json.loads(text_response)
            service_id = data.get("service_id")
            
            if service_id is not None:
                # Находим соответствующую услугу в кэше
                for svc in self.services_cache:
                    if svc.id == int(service_id):
                        return MatchResult(service_id=svc.id, score=95.0)
        except Exception as e:
            err_str = str(e)
            print(f"Ошибка при гибридном сопоставлении через Gemini: {err_str}")
            if "quota" in err_str.lower() or "429" in err_str or "limit" in err_str.lower():
                print("Gemini API quota exceeded. Disabling AI matching fallback to save API requests and avoid timeout.")
                self.ai_disabled = True
            
        return None
