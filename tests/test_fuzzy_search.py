"""
    Tests that cover the user search journeys for fuzzy matching. 
    """
import pytest
import uuid
import requests
import json
import django
from django.template import Template, Context
from django.utils.safestring import mark_safe
from django.conf import settings

settings.configure(
    TEMPLATES=[
        {"BACKEND": "django.template.backends.django.DjangoTemplates"},
    ]
)
django.setup()


def render_json_template(template, context={}):
    return json.loads(mark_safe(Template(template).render(Context(context))))


def iiif3_template_context(context):
    template_context = {
        "manifest_uuid": uuid.uuid4(),
        "canvas_uuid": uuid.uuid4(),
        "page_uuid": uuid.uuid4(),
        "annotation_uuid": uuid.uuid4(),
        "image_service_uuid": uuid.uuid4(),
    }
    return {**template_context, **context}


fuzzy_terms = [
    # Whole word partial matches
    ("Tom Eckersley", "Thom Eckersley"),
    ("Bernt Lie", "Bernt Lee"),
    ("Central Saint Martins", "Central St Martins"),
    ("Central Saint Martins", "Central school of arts and crafts"),  # expect fail
    ("Camberwell College", "Camberwell School"),
    ("1976 Chelsea degree show slides", "degree show at Chelsea college"),
    ("Browne", "Brown"),  # expect fail
    # Variety (UK/US) insensitive search
    ("theatre", "theater"),
    ("Centre", "center"),
    ("fibre", "fiber"),
    ("colour", "color"),
    ("coloured", "colored"),
    ("license", "licence"),
    ("Organisation", "Organization"),
    ("organise", "organize"),
    ("program", "programme"),
    ("disc", "disk"),
    ("catalogue", "catalog"),
    ("jewellery", "jewelry"),
    ("aluminium", "aluminum"),
    ("aeroplane", "airplane"),
    ("grey", "gray"),
    ("cheque", "check"),
    ("artefact", "artifact"),
    ("aesthetic", "esthetic"),
    ("woollen", "woolen"),
    ("manoeuvre", "maneuver"),
    ("analyse", "analyze"),
    # spelling insensitive search
    ("Guiness", "Guiness"),
    ("Hippie", "Hippy"),
    ("Sculpture", "Scultpure"),
    ("Sculpture", "sculptuire"),
    ("Pandorra", "pandora"),
    ("Aalders", "alders"),
    ("french", "frenhc"),
    ("printing", "pringting"),
    ("McQueen", "mc+queen"),
    ("Kubrick", "kubrik"),
    ("Eckersley", "Eckersly"),
    ("Eckersley", "Eckersle"),
    ("Russia", "rssia"),
    ("Richard de la Mare", "de la mere"),
    # Accent insensitive search
    ("Müller", "Muller"),
    ("Møller", "Moller"),
]


def render_json_obj(obj):
    return mark_safe(json.dumps(obj, ensure_ascii=False))


@pytest.mark.parametrize("original_data,search_term", fuzzy_terms)
def test_fuzzy_matching(
    http_service,
    test_api_auth,
    fuzzy_search_manifest_template,
    original_data,
    search_term,
):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    # Load IIIF containing term to be searched for. 
    test_context = iiif3_template_context(
        {
            "metadata": render_json_obj(
                [
                    {
                        "label": {"en": ["test_term"]},
                        "value": {"en": [original_data]},
                    }
                ]
            ),
        }
    )
    manifest_id = f"urn:ual:manifest:{test_context.get('manifest_uuid')}"
    manifest_json = render_json_template(fuzzy_search_manifest_template, test_context)
    post_json = {
        "contexts": [  # List of contexts with their id and type
            {"id": "urn:ual:site:1", "type": "Site"},
        ],
        "resource": manifest_json,  # this is the JSON for the IIIF resource
        "id": manifest_id,  # Madoc ID for the subject/object
        "cascade": False,
    }
    result = requests.post(
        url=http_service + "/api/search/iiif",
        json=post_json,
        headers=headers,
        auth=test_api_auth,
    )
    j = result.json()
    assert result.status_code == 201
    assert j.get("madoc_id") == manifest_id
    # query using search term 
    query = {
        "fulltext": search_term,
        "search_type": "trigram",
        "contexts": ["urn:ual:site:1"],
    }
    result = requests.post(
        url=http_service + "/api/search/search", json=query, headers=headers
    )
    j = result.json()
    assert len(j["results"]) == 1
    assert j["results"][0].get("resource_id") == manifest_id 





multiple_field_terms = [
    ((1982, "Painting"), "1982 Painting"),
]


@pytest.mark.parametrize("original_data,search_term", multiple_field_terms)
def test_mulitple_field_terms(http_service, test_api_auth, original_data, search_term):
    assert original_data == search_term
