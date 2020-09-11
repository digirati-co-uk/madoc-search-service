# Stdlib imports

import json

from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchHeadline
from django.db.models import F, Value
from django.db.models import JSONField
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.translation import get_language


# Django Imports
from rest_framework import generics, filters, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse


# Local imports
from .serializers import UserSerializer, IndexablesSerializer, IIIFSerializer, ContextSerializer
from .models import Indexables, IIIFResource, Context
from .prezi_upgrader import Upgrader
from .langbase import LANGBASE
from .serializer_utils import flatten_iiif_descriptive

default_lang = get_language()
upgrader = Upgrader(flags={"default_lang": default_lang})


@api_view(["GET"])
def api_root(request, format=None):
    return Response(
        {
            "iiif": reverse("iiifresource-list", request=request, format=format),
            "indexable": reverse("indexables-list", request=request, format=format),
            "contexts": reverse("context-list", request=request, format=format),
        }
    )


class UserList(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserDetail(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class IIIFDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = IIIFResource.objects.all()
    serializer_class = IIIFSerializer

    def update(self, request, *args, **kwargs):
        """
        Override the update so that we can rewrite the format coming from Madoc in the event of
        an Update operation.
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        d = request.data
        # Try to populate from the request data, but if it's not there, just use existing
        data_dict = {
            "madoc_id": d.get("madoc_id", instance.madoc_id),
            "madoc_thumbnail": d.get("madoc_thumbnail", instance.madoc_thumbnail),
        }
        contexts = d.get("contexts")
        iiif3 = None
        # If we have IIIF stuff as a "resource" in the request.data
        if d.get("resource"):
            if d["resource"].get("@context") == "http://iiif.io/api/presentation/2/context.json":
                iiif3 = upgrader.process_resource(d["resource"], top=True)
                iiif3["@context"] = "http://iiif.io/api/presentation/3/context.json"
            else:
                iiif3 = d["resource"]
            for k in [
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
            ]:
                data_dict[k] = iiif3.get(k, getattr(instance, k, None))
        if iiif3:
            indexable_list = flatten_iiif_descriptive(
                iiif=iiif3, default_language=default_lang, lang_base=LANGBASE
            )
            if indexable_list:
                _ = Indexables.objects.filter(iiif__pk=instance.madoc_id).filter(
                    type__in=["descriptive", "metadata"]
                ).delete()
                for _indexable in indexable_list:
                    indexable_obj = Indexables(
                        **_indexable,
                        iiif=instance,
                        resource_id=instance.madoc_id
                    )
                    indexable_obj.save()


        serializer = self.get_serializer(instance, data=data_dict, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if contexts:
            c_objs = [Context.objects.get_or_create(**context) for context in contexts]
            c_objs_set = [c_obj for c_obj, _ in c_objs]
            instance.contexts.set(c_objs_set)
            instance.save()
        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)


class IIIFList(generics.ListCreateAPIView):
    queryset = IIIFResource.objects.all()
    serializer_class = IIIFSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]

    def create(self, request, *args, **kwargs):
        d = request.data
        data_dict = {"madoc_id": d["id"], "madoc_thumbnail": d["thumbnail"]}
        contexts = d.get("contexts")
        if d["resource"].get("@context") == "http://iiif.io/api/presentation/2/context.json":
            iiif3 = upgrader.process_resource(d["resource"], top=True)
            iiif3["@context"] = "http://iiif.io/api/presentation/3/context.json"
        else:
            iiif3 = d["resource"]
        for k in [
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
        ]:
            data_dict[k] = iiif3.get(k)
        serializer = self.get_serializer(data=data_dict)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        if contexts:
            instance = IIIFResource.objects.get(madoc_id=data_dict["madoc_id"])
            c_objs = [Context.objects.get_or_create(**context) for context in contexts]
            if instance:
                c_objs_set = [c_obj for c_obj, _ in c_objs]
                instance.contexts.set(c_objs_set)
                instance.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ContextDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Context.objects.all()
    serializer_class = ContextSerializer
    lookup_field = "slug"


class ContextList(generics.ListCreateAPIView):
    queryset = Context.objects.all()
    serializer_class = ContextSerializer


class IndexablesDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Indexables.objects.all()
    serializer_class = IndexablesSerializer


class IndexablesList(generics.ListCreateAPIView):
    serializer_class = IndexablesSerializer
    # filter_backends = [DjangoFilterBackend]
    # search_fields = ["indexable", "original_content", "=resource_id", "=content_id"]

    def get_queryset(self):
        search_string = self.request.query_params.get("fulltext", None)
        language = self.request.query_params.get("search_language", "english")
        search_type = self.request.query_params.get("search_type", "websearch")
        filter_kwargs = {}
        for param in self.request.query_params:
            if param not in ["fulltext", "search_language", "search_type"]:
                filter_kwargs[f"{param}__iexact"] = self.request.query_params.get(param, None)
        queryset = Indexables.objects.all()
        if search_string:
            query = SearchQuery(search_string, config=language, search_type=search_type)
            queryset = (
                queryset.annotate(
                    rank=SearchRank(F("search_vector"), query, cover_density=True),
                    snippet=SearchHeadline(
                        "original_content", query, max_words=50, min_words=25, max_fragments=3
                    ),
                )
                .filter(search_vector=query).filter(**filter_kwargs)
                .order_by("-rank")
            )
        facet_dict = {}
        # This should really happen elsewhere, as it won't work when filters are also applied
        # as the data is annotated before the filters, so the counts are inaccurate
        # instead, there should probably be something happening on the dataset in aggregate
        # via some manually invoked filters etc.
        for facet_key in ["type", "language_display"]:
            facet_dict[facet_key] = {}
            for t in queryset.values_list(facet_key).distinct():
                kwargs = {f"{facet_key}__exact": t[0]}
                facet_dict[facet_key][t[0]] = queryset.filter(**kwargs).count()
        return queryset.annotate(facets=Value(facet_dict, JSONField()))
