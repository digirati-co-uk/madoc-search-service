# Stdlib imports

from django.contrib.auth.models import User
from django.utils.translation import get_language_from_request, activate

# Django Imports
from rest_framework import generics, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse

# Local imports
from .permissions import IsOwnerOrReadOnly
from .serializers import UserSerializer, PresentationAPISerializer
from .models import PresentationAPIResource


@api_view(["GET"])
def api_root(request, format=None):
    return Response(
        {
            "users": reverse("user-list", request=request, format=format),
            "iiif": reverse("presentationapiresource-list", request=request, format=format)
        }
    )


class UserList(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserDetail(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class PresentationAPIResourceList(generics.ListCreateAPIView):
    queryset = PresentationAPIResource.objects.all()
    serializer_class = PresentationAPISerializer


class PresentationAPIResourceDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = PresentationAPIResource.objects.all()
    serializer_class = PresentationAPISerializer

