from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import json
from bs4 import BeautifulSoup


pg_languages = [
    "danish",
    "dutch",
    "english",
    "finnish",
    "french",
    "german",
    "hungarian",
    "italian",
    "norwegian",
    "portuguese",
    "romanian",
    "russian",
    "spanish",
    "swedish",
    "turkish",
]


def iiif_to_presentationapiresourcemodel(data_dict):
    """
    Somewhat hacky transformation of an incoming data object for the serializer
    into the correct format for the model

    """
    lookup_dict = {
        "@id": {"model_key": "identifier", "default": None, "choices": None},
        "identifier": {"model_key": "identifier", "default": None, "choices": None},
        "@type": {
            "model_key": "type",
            "default": "Man",
            "choices": (
                ("Col", "Collection"),
                ("Col", "sc:Collection"),
                ("Man", "Manifest"),
                ("Man", "sc:Manifest"),
                ("Seq", "Sequence"),
                ("Seq", "sc:Sequence"),
                ("Rng", "Range"),
                ("Rng", "sc:Range"),
                ("Cvs", "Canvas"),
                ("Cvs", "sc:Canvas"),
            ),
        },
        "type": {
            "model_key": "type",
            "default": "Man",
            "choices": (
                ("Col", "Collection"),
                ("Man", "Manifest"),
                ("Seq", "Sequence"),
                ("Rng", "Range"),
                ("Cvs", "Canvas"),
            ),
        },
        "label": {"model_key": "label", "default": None, "choices": None},
        "viewingDirection": {
            "model_key": "viewing_direction",
            "default": "l2",
            "choices": (
                ("l2r", "left-to-right"),
                ("r2l", "right-to-left"),
                ("t2b", "top-to-bottom"),
                ("b2t", "bottom-to-top"),
            ),
        },
        "viewingHint": {
            "model_key": "viewing_hint",
            "default": "paged",
            "choices": (
                ("ind", "individuals"),
                ("pgd", "paged"),
                ("cnt", "continuous"),
                ("mpt", "multi-part"),
                ("npg", "non-paged"),
                ("top", "top"),
                ("fac", "facing-pages"),
            ),
        },
        "description": {"model_key": "description", "default": None, "choices": None},
        "attribution": {"model_key": "attribution", "default": None, "choices": None},
        "license": {"model_key": "license", "default": None, "choices": None},
        "metadata": {"model_key": "metadata", "default": None, "choices": None},
    }
    return_dict = {}
    if data_dict.get("metadata"):
        if isinstance((data_dict["metadata"]), str):
            data_dict["metadata"] = json.load(data_dict["metadata"])
    for k, v in data_dict.items():
        lookup_result = lookup_dict.get(k)
        if lookup_result:
            if not lookup_result.get("choices"):
                return_dict[lookup_result["model_key"]] = v
            else:
                if v in [c[0] for c in lookup_result["choices"]]:
                    return_dict[lookup_result["model_key"]] = v
                elif v in [c[1] for c in lookup_result["choices"]]:
                    return_dict[lookup_result["model_key"]] = [
                        c[0] for c in lookup_result["choices"] if c[1] == v
                    ][0]
                else:
                    return_dict[lookup_result["model_key"]] = lookup_result.get("default")
        if return_dict.get("license"):
            val = URLValidator()
            try:
                val(return_dict["license"])
            except ValidationError:
                del (return_dict["license"])
    return return_dict


def get_language_data(lang_code=None, langbase=None):
    if lang_code:
        if len(lang_code) == 2:
            language_data = [x for x in langbase if x[1] == lang_code]
            if language_data:
                if language_data[0][-1].lower() in pg_languages:
                    pg_lang = language_data[0][-1].lower()
                else:
                    pg_lang = None
                return {
                    "language_iso629_2": language_data[0][0],
                    "language_iso629_1": language_data[0][1],
                    "language_display": language_data[0][-1].lower(),
                    "language_pg": pg_lang,
                }
        elif len(lang_code) == 3:
            language_data = [x for x in langbase if x[0] == lang_code]
            if language_data:
                if language_data[0][-1].lower() in pg_languages:
                    pg_lang = language_data[0][-1].lower()
                else:
                    pg_lang = None
                return {
                    "language_iso629_2": language_data[0][0],
                    "language_iso629_1": language_data[0][1],
                    "language_display": language_data[0][-1].lower(),
                    "language_pg": pg_lang,
                }
    return {
        "language_iso629_2": None,
        "language_iso629_1": None,
        "language_display": None,
        "language_pg": None,
    }


