from app.matching.matcher import Matcher
from app.models.service import Service
from app.matching.normalizer import Normalizer
import rapidfuzz

print(Normalizer.match_terms("Прием врача-терапевта первичный"))
