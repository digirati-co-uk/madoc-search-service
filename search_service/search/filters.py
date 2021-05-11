import logging
from datetime import datetime

import pytz
from django.contrib.postgres.search import SearchRank
from django.db.models import F
from django.db.models import Max
from django.db.models import OuterRef, Subquery
from django.db.models import Q, Value, FloatField, IntegerField, CharField, DateTimeField
from rest_framework.filters import BaseFilterBackend

from .models import IIIFResource, Indexables

utc = pytz.UTC

logger = logging.getLogger(__name__)


class FacetListFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        """
        Return a filtered queryset.
        """

        if request.data.get("prefilter_kwargs", None):
            # Just check if this thing is all nested Q() objects
            if all([type(k) == Q for k in request.data["prefilter_kwargs"]]):
                # This is a chaining operation
                for f in request.data["prefilter_kwargs"]:
                    queryset = queryset.filter(*(f,))
        return queryset


class AutoCompleteFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        contexts_queryset = IIIFResource.objects.all()
        if request.data.get("prefilter_kwargs", None):
            # Just check if this thing is all nested Q() objects
            if all([type(k) == Q for k in request.data.get("prefilter_kwargs")]):
                # This is a chaining operation
                for f in request.data.get("prefilter_kwargs"):
                    contexts_queryset = contexts_queryset.filter(*(f,))
        if request.data.get("filter_kwargs", None):
            contexts_queryset = contexts_queryset.filter(**request.data["filter_kwargs"])
        if request.data.get("postfilter_kwargs", None):
            # Just check if this thing is nested Q() objects, rather than dicts
            if type(request.data["postfilter_kwargs"][0]) == Q:
                # This is also a chainging operation but the filters being
                # chained might contain "OR"s rather than ANDs
                if request.data.get("facet_on_manifests", None):
                    if request.data["facet_on_manifests"] is True:
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
                        for f in request.data["postfilter_kwargs"]:
                            manifests = manifests.filter(*(f,))
                        contexts_queryset = contexts_queryset.filter(
                            **{"contexts__id__in": manifests}
                        )
                    else:
                        logger.debug("Facet on manifests is False")
                        for f in request.data["postfilter_kwargs"]:
                            contexts_queryset = contexts_queryset.filter(*(f,))
                else:
                    logger.debug("Can't find facet on manifests in context")
                    for f in request.data["postfilter_kwargs"]:
                        contexts_queryset = contexts_queryset.filter(*(f,))
            else:  # GET requests (i.e. without the fancy Q reduction)
                for filter_dict in request.data["postfilter_kwargs"]:
                    # This is a chaining operation
                    # Appending each filter one at a time
                    contexts_queryset = contexts_queryset.filter(**filter_dict).values("id")
        logger.debug(contexts_queryset)
        queryset = queryset.filter(iiif__contexts__id__in=contexts_queryset)
        if request.data.get("autocomplete_type", None):
            queryset = queryset.filter(type__iexact=request.data["autocomplete_type"])
        if request.data.get("autocomplete_subtype", None):
            queryset = queryset.filter(subtype__iexact=request.data["autocomplete_subtype"])
        if request.data.get("autocomplete_query", None):
            queryset = queryset.filter(indexable__istartswith=request.data["autocomplete_subtype"])
        return queryset.distinct()


def get_sort_default(order_key):
    """
    Unused function (for now), as the sorting is based on rank, if no
    order_key is provided.
    """
    if value_for_sort := order_key.get("value_for_sort"):
        if value_for_sort.startswith("indexable_int"):
            return 0, IntegerField()
        elif value_for_sort.startswith("indexable_float"):
            return 0.0, FloatField()
        elif value_for_sort.startswith("indexable_date"):
            return datetime.min.replace(tzinfo=utc), DateTimeField()
        else:
            return "", CharField()

    if order_key.get("type") and order_key.get("subtype"):
        return "", CharField()

    return 0.0, FloatField()


class IIIFSearchFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        """
        Return a filtered queryset.
        """
        order_key = request.data.get("sort_order", None)
        if request.data.get("prefilter_kwargs", None):
            # Just check if this thing is all nested Q() objects
            if all([type(k) == Q for k in request.data.get("prefilter_kwargs")]):
                # This is a chaining operation
                for f in request.data.get("prefilter_kwargs"):
                    queryset = queryset.filter(*(f,))
        if request.data.get("filter_kwargs", None):
            logger.info("Got filter kwargs")
            queryset = queryset.filter(**request.data.get("filter_kwargs"))
        if request.data.get("postfilter_kwargs", None):
            # Just check if this thing is nested Q() objects, rather than dicts
            if type(request.data.get("postfilter_kwargs")[0]) == Q:
                # This is also a chainging operation but the filters being
                # chained might contain "OR"s rather than ANDs
                if request.data.get("facet_on_manifests", None):
                    if request.data.get("facet_on_manifests") is True:
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
                        for f in request.data.get("postfilter_kwargs"):
                            manifests = manifests.filter(*(f,))
                        queryset = queryset.filter(**{"contexts__id__in": manifests})
                    else:
                        logger.debug("Facet on manifests is False")
                        for f in request.data.get("postfilter_kwargs"):
                            queryset = queryset.filter(*(f,))
                else:
                    logger.debug("Can't find facet on manifests in context")
                    for f in request.data.get("postfilter_kwargs"):
                        queryset = queryset.filter(*(f,))
            else:  # GET requests (i.e. without the fancy Q reduction)
                for filter_dict in request.data.get("postfilter_kwargs"):
                    # This is a chaining operation
                    # Appending each filter one at a time
                    queryset = queryset.filter(**filter_dict)
        search_query = None
        if request.data.get("hits_filter_kwargs"):
            # We have a dictionary of queries to use, so we use that
            search_query = request.data["hits_filter_kwargs"].get("search_vector", None)
        logger.warning(f"Search query {search_query}")
        if search_query:
            logger.debug(f"Search query for the ranking {search_query}")
            queryset = queryset.distinct().annotate(
                rank=Max(
                    SearchRank(F("indexables__search_vector"), search_query, cover_density=True),
                    output_field=FloatField(),
                ),
            )
        else:
            queryset = queryset.distinct().annotate(
                rank=Value(0.0, FloatField()),
            )
        if isinstance(order_key, dict) and order_key.get("type") and order_key.get("subtype"):
            val = order_key.get("value_for_sort", "indexable")
            if order_key.get("direction") == "descending":
                queryset = queryset.annotate(
                    sortk=Subquery(
                        Indexables.objects.filter(
                            iiif=OuterRef("pk"),
                            type__iexact=order_key.get("type"),
                            subtype__iexact=order_key.get("subtype"),
                        ).values(val)[:1]
                    )
                ).order_by("-sortk")
            else:
                queryset = queryset.annotate(
                    sortk=Subquery(
                        Indexables.objects.filter(
                            iiif=OuterRef("pk"),
                            type__iexact=order_key.get("type"),
                            subtype__iexact=order_key.get("subtype"),
                        ).values(val)[:1]
                    )
                ).order_by("sortk")
            return queryset
        return queryset.order_by("-rank")
