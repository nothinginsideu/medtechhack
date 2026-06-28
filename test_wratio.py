from rapidfuzz import fuzz
print(fuzz.WRatio("Прием врача кардиолога", "Консультация кардиолога"))
print(fuzz.token_set_ratio("Прием врача кардиолога", "Консультация кардиолога"))
