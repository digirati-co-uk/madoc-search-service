from langdetect import detect
from queries import test_queries
import json
import unicodedata

results = {}


def is_latin(text):
    return all([('LATIN' in unicodedata.name(x) or unicodedata.category(x).startswith('P')
                 or unicodedata.category(x).startswith('N') or
                 unicodedata.category(x).startswith('Z')) for x in text])


for q in test_queries:
    for k, v in q["query"].items():
        test_val = None
        if isinstance(v, str):
            test_val = v
        elif isinstance(v, dict):
            for _, val in v.items():
                test_val = val
        try:
            val_lang = detect(test_val)
            results[q["label"]] = {"query_string": test_val, "language_code": val_lang,
                                   "latin": is_latin(test_val)}
        except TypeError:
            results[q["label"]] = {"query_string": test_val, "language_code": None,
                                   "latin": is_latin(test_val)}
#
# print(json.dumps(results, indent=2, ensure_ascii=False))
print(is_latin("Kdy odlétá příští letadlo do Prahy?"))
print(is_latin("Все люди рождаются"))