def process_field(field_instance, key, default_language, lang_base, field_type="descriptive"):
    val = None
    lang = default_language
    subtype = key
    field_data = []
    if field_instance:
        if not field_instance.get("label"):
            # Problem here with multilanguage label field
            for val_lang, val in field_instance.items():
                if val_lang in ["@none", "none"]:
                    lang = default_language
                else:
                    lang = val_lang
                if val:
                    if val:
                        for v in val:
                            field_data.append(
                                {
                                    "type": field_type,
                                    "subtype": subtype.lower(),
                                    "indexable": BeautifulSoup(v, "html.parser").text,
                                    "original_content": {subtype: v},
                                    **get_language_data(lang_code=lang, langbase=lang_base),
                                }
                            )
        else:
            for label_lang, label_val in field_instance.get("label").items():
                if label_val:
                    subtype = label_val[0]
            if field_instance.get("value"):
                for lang, val in field_instance["value"].items():
                    if lang in ["@none", "none"]:
                        lang = default_language
            language_data = get_language_data(lang_code=lang, langbase=lang_base)
            if val:
                for v in val:
                    field_data.append(
                        {
                            "type": field_type,
                            "subtype": subtype.lower(),
                            "indexable": BeautifulSoup(v, "html.parser").text,
                            "original_content": {subtype: v},
                            **language_data,
                        }
                    )
        return field_data
    return


def flatten_iiif_descriptive(iiif, default_language=None, lang_base=None):
    """
    Flatten the descriptive fields in a Presentation API into a list of dicts
    that can be passed to the Indexables model and serializers
    """
    field_data = []
    dict_fields = [
        ("label", "descriptive"),
        ("requiredStatement", "descriptive"),
        ("summary", "descriptive"),
        ("metadata", "metadata"),
    ]
    for d in dict_fields:
        if iiif.get(d[0]):
            if isinstance(iiif[d[0]], dict):
                field_instances = [iiif[d[0]]]
            elif isinstance(iiif[d[0]], list):
                field_instances = iiif[d[0]]
            else:
                field_instances = None
            if field_instances:
                for field_instance in field_instances:
                    returned_data = process_field(
                        field_instance=field_instance,
                        lang_base=lang_base,
                        default_language=default_language,
                        key=d[0],
                        field_type=d[1],
                    )
                    if returned_data:
                        field_data += returned_data
    if field_data:
        return field_data
    else:
        return


