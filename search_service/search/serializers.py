from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Indexables, IIIFResource, Context
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchHeadline
from django.db.models import F, Value


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username", "email"]


class ContextSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Context
        fields = ["url", "id", "type", "slug"]
        extra_kwargs = {"url": {"lookup_field": "slug"}}


class IIIFSerializer(serializers.HyperlinkedModelSerializer):
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
    contexts = ContextSerializer(read_only=True, many=True)

    class Meta:
        model = IIIFResource
        fields = ["url", "madoc_id", "madoc_thumbnail", "id", "type", "label", "contexts"]


class ContextSummarySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Context
        fields = ["url", "id", "type"]
        extra_kwargs = {"url": {"lookup_field": "slug"}}


class IndexablesSummarySerializer(serializers.HyperlinkedModelSerializer):
    rank = serializers.FloatField(default=None, read_only=True)
    snippet = serializers.CharField(default=None, read_only=True)
    language = serializers.CharField(default=None, read_only=None, source="language_iso629_1")
    # facets = serializers.JSONField(default=None, read_only=True)

    class Meta:
        model = Indexables
        fields = ["type", "subtype", "snippet", "language", "rank", "original_content"]


class IIIFSearchSummarySerializer(serializers.HyperlinkedModelSerializer):
    context = ContextSummarySerializer(read_only=True, many=True, source="contexts")
    hits = serializers.SerializerMethodField("get_hits")
    resource_id = serializers.CharField(source="madoc_id")
    resource_type = serializers.CharField(source="type")

    def get_hits(self, iiif):
        qs = Indexables.objects.filter(iiif=iiif)
        search_string = self.context["request"].query_params.get("fulltext", None)
        language = self.context["request"].query_params.get("search_language", None)
        search_type = self.context["request"].query_params.get("search_type", "websearch")
        filter_kwargs = {"rank__gt": 0.0}
        for param in self.context["request"].query_params:
            if param not in ["fulltext", "search_language", "search_type"]:
                if param in [
                    "hit_type",
                    "language_iso629_2",
                    "language_iso629_1",
                    "language_display",
                    "language_pg",
                ]:
                    filter_kwargs[f"{param}__iexact"] = self.context["request"].query_params.get(
                        param, None
                    )
        if search_string:
            if language:
                query = SearchQuery(search_string, config=language, search_type=search_type)
            else:
                query = SearchQuery(search_string, search_type=search_type)
            qs = (
                qs.annotate(
                    rank=SearchRank(F("search_vector"), query, cover_density=True),
                    snippet=SearchHeadline(
                        "original_content", query, max_words=50, min_words=25, max_fragments=3
                    ),
                )
                .filter(search_vector=query, **filter_kwargs)
                .order_by("-rank")
            )
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
            "label",
            "context",
            "hits",
        ]


class IndexablesSerializer(serializers.HyperlinkedModelSerializer):
    rank = serializers.FloatField(default=None, read_only=True)
    snippet = serializers.CharField(default=None, read_only=True)
    facets = serializers.JSONField(default=None, read_only=True)
    iiif = IIIFSummary(read_only=True)

    class Meta:
        model = Indexables
        fields = [
            "url",
            "resource_id",
            "content_id",
            "original_content",
            "indexable",
            "search_vector",
            "type",
            "subtype",
            "language_iso629_2",
            "language_iso629_1",
            "language_display",
            "language_pg",
            "rank",
            "snippet",
            "facets",
            "iiif",
        ]
        read_only_fields = ["search_vector", "rank", "snippet"]
