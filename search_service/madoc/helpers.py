import re
import json
import base64
from django.core.exceptions import PermissionDenied
from django.http.request import HttpRequest
from django.conf import settings

def user_with_scope(request, required_scope):

    if not 'madoc.middleware.MadocMiddleware' in settings.MIDDLEWARE:
        return None

    try:
        madoc = request.madoc

        if not madoc:
            raise PermissionDenied()

        user = madoc['user']
        user_scopes = madoc['scope']

        if not user or not user['id']:
            raise PermissionDenied()
        
        # Only need to check scopes if not an admin
        if not 'site.admin' in user_scopes:
            for scope in required_scope:
                if not scope in user_scopes:
                    raise PermissionDenied()

        return madoc

    except AttributeError:
        raise PermissionDenied()

def jwt_from_request(request: HttpRequest):
    auth_header = request.headers.get('Authorization');
    if not auth_header:
        return None

    g = re.match("^Bearer\s+(.*)", auth_header)

    if not g:
        return None

    return g.group(1);

def as_user_from_request(request: HttpRequest):
    site_id_header = request.headers.get('x-madoc-site-id')
    user_id_header = request.headers.get('x-madoc-user-id')
    user_name_header = request.headers.get('x-madoc-user-name')

    asUser = None
    if site_id_header or user_id_header:
        asUser = {
            'user_id': None,
            'site_id': None,
            'user_name': None
        }
        if user_id_header:
            asUser['user_id'] = int(user_id_header)
        if site_id_header:
            asUser['site_id'] = int(site_id_header)
        if user_name_header:
            asUser['user_name'] = user_name_header

    return asUser

def get_token(token):
    (header, payload, sig) = token.split('.')

    payload += '=' * (-len(payload) % 4)
    payload_data = json.loads(base64.urlsafe_b64decode(payload).decode())

    header += '=' * (-len(header) % 4)
    header_data = json.loads(base64.urlsafe_b64decode(header).decode())

    return {
        'token': token,
        'header': header_data,
        'payload': payload_data,
    }

def parse_jwt(token, as_user):

    if not token['payload']: 
        return None

    gateway = token['payload']['iss'] == 'urn:madoc:gateway'
    if 'service' in token['payload']:
        is_service = bool(token['payload']['service'])
    else:
        is_service = False


    if is_service:
        user_id = token['payload']['sub'].split('urn:madoc:service:')[1]
    else:
        user_id = int(token['payload']['sub'].split('urn:madoc:user:')[1])

    user = {
        'id': None,
        'urn': None,
        'service': None,
        'service_id': None,
        'name': None
    }

    site = {
        'id': None,
        'urn': None,
        'name': None,
    }

    if is_service and as_user:
        user['id'] = as_user['user_id']
    else:
        user['id'] = user_id

    if user['id']:
        user['urn'] = 'urn:madoc:user:' + str(user['id'])

    user['service'] = is_service
    if is_service:
        user['service_id'] = user_id;

    if is_service and as_user and as_user['user_name']:
        user['name'] = as_user['user_name']
    else:
        user['name'] = token['payload']['name']

    site['gateway'] = gateway
    if gateway:
        if is_service and as_user and as_user['site_id']:
            site['id'] = as_user['site_id'];
            site['urn'] = "urn:madoc:site:" + str(as_user['site_id']);
        else:
            site['id'] = None
    else:
        site['id'] = int(token['payload']['iss'].split('urn:madoc:site:')[1])
        site['urn'] = token['payload']['iss'];
    
    site['name'] = token['payload']['iss_name']
    
    scope = token['payload']['scope'].split(' ')

    filter(None, scope)

    return {
        'token': token['token'],
        'user': user,
        'site': site,
        'scope': scope,
    }
