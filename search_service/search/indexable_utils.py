from .serializer_utils import simplify_ocr, simplify_capturemodel

process = {"ocr": simplify_ocr, "capturemodel": simplify_capturemodel}


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


def gen_indexables(data):
    func = None
    if (resource := data.get("resource")) is not None:
        resource_type = data.get("type", identify_format(resource))
        shared_fields = {
            "type": resource_type,
            "content_id": data.get("content_id"),
            "resource_id": data.get("resource_id"),
        }
        if resource_type:
            func = process.get(resource_type)
        if func:
            return [{**shared_fields, **indexable} for indexable in func(resource)]
    return
