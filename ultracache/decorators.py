import hashlib
import types
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.utils.decorators import available_attrs
from django.views.generic.base import TemplateResponseMixin

from ultracache import _thread_locals
from ultracache.utils import cache_meta, get_current_site_pk


def cached_get(timeout, *params):
    """Decorator applied specifically to a view's get method"""

    def decorator(view_func):
        @wraps(view_func, assigned=available_attrs(view_func))
        def _wrapped_view(view_or_request, *args, **kwargs):

            # The type of the request gets muddled when using a function based
            # decorator. We must use a function based decorator so it can be
            # used in urls.py.
            request = getattr(view_or_request, "request", view_or_request)

            if not hasattr(_thread_locals, "ultracache_request"):
                setattr(_thread_locals, "ultracache_request", request)

           # If request not GET or HEAD never cache
            if request.method.lower() not in ("get", "head"):
                return view_func(view_or_request, *args, **kwargs)

            # If request contains messages never cache
            l = 0
            try:
                l = len(request._messages)
            except (AttributeError, TypeError):
                pass
            if l:
                return view_func(view_or_request, *args, **kwargs)

            # Compute a cache key
            li = [str(view_or_request.__class__), view_func.__name__]

            # request.get_full_path is implicitly added it no other request
            # path is provided. get_full_path includes the querystring and is
            # the more conservative approach but makes it trivially easy for a
            # request to bust through the cache.
            if not set(params).intersection(set((
                "request.get_full_path()", "request.path", "request.path_info"
            ))):
                li.append(request.get_full_path())

            if "django.contrib.sites" in settings.INSTALLED_APPS:
                li.append(get_current_site_pk(request))

            # Pre-sort kwargs
            keys = list(kwargs.keys())
            keys.sort()
            for key in keys:
                li.append("%s,%s" % (key, kwargs[key]))

            # Extend cache key with custom variables
            for param in params:
                if not isinstance(param, str):
                    param = str(param)
                li.append(eval(param))

            s = ":".join([str(l) for l in li])
            hashed = hashlib.md5(s.encode("utf-8")).hexdigest()
            cache_key = "ucache-get-%s" % hashed
            cached = cache.get(cache_key, None)
            if cached is None:
                # The get view as outermost caller may bluntly set _ultracache
                request._ultracache = []
                response = view_func(view_or_request, *args, **kwargs)
                content = None
                if isinstance(response, TemplateResponse):
                    content = response.render().rendered_content
                elif isinstance(response, HttpResponse):
                    content = response.content
                if content is not None:
                    headers = getattr(response, "_headers", {})
                    cache.set(
                        cache_key,
                        {"content": content, "headers": headers},
                        timeout
                    )
                    cache_meta(request, cache_key)
            else:
                response = HttpResponse(cached["content"])
                # Headers has a non-obvious format
                for k, v in cached["headers"].items():
                    response[v[0]] = v[1]

            return response

        return _wrapped_view
    return decorator


def xultracache(timeout, *params):
    """Decorator applied to a view class. The get method is decorated
    implicitly."""

    def decorator(cls):
        #@wraps(cls, assigned=available_attrs(cls))
        def _wrapped_cls(*args, **kwargs):
            import pdb;pdb.set_trace()
            #klass = cls(*args, **kwargs)
            cls.get = cached_get(cls.get, timeout, *params)
            return cls

        return _wrapped_cls
    return decorator


def ultracache(timeout, *params):
    """Decorator applied to a view class. The get method is decorated
    implicitly."""

    def decorator(cls):
        class WrappedClass(cls):
            def __init__(self, *args, **kwargs):
                super(WrappedClass, self).__init__(*args, **kwargs)

            @cached_get(timeout, *params)
            def get(self, *args, **kwargs):
                return super(WrappedClass, self).get(*args, **kwargs)

        return WrappedClass
    return decorator


class zultracache(object):

    def __init__(self, timeout, *params):
        self.timeout = timeout
        self.params = params

    def __call__(self, cls):
        class Wrapped(cls):
            pass
            #classattr = self.arg
            #def new_method(self, value):
            #    return value * 2
            cls.get = cached_get(cls.get, (self.timeout, self.params))

            #@cached_get(self.timeout, *self.params)
            #def get(*args, **kwargs):
            #    return super().get(*args, **kwargs)

        return Wrapped
