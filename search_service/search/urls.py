from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework.schemas import get_schema_view

from . import views


urlpatterns = [
    path("api/search/", views.api_root),
    path("api/search/indexables", views.IndexablesList.as_view(), name="indexables-list"),
    path(
        "api/search/indexables/<int:pk>",
        views.IndexablesDetail.as_view(),
        name="indexables-detail",
    ),
    path("api/search/model", views.ModelList.as_view(), name="model-list"),
    path(
        "api/search/model/<int:pk>",
        views.ModelDetail.as_view(),
        name="model-detail",
    ),
    path(
        "api/search/search",
        views.IIIFSearch.as_view({"get": "list", "post": "list"}),
        name="search",
    ),
    path(
        "api/search/autocomplete",
        views.Autocomplete.as_view({"get": "list", "post": "list"}),
        name="autocomplete",
    ),
    path(
        "api/search/facets",
        views.Facets.as_view({"get": "list", "post": "list"}),
        name="facets",
    ),
    path("api/search/iiif", views.IIIFList.as_view(), name="iiifresource-list"),
    path("api/search/iiif/<str:pk>", views.IIIFDetail.as_view(), name="iiifresource-detail"),
    path("api/search/contexts", views.ContextList.as_view(), name="context-list"),
    path("api/search/contexts/<slug:slug>", views.ContextDetail.as_view(), name="context-detail"),
    path(
        "api/search/openapi",
        get_schema_view(
            title="Madoc Search", description="API for searching Madoc resources", version="0.0.1"
        ),
        name="openapi-schema",
    ),
]

urlpatterns = format_suffix_patterns(urlpatterns)
urlpatterns += [path("api-auth/", include("rest_framework.urls"))]
