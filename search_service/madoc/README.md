# Madoc middleware

When enabled this will add a "madoc" dictionary to each request object. If a JWT is present it will be parsed (NOT validated) 
and the data extracted.

The resulting dictionary will be something like this:
```python
request.madoc = {
  'token': '...', 
  'user': {
    'id': 1, 
    'urn': 'urn:madoc:user:1', 
    'service': False, 
    'service_id': None, 
    'name': 'admin'
  }, 
  'site': {
    'id': 1, 
    'urn': 'urn:madoc:site:1', 
    'name': 'Default site', 
    'gateway': False
  }, 
  'scope': ['site.admin', 'tasks.admin', 'models.admin']
}
```

You can use either `request.madoc['site']['urn']` or `request.madoc['site']['id']` if you want to apply a 
pre-applied filter on a site. Note, this will not be usable if `request.madoc['gateway']` is `True`.


Additionally a recreation of a Madoc internal function that is used for requiring a JWT + scope has been added.

In a view, you can pass in a request object and a list of required scopes.

```python
from madoc.helpers import user_with_scope

class SomeClass:
  def get_some_route(self, request):
    # Will raise a PermissionDenied
    user_with_scope(request, ["site.view"])

    self.some_view_action()

  def get_some_other_route(self, request):
    # Returns the `request.madoc` dict
    madoc = user_with_scope(request, ["site.admin"])

    # Which can be used for sandboxing.
    site_urn = madoc['site']['urn']

    self.some_admin_action()
```

To enable, you need to install the middleware in `settings.py`

```diff
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
+    "madoc.middleware.MadocMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

You can use `user_with_scope()` if you don't have the middleware installed and it will skip over it. That
may be useful for development or when search is used without JWTs.

Next steps for the library may be to generalise the shape of the above parsed token that could be used
outside of a Madoc context. Also it may be useful to have search specific scopes. (e.g. `search.read`, `search.admin`) and
make the "admin" context configurable (If you have `site.admin` scope, then you have any others).