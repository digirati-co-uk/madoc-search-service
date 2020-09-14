import requests

collections = [
    # "https://iiif.ub.uni-leipzig.de/static/collections/Drucke17/collection.json",
    # "https://iiif.ub.uni-leipzig.de/static/collections/Drucke16/collection.json",
    # "https://iiif.ub.uni-leipzig.de/static/collections/misc/cdvost2018.json",
    "https://iiif.hab.de/collection/project/mssox.json"
]


for coll in collections:
    collection = requests.get(
       coll
    ).json()
    # try:
    #     manifests = collection.get("manifests")
    # except TypeError:
    manifests = collection.get("members")
    for m in manifests[1:]:
        print(m["@id"])
        j = requests.get(m["@id"]).json()
        if j:
            post_json = {
                "contexts": [
                    {"id": "urn:madoc:site:2", "type": "Site"},
                    {
                        "id": coll,
                        "type": "Collection",
                    },
                ],
                "resource": j,
                "id": f"urn:madoc:manifest:{m['@id'].split('/')[-2]}",
                "thumbnail": f"http://madoc.foo/thumbnail/{m['@id'].split('/')[-2]}/fake.jpg",
            }
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            p = requests.post(url="http://localhost:8000/iiif/", json=post_json, headers=headers)
            print(p.status_code)
