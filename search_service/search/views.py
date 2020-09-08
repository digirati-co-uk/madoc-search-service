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
from rest_framework.response import Response
from rest_framework import status
from .models import PresentationAPIResource
from .serializer_utils import iiif_to_presentationapiresourcemodel


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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=iiif_to_presentationapiresourcemodel(data_dict=request.data))
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class PresentationAPIResourceDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = PresentationAPIResource.objects.all()
    serializer_class = PresentationAPISerializer



