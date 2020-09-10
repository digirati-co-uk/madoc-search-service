# Stdlib imports

from django.contrib.auth.models import User
from django.db.models import F
from django.utils.translation import get_language_from_request, activate
from django.http import Http404, HttpResponse
import json

# Django Imports
from rest_framework import generics, permissions, filters
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchHeadline
from django_filters.rest_framework import DjangoFilterBackend


# Local imports
from .permissions import IsOwnerOrReadOnly
from .serializers import UserSerializer, PresentationAPISerializer, IndexablesSerializer
from rest_framework.response import Response
from rest_framework import status
from .models import PresentationAPIResource, Indexables
from .serializer_utils import iiif_to_presentationapiresourcemodel


@api_view(["GET"])
def api_root(request, format=None):
    return Response(
        {
            "users": reverse("user-list", request=request, format=format),
            "iiif": reverse("presentationapiresource-list", request=request, format=format),
            "indexable": reverse("indexables-list", request=request, format=format),
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
        serializer = self.get_serializer(
            data=iiif_to_presentationapiresourcemodel(data_dict=request.data)
        )
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class PresentationAPIResourceDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = PresentationAPIResource.objects.all()
    serializer_class = PresentationAPISerializer


class IndexablesDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Indexables.objects.all()
    serializer_class = IndexablesSerializer


class IndexablesList(generics.ListCreateAPIView):
    serializer_class = IndexablesSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ["indexable", "original_content", "=resource_id", "=content_id"]

    def get_queryset(self):
        search_string = self.request.query_params.get("fulltext", None)
        language = self.request.query_params.get("search_language", "english")
        search_type = self.request.query_params.get("search_type", "websearch")
        if search_string:
            query = SearchQuery(search_string, config=language,
                                search_type=search_type)
            return (
                Indexables.objects.annotate(
                    rank=SearchRank(F("search_vector"), query, cover_density=True),
                    snippet=SearchHeadline("original_content", query, max_words=50, min_words=25,
                                           max_fragments=3),
                )
                .filter(search_vector=query)
                .order_by("-rank")
            )
        return Indexables.objects.all()
