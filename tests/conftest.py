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
    with open("fixtures/iiif/collection_fixture.json", "r") as f:
        return json.load(f)


@pytest.fixture
def iiif2_manifest():
    with open("fixtures/muya/manifest.json", "r") as f:
        return json.load(f)


@pytest.fixture
def iiif3_manifest():
    with open("fixtures/muya/manifest_3.json", "r") as f:
        return json.load(f)
