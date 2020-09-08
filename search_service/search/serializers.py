from django.contrib.auth.models import User
from rest_framework import serializers
from drf_writable_nested.serializers import WritableNestedModelSerializer
from drf_writable_nested.mixins import UniqueFieldsMixin
from .models import MadocContext, PresentationAPIResource


class UserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = User
        fields = ["url", "username", "email"]


class ContextsSerializer(UniqueFieldsMixin, serializers.HyperlinkedModelSerializer):

    class Meta:
        model = MadocContext
        fields = ["url", "id", "label", "identifier"]


class PresentationAPISerializer(UniqueFieldsMixin, WritableNestedModelSerializer):
    class Meta:
        model = PresentationAPIResource
        fields = ["url", "id", "identifier", "label", "description", "type",
                  "viewing_direction", "viewing_hint", "attribution",
                  "license", "navdate", "metadata", "search_vect",
                  "m_summary", "contexts_json"]
        read_only_fields = ["url", "id", "m_summary", "search_vect"]



