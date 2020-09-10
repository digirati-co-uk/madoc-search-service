from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework import status
from drf_writable_nested.serializers import WritableNestedModelSerializer
from .models import PresentationAPIResource, Indexables
from .serializer_utils import iiif_to_presentationapiresourcemodel


class UserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = User
        fields = ["url", "username", "email"]


class PresentationAPISerializer(WritableNestedModelSerializer):
    class Meta:
        model = PresentationAPIResource
        fields = ["url", "id", "identifier", "label", "description", "type",
                  "viewing_direction", "viewing_hint", "attribution",
                  "license", "navdate", "metadata", "search_vect",
                  "m_summary", "within"]
        read_only_fields = ["url", "id", "m_summary", "search_vect", "metadata"]


class IndexablesSerializer(serializers.HyperlinkedModelSerializer):
    rank = serializers.FloatField(default=None, read_only=True)
    snippet = serializers.CharField(default=None, read_only=True)

    class Meta:
        model = Indexables
        fields = ["url", "resource_id", "content_id", "original_content",
                  "indexable", "search_vector", "type", "language_iso629_2",
                  "language_iso629_1", "language_display", "language_pg", "rank", "snippet"]
        read_only_fields = ["search_vector", "rank", "snippet"]



