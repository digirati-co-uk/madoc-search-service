import json
import os
import pytest
import requests


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    print("Root dir", str(pytestconfig.rootdir))
    return os.path.join(str(pytestconfig.rootdir), "docker-compose.yml")


@pytest.fixture
def iiif_collection():
    with open("./fixtures/iiif/collection_fixture.json", "r") as f:
        return json.load(f)


@pytest.fixture
def iiif2_manifest():
    with open("./fixtures/muya/manifest.json", "r") as f:
        return json.load(f)


@pytest.fixture
def iiif3_manifest():
    with open("./fixtures/muya/manifest_3.json", "r") as f:
        return json.load(f)

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
