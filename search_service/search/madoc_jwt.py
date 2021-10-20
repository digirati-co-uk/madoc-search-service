# Stdlib imports
import json
import logging
import base64

def jwt_payload_from_request(request): 
    if jwt:=request.headers.get('BEARER'): 
        payload = jwt.split('.')[1]
        decoded_payload = base64.b64decode(payload.encode('utf-8') + b'==')
        return json.loads(decoded_payload)
    else: 
        return None

def get_header_madoc_site_urn(request): 
    if site_id:=request.headers.get('x-madoc-site-id'): 
        return f'urn:madoc:site:{site_id}'
    else: 
        return None

def request_madoc_site_urn(request): 
    if jwt_payload:= jwt_payload_from_request(request): 
        if jwt_payload.get('service') == True: 
            return get_header_madoc_site_urn(request)
        else: 
            return jwt_payload.get('iss')
    else: 
        return None


