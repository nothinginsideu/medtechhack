import typing
from rapidfuzz import fuzz

from app.matching.normalizer import Normalizer
from sqlalchemy.future import select
from app.models.service import Service


class MatchResult(typing.NamedTuple):
    service_id: int
    score: float


# Auto-link above this; below it the item goes to the unmatched queue for review.
AUTO_MATCH_THRESHOLD = 85.0
# Below fuzzy-only floor we don't even consider it a suggestion.
FUZZY_FLOOR = 60.0


class Matcher:
    def __init__(self, db_session, auto_threshold: float = AUTO_MATCH_THRESHOLD):
        self.db = db_session
        self.auto_threshold = auto_threshold
        # (normalized surface, match_terms_cand, cand_words_set, owner service)
        self._entries: list[tuple[str, str, set[str], Service]] = []
        self._by_id: dict[int, Service] = {}
        self.ai_disabled = True  # Disable AI to prevent 5 minute timeouts on rate limit

    async def load_services(self):
        result = await self.db.execute(select(Service))
        services = result.scalars().all()

        self._entries = []
        self._by_id = {s.id: s for s in services}

        for s in services:
            primary = Normalizer.normalize_text(s.name_ru)
            if primary:
                cand = Normalizer.match_terms(primary)
                cand_words = set(Normalizer.tokens(cand))
                self._entries.append((primary, cand, cand_words, s))
            if isinstance(s.synonyms, list):
                for syn in s.synonyms:
                    norm_syn = Normalizer.normalize_text(syn)
                    if norm_syn and norm_syn != primary:
                        cand_syn = Normalizer.match_terms(norm_syn)
                        cand_words_syn = set(Normalizer.tokens(cand_syn))
                        self._entries.append((norm_syn, cand_syn, cand_words_syn, s))

    def exact_match(self, text: str) -> MatchResult | None:
        norm = Normalizer.normalize_text(text)
        if not norm:
            return None
        for surface, _, _, svc in self._entries:
            if norm == surface:
                return MatchResult(svc.id, 100.0)
        return None

    def fuzzy_match(self, text: str) -> MatchResult | None:
        # Strip low-signal filler ("услуга", "исследование", ...) so that
        # "прием терапевта" is compared against catalog entries on the words
        # that actually discriminate one service from another.
        norm = Normalizer.match_terms(text)
        if len(norm) < 3:
            return None

        text_words = set(Normalizer.tokens(norm))
        best_score = 0.0
        best_svc: Service | None = None

        for surface, cand, cand_words, svc in self._entries:
            if not cand:
                continue

            score = fuzz.token_set_ratio(norm, cand)

            # Boost score if a high fraction of catalog words are present in the input
            if score >= 70.0:
                cand_word_list = cand.split()
                norm_word_list = norm.split()
                if len(cand_word_list) > 0:
                    matched_words = sum(1 for w in cand_word_list if w in norm_word_list)
                    coverage = matched_words / len(cand_word_list)
                    if coverage >= 0.6:
                        score = max(score, 86.0)

            if score > best_score:
                best_score = score
                best_svc = svc

        if best_svc is not None and best_score >= FUZZY_FLOOR:
            return MatchResult(best_svc.id, best_score)
        return None

    def match(self, text: str) -> MatchResult | None:
        # 1. Exact match against name + every synonym — high precision.
        res = self.exact_match(text)
        if res:
            return res
        # 2. Weighted fuzzy match.
        fuzzy = self.fuzzy_match(text)
        if fuzzy and fuzzy.score >= self.auto_threshold:
            return fuzzy
        return fuzzy  # caller decides whether to link or queue based on score

    async def ai_match_fallback(self, original_text: str) -> MatchResult | None:
        if self.ai_disabled:
            return None

        from app.core.config import settings
        import google.generativeai as genai
        import json
        import asyncio

        if not settings.GEMINI_API_KEY:
            return None

        norm = Normalizer.normalize_text(original_text)
        if not norm:
            return None

        candidates_map: dict[int, tuple[Service, float]] = {}
        for surface, svc in self._entries:
            score = fuzz.token_set_ratio(norm, surface)
            if svc.id not in candidates_map or score > candidates_map[svc.id][1]:
                candidates_map[svc.id] = (svc, score)

        candidates = sorted(candidates_map.values(), key=lambda x: x[1], reverse=True)[:15]
        if not candidates:
            return None

        candidates_str = "\n".join(f"- ID: {c[0].id}, Название: {c[0].name_ru}" for c in candidates)

        prompt = (
            "Ты — медицинский эксперт-сопоставитель данных.\n"
            f'Дано сырое название услуги из прайс-листа клиники: "{original_text}"\n\n'
            "Среди следующих услуг из эталонного справочника выбери ту, которая является "
            "клиническим синонимом или совпадением (учитывая аббревиатуры, языки, формулировки):\n"
            f"{candidates_str}\n\n"
            "Если точного совпадения или синонима нет — верни null.\n"
            'Ответь строго JSON: {"service_id": <id_или_null>}'
        )

        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: model.generate_content(
                    prompt, generation_config={"response_mime_type": "application/json"}
                ),
            )
            data = json.loads(response.text.strip())
            service_id = data.get("service_id")
            if service_id is not None and int(service_id) in self._by_id:
                return MatchResult(int(service_id), 95.0)
        except Exception as e:
            err = str(e).lower()
            print(f"Ошибка Gemini при сопоставлении: {e}")
            if "quota" in err or "429" in err or "limit" in err:
                self.ai_disabled = True
        return None
