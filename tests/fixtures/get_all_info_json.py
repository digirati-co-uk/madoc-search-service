import requests
import json
import itertools
import pathlib
import urllib.parse


def resources_by_type(iiif, iiif_type="Canvas", master_resources=None):
    """
    Iterate a Presentation API 3 manifest and produce a list of resources by type, e.g. Canvases
    or Annotations.
    """
    if not master_resources:
        working_resources = []
    else:
        working_resources = master_resources
    if (items := iiif.get("items", None)) is not None:
        resources = [c for c in items if c.get("type") is not None]
        filtered_resources = [r for r in resources if r.get("type") == iiif_type]
        if filtered_resources:
            working_resources += filtered_resources
        else:
            for f in resources:
                working_resources += resources_by_type(
                    iiif=f, iiif_type=iiif_type, master_resources=filtered_resources
                )
    return working_resources


def main():
    iiif_dir = pathlib.Path("./iiif")
    muya_dir = pathlib.Path("./muya")
    store_dir = pathlib.Path("./iiif3_store")

    for manifest in iiif_dir.iterdir():
        if manifest.name.startswith("0"):
            manifest_json = json.load(manifest.open(mode="r"))
            image_service = manifest_json["sequences"][0]["canvases"][0]["images"][0][
                "resource"
            ]["service"]["@id"]
            url = f"{image_service}/info.json"
            info = requests.get(url)
            path = pathlib.Path("." + urllib.parse.urlparse(url).path)
            path.parent.mkdir(parents=True, exist_ok=True)
            json.dump(info.json(), path.open(mode="w"))


if __name__ == "__main__":
    main()
