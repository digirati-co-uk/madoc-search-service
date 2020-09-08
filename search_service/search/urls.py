from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns

from . import views


urlpatterns = [
    path("", views.api_root),
    path("users/", views.UserList.as_view(), name="user-list"),
    path("users/<int:pk>/", views.UserDetail.as_view(), name="user-detail"),
    path("context/", views.MadocContextList.as_view(), name="madoccontext-list"),
    path("context/<uuid:pk>/", views.MadocContextDetail.as_view(), name="madoccontext-detail"),
    path("iiif/", views.PresentationAPIResourceList.as_view(), name="presentationapiresource-list"),
    path("iiif/<uuid:pk>/", views.PresentationAPIResourceDetail.as_view(), name="presentationapiresource-detail")
]

urlpatterns = format_suffix_patterns(urlpatterns)
urlpatterns += [path("api-auth/", include("rest_framework.urls"))]
