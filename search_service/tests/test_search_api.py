import json

import pytest
import requests
from requests.exceptions import ConnectionError


def is_responsive_404(url):
    """
    Hit a non existing url, expect a 404.  Used to check the service is up as a fixture.
    :param url:
    :return:
    """
    try:
        response = requests.get(url)
        if response.status_code == 404:
            return True
    except ConnectionError:
        return False


#
#
@pytest.fixture(scope="session")
def http_service(docker_ip, docker_services):
    """
    Ensure that Djano service is up and responsive.
    """

    # `port_for` takes a container port and returns the corresponding host port
    port = docker_services.port_for("django", 8000)
    url = "http://{}:{}".format(docker_ip, port)
    url404 = f"{url}/missing"
    docker_services.wait_until_responsive(
        timeout=120.0, pause=0.1, check=lambda: is_responsive_404(url404)
    )
    return url


def test_root_get(http_service):
    """
    Check that the basic /configurator/ URI 200s

    :param http_service:
    :return:
    """
    status = 200
    response = requests.get(http_service + "/api/search/")
    assert response.status_code == status


def test_collection_fixture(iiif_collection):
    assert iiif_collection[0] == "0000000140.json"


def test_iiif_instance(http_service, iiif_collection):
    """
    Create a single iiif item that can be used for various tests.

    :return: requests response
    """
    foo = iiif_collection
    with open(f"./fixtures/iiif/{foo[0]}", "r") as manifest_f:
        manifest_json = json.load(manifest_f)
    id = foo[0].replace(".json", "")
    image_service = manifest_json["sequences"][0]["canvases"][0]["images"][0]["resource"][
        "service"
    ]["@id"]
    post_json = {
        "contexts": [  # List of contexts with their id and type
            {"id": "urn:muya:site:1", "type": "Site"},
            {"id": "Leipzig", "type": "Collection"},
        ],
        "resource": manifest_json,  # this is the JSON for the IIIF resource
        "id": f"urn:muya:manifest:{id}",  # Madoc ID for the subject/object
        "thumbnail": f"{image_service}/full/400,/0/default.jpg",  # Thumbnail URL
        "cascade": False,
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/iiif", json=post_json, headers=headers)
    j = result.json()
    assert result.status_code == 201
    assert j.get("madoc_id") == f"urn:muya:manifest:{id}"
    assert j.get("madoc_thumbnail") == f"{image_service}/full/400,/0/default.jpg"
    assert j.get("first_canvas_id") is not None
    assert j.get("first_canvas_json") is not None


def test_bulk_iiif_ingest(http_service, iiif_collection):
    """Check that a bulk ingest of many manifests returns no errors"""
    responses = []
    for manifest in iiif_collection[1:]:
        with open(f"./fixtures/iiif/{manifest}", "r") as manifest_f:
            manifest_json = json.load(manifest_f)
            id = manifest.replace(".json", "")
            image_service = manifest_json["sequences"][0]["canvases"][0]["images"][0]["resource"][
                "service"
            ]["@id"]
            post_json = {
                "contexts": [  # List of contexts with their id and type
                    {"id": "urn:muya:site:1", "type": "Site"},
                    {"id": "Leipzig", "type": "Collection"},
                ],
                "resource": manifest_json,  # this is the JSON for the IIIF resource
                "id": f"urn:muya:manifest:{id}",  # Madoc ID for the subject/object
                "thumbnail": f"{image_service}/full/400,/0/default.jpg",  # Thumbnail URL
                "cascade": False,
            }
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            result = requests.post(
                url=http_service + "/api/search/iiif", json=post_json, headers=headers
            )
            responses.append(result.status_code)
    assert all([r == 201 for r in responses])


def test_iiif_instance_again(http_service, iiif_collection):
    """
    Repost the same single IIIF instance
    """
    foo = iiif_collection
    with open(f"./fixtures/iiif/{foo[0]}", "r") as manifest_f:
        manifest_json = json.load(manifest_f)
    id = foo[0].replace(".json", "")
    image_service = manifest_json["sequences"][0]["canvases"][0]["images"][0]["resource"][
        "service"
    ]["@id"]
    post_json = {
        "contexts": [  # List of contexts with their id and type
            {"id": "urn:muya:site:1", "type": "Site"},
            {"id": "Leipzig", "type": "Collection"},
        ],
        "resource": manifest_json,  # this is the JSON for the IIIF resource
        "id": f"urn:muya:manifest:{id}",  # Madoc ID for the subject/object
        "thumbnail": f"{image_service}/full/400,/0/default.jpg",  # Thumbnail URL
        "cascade": False,
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/iiif", json=post_json, headers=headers)
    assert result.status_code == 400  # SHould fail but should it be a 400?


def test_simple_metadata_query(http_service):
    query = {
        "fulltext": "Mietzsching",
        "contexts": ["urn:muya:site:1"],
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/search", json=query, headers=headers)
    assert result.status_code == requests.codes.ok


def test_simple_metadata_query_pagination(http_service):
    query = {
        "fulltext": "Mietzsching",
        "contexts": ["urn:muya:site:1"],
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/search", json=query, headers=headers)
    j = result.json()
    assert j["pagination"] == {
        "next": None,
        "page": 1,
        "pageSize": 25,
        "previous": None,
        "totalPages": 1,
        "totalResults": 1,
    }


def test_simple_metadata_query_page_size(http_service):
    query = {
        "fulltext": "Mietzsching",
        "contexts": ["urn:muya:site:1"],
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/search", json=query, headers=headers,
                           params={"page_size": 10})
    j = result.json()
    assert j["pagination"] == {
        "next": None,
        "page": 1,
        "pageSize": 10,
        "previous": None,
        "totalPages": 1,
        "totalResults": 1,
    }


def test_simple_metadata_query_results(http_service):
    query = {
        "fulltext": "Mietzsching",
        "contexts": ["urn:muya:site:1"],
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/search", json=query, headers=headers)
    j = result.json()
    assert len(j["results"]) == 1


def test_simple_metadata_query_contexts(http_service):
    query = {
        "fulltext": "Mietzsching",
        "contexts": ["urn:muya:site:1"],
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/search", json=query, headers=headers)
    j = result.json()
    contexts = [x["id"] for x in j["results"][0]["contexts"]]
    assert "https://iiif.ub.uni-leipzig.de/0000000141/manifest.json" in contexts
    assert "Leipzig" in contexts
    assert "urn:muya:manifest:0000000141" in contexts


def test_simple_metadata_query_hits(http_service):
    query = {
        "fulltext": "Mietzsching",
        "contexts": ["urn:muya:site:1"],
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/search", json=query, headers=headers)
    j = result.json()
    hit = j["results"][0]["hits"][0]
    assert "Mietzsching" in hit["snippet"]
    assert hit["type"] == "metadata"
    assert hit["subtype"] == "author"


def test_simple_metadata_query_facet_results(http_service):
    query = {
        "fulltext": "Mietzsching",
        "contexts": ["urn:muya:site:1"],
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/search", json=query, headers=headers)
    j = result.json()
    facets = j["facets"]
    assert facets.get("metadata") is not None
    assert facets["metadata"].get("author") is not None
    assert (
        facets["metadata"]["author"].get("Mietzsching, Christoph [GNDNR:1058639463]") is not None
    )
    assert facets["metadata"]["author"].get("Mietzsching, Christoph [GNDNR:1058639463]") == 1


def test_simple_facet_query_pagination(http_service):
    query = {
        "contexts": ["urn:muya:site:1"],
        "facets": [
            {"type": "metadata", "subtype": "manifest type", "value": "monograph"},
        ],
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/search", json=query, headers=headers)
    j = result.json()
    assert result.status_code == requests.codes.ok
    assert j["pagination"] == {
        "next": "http://127.0.0.1:8000/api/search/search?page=2",
        "page": 1,
        "pageSize": 25,
        "previous": None,
        "totalPages": 3,
        "totalResults": 73,
    }
    assert len(j["results"]) == 25


def test_simple_facet_query_multiplefacets(http_service):
    query = {
        "contexts": ["urn:muya:site:1"],
        "facets": [
            {"type": "metadata", "subtype": "manifest type", "value": "monograph"},
            {"type": "metadata", "subtype": "publisher", "value": "Wittigau"},
        ],
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/search", json=query, headers=headers)
    j = result.json()
    assert result.status_code == requests.codes.ok
    assert j["pagination"] == {
        "next": None,
        "page": 1,
        "pageSize": 25,
        "previous": None,
        "totalPages": 1,
        "totalResults": 3,
    }
    assert len(j["results"]) == 3


def test_contexts_only_query(http_service):
    query = {
        "contexts": ["urn:muya:site:1"],
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/search", json=query, headers=headers)
    j = result.json()
    assert result.status_code == requests.codes.ok
    assert j["pagination"] == {
        "next": "http://127.0.0.1:8000/api/search/search?page=2",
        "page": 1,
        "pageSize": 25,
        "previous": None,
        "totalPages": 4,
        "totalResults": 76,
    }


def test_facet_api(http_service):
    query = {
        "contexts": ["urn:muya:site:1"],
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/facets", json=query, headers=headers)
    j = result.json()
    assert result.status_code == requests.codes.ok
    assert j == {
        "metadata": [
            "author",
            "call number",
            "collection",
            "comment",
            "date of publication",
            "kitodo",
            "manifest type",
            "owner",
            "part of",
            "physical description",
            "place of publication",
            "publisher",
            "related",
            "source ppn (swb)",
            "urn",
            "vd17",
        ]
    }


def test_facet_api_types(http_service):
    query = {"contexts": ["urn:muya:site:1"], "facet_types": ["metadata", "descriptive"]}
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/facets", json=query, headers=headers)
    j = result.json()
    assert result.status_code == requests.codes.ok
    assert j["descriptive"] == ["attribution", "label"]


def test_simple_metadata_query_single_metadata_fields(http_service):
    query = {
        "fulltext": "Mietzsching",
        "contexts": ["urn:muya:site:1"],
        "metadata_fields": {"en": ["Author"]},
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/search", json=query, headers=headers)
    j = result.json()
    result = j.get("results")[0]
    metadata = result.get("metadata")
    assert metadata is not None
    assert len(metadata) == 1
    assert metadata[0].get("label", {}).get("en")[0] == "Author"
    assert metadata[0].get("value", {}).get("en")[0] == "Mietzsching, Christoph [GNDNR:1058639463]"


def test_simple_metadata_query_no_metadata_fields(http_service):
    query = {
        "fulltext": "Mietzsching",
        "contexts": ["urn:muya:site:1"],
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/search", json=query, headers=headers)
    j = result.json()
    result = j.get("results")[0]
    metadata = result.get("metadata")
    assert metadata is not None
    assert len(metadata) == 17
    for metadata_item in metadata:
        if metadata_item.get("label", {}).get("en")[0] == "Author":
            assert (
                metadata_item.get("value", {}).get("en")[0]
                == "Mietzsching, Christoph [GNDNR:1058639463]"
            )
            break


def test_simple_metadata_query_multiple_metadata_fields(http_service):
    query = {
        "fulltext": "Mietzsching",
        "contexts": ["urn:muya:site:1"],
        "metadata_fields": {"en": ["Author", "Kitodo"]},
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/search", json=query, headers=headers)
    j = result.json()
    result = j.get("results")[0]

    metadata = result.get("metadata")
    assert metadata is not None
    assert len(metadata) == 2
    for metadata_item in metadata:
        if metadata_item.get("label", {}).get("en")[0] == "Author":
            assert (
                metadata_item.get("value", {}).get("en")[0]
                == "Mietzsching, Christoph [GNDNR:1058639463]"
            )
        if metadata_item.get("label", {}).get("en")[0] == "Kitodo":
            assert metadata_item.get("value", {}).get("en")[0] == "238"


def test_simple_query_madoc_thumbnail(http_service):
    query = {
        "fulltext": "urn:nbn:de:bsz:15-0008-232402",
        "contexts": ["urn:muya:site:1"],
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/search", json=query, headers=headers)
    j = result.json()
    result = j.get("results")[0]
    assert (
        result.get("label", {}).get("en", [""])[0]
        == "Kurze und deutliche Einleitung zu dem Wahren Christenthum"
    )
    assert (
        result.get("madoc_thumbnail")
        == "https://iiif.ub.uni-leipzig.de/iiif/j2k/0000/0129/0000012903/00000001.jpx/full/400,/0/default.jpg"
    )
    assert result.get("thumbnail") is None


def test_simple_query_thumbnail(http_service):
    """
    Adds an additional manifest from /fixtures/muya/ where the iiif
    has a thumbnail block to allow testing for its presence after ingest and querying.
    """
    with open(f"./fixtures/muya/manifest_3.json", "r") as manifest_f:
        manifest_json = json.load(manifest_f)
    manifest_id = "iiif3_thumbnail_test"
    thumbnail_url = manifest_json.get("thumbnail")[0].get("id")
    post_json = {
        "contexts": [  # List of contexts with their id and type
            {"id": "urn:muya:site:1", "type": "Site"},
        ],
        "resource": manifest_json,
        "id": manifest_id,
        "thumbnail": thumbnail_url,
        "cascade": False,
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/iiif", json=post_json, headers=headers)
    j = result.json()
    assert result.status_code == 201
    assert j.get("madoc_id") == manifest_id
    assert j.get("madoc_thumbnail") == thumbnail_url

    query = {
        "fulltext": "Neubauer 1159",
        "contexts": ["urn:muya:site:1"],
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/search", json=query, headers=headers)
    j = result.json()
    result = j.get("results")[0]
    assert result.get("label", {}).get("en", [""])[0] == "Bodleian Library MS. Arch. Selden A. 3"
    assert result.get("madoc_thumbnail") == thumbnail_url
    assert result.get("thumbnail") == [
        {
            "id": "https://iiif.bodleian.ox.ac.uk/iiif/image/f4c4d772-d19b-42d6-b817-805e405c7714/full/256,/0/default.jpg",
            "type": "Image",
            "service": [
                {
                    "@id": "https://iiif.bodleian.ox.ac.uk/iiif/image/f4c4d772-d19b-42d6-b817-805e405c7714",
                    "@type": "ImageService2",
                    "profile": "http://iiif.io/api/image/2/level1.json",
                },
                {
                    "id": "https://iiif.bodleian.ox.ac.uk/iiif/image/f4c4d772-d19b-42d6-b817-805e405c7714",
                    "type": "ImageService3",
                    "profile": "level1",
                },
            ],
        }
    ]


def test_manifest_update_nochange(http_service, iiif_collection):
    foo = iiif_collection
    with open(f"./fixtures/iiif/{foo[0]}", "r") as manifest_f:
        manifest_json = json.load(manifest_f)
    id = foo[0].replace(".json", "")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    identifier = f"urn:muya:manifest:{id}"
    payload = {
        "madoc_id": identifier,
        "resource": manifest_json,
        "type": "Manifest",
        "id": manifest_json["@id"],
    }
    r = requests.put(
        url=http_service + f"/api/search/iiif/{identifier}", json=payload, headers=headers
    )
    j = r.json()
    assert r.status_code == 200
    print(j.get("label"))


def test_manifest_update_labelchange(http_service, iiif_collection):
    foo = iiif_collection
    with open(f"./fixtures/iiif/{foo[0]}", "r") as manifest_f:
        manifest_json = json.load(manifest_f)
    id = foo[0].replace(".json", "")
    manifest_json["label"] = "QuickBrownFoxLazyDog"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    identifier = f"urn:muya:manifest:{id}"
    payload = {
        "madoc_id": identifier,
        "resource": manifest_json,
        "type": "Manifest",
        "id": manifest_json["@id"],
    }
    r = requests.put(
        url=http_service + f"/api/search/iiif/{identifier}", json=payload, headers=headers
    )
    assert r.status_code == 200


def test_updated_label(http_service):
    query = {
        "fulltext": "QuickBrownFoxLazyDog",
        "contexts": ["urn:muya:site:1"],
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    result = requests.post(url=http_service + "/api/search/search", json=query, headers=headers)
    assert result.status_code == requests.codes.ok
    j = result.json()
    assert len(j["results"]) == 1
    assert j["results"][0]["resource_id"] == "urn:muya:manifest:0000000140"
