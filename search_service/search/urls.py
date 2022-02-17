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
    path("api/search/", api_root),
    path("api/search/indexables", IndexablesList.as_view(), name="search.api.indexables_list"),
    path("api/search/indexables/<int:pk>", IndexablesDetail.as_view(), name="search.api.indexables_detail"),
    path("api/search/model", ModelList.as_view(), name="search.api.model_list"),
    path("api/search/model/<int:pk>", ModelDetail.as_view(), name="search.api.model_detail"),
    path("api/search/search", IIIFSearch.as_view({"get": "list", "post": "list"}), name="search.api.search"),
    path("api/search/autocomplete", Autocomplete.as_view({"get": "list", "post": "list"}), name="search.api.autocomplete"),
    path("api/search/facets", Facets.as_view({"get": "list", "post": "list"}), name="search.api.facets"),
    path("api/search/iiif", IIIFList.as_view(), name="search.api.iiifresource_list"),
    path("api/search/iiif/<str:pk>", IIIFDetail.as_view(), name="search.api.iiifresource_detail"),
    path("api/search/contexts", ContextList.as_view(), name="search.api.context_list"),
    path("api/search/contexts/<slug:slug>", ContextDetail.as_view(), name="search.api.context_detail"),
    path("api/search/openapi", get_schema_view(title="IIIF Search", description="IIIF Search API", version="0.0.1"), name="search.api.openapi_schema")
]

urlpatterns = format_suffix_patterns(urlpatterns)
urlpatterns += [path("api/search/api-auth/", include("rest_framework.urls"))]
