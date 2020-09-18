import requests
import json


def test_ingest():
    collections = [
        "https://iiif.ub.uni-leipzig.de/static/collections/Drucke17/collection.json",
        "https://iiif.ub.uni-leipzig.de/static/collections/Drucke16/collection.json",
        "https://iiif.ub.uni-leipzig.de/static/collections/misc/cdvost2018.json",
        "https://iiif.hab.de/collection/project/mssox.json",
        "https://www.e-codices.unifr.ch/metadata/iiif/collection/sl.json",
        "https://www.e-codices.unifr.ch/metadata/iiif/collection/saa.json",
        "https://www.e-codices.unifr.ch/metadata/iiif/collection/bge.json",
        "https://digital.library.villanova.edu/Collection/vudl:294849/IIIF",
        "https://digital.library.villanova.edu/Collection/vudl:289364/IIIF",
        "https://digital.library.villanova.edu/Collection/vudl:313874/IIIF",
        "https://digital.library.villanova.edu/Collection/vudl:293828/IIIF",
        "https://digital.library.villanova.edu/Collection/vudl:287996/IIIF",
        "https://digital.library.villanova.edu/Collection/vudl:321794/IIIF",
        "https://digital.library.villanova.edu/Collection/vudl:289113/IIIF",
        "https://view.nls.uk/collections/7446/74466699.json",
    ]
    for coll in collections:
        collection = requests.get(coll).json()
        manifests = collection.get("members", collection.get("manifests", None))
        for m in manifests:
            print(m["@id"])
            j = requests.get(m["@id"]).json()
            if j:
                post_json = {
                    "contexts": [  # List of contexts with their id and type
                        {"id": "urn:madoc:site:2", "type": "Site"},
                        {"id": coll, "type": "Collection"},
                    ],
                    "resource": j,  # this is the JSON for the IIIF resource
                    "id": f"urn:madoc:manifest:{m['@id'].split('/')[-2]}",  # Madoc ID for the subject/object
                    "thumbnail": f"http://madoc.foo/thumbnail/{m['@id'].split('/')[-2]}/fake.jpg",  # Thumbnail URL
                }
                headers = {"Content-Type": "application/json", "Accept": "application/json"}
                p = requests.post(
                    url="http://localhost:8000/iiif/", json=post_json, headers=headers
                )
                print(p.status_code)


def test_faceted_query():
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    query = {
        # "fulltext": "Abbey",
        "facet_fields": ['text language', 'place of origin (english)',
                         'collection name', 'publisher', "persons", "material", "location"],
        "contexts": ["urn:madoc:site:2"],
        "facets": [
            {"type": "metadata", "subtype": "collection name", "value": "Staat", "field_lookup": "istartswith"},
            {"type": "metadata", "subtype": "material", "value": "paper"},
            {"type": "metadata", "subtype": "material", "value": "parchment"},
            {"type": "metadata", "subtype": "text language", "value": "German"},
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


if __name__ == "__main__":
    test_faceted_query()