if __name__ == "__main__":
    test_data = [
        {
            "@context": "http://iiif.io/api/presentation/3/context.json",
            "id": "https://example.org/iiif/book1/manifest",
            "type": "Manifest",
            "label": {"en": ["Book 1"]},
            "metadata": [
                {"label": {"en": ["Author"]}, "value": {"none": ["Anne Author"]}},
                {
                    "label": {"en": ["Published"]},
                    "value": {"en": ["Paris, circa 1400"], "fr": ["Paris, environ 1400"]},
                },
                {
                    "label": {"en": ["Notes"]},
                    "value": {"en": ["Text of note 1", "Text of note 2"]},
                },
                {
                    "label": {"en": ["Source"]},
                    "value": {
                        "none": [
                            '<span>From: <a href="https://example.org/db/1.html">Some Collection</a></span>'
                        ]
                    },
                },
            ],
            "summary": {"en": ["Book 1, written be Anne Author, published in Paris around 1400."]},
            "thumbnail": [
                {
                    "id": "https://example.org/iiif/book1/page1/full/80,100/0/default.jpg",
                    "type": "Image",
                    "format": "image/jpeg",
                    "service": [
                        {
                            "id": "https://example.org/iiif/book1/page1",
                            "type": "ImageService3",
                            "profile": "level1",
                        }
                    ],
                }
            ],
            "viewingDirection": "right-to-left",
            "behavior": ["paged"],
            "navDate": "1856-01-01T00:00:00Z",
            "rights": "https://creativecommons.org/licenses/by/4.0/",
            "requiredStatement": {
                "label": {"en": ["Attribution"]},
                "value": {"en": ["Provided by Example Organization"]},
            },
            "provider": [
                {
                    "id": "https://example.org/about",
                    "type": "Agent",
                    "label": {"en": ["Example Organization"]},
                    "homepage": [
                        {
                            "id": "https://example.org/",
                            "type": "Text",
                            "label": {"en": ["Example Organization Homepage"]},
                            "format": "text/html",
                        }
                    ],
                    "logo": [
                        {
                            "id": "https://example.org/service/inst1/full/max/0/default.png",
                            "type": "Image",
                            "format": "image/png",
                            "service": [
                                {
                                    "id": "https://example.org/service/inst1",
                                    "type": "ImageService3",
                                    "profile": "level2",
                                }
                            ],
                        }
                    ],
                    "seeAlso": [
                        {
                            "id": "https://data.example.org/about/us.jsonld",
                            "type": "Dataset",
                            "format": "application/ld+json",
                            "profile": "https://schema.org/",
                        }
                    ],
                }
            ],
            "homepage": [
                {
                    "id": "https://example.org/info/book1/",
                    "type": "Text",
                    "label": {"en": ["Home page for Book 1"]},
                    "format": "text/html",
                }
            ],
            "service": [
                {
                    "id": "https://example.org/service/example",
                    "type": "ExampleExtensionService",
                    "profile": "https://example.org/docs/example-service.html",
                }
            ],
            "seeAlso": [
                {
                    "id": "https://example.org/library/catalog/book1.xml",
                    "type": "Dataset",
                    "format": "text/xml",
                    "profile": "https://example.org/profiles/bibliographic",
                }
            ],
            "rendering": [
                {
                    "id": "https://example.org/iiif/book1.pdf",
                    "type": "Text",
                    "label": {"en": ["Download as PDF"]},
                    "format": "application/pdf",
                }
            ],
            "partOf": [{"id": "https://example.org/collections/books/", "type": "Collection"}],
            "start": {"id": "https://example.org/iiif/book1/canvas/p2", "type": "Canvas"},
            "services": [
                {
                    "@id": "https://example.org/iiif/auth/login",
                    "@type": "AuthCookieService1",
                    "profile": "http://iiif.io/api/auth/1/login",
                    "label": "Login to Example Institution",
                    "service": [
                        {
                            "@id": "https://example.org/iiif/auth/token",
                            "@type": "AuthTokenService1",
                            "profile": "http://iiif.io/api/auth/1/token",
                        }
                    ],
                }
            ],
            "items": [
                {
                    "id": "https://example.org/iiif/book1/canvas/p1",
                    "type": "Canvas",
                    "label": {"none": ["p. 1"]},
                    "height": 1000,
                    "width": 750,
                    "items": [
                        {
                            "id": "https://example.org/iiif/book1/page/p1/1",
                            "type": "AnnotationPage",
                            "items": [
                                {
                                    "id": "https://example.org/iiif/book1/annotation/p0001-image",
                                    "type": "Annotation",
                                    "motivation": "painting",
                                    "body": {
                                        "id": "https://example.org/iiif/book1/page1/full/max/0/default.jpg",
                                        "type": "Image",
                                        "format": "image/jpeg",
                                        "service": [
                                            {
                                                "id": "https://example.org/iiif/book1/page1",
                                                "type": "ImageService3",
                                                "profile": "level2",
                                                "service": [
                                                    {
                                                        "@id": "https://example.org/iiif/auth/login",
                                                        "@type": "AuthCookieService1",
                                                    }
                                                ],
                                            }
                                        ],
                                        "height": 2000,
                                        "width": 1500,
                                    },
                                    "target": "https://example.org/iiif/book1/canvas/p1",
                                }
                            ],
                        }
                    ],
                    "annotations": [
                        {
                            "id": "https://example.org/iiif/book1/comments/p1/1",
                            "type": "AnnotationPage",
                        }
                    ],
                },
                {
                    "id": "https://example.org/iiif/book1/canvas/p2",
                    "type": "Canvas",
                    "label": {"none": ["p. 2"]},
                    "height": 1000,
                    "width": 750,
                    "items": [
                        {
                            "id": "https://example.org/iiif/book1/page/p2/1",
                            "type": "AnnotationPage",
                            "items": [
                                {
                                    "id": "https://example.org/iiif/book1/annotation/p0002-image",
                                    "type": "Annotation",
                                    "motivation": "painting",
                                    "body": {
                                        "id": "https://example.org/iiif/book1/page2/full/max/0/default.jpg",
                                        "type": "Image",
                                        "format": "image/jpeg",
                                        "service": [
                                            {
                                                "id": "https://example.org/iiif/book1/page2",
                                                "type": "ImageService3",
                                                "profile": "level2",
                                            }
                                        ],
                                        "height": 2000,
                                        "width": 1500,
                                    },
                                    "target": "https://example.org/iiif/book1/canvas/p2",
                                }
                            ],
                        }
                    ],
                },
            ],
            "structures": [
                {
                    "id": "https://example.org/iiif/book1/range/r0",
                    "type": "Range",
                    "label": {"en": ["Table of Contents"]},
                    "items": [
                        {
                            "id": "https://example.org/iiif/book1/range/r1",
                            "type": "Range",
                            "label": {"en": ["Introduction"]},
                            "supplementary": {
                                "id": "https://example.org/iiif/book1/annocoll/introTexts",
                                "type": "AnnotationCollection",
                            },
                            "items": [
                                {
                                    "id": "https://example.org/iiif/book1/canvas/p1",
                                    "type": "Canvas",
                                },
                                {
                                    "type": "SpecificResource",
                                    "source": "https://example.org/iiif/book1/canvas/p2",
                                    "selector": {
                                        "type": "FragmentSelector",
                                        "value": "xywh=0,0,750,300",
                                    },
                                },
                            ],
                        }
                    ],
                }
            ],
            "annotations": [
                {
                    "id": "https://example.org/iiif/book1/page/manifest/1",
                    "type": "AnnotationPage",
                    "items": [
                        {
                            "id": "https://example.org/iiif/book1/page/manifest/a1",
                            "type": "Annotation",
                            "motivation": "commenting",
                            "body": {
                                "type": "TextualBody",
                                "language": "en",
                                "value": "I love this manifest!",
                            },
                            "target": "https://example.org/iiif/book1/manifest",
                        }
                    ],
                }
            ],
        }
    ]
    from search_service.search.prezi_upgrader import Upgrader
    from search_service.search.langbase import LANGBASE

    default_lang = "en"
    upgrader = Upgrader(flags={"default_lang": default_lang})
    test_data.append(
        upgrader.process_uri(uri="https://wellcomelibrary.org/iiif/b18031900-18/manifest")
    )
    import requests

    test_data.append(
        requests.get(
            "https://raw.githubusercontent.com/digirati-labs/hyperion/feature/refactor/fixtures/2-to-3-converter/manifests/ncsu-libraries-manifest.json"
        ).json()
    )
    test_data.append(
        requests.get(
            "https://raw.githubusercontent.com/digirati-labs/hyperion/feature/refactor/fixtures/2-to-3-converter/manifests/dzkimgs.l.u-tokyo.ac.jp__iiif__zuzoubu__12b02__manifest.json"
        ).json()
    )
    test_data.append(
        requests.get(
            "https://raw.githubusercontent.com/digirati-labs/hyperion/feature/refactor/fixtures/2-to-3-converter/manifests/british-library-manifest.json"
        ).json()
    )
    test_data.append(
        requests.get(
            "https://raw.githubusercontent.com/digirati-labs/hyperion/feature/refactor/fixtures/2-to-3-converter/manifests/lbiiif.riksarkivet.se__arkis!R0000004__manifest.json"
        ).json()
    )

    for j in test_data:
        result = flatten_iiif_descriptive(iiif=j, default_language="en", lang_base=LANGBASE)
        if result:
            print(json.dumps(result, indent=2, ensure_ascii=False))
