# Django Imports

import itertools
import logging
from collections import defaultdict
from copy import deepcopy

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import get_language
from django_filters import rest_framework as df_filters
from django_filters.rest_framework import DjangoFilterBackend

# DRF Imports
from rest_framework import generics, filters, status
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError, ParseError
from rest_framework.response import Response
from rest_framework.reverse import reverse

from .filters import IIIFSearchFilter, FacetListFilter, AutoCompleteFilter
from .indexable_utils import gen_indexables

# Local imports
from .langbase import LANGBASE
from .models import Indexables, IIIFResource, Context
from .parsers import IIIFSearchParser
from .prezi_upgrader import Upgrader
from .serializer_utils import flatten_iiif_descriptive, resources_by_type
from .serializers import (
    UserSerializer,
    IndexablesSerializer,
    IIIFSerializer,
    ContextSerializer,
    IIIFSearchSummarySerializer,
    CaptureModelSerializer,
    AutocompleteSerializer,
)
from .madoc_jwt import (
        request_madoc_site_urn, 
        )

# Globals
default_lang = get_language()
upgrader = Upgrader(flags={"default_lang": default_lang})
global_facet_on_manifests = settings.FACET_ON_MANIFESTS_ONLY
global_facet_types = ["metadata"]


logger = logging.getLogger(__name__)


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

    def get_object(self):
        if madoc_site_urn:= request_madoc_site_urn(self.request): 
            logger.debug(f"Got madoc site urn: {madoc_site_urn}")
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            url_id = self.kwargs.get(lookup_url_kwarg)
            self.kwargs[lookup_url_kwarg] = f'{madoc_site_urn}|{url_id}'
        return super().get_object()

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
            "madoc_id": instance.madoc_id, 
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
            first_canvas_json = next(iter(resources_by_type(iiif=iiif3)), None)
            if first_canvas_json:
                data_dict["first_canvas_json"] = first_canvas_json
                data_dict["first_canvas_id"] = first_canvas_json.get("id")
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
                first_canvas_json = next(iter(resources_by_type(iiif=iiif3_resource)), None)
                if first_canvas_json:
                    local_dict["first_canvas_json"] = first_canvas_json
                    local_dict["first_canvas_id"] = first_canvas_json.get("id")
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

        if (overridden := request.parser_context.get("kwargs").get("data_override")) is not None:
            logger.debug(
                "Using a data object passed in from an external view, rather than the request"
            )
            d = overridden
        else:
            d = request.data
        # Cascade
        cascade = d.get("cascade")
        logger.debug("Truth(y) value of cascade", bool(cascade))
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

        if madoc_site_urn:= request_madoc_site_urn(request): 
            logger.debug(f"Got madoc site urn: {madoc_site_urn}")
            madoc_id = f"{madoc_site_urn}|{d['id']}"
        else: 
            madoc_id = d["id"]

        logger.debug(f"Creating with madoc_id: {madoc_id}")
        # Create the manifest and return the data and header information
        manifest_data, manifest_headers = ingest_iiif(
            iiif3_resource=iiif3,
            resource_contexts=contexts,
            madoc_id=madoc_id,
            madoc_thumbnail=d["thumbnail"],
            child=False,
            parent=None,
        )
        if iiif3.get("items"):
            logger.debug(f"Got items, this is where I would cascade: {len(iiif3['items'])} items.")
            logger.debug(f"Cascade is {cascade}")
            if cascade:
                for num, item in enumerate(iiif3["items"]):
                    item_data, item_headers = ingest_iiif(
                        iiif3_resource=item,
                        resource_contexts=contexts,
                        madoc_id=":".join([madoc_id, item["type"].lower(), str(num)]),
                        madoc_thumbnail=d["thumbnail"],
                        child=True,
                        parent=d["id"],
                    )
                    logger.debug(f"Cascaded: {item_headers}")
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
    queryset = Indexables.objects.all()
    filterset_fields = [
        "resource_id",
        "content_id",
        "iiif__madoc_id",
        "iiif__contexts__id",
        "type",
        "subtype",
    ]


class ContextFilterSet(df_filters.FilterSet):
    """
    Currently unused. Test filterset to change the filter field for contexts, e.g. to
    "cont"
    """

    cont = df_filters.filters.CharFilter(field_name="contexts__id", lookup_expr="iexact")

    class Meta:
        model = Context
        fields = ["cont"]


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


class SearchBaseClass(viewsets.ReadOnlyModelViewSet):
    """
    BaseClass for Search Service APIs.
    """

    queryset = IIIFResource.objects.all().distinct()
    serializer_class = IIIFSearchSummarySerializer
    parser_classes = [IIIFSearchParser]


