from django.core.validators import URLValidator
from django.core.exceptions import ValidationError


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
                del(return_dict["license"])
    return return_dict


if __name__ == "__main__":
    import requests

    j = requests.get(
        "http://madoc.dlcs.digirati.io/public/storage/urn:madoc:site:1/AA00000463_00010/public/AA00000463_00010_manifest.json"
    ).json()
    j["viewingDirection"] = "left-to-right"
    j["license"] = "https://creativecommons.org/licenses/by-nc/4.0/"
    foo = iiif_to_presentationapiresourcemodel(data_dict=j)
    print(foo)
