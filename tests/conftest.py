import json
import pathlib
import pytest

from .utils import is_responsive_404


@pytest.fixture
def tests_dir():
    return pathlib.Path(__file__).resolve().parent


@pytest.fixture
def test_api_auth():
    return (
        "admin",
        "password",
    )


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    return pathlib.Path(__file__).resolve().parent / "docker-compose.test.yml"


@pytest.fixture
def iiif_collection(tests_dir):
    return json.load(
        (tests_dir / "fixtures/iiif/collection_fixture.json").open(encoding="utf-8")
    )


@pytest.fixture
def iiif2_manifest(tests_dir):
    return json.load((tests_dir / "fixtures/muya/manifest.json").open(encoding="utf-8"))


@pytest.fixture
def iiif3_manifest(tests_dir):
    return json.load(
        (tests_dir / "fixtures/muya/manifest_3.json").open(encoding="utf-8")
    )


@pytest.fixture
def iiif_store_manifest(tests_dir):
    return json.load(
        (tests_dir / "fixtures/iiif3_store/iiif3_forager.json").open(encoding="utf-8")
    )


@pytest.fixture
def tei_store_muya_structure_document(tests_dir):
    xml_data = (
        (tests_dir / "../muya_discovery/tei_store/data/muya_structure.xml")
        .open(encoding="utf-8")
        .read()
    )
    return {"original_id": "muya_structure", "xml": xml_data}


@pytest.fixture
def tei_store_document_1(tests_dir):
    xml_data = (
        (
            tests_dir
            / "fixtures/muya_tei/0029_Pouladi3/0029_Pouladi3_027r-038r_Y_09-11.xml"
        )
        .open(encoding="utf-8")
        .read()
    )
    json_data = json.load(
        (
            tests_dir
            / "fixtures/muya_tei/parsed_data/0029_Pouladi3_027r-038r_Y_09-11.json"
        ).open(encoding="utf-8")
    )
    plaintext_data = (
        (
            tests_dir
            / "fixtures/muya_tei/parsed_data/0029_Pouladi3_027r-038r_Y_09-11.txt"
        )
        .open(encoding="utf-8")
        .read()
    )
    return {
        "xml": xml_data,
        "json": json_data,
        "plaintext": plaintext_data.strip(),
        "original_id": "test_tei_document_1",
    }


@pytest.fixture
def tei_store_document_2(tests_dir):
    xml_data = (
        (tests_dir / "fixtures/muya_tei/0451_T54/0451_T54_037v-097v_Y_03-08.xml")
        .open(encoding="utf-8")
        .read()
    )
    return {"xml": xml_data, "original_id": "test_tei_document_2"}


@pytest.fixture
def tei_store_Y_10(tests_dir):
    return json.load(
        (tests_dir / "fixtures/muya_tei/parsed_data/Y_10.json").open(encoding="utf-8")
    )


@pytest.fixture
def tei_store_P28r_29(tests_dir):
    return json.load(
        (tests_dir / "fixtures/muya_tei/parsed_data/P28r_29.json").open(
            encoding="utf-8"
        )
    )


@pytest.fixture
def manifest_with_ranges(tests_dir):
    return json.load(
        (tests_dir / "fixtures/muya/manifest_ranges.json").open(encoding="utf-8")
    )


@pytest.fixture
# Just returns the values as coded in the view, to check against in the test
def expected_card_view_metadata_fields():
    return {
        "author": "Author",
        "publisher": "Publisher",
        "date_of_publication": "Date of publication",
        "binding": "Binding",
    }


@pytest.fixture
def expected_list_view_metadata_fields():
    return {
        "author": "Author",
        "publisher": "Publisher",
        "date_of_publication": "Date of publication",
        "binding": "Binding",
    }


@pytest.fixture
def expected_normalised_metadata():
    return {
        "kitodo": {"label": "Kitodo", "value": ["238"]},
        "urn": {"label": "URN", "value": ["urn:nbn:de:bsz:15-0007-98422"]},
        "vd17": {"label": "VD17", "value": ["VD17 15:728646T"]},
        "collection": {"label": "Collection", "value": ["VD17", "VD17"]},
        "source_ppn_(swb)": {"label": "Source PPN (SWB)", "value": ["032340214"]},
        "call_number": {"label": "Call number", "value": ["4-B.S.T.88"]},
        "owner": {"label": "Owner", "value": ["Leipzig University Library"]},
        "author": {
            "label": "Author",
            "value": ["Mietzsching, Christoph [GNDNR:1058639463]"],
        },
        "place_of_publication": {"label": "Place of publication", "value": [""]},
        "date_of_publication": {"label": "Date of publication", "value": ["1690"]},
        "publisher": {"label": "Publisher", "value": [""]},
        "physical_description": {"label": "Physical description", "value": ["107 S."]},
        "manifest_type": {"label": "Manifest Type", "value": ["monograph"]},
        "comment": {
            "label": "comment",
            "value": [
                "Paginierfehler: S.32 und 33 doppelt, nach S. 86 folgt 89 (87, 88 nicht vergeben)"
            ],
        },
    }


