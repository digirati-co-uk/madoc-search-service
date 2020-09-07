from django.contrib.auth.models import User
from rest_framework import serializers
# from drf_writable_nested.serializers import WritableNestedModelSerializer


class UserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = User
        fields = ["url", "username", "email"]
