from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Indexables, IIIFResource, Context


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username", "email"]


class ContextSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Context
        fields = ["url", "id", "type", "slug"]
        extra_kwargs = {
            'url': {'lookup_field': 'slug'},
        }


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
            "contexts"
        ]


class IIIFSummary(serializers.HyperlinkedModelSerializer):
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
            "contexts"
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
            "iiif"
        ]
        read_only_fields = ["search_vector", "rank", "snippet"]