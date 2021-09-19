import re
import json
import base64
from typing import List, Optional
from django.core.exceptions import PermissionDenied
from django.http.request import HttpRequest
from django.conf import settings


class AsUser():
    def __init__(self):
        self.user_id: Optional[int] = None
        self.site_id: Optional[int] = None
        self.user_name: Optional[str] = None

class MadocUser():
    def __init__(self):
        self.id: Optional[int] = None
        self.urn: Optional[str] = None
        self.service = False
        self.service_id: Optional[str] = None
        self.name: Optional[str] = None

class MadocSite():
    def __init__(self):
        self.gateway = False
        self.id: Optional[int] = None
        self.urn: Optional[str] = None
        self.name: Optional[str] = None

class MadocContext():
    def __init__(self, token: str, user: MadocUser, site: MadocSite, scope: List[str] ):
        self.token = token
        self.user = user
        self.site = site
        self.scope = scope


"""
Enforces JWT in request contains the provided scopes, or a global scope (default: site.admin) 
If the request does not have the scope, a PermissionDenied exception will be raised

:param request: Django HTTPRequest, usually passed into the view.
:param required_scope: list of scopes that is required to continue.
:param admin_scope: override the admin scope
"""
def user_with_scope(request: HttpRequest, required_scope: List[str], admin_scope = "site.admin"):

    if not "madoc.middleware.MadocMiddleware" in settings.MIDDLEWARE:
        return None

    try:
        madoc: MadocContext = request.madoc

        if not madoc:
            raise PermissionDenied()

        user = madoc.user
        user_scopes = madoc.scope

        if not user or not user.id:
            raise PermissionDenied()
        
        # Only need to check scopes if not an admin
        if not admin_scope in user_scopes:
            for scope in required_scope:
                if not scope in user_scopes:
                    raise PermissionDenied()

        return madoc

    except AttributeError:
        raise PermissionDenied()


"""
Given an HTTPRequest this will extract the JWT from the bearer token

:param request: Django HTTPRequest, usually passed into the view.
"""
def jwt_from_request(request: HttpRequest):
    auth_header = request.headers.get("Authorization");
    if not auth_header:
        return None

    g = re.match("^Bearer\s+(.*)", auth_header)

    if not g:
        return None

    return g.group(1);


"""
Given an HTTPRequest this will extract madoc header overrides. These are used when a 
service makes a request on behalf of another user with their token.

:param request: Django HTTPRequest, usually passed into the view.
"""
def as_user_from_request(request: HttpRequest):
    site_id_header = request.headers.get("x-madoc-site-id")
    user_id_header = request.headers.get("x-madoc-user-id")
    user_name_header = request.headers.get("x-madoc-user-name")

    asUser = None
    if site_id_header or user_id_header:
        asUser = AsUser()
        if user_id_header:
            asUser.user_id = int(user_id_header)
        if site_id_header:
            asUser.site_id = int(site_id_header)
        if user_name_header:
            asUser.user_name = user_name_header

    return asUser

"""
Given a JWT from the Bearer token, this will parse (but not verify) the token
and return the original token, the payload and the header JSON.

:param request: Django HTTPRequest, usually passed into the view.
"""
def get_token(token):
    (header, payload, sig) = token.split(".")

    payload += "=" * (-len(payload) % 4)
    payload_data = json.loads(base64.urlsafe_b64decode(payload).decode())

    header += "=" * (-len(header) % 4)
    header_data = json.loads(base64.urlsafe_b64decode(header).decode())

    return {
        "token": token,
        "header": header_data,
        "payload": payload_data,
    }


"""
Uses the output of get_token() to build up a cleaned up Madoc context. The returned
context can be used to determine the user and site the request originated from.

:param token: Token response, output of get_token()
:param as_user: Optional user/site overrides for the token
"""
def parse_jwt(token, as_user: AsUser):

    if not token["payload"]: 
        return None

    gateway = token["payload"]["iss"] == "urn:madoc:gateway"
    if "service" in token["payload"]:
        is_service = bool(token["payload"]["service"])
    else:
        is_service = False


    if is_service:
        user_id = token["payload"]["sub"].split("urn:madoc:service:")[1]
    else:
        user_id = int(token["payload"]["sub"].split("urn:madoc:user:")[1])

    user = MadocUser()
    site = MadocSite()

    if is_service and as_user:
        user.id = as_user.user_id
    else:
        user.id = user_id

    if user.id:
        user.urn = "urn:madoc:user:" + str(user.id)

    user.service = is_service
    if is_service:
        user.service_id = user_id;

    if is_service and as_user and as_user.user_name:
        user.name = as_user.user_name
    else:
        user.name = token["payload"]["name"]

    site.gateway = gateway
    if gateway:
        if is_service and as_user and as_user.site_id:
            site.id = as_user.site_id
            site.urn = "urn:madoc:site:" + str(as_user.site_id)
        else:
            site.id = None
    else:
        site.id = int(token["payload"]["iss"].split("urn:madoc:site:")[1])
        site.urn = token["payload"]["iss"];
    
    site.name = token["payload"]["iss_name"]
    
    scope = token["payload"]["scope"].split(" ")

    filter(None, scope)

    return MadocContext(token["token"], user, site, scope)