class IIIFSearch(SearchBaseClass):
    """
    Simple read only view for the IIIF data with methods for
    adding hits and generating facets for return in the results

    Uses a custom paginator to fit the Madoc model.
    """

    filter_backends = [IIIFSearchFilter]

    def get_facets(self, request):
        facet_summary = defaultdict(dict)
        # If we haven't been provided a list of facet fields via a POST
        # just generate the list by querying the unique list of metadata subtypes
        # Make a copy of the query so we aren't running the get_queryset logic every time
        facetable_queryset = self.filter_queryset(queryset=self.get_queryset())
        if request.data.get("facet_on_manifests", None):
            """
            Facet on IIIF objects where:

             1. They are associated (via the reverse relationship on `contexts`) with the queryset,
                and where the associated context is a manifest
             2. The object type is manifest

             In other words, give me all the manifests where they are associated with a manifest context
              that is related to the objects in the queryset. This manifest context should/will be
              themselves as manifests are associated with themselves as context.
            """
            facetable_q = self.queryset.filter(
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

        facet_filter_args = [
                models.Q(indexables__type__in=request.data.get("facet_types", ["metadata"])), 
                ]
        if facet_fields:=request.data.get("facet_fields"):
            facet_filter_args.append(
                models.Q(indexables__subtype__in=facet_fields)
                )
        if facet_languages:=request.data.get("facet_languages"):
            facet_language_codes = set(map(lambda x: x.split('-')[0], facet_languages))
            iso639_1_codes = list(filter(lambda x: len(x)==2, facet_language_codes))
            iso639_2_codes = list(filter(lambda x: len(x)==3, facet_language_codes))
            # Always include indexables where no language is specified. This will be cases where there it has neither iso639 field set. 
            facet_language_filter = (models.Q(indexables__language_iso639_1__isnull=True) & models.Q(indexables__language_iso639_2__isnull=True)) 
            if iso639_1_codes: 
                facet_language_filter |= models.Q(indexables__language_iso639_1__in=iso639_1_codes) 
            if iso639_2_codes: 
                facet_language_filter |= models.Q(indexables__language_iso639_2__in=iso639_2_codes)
            facet_filter_args.append(facet_language_filter)

        facet_summary = (
            facetable_q.filter(*facet_filter_args)
            .values("indexables__type", "indexables__subtype", "indexables__indexable")
            .annotate(n=models.Count("pk", distinct=True))
            .order_by("indexables__type", "indexables__subtype", "-n", "indexables__indexable")
        )
        grouped_facets = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
        truncate_to = request.data.get("num_facets", 10)
        truncated_facets = defaultdict(lambda: defaultdict(dict))
        # Turn annotated list of results into a deeply nested dict
        for facet in facet_summary:
            grouped_facets[facet["indexables__type"]][facet["indexables__subtype"]][
                facet["indexables__indexable"]
            ] = facet["n"]
        # Take the deeply nested dict and truncate the leaves of the tree to just N keys.
        for facet_type, facet_subtypes in grouped_facets.items():
            for k, v in facet_subtypes.items():
                truncated_facets[facet_type][k] = dict(itertools.islice(v.items(), truncate_to))
        return truncated_facets

    def list(self, request, *args, **kwargs):
        logger.info('Search list being called')
        resp = super().list(request, *args, **kwargs)
        resp.data.update({"facets": self.get_facets(request=request)})
        return resp


class Facets(SearchBaseClass):
    """
    Simple read only view to return a list of facet fields
    """

    filter_backends = [FacetListFilter]

    def get_facet_list(self, request):
        facet_dict = defaultdict(list)
        # If we haven't been provided a list of facet fields via a POST
        # just generate the list by querying the unique list of metadata subtypes
        # Make a copy of the query so we aren't running the get_queryset logic every time
        facetable_queryset = self.filter_queryset(queryset=self.get_queryset())
        if request.data.get("facet_on_manifests", None):
            """
            Facet on IIIF objects where:

             1. They are associated (via the reverse relationship on `contexts`) with the queryset,
                and where the associated context is a manifest
             2. The object type is manifest

             In other words, give me all the manifests where they are associated with a manifest
             context that is related to the objects in the queryset. This manifest context
             should/will be themselves as manifests are associated with themselves as context.
            """
            facetable_q = IIIFResource.objects.filter(
                contexts__associated_iiif__madoc_id__in=facetable_queryset,
                contexts__type__iexact="manifest",
                type__iexact="manifest",
            ).distinct()
        else:
            """
            Otherwise, just create the facets on the objects that are in the queryset,
            rather than their containing manifest contexts.
            """
            facetable_q = facetable_queryset
        facet_fields = []
        if not request.data.get("facet_types", None):
            request.data["facet_types"] = ["metadata"]
        for facet_type in request.data["facet_types"]:
            for t in (
                facetable_q.filter(indexables__type__iexact=facet_type)
                .values("indexables__subtype")
                .distinct()
            ):
                for _, v in t.items():
                    if v and v != "":
                        facet_fields.append((facet_type, v))
        facet_l = sorted(list(set(facet_fields)))
        for i in facet_l:
            facet_dict[i[0]].append(i[1])
        return facet_dict

    def list(self, request, *args, **kwargs):
        response = super(Facets, self).list(request, args, kwargs)
        response.data = self.get_facet_list(request=request)
        return response


class Autocomplete(SearchBaseClass):
    queryset = Indexables.objects.all()
    serializer_class = AutocompleteSerializer
    filter_backends = [AutoCompleteFilter]

    def list(self, request, *args, **kwargs):
        facetable_queryset = self.filter_queryset(self.get_queryset().all())
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
