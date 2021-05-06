import requests
import json
from langdetect import detect
import unicodedata

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
    {
        "query": {"fulltext": "京城 洪淳"},
        "label": "Fulltext: Space separated terms from two different fields",
    },
    {"query": {"fulltext": "[서울]"}, "label": "Fulltext: space-delimited part of field (Korean)"},
    {"query": {"fulltext": "울"}, "label": "Fulltext: non-space-delimited part of field (Korean)"},
    {
        "query": {"fulltext": "전심쳥젼"},
        "label": "Fulltext: non-space-delimited part of field " "(Chinese example from MAD-668)",
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
        "label": "Raw (Indexable): regex for start of field " "(Chinese example from MAD-668)",
    },
    {
        "query": {"raw": {"indexables__indexable__regex": f"^(傳심청전?)"}},
        "label": "Raw (Indexable): regex for start of field which should fail to match "
        "(Chinese example from MAD-668)",
    },
]


def is_latin(text):
    return all(
        [
            (
                "LATIN" in unicodedata.name(x)
                or unicodedata.category(x).startswith("P")
                or unicodedata.category(x).startswith("N")
                or unicodedata.category(x).startswith("Z")
            )
            for x in text
        ]
    )


def fixed_queries():
    fixed_results = {}
    for q in test_queries:
        fixed_summary = None
        for k, v in q["query"].items():
            test_query = q["query"]
            if k == "fulltext":
                if not is_latin(v):
                    test_query = {"raw": {"indexables__indexable__icontains": v}}
        fixed_status, fixed_result = run_query(test_query)
        if fixed_result:
            if result.get("pagination"):
                fixed_summary = {"totalResults": fixed_result["pagination"].get("totalResults")}
        fixed_results[q["label"]] = {
            "status_code": fixed_status,
            "result": fixed_summary,
            "query": q["query"],
            "processed_query": test_query,
        }
    return fixed_results


if __name__ == "__main__":
    results = {}

    for q in test_queries:
        summary = None
        status, result = run_query(q["query"])
        if result:
            if result.get("pagination"):
                summary = {"totalResults": result["pagination"].get("totalResults")}
        results[q["label"]] = {"status_code": status, "result": summary, "query": q["query"]}
    # print(json.dumps(results, indent=2, ensure_ascii=False))
    f = fixed_queries()
    print(json.dumps(f, indent=2, ensure_ascii=False))

