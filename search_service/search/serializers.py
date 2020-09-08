from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework import status
from drf_writable_nested.serializers import WritableNestedModelSerializer
from .models import PresentationAPIResource
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
        read_only_fields = ["url", "id", "m_summary", "search_vect"]






