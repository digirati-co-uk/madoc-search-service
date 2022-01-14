from .serializer_utils import simplify_ocr, simplify_capturemodel
import bleach

process = {"ocr": simplify_ocr, "capturemodel": simplify_capturemodel}


def clean_values(cleanable_object, allowed_tags=('a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em',
                                                 'i', 'li', 'ol', 'strong', 'ul', 'span', 'br')):
    if cleanable_object:
        if isinstance(cleanable_object, list):
            cleanable_object = [clean_values(item) for item in cleanable_object]
        elif isinstance(cleanable_object, dict):
            for k, v in cleanable_object.items():
                cleanable_object[k] = clean_values(v)
        elif isinstance(cleanable_object, str):
            cleanable_object = bleach.clean(cleanable_object, tags=list(allowed_tags))
        return cleanable_object
    return


def identify_format(resource):
    """ "
    Takes incoming "resource" data from a POST to the indexer
    and identifies the format of that data.
    """
    if resource.get("paragraph"):
        return "ocr"
    elif resource.get("document"):
        return "capturemodel"
    return


def gen_indexables(data, sep="."):
    func = None
    if (resource := data.get("resource")) is not None:
        resource_type = data.get("type", identify_format(resource))
        shared_fields = {
            "type": resource_type,
            "content_id": data.get("content_id",
                                   sep.join([data.get("resource_id"),
                                             resource_type])),
            "resource_id": data.get("resource_id"),
        }
        if resource_type:
            func = process.get(resource_type)
        if func:
            return [{**shared_fields, **indexable} for indexable in func(resource)]
    return
