from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns

from . import views


urlpatterns = [
    path("", views.api_root),
    path("iiif/", views.IIIFList.as_view(), name="iiifresource-list"),
    path("iiif/<str:pk>/", views.IIIFDetail.as_view(), name="iiifresource-detail"),
    path("indexables/", views.IndexablesList.as_view(), name="indexables-list"),
    path("indexables/<int:pk>/", views.IndexablesDetail.as_view(), name="indexables-detail"),
]

urlpatterns = format_suffix_patterns(urlpatterns)
urlpatterns += [path("api-auth/", include("rest_framework.urls"))]
