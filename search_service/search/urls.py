from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns

from . import views


urlpatterns = [
    path("", views.api_root),
    path("users/", views.UserList.as_view(), name="user-list"),
    path("users/<int:pk>/", views.UserDetail.as_view(), name="user-detail"),
    path("iiif/", views.PresentationAPIResourceList.as_view(), name="presentationapiresource-list"),
    path("iiif/<uuid:pk>/", views.PresentationAPIResourceDetail.as_view(), name="presentationapiresource-detail"),
    path("indexables/", views.IndexablesList.as_view(), name="indexables-list"),
    path("indexables/<int:pk>/", views.IndexablesDetail.as_view(), name="indexables-detail"),
]

urlpatterns = format_suffix_patterns(urlpatterns)
urlpatterns += [path("api-auth/", include("rest_framework.urls"))]
