import logging

from django.contrib.postgres.search import (
    SearchRank,
    TrigramSimilarity,
    TrigramWordSimilarity,
)
from django.db.models import F
from django.db.models import Max
from django.db.models import OuterRef, Subquery
from django.db.models import Q, Value, FloatField
from rest_framework.filters import BaseFilterBackend

from .models import IIIFResource, Context, Indexables

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
            contexts_queryset = contexts_queryset.filter(
                **request.data["filter_kwargs"]
            )
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
                    contexts_queryset = contexts_queryset.filter(**filter_dict).values(
                        "id"
                    )
        logger.debug(contexts_queryset)
        queryset = queryset.filter(iiif__contexts__id__in=contexts_queryset)
        if request.data.get("autocomplete_type", None):
            queryset = queryset.filter(type__iexact=request.data["autocomplete_type"])
        if request.data.get("autocomplete_subtype", None):
            queryset = queryset.filter(
                subtype__iexact=request.data["autocomplete_subtype"]
            )
        if request.data.get("autocomplete_query", None):
            queryset = queryset.filter(
                indexable__istartswith=request.data["autocomplete_subtype"]
            )
        return queryset.distinct()


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
            queryset = queryset.filter(**request.data.get("filter_kwargs"))
        # Step up to a different level and filter to those things which are part of the context
        # of an object that meets the contains_kwargs filters.
        if request.data.get("contains_kwargs", None):
            # These are filters that are keyed off the context, not the iiif resource
            # filter to contexts that match this set of filters.
            contains_queryset = (
                Context.objects.filter(**request.data.get("contains_kwargs"))
                .distinct()
                .values("id")
            )
            # Filter the list of IIIF objects to those objects whose identifier is in the
            # list of contexts that match the query above.

            queryset = queryset.filter(
                madoc_id__in=[x["id"] for x in contains_queryset]
            )
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
        if hits_filter_kwargs := request.data.get("hits_filter_kwargs"):
            # We have a dictionary of queries to use, so we use that
            search_query = hits_filter_kwargs.get("search_vector", None)
            search_string = hits_filter_kwargs.get("search_string", None)
            search_type = hits_filter_kwargs.get("search_type")
        else:
            search_type = None

        logger.warning(f"Search query {search_query}")
        if search_type == "trigram":
            logger.warning(f"TrigramSimilarity for the ranking {search_string}")
            queryset = queryset.distinct().annotate(
                rank=Max(TrigramSimilarity("indexables__indexable", search_string)),
            )
        elif search_type == "trigram_word":
            logger.warning(f"TrigramWordSimilarity for the ranking {search_string}")
            queryset = queryset.distinct().annotate(
                rank=Max(TrigramWordSimilarity(search_string, "indexables__indexable")),
            )

        elif search_query:
            logger.warning(f"Search query for the ranking {search_query}")
            queryset = queryset.distinct().annotate(
                rank=Max(
                    SearchRank(
                        F("indexables__search_vector"), search_query, cover_density=True
                    ),
                    output_field=FloatField(),
                ),
            )
        else:
            queryset = queryset.distinct().annotate(
                rank=Value(0.0, FloatField()),
            )
        # Some ordering has been passed in from the request parser
        if (
            isinstance(order_key, dict)
            and order_key.get("type")
            and order_key.get("subtype")
        ):
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
                ).order_by(F("sortk").desc(nulls_last=True))
            else:
                queryset = queryset.annotate(
                    sortk=Subquery(
                        Indexables.objects.filter(
                            iiif=OuterRef("pk"),
                            type__iexact=order_key.get("type"),
                            subtype__iexact=order_key.get("subtype"),
                        ).values(val)[:1]
                    )
                ).order_by(F("sortk").asc(nulls_last=True))
            return queryset
        # Otherwise, default to sorting by rank.
        return queryset.distinct().order_by("-rank")
