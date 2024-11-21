from madoc.helpers import as_user_from_request, jwt_from_request, parse_jwt, get_token
from typing import Optional
from django.contrib import auth
from django.contrib.auth.middleware import MiddlewareMixin
from django.http import HttpResponseForbidden
from django.http.request import HttpRequest


class MadocMiddleware(MiddlewareMixin):

    def process_view(self, request: Optional[HttpRequest], view_func, view_args, view_kwargs):
        if not request:
            return None

        raw_token = jwt_from_request(request)
        if not raw_token:
            request.madoc = None
            return None

        token = get_token(raw_token)
        if token:
            as_user = as_user_from_request(request)
            request.madoc = parse_jwt(token, as_user) 