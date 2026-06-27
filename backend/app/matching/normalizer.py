import re

class Normalizer:
    @staticmethod
    def normalize_text(text: str) -> str:
        if not text:
            return ""
        
        # Remove leading codes (e.g. "EN23. ", "B05.015.001 ", "UZ21.32 - ", "LA. 001.003: ")
        text = re.sub(r'^[a-z0-9\.\-\/\s]{2,15}[\.\:\-\s]+', '', text, flags=re.IGNORECASE)
        
        text = text.lower()
        # Удаляем лишние символы, оставляем буквы и цифры
        text = re.sub(r'[^a-zа-я0-9\s]', ' ', text)
        
        # Фильтруем общие медицинские стоп-слова для повышения точности нечеткого поиска
        stop_words = {
            'исследование', 'исследований', 'анализатор', 'анализаторе',
            'определение', 'метод', 'методом', 'ручным', 'количественное', 'качественное'
        }
        words = text.split()
        filtered_words = [w for w in words if w not in stop_words]
        text = " ".join(filtered_words)
        
        # Убираем двойные пробелы
        text = re.sub(r'\s+', ' ', text).strip()
        return text
