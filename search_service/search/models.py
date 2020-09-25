
from django.contrib.postgres.search import SearchVectorField, SearchVector
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from model_utils.models import TimeStampedModel
from django_extensions.db.fields import AutoSlugField

# from .langbase import INTERNET_LANGUAGES
from django.utils.translation import ugettext_lazy as _


# Add Models


class Context(TimeStampedModel):
    """"
    Context

    """

    id = models.CharField(
        max_length=512, primary_key=True, editable=True, verbose_name=_("Identifier (Context)")
    )
    type = models.CharField(max_length=30)
    slug = AutoSlugField(populate_from="id")


class IIIFResource(TimeStampedModel):
    madoc_id = models.CharField(
        max_length=512, primary_key=True, verbose_name=_("Identifier (Madoc)")
    )
    madoc_thumbnail = models.URLField(blank=True, null=True)
    id = models.URLField(verbose_name=_("IIIF id"))
    slug = AutoSlugField(populate_from="madoc_id")
    type = models.CharField(max_length=30)
    label = models.JSONField(blank=True, null=True)
    thumbnail = models.JSONField(blank=True, null=True)
    summary = models.JSONField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    navDate = models.DateTimeField(blank=True, null=True)
    rights = models.URLField(blank=True, null=True)
    requiredStatement = models.JSONField(blank=True, null=True)
    provider = models.JSONField(blank=True, null=True)
    items = models.ManyToManyField("self", blank=True, related_name="ispartof")
    contexts = models.ManyToManyField(Context, blank=True, related_name="associated_iiif")


class Indexables(TimeStampedModel):
    """
    Model for storing indexable data per object

    id: autogenerated
    resource: e.g. manifest id, canvas id, etc (this is a foreign key)
    resource_id: this is just a string
    ? contexts: store here, or on the related resource (prob. resource)
    type: metadata, capture model, presentation_api, see_also
    language_iso639_2: e.g. eng, ara   ? store just this but use lookups to identify
    language_iso639_1: e.g. en, ar
    language_display: e.g English
    language_pg: postgres language
    indexable: concatenated/summarised content for indexing
    search_vector: search vector for the indexer to use
    original_content: textual content (as per original), if the original is JSON, this will be
        dumped/serialised JSON, rather than a JSON object

    N.B. gin index on search_vector for speed/performance

    https://www.loc.gov/standards/iso639-2/php/code_list.php
    """

    # objects = IndexableManager()
    resource_id = models.CharField(
        max_length=512, verbose_name=_("Identifier (URL/URI/URN) for associated IIIF resource")
    )
    content_id = models.CharField(
        max_length=512,
        verbose_name=_("Identifier (URL/URI/URN) for the content, if it has one"),
        blank=True,
        null=True,
    )
    iiif = models.ForeignKey(
        IIIFResource, related_name="indexables", blank=True, on_delete=models.CASCADE
    )
    indexable = models.TextField()
    original_content = models.TextField()
    search_vector = SearchVectorField(blank=True, null=True)
    language_iso639_2 = models.CharField(max_length=3, blank=True, null=True)
    language_iso639_1 = models.CharField(max_length=2, blank=True, null=True)
    language_display = models.CharField(max_length=64, blank=True, null=True)
    language_pg = models.CharField(max_length=64, blank=True, null=True)
    selector = models.JSONField(blank=True, null=True)
    type = models.CharField(max_length=64)
    subtype = models.CharField(max_length=256)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if "update_fields" not in kwargs or "search_vector" not in kwargs["update_fields"]:
            if self.language_pg:
                self.search_vector = SearchVector("indexable", weight="A", config=self.language_pg)
            else:
                self.search_vector = SearchVector("indexable", weight="A")
            self.save(update_fields=["search_vector"])

    class Meta:
        # Add a postgres index for the search_vector
        indexes = [
            GinIndex(fields=["search_vector"]),
            models.Index(fields=["original_content"]),
            models.Index(fields=["content_id"]),
            models.Index(fields=["language_iso639_2", "language_iso639_1", "language_display"]),
            models.Index(fields=["type"]),
            models.Index(fields=["subtype"]),
        ]
