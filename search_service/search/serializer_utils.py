from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.utils.text import slugify
import json
from bs4 import BeautifulSoup
from collections import defaultdict
from ordered_set import OrderedSet


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
                del return_dict["license"]
    return return_dict


def get_language_data(lang_code=None, langbase=None):
    if lang_code:
        if "-" in lang_code:
            lang_code = lang_code.split("-")[0]
        if len(lang_code) == 2:
            language_data = [x for x in langbase if x[1] == lang_code]
            if language_data:
                if language_data[0][-1].lower() in pg_languages:
                    pg_lang = language_data[0][-1].lower()
                else:
                    pg_lang = None
                return {
                    "language_iso639_2": language_data[0][0],
                    "language_iso639_1": language_data[0][1],
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
                    "language_iso639_2": language_data[0][0],
                    "language_iso639_1": language_data[0][1],
                    "language_display": language_data[0][-1].lower(),
                    "language_pg": pg_lang,
                }
    return {
        "language_iso639_2": None,
        "language_iso639_1": None,
        "language_display": None,
        "language_pg": None,
    }


def process_field(field_instance, key, default_language, lang_base, field_type="descriptive",
                  field_indexable_type="text"):
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
                    for v in val:
                        if field_indexable_type == "text":
                            field_data.append(
                                {
                                    "type": field_type,
                                    "subtype": subtype.lower(),
                                    "indexable": BeautifulSoup(v, "html.parser").text,
                                    "original_content": {subtype: v},
                                    **get_language_data(lang_code=lang, langbase=lang_base),
                                }
                            )
                        elif field_indexable_type == "date":
                            """
                            This assumes a single navDate, but we translate this into a datetime
                            range via adding two indexables.
                            """
                            field_data.append(
                                {
                                    "type": field_type,
                                    "subtype": subtype.lower(),
                                    "indexable_date_range_start": v,
                                    "original_content": {subtype: v},
                                }
                            )
                            field_data.append(
                                {
                                    "type": field_type,
                                    "subtype": subtype.lower(),
                                    "indexable_date_range_end": v,
                                    "original_content": {subtype: v},
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
                    if field_indexable_type == "text":
                        field_data.append(
                            {
                                "type": field_type,
                                "subtype": subtype.lower(),
                                "indexable": BeautifulSoup(v, "html.parser").text,
                                "original_content": {subtype: v},
                                **language_data,
                            }
                        )
                    elif field_indexable_type == "date":
                        """
                        This assumes a single navDate, but we translate this into a datetime
                        range via adding two indexables.
                        """
                        field_data.append(
                            {
                                "type": field_type,
                                "subtype": subtype.lower(),
                                "indexable_date_range_start": v,
                                "original_content": {subtype: v},
                            }
                        )
                        field_data.append(
                            {
                                "type": field_type,
                                "subtype": subtype.lower(),
                                "indexable_date_range_end": v,
                                "original_content": {subtype: v},
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
        ("label", "descriptive", "text"),
        ("requiredStatement", "descriptive", "text"),
        ("summary", "descriptive", "text"),
        ("metadata", "metadata", "text"),
        ("navDate", "descriptive", "date")
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
                        field_indexable_type=d[2]
                    )
                    if returned_data:
                        field_data += returned_data
    if field_data:
        return field_data
    else:
        return


def simplify_selector(selector):
    """
    Simplify a selector from the OCR intermediate format or capture model format
    into a compact representation

    "selector": {
        "id": "0db4fdc1-73dd-4555-95da-7cbc746c980c",
        "state": {
            "height": "60",
            "width": "20",
            "x": "821",
            "y": "644"
        },
        "type": "box-selector"
    },

    Becomes (XYWH):

        832,644,20,60
    """
    if selector:
        if selector.get("state"):
            if (selector_type := selector.get("type")) is not None:
                if selector_type == "box-selector":
                    selector_list = [
                        selector["state"].get("x"),
                        selector["state"].get("y"),
                        selector["state"].get("width"),
                        selector["state"].get("height"),
                    ]
                    if all([x is not None for x in selector_list]):
                        try:
                            return {selector_type: [int(x) for x in selector_list]}
                        except ValueError:
                            return
    return


def simplify_ocr(ocr):
    """
    Simplify ocr to just a single continuous page of text, with selectors.
    """
    simplified = dict(text=[], selector=defaultdict(list))
    if ocr.get("paragraph"):
        for paragraph in ocr["paragraph"]:
            if paragraph.get("properties"):
                if paragraph["properties"].get("lines"):
                    for line in paragraph["properties"]["lines"]:
                        if line.get("properties"):
                            if line["properties"].get("text"):
                                for text in line["properties"]["text"]:
                                    simplified["text"].append(text.get("value"))
                                    selector_obj = simplify_selector(text["selector"])
                                    if selector_obj:
                                        for k, v in selector_obj.items():
                                            simplified["selector"][k].append(v)
    simplified["indexable"] = " ".join([t for t in simplified["text"] if t])
    simplified["original_content"] = simplified["indexable"]
    simplified["subtype"] = "intermediate"
    return [simplified]


def simplify_label(s):
    return ".".join(OrderedSet(s.split(".")))


def recurse_properties(properties, indexables=None, doc_subtype=None, target=None):
    if not indexables:
        indexables = []
    if properties:
        if properties.get("properties"):  # This is a nested model so recurse into that
            indexables += recurse_properties(
                properties=properties.get("properties"),
                doc_subtype=simplify_label(
                    ".".join([doc_subtype, slugify(properties.get("type", ""))])
                ),
            )
        if properties.get("value"):  # This is just the content of a list of values so index them
            d = {
                "subtype": simplify_label(doc_subtype),
                "indexable": properties.get("value"),
                "original_content": properties.get("value"),
                "content_id": properties["id"],
                "resource_id": target,
            }
            # Check for selector
            if properties.get("selector"):
                d["selector"] = {
                    k: [v]
                    for k, v in simplify_selector(properties.get("selector")).items()
                    if simplify_selector(properties.get("selector")) is not None
                }
            indexables.append(d)
        else:  # Iterate through the keys in the dictionary
            for property_key, property_value in properties.items():
                # It's a list, so we should extract the indexables from each one
                if isinstance(property_value, list):
                    for x in property_value:
                        indexables += recurse_properties(
                            properties=x,
                            doc_subtype=simplify_label(".".join([doc_subtype, slugify(property_key)])),
                        )
                # It's a dictionary
                if isinstance(property_value, dict):
                    # To Do: Work out why this isn't working (some sort of simple nesting issue)
                    # indexables += recurse_properties(
                    #         properties=property_value,
                    #         doc_subtype=simplify_label(".".join([doc_subtype, slugify(property_key)])),
                    #     )
                    if property_value.get("value"):
                        d = {
                            "subtype": simplify_label(".".join(
                                [doc_subtype, slugify(property_value.get("label", ""))]
                            )),
                            "indexable": property_value.get("value"),
                            "original_content": property_value.get("value"),
                            "content_id": property_value["id"],
                            "resource_id": target,
                        }
                        if property_value.get("selector"):
                            d["selector"] = {
                                k: [v]
                                for k, v in simplify_selector(
                                    property_value.get("selector")
                                ).items()
                                if simplify_selector(property_value.get("selector")) is not None
                            }
                        indexables.append(d)
                    if property_value.get("properties"):
                        indexables += recurse_properties(
                            properties=property_value.get("properties"),
                            doc_subtype=simplify_label(".".join(
                                [doc_subtype, slugify(property_value.get("type", ""))]
                            )),
                        )
    return indexables


def simplify_capturemodel(capturemodel):
    """
    Function for parsing a capture model into indexables
    """
    if (document := capturemodel.get("document")) is not None:
        indexables = []
        doc_subtype = document.get("type")
        if (targets := capturemodel.get("target")) is not None:
            target = targets[-1].get("id")
        else:
            target = None
        if document.get("properties"):
            # This has regions of interest
            if (regions := document["properties"].get("region")) is not None:
                for region in regions:
                    if region.get("value"):
                        indexables.append(
                            {
                                "subtype": ".".join(
                                    [doc_subtype, slugify(region.get("label", ""))]
                                ),
                                "indexable": region.get("value"),
                                "original_content": region.get("value"),
                                "selector": {
                                    k: [v]
                                    for k, v in simplify_selector(region.get("selector")).items()
                                },
                                "content_id": region["id"],
                                "resource_id": target,
                            }
                        )
            else:
                # This is some sort of entity type tagging task, or other non region of interest
                # so we are going to recurse into the nesting
                indexables += recurse_properties(
                    properties=document.get("properties"), doc_subtype=doc_subtype, target=target
                )
        return indexables
    return


def calc_offsets(obj):
    """
    The search "hit" should have a 'fullsnip' annotation which is a the entire
    text of the indexable resource, with <start_sel> and <end_sel> wrapping each
    highlighted word.

    Check if there's a selector on the indexable, and then if there's a box-selector
    use this to generate a list of xywh coordinates by retrieving the selector by
    its index from a list of lists
    """
    if hasattr(obj, "fullsnip"):
        words = obj.fullsnip.split(" ")
        offsets = []
        if words:
            for i, word in enumerate(words):
                if "<start_sel>" in word and "<end_sel>" in word:
                    offsets.append(i)
            if offsets:
                if obj.selector:
                    if (boxes := obj.selector.get("box-selector")) is not None:
                        return [boxes[x] for x in offsets if boxes[x]]
    return


if __name__ == "__main__":
    import requests

    # from search_service.search.tests import test_model
    model_list = [
        "https://raw.githubusercontent.com/digirati-co-uk/capture-models/master/fixtures/02-nesting/01-nested-model.json",
        "https://raw.githubusercontent.com/digirati-co-uk/capture-models/master/fixtures/02-nesting/02-nested-mixed.json",
        "https://raw.githubusercontent.com/digirati-co-uk/capture-models/master/fixtures/02-nesting/03-deeply-nested-subset.json",
        "https://raw.githubusercontent.com/digirati-co-uk/capture-models/master/fixtures/02-nesting/04-deeply-nested-mixed-instance.json",
        "https://raw.githubusercontent.com/digirati-co-uk/capture-models/master/fixtures/02-nesting/05-nested-model-multiple.json",
        "https://raw.githubusercontent.com/digirati-co-uk/capture-models/master/fixtures/02-nesting/06-ocr.json"
    ]
    test_results = {}
    for m in model_list:
        k = m.split("/")[-1]
        j = requests.get(m).json()
        test_results[k] = simplify_capturemodel(j)
    with open("/Volumes/MMcG_SSD/Github/madoc_search_proto/capturemodels.json", "w") as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    # bar = simplify_capturemodel(capturemodel=test_model)
    # print(json.dumps(bar, indent=2, ensure_ascii=False))
    # foo = requests.get(
    #     "https://raw.githubusercontent.com/digirati-co-uk/capture-models/master/fixtures/02-nesting/"
    #     "05-nested-model-multiple.json"
    # ).json()
    # bar = simplify_capturemodel(foo)
    # print(json.dumps(bar, indent=2, ensure_ascii=False))