@pytest.fixture(scope="session")
def http_service(docker_ip, docker_services):
    """
    Ensure that Django service is up and responsive.
    """

    # `port_for` takes a container port and returns the corresponding host port
    port = docker_services.port_for("django", 8000)
    url = "http://{}:{}".format(docker_ip, port)
    url404 = f"{url}/missing"
    docker_services.wait_until_responsive(
        timeout=600.0, pause=0.1, check=lambda: is_responsive_404(url404)
    )
    return url


@pytest.fixture(scope="session")
def madoc_access_jwt_headers():
    return {
            'Bearer': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6IlF1QmxtaWl3VnJMb05EeEdGNm1vaVFLbHhJMHQ4VWdocVltWUdqWmdvQmsifQ.eyJzY29wZSI6InNpdGUuYWRtaW4gdGFza3MuYWRtaW4gbW9kZWxzLmFkbWluIiwiaXNzX25hbWUiOiJEZWZhdWx0IHNpdGUiLCJuYW1lIjoiYWRtaW4iLCJzdWIiOiJ1cm46bWFkb2M6dXNlcjoxIiwiaXNzIjoidXJuOm1hZG9jOnNpdGU6MSIsImlhdCI6MTYyNzkyMDM4NywiZXhwIjoxNjU5NDU2Mzg3fQ.ORxy63txUVRkTB9ul48jwrHR_YkZZBwmqmp_KjqfzXtwRCUjSvtF0auqHkpp7qlKt46ZzHm4FxtsO7J2PYtuFmBbP6SpiDoQj1IDXfXQ_B_lK7HApJxS0RY71KQG8YKKo26d5-9_N9f0J_ey5vW9L4NWNn3-0k45XZK41JEAGG4jjYr0O55w3FF_C3ussmgzcZDp6vf6wzgpEEwoQEzuzjLcoJo_WYKv36W2HdIfjypst3gE9wcQWgdguRdaVLKKpwnOR6F12BgOhv1j9NufnWuhMOPO-0EpGHTolb7bceIxDasSEksc0ocX5nql76WSx09pwihUcfOFwTTrzc6oZA'
            }


@pytest.fixture(scope="session")
def madoc_service_jwt_headers():
    return {
            'x-madoc-site-id': '1',
            'Bearer': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6ImFJNGpaeXJLUHBmM2Y1eWZZbU91Sm9WelB2dzhxTmFxNHVoZW9kZi1FREkifQ.eyJzY29wZSI6Im1vZGVscy5hZG1pbiBzaXRlLmFkbWluIHRhc2tzLmFkbWluIiwiaXNzX25hbWUiOiJNYWRvYyBQbGF0Zm9ybSBHYXRld2F5IiwibmFtZSI6Ik1hZG9jIFRTIiwic2VydmljZSI6dHJ1ZSwic3ViIjoidXJuOm1hZG9jOnNlcnZpY2U6bWFkb2MtdHMiLCJpc3MiOiJ1cm46bWFkb2M6Z2F0ZXdheSIsImlhdCI6MTYzMjIxNjc1NX0.HynxkZARkCzTmRwYcwOsej2vUJSw7KcwBFJE9SiqsvIV4UfB0VhtLj7NV1a0iI2BPAip4TEExYYCG7iknBMD_3hA2ew68TEcw4FvPaJ0-DKm99zD4UXDDhPi5mUoLbCXVRwPr1s0jrOynG8Vqz_RR5zIOjvFK1fr9UCFvn4GCB-xLgwLdPiVtscXSfa6fo_mawB2RNZS-rRxm98Te3CFl3UutWUsUqgMeYBCivHa3-GXiOZ-aghSJaYRLWV2DOQlKgs_7pgU08S_iU3WOuyOSv-rSnQvPnAHbZvQApVkPff-Ip_BR-_Kvuf_t-p_lXY7q6y5C124QwwoA1BlJGRmJQ'
            }