from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Indexables, IIIFResource, Context
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchHeadline
from django.db.models import F
from .serializer_utils import simplify_ocr, calc_offsets


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username", "email"]


class ContextSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer for Context objects, i.e. for the site, project, collection, etc
    that might be associated with a IIIF resource.
    """

    class Meta:
        model = Context
        fields = ["url", "id", "type", "slug"]
        extra_kwargs = {"url": {"lookup_field": "slug"}}


class IIIFSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer for IIIF Prezi 3 resources.
    """

    contexts = ContextSerializer(read_only=True, many=True)

    class Meta:
        model = IIIFResource
        fields = [
            "url",
            "madoc_id",
            "madoc_thumbnail",
            "id",
            "type",
            "label",
            "thumbnail",
            "summary",
            "metadata",
            "rights",
            "provider",
            "requiredStatement",
            "navDate",
            "contexts",
        ]


class IIIFSummary(serializers.HyperlinkedModelSerializer):
    """
    Serializer that produces a summary of a IIIF resource for return in lists
    of search results or other similar nested views
    """

    contexts = ContextSerializer(read_only=True, many=True)

    class Meta:
        model = IIIFResource
        fields = ["url", "madoc_id", "madoc_thumbnail", "id", "type", "label", "contexts"]


class ContextSummarySerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer that produces a summary of a Context object for return in lists of
    search results or other similar nested views
    """

    class Meta:
        model = Context
        fields = ["url", "id", "type"]
        extra_kwargs = {"url": {"lookup_field": "slug"}}


class IndexablesSummarySerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer that produces a summary of an individually indexed "field" or text
    reource for return in lists of results or other similar nested views
    """

    rank = serializers.FloatField(default=None, read_only=True)
    snippet = serializers.CharField(default=None, read_only=True)
    language = serializers.CharField(default=None, read_only=None, source="language_iso639_1")
    bounding_boxes = serializers.SerializerMethodField()

    def get_bounding_boxes(self, obj):
        return calc_offsets(obj)

    class Meta:
        model = Indexables
        fields = ["type", "subtype", "snippet", "language", "rank", "bounding_boxes"]


class IIIFSearchSummarySerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer that produces the summarized search results.
    """

    contexts = ContextSummarySerializer(read_only=True, many=True)
    hits = serializers.SerializerMethodField("get_hits")
    resource_id = serializers.CharField(source="madoc_id")
    resource_type = serializers.CharField(source="type")
    rank = serializers.SerializerMethodField("get_rank")

    def get_rank(self, iiif):
        """
        Serializer method that calculates the average rank from the hits associated
        with this search result
        """
        try:
            return max([h["rank"] for h in self.get_hits(iiif=iiif)])
        except TypeError:
            return 1.0

    def get_hits(self, iiif):
        """
        Serializer method that calculates the hits to return along with this search
        result
        """
        # Rank must be greater than 0 (i.e. this is some kind of hit)
        filter_kwargs = {"rank__gt": 0.0}
        # Filter the indexables to query against to just those associated with this IIIF resource
        qs = Indexables.objects.filter(iiif=iiif)
        if self.context.get("hits_filter_kwargs"):
            # We have a dictionary of queries to use, so we use that
            search_query = self.context["hits_filter_kwargs"].get("search_vector", None)
        else:
            # Otherwise, this is probably a simple GET request, so we construct the queries from params
            search_string = self.context["request"].query_params.get("fulltext", None)
            language = self.context["request"].query_params.get("search_language", None)
            search_type = self.context["request"].query_params.get("search_type", "websearch")
            if search_string:
                if language:
                    search_query = SearchQuery(
                        search_string, config=language, search_type=search_type
                    )
                else:
                    search_query = SearchQuery(search_string, search_type=search_type)
            else:
                search_query = None
        if search_query:
            # Annotate the results in the queryset with rank, and with a snippet
            qs = (
                qs.annotate(
                    rank=SearchRank(F("search_vector"), search_query, cover_density=True),
                    snippet=SearchHeadline(
                        "original_content",
                        search_query,
                        max_words=50,
                        min_words=25,
                        max_fragments=3,
                    ),
                    fullsnip=SearchHeadline(
                        "indexable",
                        search_query,
                        start_sel="<start_sel>",
                        stop_sel="<end_sel>",
                        highlight_all=True,
                    ),
                )
                .filter(search_vector=search_query, **filter_kwargs)
                .order_by("-rank")
            )
        # Use the Indexables summary serializer to return the hit list
        serializer = IndexablesSummarySerializer(instance=qs, many=True)
        return serializer.data

    class Meta:
        model = IIIFResource
        fields = [
            "url",
            "resource_id",
            "resource_type",
            "madoc_thumbnail",
            "id",
            "rank",
            "label",
            "contexts",
            "hits",
        ]


class AutocompleteSerializer(serializers.ModelSerializer):
    """
    Serializer for the Indexables for autocompletion
    """
    class Meta:
        model = Indexables
        fields = [
            "indexable",
        ]


class IndexablesSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer for the Indexables, i.e. the indexed objects that are used to
    drive search and which are associated with a IIIF resource
    """

    iiif = IIIFSummary(read_only=True)

    class Meta:
        model = Indexables
        fields = [
            "url",
            "resource_id",
            "content_id",
            "original_content",
            "indexable",
            "indexable_date",
            "indexable_int",
            "indexable_float",
            "indexable_json",
            "selector",
            "type",
            "subtype",
            "language_iso639_2",
            "language_iso639_1",
            "language_display",
            "language_pg",
            "iiif",
        ]

    # def to_internal_value(self, data):
    #     if data.get("resource"):
    #         # To Do: Add something here that wraps the configuration for how it should parse
    #         # and index the data? Currently, if it gets a resource, it just assumes it's OCR
    #         if not data.get("type"):  # Only set this if not set
    #             data["type"] = "capturemodel"
    #         if not data.get("subtype"):  # Only set this if not set
    #             data["subtype"] = "ocr"
    #         # Assumption that this is OCR
    #         simplified = simplify_ocr(data["resource"])
    #         if simplified.get("indexable"):
    #             data["indexable"] = simplified["indexable"]
    #             data["original_content"] = simplified["indexable"]
    #         if simplified.get("selectors"):
    #             data["selector"] = simplified["selectors"]
    #         print("Internal value")
    #     return super(IndexablesSerializer, self).to_internal_value(data)

    def create(self, validated_data):
        # On create, associate the resource with the relevant IIIF resource
        # via the Madoc identifier for that object
        resource_id = validated_data.get("resource_id")
        content_id = validated_data.get("content_id")
        iiif = IIIFResource.objects.get(madoc_id=resource_id)
        validated_data["iiif"] = iiif
        if content_id and resource_id:
            print(f"Deleting any indexables for {resource_id} with content id {content_id}")
            Indexables.objects.filter(resource_id=resource_id, content_id=content_id).delete()
        return super(IndexablesSerializer, self).create(validated_data)


class CaptureModelSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer for the Indexables, i.e. the indexed objects that are used to
    drive search and which are associated with a IIIF resource
    """

    iiif = IIIFSummary(read_only=True)

    class Meta:
        model = Indexables
        fields = [
            "url",
            "resource_id",
            "content_id",
            "original_content",
            "indexable",
            "indexable_date",
            "indexable_int",
            "indexable_float",
            "indexable_json",
            "selector",
            "type",
            "subtype",
            "language_iso639_2",
            "language_iso639_1",
            "language_display",
            "language_pg",
            "iiif",
        ]

    def create(self, validated_data):
        # On create, associate the resource with the relevant IIIF resource
        # via the Madoc identifier for that object
        resource_id = validated_data.get("resource_id")
        content_id = validated_data.get("content_id")
        iiif = IIIFResource.objects.get(madoc_id=resource_id)
        validated_data["iiif"] = iiif
        if content_id and resource_id:
            print(f"Deleting any indexables for {resource_id} with content id {content_id}")
            Indexables.objects.filter(resource_id=resource_id, content_id=content_id).delete()
        return super(CaptureModelSerializer, self).create(validated_data)
