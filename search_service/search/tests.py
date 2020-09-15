import requests

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
    "https://view.nls.uk/collections/7446/74466699.json"
]


for coll in collections:
    collection = requests.get(
       coll
    ).json()
    manifests = collection.get("members", collection.get("manifests", None))
    for m in manifests:
        print(m["@id"])
        j = requests.get(m["@id"]).json()
        if j:
            post_json = {
                "contexts": [  # List of contexts with their id and type
                    {"id": "urn:madoc:site:2", "type": "Site"},
                    {
                        "id": coll,
                        "type": "Collection",
                    },
                ],
                "resource": j,  # this is the JSON for the IIIF resource
                "id": f"urn:madoc:manifest:{m['@id'].split('/')[-2]}",  # Madoc ID for the subject/object
                "thumbnail": f"http://madoc.foo/thumbnail/{m['@id'].split('/')[-2]}/fake.jpg",  # Thumbnail URL
            }
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            p = requests.post(url="http://localhost:8000/iiif/", json=post_json, headers=headers)
            print(p.status_code)
