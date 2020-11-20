# Django Imports

from copy import deepcopy
from functools import reduce
from operator import or_, and_

from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchQuery
from django.db import models
from django.db.models import Q
from django.utils.translation import get_language
from django_filters import rest_framework as df_filters
from django_filters.rest_framework import DjangoFilterBackend

# DRF Imports
from rest_framework import generics, filters, status
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.exceptions import ValidationError, ParseError

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
    CaptureModelSerializer,
    AutocompleteSerializer,
)
from .indexable_utils import gen_indexables

from django.conf import settings

from collections import defaultdict

# Globals
default_lang = get_language()
upgrader = Upgrader(flags={"default_lang": default_lang})
global_facet_on_manifests = settings.FACET_ON_MANIFESTS_ONLY
global_facet_types = ["metadata"]


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
        """
        Override the .create() method on the rest-framework generic ListCreateAPIViewset
        """

        def ingest_iiif(
            iiif3_resource=None,
            resource_contexts=None,
            madoc_id=None,
            madoc_thumbnail=None,
            child=False,
            parent=None,
        ):
            """ "
            Nested function that ingests the IIIF object into PostgreSQL via the Django ORM.

            :param iiif3_resource: IIIF object (this could be anything in the API spec)
            :param resource_contexts: contexts, e.g. collections, sites, manifests, etc.
            :param madoc_id: the identifier for this thing
            :param madoc_thumbnail: the thumbnail for this thing
            :param child: is this a child object, or the object that has been POSTed
            :param parent: the madoc_id for the parent object that this is being derived from (if any)
            """
            local_dict = {"madoc_id": madoc_id, "madoc_thumbnail": madoc_thumbnail}
            # Add the relevant keys from the IIIF resource into the data dictionary
            # To Do: This should probanly be working with a set of keys passed in rather than the
            # data dict from the outer context
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
                    local_dict[k] = iiif3_resource.get(k)
            parent_object = None
            if (child is True) and (parent is not None):
                parent_object = IIIFResource.objects.get(madoc_id=parent)
            """
            To Do: We potentially need something here to replace the
            perform_create with a perform_update in the event that the object exists, and then we can 
            have the operation be idempotent as a POST will update rather than error
            """
            serializer = self.get_serializer(data=local_dict)  # Serialize the data
            serializer.is_valid(raise_exception=True)  # Check it's valid
            self.perform_create(serializer)  # Create the object
            instance = IIIFResource.objects.get(
                madoc_id=local_dict["madoc_id"]
            )  # Get the object created
            if resource_contexts:
                local_contexts = deepcopy(resource_contexts)
            else:
                local_contexts = []
            if iiif3_resource:  # Add myself to the context(s)
                if local_dict.get("type"):
                    local_contexts += [{"id": madoc_id, "type": local_dict["type"]}]
                    local_contexts += [{"id": local_dict["id"], "type": local_dict["type"]}]
            if parent_object is not None:
                # If I'm, e.g. a Canvas, add my parent manifest to the list of context(s)
                local_contexts += [{"id": parent_object.id, "type": parent_object.type}]
                local_contexts += [{"id": parent_object.madoc_id, "type": parent_object.type}]
            if local_contexts:
                # Get or create the context object in the ORM
                c_objs = [Context.objects.get_or_create(**cont) for cont in local_contexts]
                if instance:  # Set the contexts Many to Many relationsip for each context
                    c_objs_set = [c_obj for c_obj, _ in c_objs]
                    instance.contexts.set(c_objs_set)
                    instance.save()
            if iiif3_resource:
                # Flatten the IIIF metadata and descriptive properties into a list of indexables
                indexable_list = flatten_iiif_descriptive(
                    iiif=iiif3_resource, default_language=default_lang, lang_base=LANGBASE
                )
                if indexable_list:
                    # Create the indexables
                    for _indexable in indexable_list:
                        indexable_obj = Indexables(
                            **_indexable, iiif=instance, resource_id=instance.madoc_id
                        )
                        indexable_obj.save()
            return serializer.data, self.get_success_headers(serializer.data)

        d = request.data
        # Cascade
        cascade = d.get("cascade")
        print("Truth(y) value of cascade", bool(cascade))
        # Get the contexts from the "context" key in the outer context of the request payload
        contexts = d.get("contexts")
        # We have a IIIF resource to index
        if d.get("resource"):
            # IIIF 2.x so convert to Presentation API 3
            if d["resource"].get("@context") == "http://iiif.io/api/presentation/2/context.json":
                iiif3 = upgrader.process_resource(d["resource"], top=True)
                iiif3["@context"] = "http://iiif.io/api/presentation/3/context.json"
            else:
                # Just use this as is
                iiif3 = d["resource"]
        else:
            # Else we have nothing to index (although the ID and the contexts will still be created)
            iiif3 = None
        if contexts:
            if iiif3:
                # Add self to context, this is so that for example, if constrain context to a specific object
                # it finds content _on_ that object, and not just on objects _within_ that object.
                if iiif3.get("type"):
                    contexts += [{"id": d["id"], "type": iiif3["type"]}]
        # Create the manifest and return the data and header information
        manifest_data, manifest_headers = ingest_iiif(
            iiif3_resource=iiif3,
            resource_contexts=contexts,
            madoc_id=d["id"],
            madoc_thumbnail=d["thumbnail"],
            child=False,
            parent=None,
        )
        if iiif3.get("items"):
            print(f"Got items, this is where I would cascade: {len(iiif3['items'])} items.")
            print(f"Cascade is {cascade}")
            if cascade:
                for num, item in enumerate(iiif3["items"]):
                    item_data, item_headers = ingest_iiif(
                        iiif3_resource=item,
                        resource_contexts=contexts,
                        madoc_id=":".join([d["id"], item["type"].lower(), str(num)]),
                        madoc_thumbnail=d["thumbnail"],
                        child=True,
                        parent=d["id"],
                    )
                    print(f"Cascaded: {item_headers}")
        return Response(manifest_data, status=status.HTTP_201_CREATED, headers=manifest_headers)


class ContextDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Context.objects.all()
    serializer_class = ContextSerializer
    lookup_field = "slug"


class ContextList(generics.ListCreateAPIView):
    queryset = Context.objects.all()
    serializer_class = ContextSerializer


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


class IndexablesDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Indexables.objects.all()
    serializer_class = IndexablesSerializer


class IndexablesList(generics.ListCreateAPIView):
    serializer_class = IndexablesSerializer
    filter_backends = [DjangoFilterBackend]
    queryset = Indexables.objects.all()
    filterset_fields = [
        "resource_id",
        "content_id",
        "iiif__madoc_id",
        "iiif__contexts__id",
        "type",
        "subtype",
    ]
    pagination_class = MadocPagination


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

    The pre-filters (applied before the fulltext query is run) and the postfilters
    (applied to generate the facet counts) are lists of Q() objects. These may be
    combined together using _reduce_ and the 'or' or 'and' operators to create complex
    boolean queries.
    """
    if req.method == "POST":
        prefilter_kwargs = []
        filter_kwargs = {}
        search_string = req.data.get("fulltext", None)
        language = req.data.get("search_language", None)
        search_type = req.data.get("search_type", "websearch")
        facet_fields = req.data.get("facet_fields", None)
        contexts = req.data.get("contexts", None)
        contexts_all = req.data.get("contexts_all", None)
        madoc_identifiers = req.data.get("madoc_identifiers", None)
        iiif_identifiers = req.data.get("iiif_identifiers", None)
        facet_queries = req.data.get("facets", None)
        facet_on_manifests = req.data.get("facet_on_manifests", global_facet_on_manifests)
        facet_types = req.data.get("facet_types", global_facet_types)
        if contexts:
            prefilter_kwargs.append(Q(**{f"contexts__id__in": contexts}))
        if contexts_all:
            for c in contexts_all:
                prefilter_kwargs.append(Q(**{"contexts__id__iexact": c}))
        if madoc_identifiers:
            prefilter_kwargs.append(Q(**{f"madoc_id__in": madoc_identifiers}))
        if iiif_identifiers:
            prefilter_kwargs.append(Q(**{f"id__in": iiif_identifiers}))
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
            "language_iso639_2",
            "language_iso639_1",
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
                                    if k
                                    in [
                                        "type",
                                        "subtype",
                                        "indexable",
                                        "value",
                                    ]  # These are the fields to query
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
            facet_on_manifests,
            facet_types,
        )
    elif req.method == "GET":
        search_string = req.query_params.get("fulltext", None)
        language = req.query_params.get("search_language", None)
        search_type = req.query_params.get("search_type", "websearch")
        filter_kwargs = {}
        postfilter_kwargs = [{}]
        prefilter_kwargs = []
        for param in req.query_params:
            if param in [
                "type",
                "subtype",
                "language_iso639_2",
                "language_iso639_1",
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
            global_facet_on_manifests,
            global_facet_types,
        )


class Facets(viewsets.ModelViewSet, RetrieveModelMixin):
    """
    Simple read only view to return a list of facet fields
    """

    queryset = IIIFResource.objects.all()
    serializer_class = IIIFSearchSummarySerializer

    def list(self, request, *args, **kwargs):
        """
        Return a simple list of facet fields when the (optional) query is passed in.

        """
        # Call a function to set the prefilter_kwargs based on incoming request
        (prefilter_kwargs, _, _, _, _, _, facet_on_manifests, facet_types) = parse_search(
            req=request
        )
        if prefilter_kwargs:
            setattr(self, "prefilter_kwargs", prefilter_kwargs)
        if facet_on_manifests:
            setattr(self, "facet_on_manifests", facet_on_manifests)
        response = super(Facets, self).list(request, args, kwargs)
        # If we haven't been provided a list of facet fields via a POST
        # just generate the list by querying the unique list of metadata subtypes
        # Make a copy of the query so we aren't running the get_queryset logic every time
        facetable_queryset = self.get_queryset().all().distinct()
        if facet_on_manifests:
            """
            Facet on IIIF objects where:

             1. They are associated (via the reverse relationship on `contexts`) with the queryset, and where
                the associated context is a manifest
             2. The object type is manifest

             In other words, give me all the manifests where they are associated with a manifest context that is
             related to the objects in the queryset. This manifest context should/will be themselves as manifests
             are associated with themselves as context.
            """
            facetable_q = IIIFResource.objects.filter(
                contexts__associated_iiif__madoc_id__in=facetable_queryset,
                contexts__type__iexact="manifest",
                type__iexact="manifest",
            ).distinct()
        else:
            """
            Otherwise, just create the facets on the objects that are in the queryset, rather than their
            containing manifest contexts.
            """
            facetable_q = facetable_queryset
        facet_fields = []
        if not facet_types:
            facet_types = ["metadata"]
        for facet_type in facet_types:
            for t in (
                facetable_q.filter(indexables__type__iexact=facet_type)
                .values("indexables__subtype")
                .distinct()
            ):
                for _, v in t.items():
                    if v and v != "":
                        facet_fields.append((facet_type, v))
        facet_dict = defaultdict(list)
        facet_l = sorted(list(set(facet_fields)))
        for i in facet_l:
            facet_dict[i[0]].append(i[1])
        response.data = facet_dict
        return response

    def get_serializer_context(self):
        """
        Pass the request into the serializer context so it is available
        in the serializer method(s), e.g. the get_hits method used to
        populate each manifest with a list of hits that match the query
        parameters
        """
        context = super(Facets, self).get_serializer_context()
        context.update({"request": self.request})
        return context

    def get_queryset(self):
        """
        Look for

            self.prefilter_kwargs: filters to execute before the fulltext search

        Apply these and return distinct objects
        """
        queryset = IIIFResource.objects.all()
        if hasattr(self, "prefilter_kwargs"):
            # Just check if this thing is all nested Q() objects
            if all([type(k) == Q for k in self.prefilter_kwargs]):
                # This is a chaining operation
                for f in self.prefilter_kwargs:
                    queryset = queryset.filter(*(f,))
        return queryset.distinct()


class Autocomplete(viewsets.ModelViewSet, ListModelMixin):
    queryset = Indexables.objects.all()
    serializer_class = AutocompleteSerializer

    def list(self, request, *args, **kwargs):
        """
        Override the LIST method,
        """
        # Call a function to set the filter_kwargs and postfilter_kwargs based on incoming request
        (
            prefilter_kwargs,
            filter_kwargs,
            postfilter_kwargs,
            _,
            _,
            _,
            facet_on_manifests,
            facet_types,
        ) = parse_search(req=request)
        if request.method == "POST":
            autocomplete_type = request.data.get("autocomplete_type", None)
            autocomplete_subtype = request.data.get("autocomplete_subtype", None)
            autocomplete_query = request.data.get("autocomplete_query", None)
        else:
            autocomplete_type = None
            autocomplete_subtype = None
            autocomplete_query = None
        if autocomplete_type:
            setattr(self, "autocomplete_type", autocomplete_type)
        if autocomplete_subtype:
            setattr(self, "autocomplete_subtype", autocomplete_subtype)
        if autocomplete_query:
            setattr(self, "autocomplete_query", autocomplete_query)
        if prefilter_kwargs:
            setattr(self, "prefilter_kwargs", prefilter_kwargs)
        if filter_kwargs:
            setattr(self, "filter_kwargs", filter_kwargs)
        if postfilter_kwargs:
            setattr(self, "postfilter_kwargs", postfilter_kwargs)
        if facet_on_manifests:
            setattr(self, "facet_on_manifests", facet_on_manifests)
        if facet_types:
            setattr(self, "facet_types", facet_types)
        # response = super(Autocomplete, self).list(request, args, kwargs)
        facetable_queryset = self.get_queryset().all()
        raw_data = (
            facetable_queryset.values("indexable")
            .distinct()
            .annotate(n=models.Count("pk", distinct=True))
            .order_by("-n")[:10]
        )
        return_data = {
            "results": [{"id": x.get("indexable"), "text": x.get("indexable")} for x in raw_data]
        }
        return Response(data=return_data)

    def get_serializer_context(self):
        """
        Pass the request into the serializer context so it is available
        in the serializer method(s), e.g. the get_hits method used to
        populate each manifest with a list of hits that match the query
        parameters
        """
        context = super(Autocomplete, self).get_serializer_context()
        context.update({"request": self.request})
        return context

    def get_queryset(self):
        """
        Look for

            self.prefilter_kwargs: filters to execute before the fulltext search
            self.filter_kwargs: filters associated with the fulltext search
            self.postfilter_kwargs: filters to run after the fulltext search

        Apply these and return distinct objects
        """
        queryset = Indexables.objects.all()
        contexts_queryset = IIIFResource.objects.all()
        if hasattr(self, "prefilter_kwargs"):
            # Just check if this thing is all nested Q() objects
            if all([type(k) == Q for k in self.prefilter_kwargs]):
                # This is a chaining operation
                for f in self.prefilter_kwargs:
                    contexts_queryset = contexts_queryset.filter(*(f,))
        if hasattr(self, "filter_kwargs"):
            contexts_queryset = contexts_queryset.filter(**self.filter_kwargs)
        if hasattr(self, "postfilter_kwargs"):
            # Just check if this thing is nested Q() objects, rather than dicts
            if type(self.postfilter_kwargs[0]) == Q:
                # This is also a chainging operation but the filters being
                # chained might contain "OR"s rather than ANDs
                if hasattr(self, "facet_on_manifests"):
                    if self.facet_on_manifests is True:
                        """
                        Create a list of manifests where the facets apply
                        and then filter the queryset to just those objects where their context
                        is one of those
                        """
                        manifests = IIIFResource.objects.filter(
                            contexts__associated_iiif__madoc_id__in=queryset,
                            contexts__type__iexact="manifest",
                            type__iexact="manifest",
                        ).distinct()
                        for f in self.postfilter_kwargs:
                            manifests = manifests.filter(*(f,))
                        contexts_queryset = contexts_queryset.filter(
                            **{"contexts__id__in": manifests}
                        )
                    else:
                        print("Facet on manifests is False")
                        for f in self.postfilter_kwargs:
                            contexts_queryset = contexts_queryset.filter(*(f,))
                else:
                    print("Can't find facet on manifests in context")
                    for f in self.postfilter_kwargs:
                        contexts_queryset = contexts_queryset.filter(*(f,))
            else:  # GET requests (i.e. without the fancy Q reduction)
                for filter_dict in self.postfilter_kwargs:
                    # This is a chaining operation
                    # Appending each filter one at a time
                    contexts_queryset = contexts_queryset.filter(**filter_dict).values("id")
        print(contexts_queryset)
        queryset = queryset.filter(iiif__contexts__id__in=contexts_queryset)
        if hasattr(self, "autocomplete_type"):
            queryset = queryset.filter(type__iexact=self.autocomplete_type)
        if hasattr(self, "autocomplete_subtype"):
            queryset = queryset.filter(subtype__iexact=self.autocomplete_subtype)
        if hasattr(self, "autocomplete_query"):
            queryset = queryset.filter(indexable__istartswith=self.autocomplete_query)
        return queryset.distinct()


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
        # Call a function to set the filter_kwargs and postfilter_kwargs based on incoming request
        (
            prefilter_kwargs,
            filter_kwargs,
            postfilter_kwargs,
            facet_fields,
            hits_filter_kwargs,
            sort_order,
            facet_on_manifests,
            facet_types,
        ) = parse_search(req=request)
        if facet_fields:
            setattr(self, "facet_fields", facet_fields)
            print("Facet fields are: ", facet_fields)
        if prefilter_kwargs:
            setattr(self, "prefilter_kwargs", prefilter_kwargs)
        if filter_kwargs:
            setattr(self, "filter_kwargs", filter_kwargs)
        if postfilter_kwargs:
            setattr(self, "postfilter_kwargs", postfilter_kwargs)
        if hits_filter_kwargs:
            setattr(self, "hits_filter_kwargs", hits_filter_kwargs)
        if facet_on_manifests:
            print("Facet on manifests", facet_on_manifests)
            setattr(self, "facet_on_manifests", facet_on_manifests)
        if facet_types:
            setattr(self, "facet_types", facet_types)
        response = super(IIIFSearch, self).list(request, args, kwargs)
        facet_summary = defaultdict(dict)
        # If we haven't been provided a list of facet fields via a POST
        # just generate the list by querying the unique list of metadata subtypes
        # Make a copy of the query so we aren't running the get_queryset logic every time
        facetable_queryset = self.get_queryset().all().distinct()
        if facet_on_manifests:
            """
            Facet on IIIF objects where:

             1. They are associated (via the reverse relationship on `contexts`) with the queryset, and where
                the associated context is a manifest
             2. The object type is manifest

             In other words, give me all the manifests where they are associated with a manifest context that is
             related to the objects in the queryset. This manifest context should/will be themselves as manifests
             are associated with themselves as context.
            """
            facetable_q = IIIFResource.objects.filter(
                contexts__associated_iiif__madoc_id__in=facetable_queryset,
                contexts__type__iexact="manifest",
                type__iexact="manifest",
            ).distinct()
        else:
            """
            Otherwise, just create the facets on the objects that are in the queryset, rather than their
            containing manifest contexts.
            """
            facetable_q = facetable_queryset
        if not facet_types:
            facet_types = ["metadata"]
        for facet_type in facet_types:
            facet_fields = []
            facet_field_labels = (
                facetable_q.filter(indexables__type__iexact=facet_type)
                .values("indexables__subtype")
                .distinct()
            )
            for t in facet_field_labels:
                for _, v in t.items():
                    facet_fields.append(v)
            for v in facet_fields:
                facet_summary[facet_type][v] = {
                    x["indexables__indexable"]: x["n"]
                    for x in facetable_q.filter(
                        indexables__type__iexact=facet_type, indexables__subtype__iexact=v
                    )
                    .values("indexables__indexable")
                    .distinct()
                    .annotate(n=models.Count("pk", distinct=True))
                    .order_by("-n")[:10]
                }
        response.data["facets"] = facet_summary
        if sort_order:
            if "rank" in sort_order:
                sort_default = 0
            else:
                sort_default = ""
            if "-" in sort_order:
                response.data["results"] = sorted(
                    response.data["results"],
                    key=lambda k: (k.get(sort_order.replace("-", ""), sort_default),),
                    reverse=True,
                )
            else:
                response.data["results"] = sorted(
                    response.data["results"], key=lambda k: (k.get(sort_order, sort_default),)
                )
        return response

    def get_serializer_context(self):
        """
        Pass the request into the serializer context so it is available
        in the serializer method(s), e.g. the get_hits method used to
        populate each manifest with a list of hits that match the query
        parameters
        """
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
        queryset = IIIFResource.objects.all()
        if hasattr(self, "prefilter_kwargs"):
            # Just check if this thing is all nested Q() objects
            if all([type(k) == Q for k in self.prefilter_kwargs]):
                # This is a chaining operation
                for f in self.prefilter_kwargs:
                    queryset = queryset.filter(*(f,))
        if hasattr(self, "filter_kwargs"):
            queryset = queryset.filter(**self.filter_kwargs)
        if hasattr(self, "postfilter_kwargs"):
            # Just check if this thing is nested Q() objects, rather than dicts
            if type(self.postfilter_kwargs[0]) == Q:
                # This is also a chainging operation but the filters being
                # chained might contain "OR"s rather than ANDs
                if hasattr(self, "facet_on_manifests"):
                    if self.facet_on_manifests is True:
                        """
                        Create a list of manifests where the facets apply
                        and then filter the queryset to just those objects where their context
                        is one of those
                        """
                        manifests = IIIFResource.objects.filter(
                            contexts__associated_iiif__madoc_id__in=queryset,
                            contexts__type__iexact="manifest",
                            type__iexact="manifest",
                        ).distinct()
                        for f in self.postfilter_kwargs:
                            manifests = manifests.filter(*(f,))
                        queryset = queryset.filter(**{"contexts__id__in": manifests})
                    else:
                        print("Facet on manifests is False")
                        for f in self.postfilter_kwargs:
                            queryset = queryset.filter(*(f,))
                else:
                    print("Can't find facet on manifests in context")
                    for f in self.postfilter_kwargs:
                        queryset = queryset.filter(*(f,))
            else:  # GET requests (i.e. without the fancy Q reduction)
                for filter_dict in self.postfilter_kwargs:
                    # This is a chaining operation
                    # Appending each filter one at a time
                    queryset = queryset.filter(**filter_dict)
        return queryset.distinct()


class ModelDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Indexables.objects.all()
    serializer_class = CaptureModelSerializer


class ModelList(generics.ListCreateAPIView):
    """
    List/Create API view for Indexables that are being created/listed
    """

    serializer_class = CaptureModelSerializer
    filter_backends = [DjangoFilterBackend]
    queryset = Indexables.objects.all()
    filterset_fields = [
        "resource_id",
        "content_id",
        "iiif__madoc_id",
        "iiif__contexts__id",
        "type",
        "subtype",
    ]
    pagination_class = MadocPagination

    def create(self, request, *args, **kwargs):
        """
        Override the .create() method on the rest-framework generic ListCreateAPIViewset
        """
        data = request.data
        good_results = []
        bad_results = []
        indexables = []
        if data.get("resource"):
            indexables = gen_indexables(data)
        if indexables:
            for indexable in indexables:
                serializer = self.get_serializer(data=indexable)  # Serialize the data
                serializer.is_valid(raise_exception=True)  # Check it's valid
                self.perform_create(serializer)  # Create the object
                if serializer.errors != {}:
                    bad_results.append(
                        (serializer.data, self.get_success_headers(serializer.data))
                    )
                else:
                    good_results.append(
                        (serializer.data, self.get_success_headers(serializer.data))
                    )
            return_status = status.HTTP_201_CREATED
            if len(good_results) > 0:
                if len(bad_results) > 0:
                    return_status = status.HTTP_206_PARTIAL_CONTENT
                return Response(
                    [res[0] for res in good_results],
                    status=return_status,
                    headers=good_results[-1][1],
                )
            raise ValidationError
        raise ParseError
