import requests
import json


BASE_API = "http://localhost:8000/api/search/search"


def run_query(query, api=BASE_API):
    """"""
    if query and api:
        r = requests.post(url=api, json=query)
        if r.status_code == requests.codes.ok:
            return r.status_code, r.json()
        else:
            return r.status_code, None


test_queries = [
    {"query": {"fulltext": "Coreanica"}, "label": "Fulltext: Western text within value list"},
    {
        "query": {"fulltext": "Bundesregierung"},
        "label": "Fulltext: Western text word within phrase",
    },
    {"query": {"fulltext": "京城書籍業組合"}, "label": "Fulltext: Entire matching field (Chinese)"},
    {"query": {"fulltext": "rhubarb"}, "label": "Fulltext: Term that does not appear in text"},
    {
        "query": {"fulltext": "京城 [서울]"},
        "label": "Fulltext: Entire matching field (Chinese AND Korean)",
    },
    {"query": {"fulltext": "[서울]"}, "label": "Fulltext: space-delimited part of field (Korean)"},
    {"query": {"fulltext": "울"}, "label": "Fulltext: non-space-delimited part of field (Korean)"},
    {
        "query": {"fulltext": "전심쳥젼"},
        "label": "Fulltext: non-space-delimited part of field "
        "(Chinese example from MAD-668)",
    },
    {
        "query": {"raw": {"indexables__original_content__icontains": "울"}},
        "label": "Raw (Original content): icontains for non-space-delimited part of field (Korean)",
    },
    {
        "query": {"raw": {"indexables__indexable__icontains": "울"}},
        "label": "Raw (Indexable): icontains for non-space-delimited part of field (Korean)",
    },
    {
        "query": {"raw": {"indexables__original_content__icontains": "전심쳥젼"}},
        "label": "Raw (Original content): icontains for non-space-delimited part of field "
        "(Chinese example from MAD-668)",
    },
    {
        "query": {"raw": {"indexables__indexable__icontains": "전심쳥젼"}},
        "label": "Raw (Indexable): icontains for non-space-delimited part of field "
        "(Chinese example from MAD-668)",
    },
    {
        "query": {"raw": {"indexables__indexable__regex": f"(전심쳥젼?)"}},
        "label": "Raw (Indexable): regex for non-space-delimited part of field "
                 "(Chinese example from MAD-668)",
    },
    {
        "query": {"raw": {"indexables__indexable__regex": f"^(洪淳?)"}},
        "label": "Raw (Indexable): regex for start of field "
                 "(Chinese example from MAD-668)",
    },
    {
        "query": {"raw": {"indexables__indexable__regex": f"^(傳심청전?)"}},
        "label": "Raw (Indexable): regex for start of field which should fail to match "
                 "(Chinese example from MAD-668)",
    },
]

results = {}

for q in test_queries:
    summary = None
    status, result = run_query(q["query"])
    if result:
        if result.get("pagination"):
            summary = {"totalResults": result["pagination"].get("totalResults")}
    results[q["label"]] = {"status_code": status, "result": summary, "query": q["query"]}

print(json.dumps(results, indent=2, ensure_ascii=False))
