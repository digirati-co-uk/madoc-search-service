import requests
import json


def test_ingest():
    collections = [
        # "https://iiif.ub.uni-leipzig.de/static/collections/Drucke17/collection.json",
        "https://iiif.hab.de/collection/project/mssox.json",
        "https://www.e-codices.unifr.ch/metadata/iiif/collection/sl.json",
        "https://digital.library.villanova.edu/Collection/vudl:294849/IIIF",
        "https://view.nls.uk/collections/7446/74466699.json",
        "https://wellcomelibrary.org/service/collections/topics/Alcoholism/",
        "https://wellcomelibrary.org/service/collections/topics/dragons/",
    ]
    for coll in collections:
        collection = requests.get(coll).json()
        manifests = collection.get("members", collection.get("manifests", None))
        for m in manifests:
            print(m["@id"])
            r = requests.get(m["@id"])
            if r.status_code == requests.codes.ok:
                j = r.json()
            else:
                j = None
            if j:
                post_json = {
                    "contexts": [  # List of contexts with their id and type
                        {"id": "urn:madoc:site:2", "type": "Site"},
                        {"id": coll, "type": "Collection"},
                    ],
                    "resource": j,  # this is the JSON for the IIIF resource
                    "id": f"urn:madoc:manifest:{m['@id'].split('/')[-2]}",  # Madoc ID for the subject/object
                    "thumbnail": f"http://madoc.foo/thumbnail/{m['@id'].split('/')[-2]}/fake.jpg",  # Thumbnail URL
                    "cascade": False,
                }
                headers = {"Content-Type": "application/json", "Accept": "application/json"}
                p = requests.post(
                    url="http://localhost:8000/api/search/iiif", json=post_json, headers=headers
                )
                print(p.status_code)


def test_faceted_query():
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    query = {
        "fulltext": "Abbey",
        "facet_fields": [
            "text language",
            "place of origin (english)",
            "collection name",
            "publisher",
            "persons",
            "material",
            "location",
        ],
        "contexts": ["urn:madoc:site:2"],
        "facets": [
            # {
            #     "type": "metadata",
            #     "subtype": "collection name",
            #     "value": "Staat",
            #     "field_lookup": "istartswith",
            # },
            # {"type": "metadata", "subtype": "material", "value": "paper"},
            {"type": "metadata", "subtype": "material", "value": "parchment"},
            # {"type": "metadata", "subtype": "text language", "value": "German"},
            # {
            #     "type": "metadata",
            #     "subtype": "text language",
            #     "value": "French",
            # },
            # {
            #     "type": "metadata",
            #     "subtype": "text language",
            #     "value": "Latin",
            # },
            # {"type": "metadata", "subtype": "author", "value": "Smith, John"},
        ],
    }
    #
    # query = {
    #     "fulltext": "Götter",
    #     "search_language": "german",
    #     "contexts": ["urn:madoc:site:2"],
    #     "facets": [
    #         {"type": "metadata", "subtype": "place of publication", "value": "Hamburg"},
    #     ]
    # }
    print(json.dumps(query, indent=2))
    r = requests.post("http://localhost:8000/api/search/search", json=query, headers=headers)
    if r.status_code == requests.codes.ok:
        j = r.json()
        # assert j["pagination"]["totalResults"] != 4
        print(json.dumps(j, indent=2, ensure_ascii=False))


def test_ocr():
    # m = "https://wellcomelibrary.org/iiif/b28034831/manifest"
    # j = requests.get(m).json()
    # if j:
    #     post_json = {
    #         "contexts": [  # List of contexts with their id and type
    #             {"id": "urn:madoc:site:2", "type": "Site"},
    #         ],
    #         "resource": j,  # this is the JSON for the IIIF resource
    #         "id": f"urn:madoc:manifest:{j['@id'].split('/')[-2]}",  # Madoc ID for the subject/object
    #         "thumbnail": f"http://madoc.foo/thumbnail/{j['@id'].split('/')[-2]}/fake.jpg",  # Thumbnail URL
    #         "cascade": True,
    #     }
    # else:
    #     post_json = None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    # if post_json:
    #     p = requests.post(
    #         url="http://localhost:8000/api/search/iiif", json=post_json, headers=headers
    #     )
    #     print(p.status_code)
    # https://wellcomelibrary.org/service/alto/b28034831/0?image=11
    # https://wellcomelibrary.org/iiif/b28034831/canvas/c11
    post_json = {
        "xresource_id": "urn:madoc:manifest:b28034831:canvas:11",
        "xcontent_id": "urn:madoc:manifest:b28034831:canvas:11:ocr",
        "xresource": requests.get(
            "http://madoc.dlcs.digirati.io/public/storage/urn:madoc:site:1/canvas-ocr/public/255/mets-alto.json"
        ).json(),
    }
    print(post_json)
    p = requests.post(url="http://localhost:8000/api/search/ocr", json=post_json, headers=headers)
    # p = requests.put(url="http://localhost:8000/api/search/indexables/158909", json=post_json,
    #                  headers=headers)
    print(p.status_code)
    print(p.json())


test_model = {
    "id": "e6533db2-86aa-460b-bcee-de29e9e737f8",
    "structure": {
        "id": "d0a92a65-2658-46fe-bc14-e5091ef4880d",
        "type": "choice",
        "label": "Bridges",
        "items": [
            {
                "id": "c8f44c56-e049-4803-acbc-8409452e7d81",
                "type": "model",
                "label": "Region of interest",
                "fields": ["region"],
            }
        ],
    },
    "document": {
        "id": "b72038ee-afa9-4a18-b5e6-22ad87f02c8d",
        "type": "entity",
        "label": "Untitled document",
        "properties": {
            "region": [
                {
                    "id": "71961317-6cbc-4c66-9777-14eea82942fe",
                    "type": "text-field",
                    "label": "Region of interest",
                    "value": "",
                    "allowMultiple": True,
                    "selector": {
                        "id": "3f276a4f-2910-4dc7-bff1-08f09a67ef63",
                        "type": "box-selector",
                        "state": None,
                    },
                },
                {
                    "id": "b3acb642-f3d3-4f33-85cc-9008b600cd2d",
                    "type": "text-field",
                    "label": "Region of interest",
                    "value": "bridges",
                    "allowMultiple": True,
                    "selector": {
                        "id": "dab80275-1784-41bc-ba4d-af50782cc4d8",
                        "type": "box-selector",
                        "state": {"x": 1496, "y": 768, "width": 358, "height": 355},
                    },
                    "revision": "802816cb-6d7d-401e-9566-7c5e8518a1d9",
                },
            ]
        },
    },
    "target": [
        {"id": "urn:madoc:collection:1478", "type": "Collection"},
        {"id": "urn:madoc:manifest:1479", "type": "Manifest"},
        {"id": "urn:madoc:canvas:1481", "type": "Canvas"},
    ],
    "derivedFrom": "4748dc6a-3494-4b4d-84b1-25de668ed665",
    "revisions": [
        {
            "structureId": "c8f44c56-e049-4803-acbc-8409452e7d81",
            "approved": True,
            "label": "Region of interest",
            "id": "802816cb-6d7d-401e-9566-7c5e8518a1d9",
            "fields": ["region"],
            "status": "accepted",
            "revises": None,
            "authors": ["urn:madoc:user:1"],
        }
    ],
    "contributors": {
        "urn:madoc:user:1": {"id": "urn:madoc:user:1", "type": "Person", "name": "Madoc TS"}
    },
}

if __name__ == "__main__":
    # test_faceted_query()
    # test_ingest()
    test_ocr()
