import re

class Normalizer:
    @staticmethod
    def normalize_text(text: str) -> str:
        if not text:
            return ""
        
        text = text.lower()
        # Удаляем лишние символы, оставляем буквы и цифры
        text = re.sub(r'[^a-zа-я0-9\s]', ' ', text)
        # Убираем двойные пробелы
        text = re.sub(r'\s+', ' ', text).strip()
        return text
