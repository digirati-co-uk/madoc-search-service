# Django Imports

from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchHeadline
from django.db import models
from django.db.models import F, Value, Q, JSONField
from django.utils.translation import get_language
from django_filters import rest_framework as df_filters
from django_filters.rest_framework import DjangoFilterBackend

# DRF Imports
from rest_framework import generics, filters, status
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.mixins import ListModelMixin
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.reverse import reverse

from operator import or_, and_
from functools import reduce

# Local imports
from .langbase import LANGBASE
from .models import Indexables, IIIFResource, Context
from .prezi_upgrader import Upgrader
from .serializer_utils import flatten_iiif_descriptive
from .serializers import (
    UserSerializer,
    IndexablesSerializer,
    IIIFSerializer,
    ContextSerializer,
    IIIFSearchSummarySerializer,
)


# Globals
default_lang = get_language()
upgrader = Upgrader(flags={"default_lang": default_lang})


@api_view(["GET"])
def api_root(request, format=None):
    return Response(
        {
            "iiif": reverse("iiifresource-list", request=request, format=format),
            "indexable": reverse("indexables-list", request=request, format=format),
            "contexts": reverse("context-list", request=request, format=format),
            "search": reverse("search", request=request, format=format),
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
                _ = (
                    Indexables.objects.filter(iiif__pk=instance.madoc_id)
                    .filter(type__in=["descriptive", "metadata"])
                    .delete()
                )
                for _indexable in indexable_list:
                    indexable_obj = Indexables(
                        **_indexable, iiif=instance, resource_id=instance.madoc_id
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
    filterset_fields = ["madoc_id"]

    def create(self, request, *args, **kwargs):
        d = request.data
        data_dict = {"madoc_id": d["id"], "madoc_thumbnail": d["thumbnail"]}
        contexts = d.get("contexts")
        if d.get("resource"):
            if d["resource"].get("@context") == "http://iiif.io/api/presentation/2/context.json":
                iiif3 = upgrader.process_resource(d["resource"], top=True)
                iiif3["@context"] = "http://iiif.io/api/presentation/3/context.json"
            else:
                iiif3 = d["resource"]
        else:
            iiif3 = None
        if contexts:
            if iiif3:
                if iiif3.get("type"):
                    contexts += [{"id": d["id"], "type": iiif3["type"]}]

        def ingest_iiif(iiif3_resource=None, resource_contexts=None):
            if iiif3_resource:
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
                    data_dict[k] = iiif3_resource.get(k)
            serializer = self.get_serializer(data=data_dict)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            instance = IIIFResource.objects.get(madoc_id=data_dict["madoc_id"])
            if resource_contexts:
                if iiif3_resource:
                    if iiif3_resource.get("type"):
                        resource_contexts += [{"id": d["id"], "type": iiif3_resource["type"]}]
                c_objs = [Context.objects.get_or_create(**cont) for cont in resource_contexts]
                if instance:
                    c_objs_set = [c_obj for c_obj, _ in c_objs]
                    instance.contexts.set(c_objs_set)
                    instance.save()
            if iiif3_resource:
                indexable_list = flatten_iiif_descriptive(
                    iiif=iiif3, default_language=default_lang, lang_base=LANGBASE
                )
                if indexable_list:
                    for _indexable in indexable_list:
                        indexable_obj = Indexables(
                            **_indexable, iiif=instance, resource_id=instance.madoc_id
                        )
                        indexable_obj.save()
            return serializer.data, self.get_success_headers(serializer.data)

        if iiif3.get("items"):
            print("Got items")
        manifest_data, manifest_headers = ingest_iiif(
            iiif3_resource=iiif3, resource_contexts=contexts
        )
        return Response(manifest_data, status=status.HTTP_201_CREATED, headers=manifest_headers)


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
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        search_string = self.request.query_params.get("fulltext", None)
        language = self.request.query_params.get("search_language", None)
        search_type = self.request.query_params.get("search_type", "websearch")
        filter_kwargs = {"rank__gt": 0.0}
        for param in self.request.query_params:
            if param not in ["fulltext", "search_language", "search_type"]:
                filter_kwargs[f"{param}__iexact"] = self.request.query_params.get(param, None)
        queryset = Indexables.objects.all()
        if search_string:
            if language:
                query = SearchQuery(search_string, config=language, search_type=search_type)
            else:
                query = SearchQuery(search_string, search_type=search_type)
            queryset = (
                queryset.annotate(
                    rank=SearchRank(F("search_vector"), query, cover_density=True),
                    snippet=SearchHeadline(
                        "original_content", query, max_words=50, min_words=25, max_fragments=3
                    ),
                )
                .filter(search_vector=query)
                .filter(**filter_kwargs)
                .order_by("-rank")
            )
        facet_dict = {}
        # This should really happen elsewhere, as it won't work when filters are also applied
        # as the data is annotated before the filters, so the counts are inaccurate
        # instead, there should probably be something happening on the dataset in aggregate
        # via some manually invoked filters etc.
        for facet_key in ["type", "language_display", "type", "subtype"]:
            facet_dict[facet_key] = {}
            for t in queryset.values_list(facet_key).distinct():
                kwargs = {f"{facet_key}__iexact": t[0]}
                facet_dict[facet_key][t[0]] = queryset.filter(**kwargs).count()
        return queryset.annotate(facets=Value(facet_dict, JSONField()))


class MadocPagination(PageNumberPagination):
    """

    Pagination class for Madoc results

    "pagination": {
        "page": 1,
        "totalPages": 35,
        "totalResults": 830
      }
    """

    def get_paginated_response(self, data):
        return Response(
            {
                "pagination": {
                    "page": self.page.number,
                    "totalPages": self.page.paginator.num_pages,
                    "totalResults": self.page.paginator.count,
                },
                "results": data,
            }
        )


class ContextFilterSet(df_filters.FilterSet):
    """
    Currently unused. Test filterset to change the filter field for contexts, e.g. to
    "cont"
    """

    cont = df_filters.filters.CharFilter(field_name="contexts__id", lookup_expr="iexact")

    class Meta:
        model = Context
        fields = ["cont"]


def parse_search(req):
    """
    Function to parse incoming search data (from request params or incoming json)
    into a set of filter kwargs that can be passed to the list and hits methods.
    """
    if req.method == "POST":
        prefilter_kwargs = {}
        filter_kwargs = {}
        search_string = req.data.get("fulltext", None)
        language = req.data.get("search_language", None)
        search_type = req.data.get("search_type", "websearch")
        facet_fields = req.data.get("facet_fields", None)
        contexts = req.data.get("contexts", None)
        madoc_identifiers = req.data.get("madoc_identifiers", None)
        iiif_identifiers = req.data.get("iiif_identifiers", None)
        facet_queries = req.data.get("facets", None)
        if contexts:
            prefilter_kwargs[f"contexts__id__in"] = contexts
        if madoc_identifiers:
            prefilter_kwargs[f"madoc_id__in"] = madoc_identifiers
        if iiif_identifiers:
            prefilter_kwargs[f"id__in"] = iiif_identifiers
        if search_string:
            if language:
                filter_kwargs["indexables__search_vector"] = SearchQuery(
                    search_string, config=language, search_type=search_type
                )
            else:
                filter_kwargs["indexables__search_vector"] = SearchQuery(
                    search_string, search_type=search_type
                )
        for p in [
            "type",
            "subtype",
            "language_iso629_2",
            "language_iso629_1",
            "language_display",
            "language_pg",
        ]:
            if req.data.get(p, None):
                filter_kwargs[f"indexables__{p}__iexact"] = req.data[p]
        postfilter_q = []
        if facet_queries:  # *** This code really needs a refactor for elegance/speed ***
            # Generate a list of keys concatenated from type and subtype
            # These should be "OR"d together later.
            # e.g.
            # {"metadata|author": []}
            sorted_facets = {
                "|".join([f.get("type", ""), f.get("subtype", "")]): [] for f in facet_queries
            }
            # Copy the query into that lookup so we can get queries against the same type/subtype
            # e.g.
            # {"metadata|author": ["John Smith", "Mary Jones"]}
            for f in facet_queries:
                sorted_facets["|".join([f.get("type", ""), f.get("subtype", "")])].append(f)
            for sorted_facet_key, sorted_facet_queries in sorted_facets.items():
                # For each combination of type/subtype
                # 1. Concatenate all of the queries into an AND
                # e.g. "type" = "metadata" AND "subtype" = "author" AND "indexables" = "John Smith"
                # 2. Concatenate all of thes einto an OR
                # so that you get something with the intent of AUTHOR = (A or B)
                postfilter_q.append(
                    reduce(  # All of the queries with the same field are OR'd together
                        or_,
                        [
                            reduce(  # All of the fields within a single facet query are AND'd together
                                and_,
                                (
                                    Q(  # Iterate the keys in the facet dict to generate the Q()
                                        **{
                                            f"indexables__{(lambda k: 'indexable' if k == 'value' else k)(k)}__"
                                            f"{sorted_facet_query.get('field_lookup', 'iexact')}": v
                                        }  # You can pass in something other than iexact using the field_lookup key
                                    )
                                    for k, v in sorted_facet_query.items()
                                    if k in ["type", "subtype", "indexable", "value"]  # These are the fields to query
                                ),
                            )
                            for sorted_facet_query in sorted_facet_queries
                        ],
                    )
                )
        hits_filter_kwargs = {
            k.replace("indexables__", ""): v
            for k, v in filter_kwargs.items()
            if k.startswith("indexables")
        }
        if search_string:
            hits_filter_kwargs["search_string"] = search_string
        if language:
            hits_filter_kwargs["language"] = language
        if search_type:
            hits_filter_kwargs["search_type"] = search_type

        sort_order = req.data.get("ordering", "-rank")
        return (
            prefilter_kwargs,
            filter_kwargs,
            postfilter_q,  # postfilter_kwargs,
            facet_fields,
            hits_filter_kwargs,
            sort_order,
        )
    elif req.method == "GET":
        search_string = req.query_params.get("fulltext", None)
        language = req.query_params.get("search_language", None)
        search_type = req.query_params.get("search_type", "websearch")
        filter_kwargs = {}
        postfilter_kwargs = [{}]
        prefilter_kwargs = {}
        for param in req.query_params:
            if param in [
                "type",
                "subtype",
                "language_iso629_2",
                "language_iso629_1",
                "language_display",
                "language_pg",
            ]:
                filter_kwargs[f"indexables__{param}__iexact"] = req.query_params.get(param, None)
            elif param == "facet_type":
                postfilter_kwargs[0][f"indexables__type__iexact"] = req.query_params.get(
                    param, None
                )
            elif param == "facet_subtype":
                postfilter_kwargs[0][f"indexables__subtype__iexact"] = req.query_params.get(
                    param, None
                )
            elif param == "facet_value":
                postfilter_kwargs[0][f"indexables__indexable__iexact"] = req.query_params.get(
                    param, None
                )
        if search_string:
            if language:
                filter_kwargs["indexables__search_vector"] = SearchQuery(
                    search_string, config=language, search_type=search_type
                )
            else:
                filter_kwargs["indexables__search_vector"] = SearchQuery(
                    search_string, search_type=search_type
                )
        hits_filter_kwargs = {
            k.replace("indexables__", ""): v
            for k, v in filter_kwargs.items()
            if k.startswith("indexables")
        }
        if search_string:
            hits_filter_kwargs["search_string"] = search_string
        if language:
            hits_filter_kwargs["language"] = language
        if search_type:
            hits_filter_kwargs["search_type"] = search_type
        sort_order = req.query_params.get("ordering", "-rank")
        return (
            prefilter_kwargs,
            filter_kwargs,
            postfilter_kwargs,
            None,
            hits_filter_kwargs,
            sort_order,
        )


class IIIFSearch(viewsets.ModelViewSet, ListModelMixin):
    """
    Simple read only view for the IIIF data with methods for
    adding hits and generating facets for return in the results

    Uses a custom paginator to fit the Madoc model.
    """

    queryset = IIIFResource.objects.all()
    serializer_class = IIIFSearchSummarySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["madoc_id", "contexts__id"]
    pagination_class = MadocPagination

    def list(self, request, *args, **kwargs):
        """
        Override the LIST method, so we can add some summary data here.

        Possible options:

        1) Accept the facets as a parameter (or blob in JSON)
        2) Accept the facets via config
        3) (as per now) facets are generated by a query across the metadata subtypes

        3 is likely the most flexible/future-proof, but is potentially slower.

        Explore:

        Ways of making this query more efficient when the number of objects is high.

        """
        print("List method")
        # Call a function to set the filter_kwargs and postfilter_kwargs based on incoming request
        (
            prefilter_kwargs,
            filter_kwargs,
            postfilter_kwargs,
            facet_fields,
            hits_filter_kwargs,
            sort_order,
        ) = parse_search(req=request)
        if facet_fields:
            setattr(self, "facet_fields", facet_fields)
        if prefilter_kwargs:
            setattr(self, "prefilter_kwargs", prefilter_kwargs)
        if filter_kwargs:
            setattr(self, "filter_kwargs", filter_kwargs)
            print(filter_kwargs)
        if postfilter_kwargs:
            setattr(self, "postfilter_kwargs", postfilter_kwargs)
        if hits_filter_kwargs:
            setattr(self, "hits_filter_kwargs", hits_filter_kwargs)
        response = super(IIIFSearch, self).list(request, args, kwargs)
        facet_summary = {"metadata": {}}
        # If we haven't been provided a list of facet fields via a POST
        # just generate the list by querying the unique list of metadata subtypes
        if not facet_fields:
            facet_fields = []
            for t in (
                self.get_queryset()
                .filter(indexables__type__iexact="metadata")
                .values("indexables__subtype")
                .distinct()
            ):
                for _, v in t.items():
                    facet_fields.append(v)
        for v in facet_fields:
            facet_summary["metadata"][v] = {
                x["indexables__indexable"]: x["n"]
                for x in self.get_queryset()
                .filter(indexables__subtype__iexact=v)
                .values("indexables__indexable")
                .distinct()
                .annotate(n=models.Count("pk"))
                .order_by("-n")[:10]
            }
        response.data["facets"] = facet_summary
        if sort_order:
            if "-" in sort_order:
                response.data["results"] = sorted(
                    response.data["results"],
                    key=lambda k: (k[sort_order.replace("-", "")],),
                    reverse=True,
                )
            else:
                response.data["results"] = sorted(
                    response.data["results"], key=lambda k: (k[sort_order],)
                )
        return response

    def get_serializer_context(self):
        """
        Pass the request into the serializer context so it is available
        in the serializer method(s), e.g. the get_hits method used to
        populate each manifest with a list of hits that match the query
        parameters
        """
        print("Updating context")
        context = super(IIIFSearch, self).get_serializer_context()
        context.update({"request": self.request})
        if hasattr(self, "hits_filter_kwargs"):
            context.update({"hits_filter_kwargs": self.hits_filter_kwargs})
        # if hasattr(self, "hits_postfilter_kwargs"):
        #     context.update({"hits_postfilter_kwargs": self.hits_postfilter_kwargs})
        return context

    def get_queryset(self):
        """
        Look for

            self.prefilter_kwargs: filters to execute before the fulltext search
            self.filter_kwargs: filters associated with the fulltext search
            self.postfilter_kwargs: filters to run after the fulltext search

        Apply these and return distinct objects
        """
        print("Updating queryset")
        queryset = IIIFResource.objects.all()
        if hasattr(self, "prefilter_kwargs"):
            queryset = queryset.filter(**self.prefilter_kwargs)
        if hasattr(self, "filter_kwargs"):
            queryset = queryset.filter(**self.filter_kwargs)
        if hasattr(self, "postfilter_kwargs"):
            # Just check if this thing is nested Q() objects, rather than dicts
            if type(self.postfilter_kwargs[0]) == Q:
                # This is also a chainging operation but the filters being
                # chained might contain "OR"s rather than ANDs
                for f in self.postfilter_kwargs:
                    queryset = queryset.filter(*(f,))
            else:  # GET requests (i.e. without the fancy Q reduction)
                for filter_dict in self.postfilter_kwargs:
                    # This is a chaining operation
                    # Appending each filter one at a time
                    queryset = queryset.filter(**filter_dict)
        return queryset.distinct()
