import re


class Normalizer:
    # Prepositions / conjunctions / filler — safe to drop before comparison.
    STOP_WORDS = {
        "в", "во", "на", "и", "или", "с", "со", "по", "для", "при",
        "тг", "тенге", "kzt", "руб", "рубль",
    }

    # Words that carry almost no discriminative signal between medical services.
    # Lowercased; dropped only during matching, never during indexing of the catalog name.
    GENERIC_TOKENS = {
        "услуга", "услуги", "цена", "цены", "стоимость",
        "клиника", "клиники", "центр", "исследование", "исследований",
        "определение", "метод", "методом", "ручным",
        "количественное", "качественное", "прием", "консультация",
        "врача", "врач", "взрослый", "детский", "первичный", "повторный",
        "специалиста", "проведение", "лечение", "лечения", "диагностика",
        "check", "up", "анализаторе", "анализатор", "однократно",
        "последующим", "расчетом", "отношения", "воз", "мо30", "сн", "в04", "в06", "операция",
        "параметр", "параметра", "параметров", "класс", "классов", "класса",
        "средней", "тяжести", "сыворотка", "сыворотке", "сыворотк"
    }

    # Medical abbreviations to expand for honest high-confidence matching
    ABBREVIATIONS = {
        "мрт": "магнитно резонансная томография",
        "кт": "компьютерная томография",
        "узи": "ультразвуковое",
        "экг": "электрокардиография",
        "рентген": "рентгенография",
        "фгдс": "фиброгастродуоденоскопия",
        "ээг": "электроэнцефалография",
        "оак": "общий анализ крови",
        "оам": "общий анализ мочи",
        "алт": "аланинаминотрансфераза",
        "аст": "аспартатаминотрансфераза",
        "пти": "протромбиновое",
        "лпвп": "липопротеиды высокой плотности",
        "лпнп": "липопротеиды низкой плотности",
    }

    @staticmethod
    def normalize_text(text: str) -> str:
        if not text:
            return ""

        # Strip leading service codes ("EN23.", "B05.015.001", "UZ21.32 -", "LA. 001.003:")
        text = re.sub(r'^[a-z0-9.\-/ ]{2,15}[.:\- ]+', '', text, flags=re.IGNORECASE)

        text = text.lower()
        text = re.sub(r'[^a-zа-я0-9 ]', ' ', text)

        words = text.split()
        
        # Expand abbreviations honestly
        expanded_words = []
        for w in words:
            if w in Normalizer.ABBREVIATIONS:
                expanded_words.extend(Normalizer.ABBREVIATIONS[w].split())
            else:
                expanded_words.append(w)
                
        filtered = [w for w in expanded_words if w not in Normalizer.STOP_WORDS]
        return re.sub(r'\s+', ' ', " ".join(filtered)).strip()

    @staticmethod
    def tokens(text: str) -> list[str]:
        return [w for w in Normalizer.normalize_text(text).split() if len(w) >= 2]

    @staticmethod
    def match_terms(text: str) -> str:
        """Normalized text with low-signal medical filler removed — for fuzzy comparison only."""
        valid_words = [
            Normalizer.stem_word(w) for w in Normalizer.normalize_text(text).split()
            if w not in Normalizer.GENERIC_TOKENS and len(w) >= 2
        ]
        return " ".join(valid_words)

    @staticmethod
    def stem_word(word: str) -> str:
        word = word.lower().strip().replace("ё", "е")
        suffixes = (
            "иями", "ями", "ами", "ого", "его", "ому", "ему", "ими", "ыми",
            "ая", "ое", "ые", "ых", "их", "ам", "ям", "ом", "ем", "ой",
            "ей", "ий", "ый", "а", "я", "о", "е", "и", "ы", "у", "ю", "ь",
        )
        for suffix in suffixes:
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                return word[:-len(suffix)]
        return word

    @staticmethod
    def search_terms(text: str) -> list[str]:
        terms: list[str] = []
        for token in Normalizer.tokens(text):
            stemmed = Normalizer.stem_word(token)
            if stemmed and stemmed not in terms:
                terms.append(stemmed)
        return terms
