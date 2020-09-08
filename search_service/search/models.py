import uuid
from bs4 import BeautifulSoup

from django.contrib.postgres.search import SearchVectorField, SearchVector
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from model_utils.models import TimeStampedModel

# from .langbase import INTERNET_LANGUAGES
from django.utils.translation import ugettext_lazy as _


# Add Models

class PresentationAPIResource(TimeStampedModel):
    """
    IIIF Manifest, Collection, etc.

    To Do: Add logo, thumbnail, etc
    """

    IIIFTYPES = (
        ("Col", _("Collection")),
        ("Man", _("Manifest")),
        ("Seq", _("Sequence")),
        ("Rng", _("Range")),
        ("Cvs", _("Canvas")),
    )
    VIEWINGDIRECTION = (
        ("l2r", _("left-to-right")),
        ("r2l", _("right-to-left")),
        ("t2b", _("top-to-bottom")),
        ("b2t", _("bottom-to-top")),
    )
    VIEWINGHINT = (
        ("ind", _("individuals")),
        ("pgd", _("paged")),
        ("cnt", _("continuous")),
        ("mpt", _("multi-part")),
        ("npg", _("non-paged")),
        ("top", _("top")),
        ("fac", _("facing-pages")),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=512, verbose_name=_("Label"))
    identifier = models.CharField(max_length=512, verbose_name=_("Identifier (URL/URI/URN)"))
    within = ArrayField(base_field=models.CharField(max_length=2048), verbose_name=_("Within"),
                        null=True, blank=True)
    type = models.CharField(max_length=3, choices=IIIFTYPES, verbose_name=_("IIIF Object Type"))
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))
    attribution = models.CharField(
        max_length=512, verbose_name=_("Attribution"), blank=True, null=True
    )
    license = models.URLField(verbose_name=_("License (URL)"), blank=True, null=True)
    viewing_direction = models.CharField(
        max_length=3, choices=VIEWINGDIRECTION, verbose_name=_("Viewing direction"), default="l2r"
    )
    viewing_hint = models.CharField(
        max_length=3, choices=VIEWINGHINT, verbose_name=_("Viewing hint"), default="pgd"
    )
    navdate = models.DateTimeField(blank=True, null=True, verbose_name=_("Navigation date"))
    search_vect = SearchVectorField(null=True)
    metadata = models.JSONField(blank=True, null=True, verbose_name=_("IIIF Metadata block"))
    m_summary = models.TextField(blank=True, null=True, verbose_name=_("Metadata summary"))

    def save(self, *args, **kwargs):
        self.m_summary = BeautifulSoup(
                " ".join(
                    [i.get("value").replace("<br>", " ") for i in self.metadata if i.get("value")]
                ),
                "html.parser",
            ).text
        super().save(*args, **kwargs)
        if 'update_fields' not in kwargs or 'search_vect' not in kwargs['update_fields']:
            self.search_vect = (
                    SearchVector("label", weight="A")
                    + SearchVector("description", weight="C")
                    + SearchVector("attribution", weight="A")
                    + SearchVector("m_summary", weight="B",
                                   )
            )
            self.save(update_fields=['search_vect'])

    class Meta:
        indexes = [GinIndex(fields=["search_vect"])]
