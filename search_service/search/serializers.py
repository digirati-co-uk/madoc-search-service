from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Indexables, IIIFResource


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ["url", "username", "email"]


class IndexablesSerializer(serializers.HyperlinkedModelSerializer):
    rank = serializers.FloatField(default=None, read_only=True)
    snippet = serializers.CharField(default=None, read_only=True)
    facets = serializers.JSONField(default=None, read_only=True)

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
            "language_iso629_2",
            "language_iso629_1",
            "language_display",
            "language_pg",
            "rank",
            "snippet",
            "facets",
        ]
        read_only_fields = ["search_vector", "rank", "snippet"]


class IIIFSerializer(serializers.HyperlinkedModelSerializer):

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
        ]
