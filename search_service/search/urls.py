from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework.schemas import get_schema_view
from rest_framework import routers

from .views import (
        api_root, 
        IndexablesList, 
        IndexablesDetail, 
        ModelList, 
        ModelDetail, 
        IIIFSearch, 
        Autocomplete, 
        Facets, 
        IIIFList, 
        IIIFDetail, 
        ContextList, 
        ContextDetail,
        # IIIFResourceViewset
        )


router = routers.DefaultRouter(trailing_slash=False)


# router.register("iiif", IIIFResourceViewset)

urlpatterns = [
    path("", api_root),
    path("indexables", IndexablesList.as_view(), name="iiif_search.api.indexables_list"),
    path("indexables/<int:pk>", IndexablesDetail.as_view(), name="iiif_search.api.indexables_detail"),
    path("model", ModelList.as_view(), name="iiif_search.api.model_list"),
    path("model/<int:pk>", ModelDetail.as_view(), name="iiif_search.api.model_detail"),
    path("search", IIIFSearch.as_view({"get": "list", "post": "list"}), name="iiif_search.api.search"),
    path("autocomplete", Autocomplete.as_view({"get": "list", "post": "list"}), name="iiif_search.api.autocomplete"),
    path("facets", Facets.as_view({"get": "list", "post": "list"}), name="iiif_search.api.facets"),
    path("iiif", IIIFList.as_view(), name="iiif_search.api.iiifresource_list"),
    path("iiif/<str:pk>", IIIFDetail.as_view(), name="iiif_search.api.iiifresource_detail"),
    path("contexts", ContextList.as_view(), name="iiif_search.api.context_list"),
    path("contexts/<slug:slug>", ContextDetail.as_view(), name="iiif_search.api.context_detail"),
    path("openapi", get_schema_view(title="IIIF Search", description="IIIF Search API", version="0.0.1"), name="iiif_search.api.openapi_schema")
]

urlpatterns = format_suffix_patterns(urlpatterns)
urlpatterns += [path("api-auth/", include("rest_framework.urls"))]
