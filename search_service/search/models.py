import uuid

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from model_utils.models import TimeStampedModel

from .langbase import INTERNET_LANGUAGES
from django.utils.translation import ugettext_lazy as _


# Add Models


class MadocContext(TimeStampedModel):
    """
    Identifiers/labels/urns for sites, projects, collections, etc that contain resources
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=512, verbose_name=_("Label"))
    identifier = models.CharField(
        max_length=512, verbose_name=_("Identifier (URL/URI/URN)")
    )


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
    identifier = models.CharField(
        max_length=512, verbose_name=_("Identifier (URL/URI/URN)")
    )
    contexts = models.ManyToManyField(MadocContext, related_name="iiifresources")
    type = models.CharField(
        max_length=3, choices=IIIFTYPES, verbose_name=_("IIIF Object Type")
    )
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))
    attribution = models.CharField(max_length=512, verbose_name=_("Attribution"),
                                   blank=True, null=True)
    license = models.URLField(verbose_name=_("License (URL)"), blank=True, null=True)
    viewing_direction = models.CharField(
        max_length=3, choices=VIEWINGDIRECTION, verbose_name=_("Viewing direction"),
        default="l2r"
    )
    viewing_hint = models.CharField(
        max_length=3, choices=VIEWINGHINT, verbose_name=_("Viewing hint"),
        default="pgd"
    )
    navdate = models.DateTimeField(blank=True, null=True, verbose_name=_("Navigation date"))
    search_vect = SearchVectorField(null=True)

    class Meta:
        indexes = [
            GinIndex(fields=['search_vect']),
        ]

