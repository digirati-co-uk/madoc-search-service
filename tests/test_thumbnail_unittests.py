from search_service.search.iiif_utils import get_iiif_resource_thumbnail_json
from search_service.search.prezi_upgrader import Upgrader

upgrader = Upgrader(flags={"default_lang": "en"})


def test__manifest_has_thumbnail_no_dereference_no_canvas(iiif3_manifest):
    """
    Should just return the thumbnail block that appears in the manifest
    :param iiif3_manifest:
    :return:
    """
    thumbnail = get_iiif_resource_thumbnail_json(
        iiif_resource=iiif3_manifest, fallback=False, first_canvas_json=None
    )
    assert thumbnail == [
        {
            "id": "https://iiif.bodleian.ox.ac.uk/iiif/image/f4c4d772-d19b-42d6-b817-805e405c7714/full/256,/0/default.jpg",
            "type": "Image",
            "service": [
                {
                    "@id": "http://mock-remote-http.org/iiif/image/f4c4d772-d19b-42d6-b817-805e405c7714",
                    "@type": "ImageService2",
                    "profile": "http://iiif.io/api/image/2/level1.json",
                },
                {
                    "id": "http://mock-remote-http.org/iiif/image/f4c4d772-d19b-42d6-b817-805e405c7714",
                    "type": "ImageService3",
                    "profile": "level1",
                },
            ],
        }
    ]


def test__manifest_has_thumbnail_failed_dereference_no_canvas(iiif3_manifest):
    """
    This test should return None as the derference of the info.json will fail as it has not
    been mocked.

    :param iiif3_manifest:
    :return:
    """

    thumbnail = get_iiif_resource_thumbnail_json(
        iiif_resource=iiif3_manifest, fallback=True, first_canvas_json=None
    )
    assert thumbnail is None


def test__manifest_no_thumbnail_no_dereference_no_canvas(iiif2_manifest):
    """
    Should return None as there's no thumbnail block, no canvas and we aren't de-referencing
    :param iiif_manifest:
    :return:
    """
    thumbnail = get_iiif_resource_thumbnail_json(
        iiif_resource=iiif2_manifest, fallback=False, first_canvas_json=None
    )
    assert thumbnail is None


def test__manifest_no_thumbnail_dereference_no_canvas(iiif2_manifest):
    """
    Should just return None as there's nothing to de-reference

    :param iiif2_manifest:
    :return:
    """
    thumbnail = get_iiif_resource_thumbnail_json(
        iiif_resource=iiif2_manifest, fallback=True, first_canvas_json=None
    )
    assert thumbnail is None


def test__manifest_no_thumbnail_no_dereference_canvas(iiif2_manifest):
    """
    Should return thumbnail json based on the first canvas
    :param iiif2_manifest:
    :return:
    """
    iiif3 = upgrader.process_resource(iiif2_manifest, top=True)
    iiif3["@context"] = "http://iiif.io/api/presentation/3/context.json"
    thumbnail = get_iiif_resource_thumbnail_json(
        iiif_resource=iiif3, fallback=False, first_canvas_json=iiif3["items"][0]
    )
    assert thumbnail == [
        {
            "format": "image/jpeg",
            "height": 5760,
            "id": "https://iiif.ub.uni-leipzig.de/0000002636/00000001.jpg",
            "label": {"en": ["Vorderdeckel"]},
            "service": [
                {
                    "@id": "http://mock-remote-http.org/iiif/j2k/0000/0026/0000002636/00000001.jpx",
                    "@type": "ImageService2",
                    "profile": "http://iiif.io/api/image/2/level1.json",
                }
            ],
            "type": "Image",
            "width": 3840,
        }
    ]


def test__manifest_no_thumbnail_dereference_canvas_404(iiif2_manifest):
    """
    Should return thumbnail json based on the first canvas
    :param iiif2_manifest:
    :return:
    """
    iiif3 = upgrader.process_resource(iiif2_manifest, top=True)
    iiif3["@context"] = "http://iiif.io/api/presentation/3/context.json"
    thumbnail = get_iiif_resource_thumbnail_json(
        iiif_resource=iiif3, fallback=True, first_canvas_json=iiif3["items"][0]
    )
    assert thumbnail is None


def test__manifest_no_thumbnail_dereference_canvas(iiif2_manifest):
    """
    Should return thumbnail json based on the first canvas
    :param iiif2_manifest:
    :return:
    """
    iiif3 = upgrader.process_resource(iiif2_manifest, top=True)
    iiif3["@context"] = "http://iiif.io/api/presentation/3/context.json"
    canvas = {
        "label": {"en": ["Vorderdeckel"]},
        "height": 5760,
        "width": 3840,
        "type": "Canvas",
        "id": "https://iiif.ub.uni-leipzig.de/0000002636/canvas/00000001",
        "items": [
            {
                "type": "AnnotationPage",
                "items": [
                    {
                        "motivation": "painting",
                        "type": "Annotation",
                        "id": "https://iiif.ub.uni-leipzig.de/0000002636/anno/0d099c59-a6c5-459f-90bf-ed2db5c52ac2",
                        "target": "https://iiif.ub.uni-leipzig.de/0000002636/canvas/00000001",
                        "body": {
                            "label": {"en": ["Vorderdeckel"]},
                            "format": "image/jpeg",
                            "height": 5760,
                            "width": 3840,
                            "service": [
                                {
                                    "@id": "https://iiif.ub.uni-leipzig.de/iiif/j2k/0000/0026/0000002636/00000001.jpx",
                                    "profile": "http://iiif.io/api/image/2/level1.json",
                                    "@type": "ImageService2",
                                }
                            ],
                            "type": "Image",
                            "id": "https://iiif.ub.uni-leipzig.de/0000002636/00000001.jpg",
                        },
                    }
                ],
                "id": "https://example.org/uuid/087daefb-8ca1-48cf-8f1b-b7e444b296c4",
            }
        ],
    }
    thumbnail = get_iiif_resource_thumbnail_json(
        iiif_resource=iiif3, fallback=True, first_canvas_json=canvas
    )
    assert thumbnail == [
        {
            "format": "image/jpeg",
            "height": 5760,
            "id": "https://iiif.ub.uni-leipzig.de/0000002636/00000001.jpg",
            "label": {"en": ["Vorderdeckel"]},
            "service": [
                {
                    "@id": "https://iiif.ub.uni-leipzig.de/iiif/j2k/0000/0026/0000002636/00000001.jpx",
                    "@type": "ImageService2",
                    "info": {
                        "@context": "http://iiif.io/api/image/2/context.json",
                        "@id": "https://iiif.ub.uni-leipzig.de/fcgi-bin/iipsrv.fcgi?iiif=/j2k/0000/0026/0000002636/00000001.jpx",
                        "height": 5760,
                        "profile": [
                            "http://iiif.io/api/image/2/level1.json",
                            {
                                "formats": ["jpg"],
                                "qualities": ["native", "color", "gray"],
                                "supports": [
                                    "regionByPct",
                                    "sizeByForcedWh",
                                    "sizeByWh",
                                    "sizeAboveFull",
                                    "rotationBy90s",
                                    "mirroring",
                                    "gray",
                                ],
                            },
                        ],
                        "protocol": "http://iiif.io/api/image",
                        "tiles": [
                            {"height": 256, "scaleFactors": [1, 2, 4, 8, 16, 32], "width": 256}
                        ],
                        "width": 3840,
                    },
                    "profile": "http://iiif.io/api/image/2/level1.json",
                }
            ],
            "type": "Image",
            "width": 3840,
        }
    ]
