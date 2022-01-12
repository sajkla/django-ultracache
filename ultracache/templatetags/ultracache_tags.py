from django import template
try:
    from django.utils.encoding import force_str
except ImportError:
    from django.utils.encoding import force_text as force_str
try:
    from django.utils.translation import ugettext as _
except ImportError:
    from django.utils.translation import gettext as _
from django.utils.functional import Promise
from django.templatetags.cache import CacheNode
from django.template.base import VariableDoesNotExist
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.conf import settings

from ultracache import _thread_locals
from ultracache.utils import cache_meta, get_current_site_pk


register = template.Library()


class UltraCacheNode(CacheNode):
    """Based on Django's default cache template tag. Add SITE_ID as implicit
    vary on parameter is sites product is installed. Allow unresolvable
    variables. Allow translated strings."""

    def __init__(self, *args):
        # Django 1.7 introduced cache_name. Using different caches makes
        # invalidation difficult. It will be supported in a future version.
        try:
            super(UltraCacheNode, self).__init__(*args, cache_name=None)
        except TypeError:
            super(UltraCacheNode, self).__init__(*args)

    def render(self, context):
        try:
            expire_time = self.expire_time_var.resolve(context)
        except VariableDoesNotExist:
            raise TemplateSyntaxError(
                "ultracache tag got an unknown variable: %r" % self.expire_time_var.var
            )
        try:
            expire_time = int(expire_time)
        except (ValueError, TypeError):
            raise TemplateSyntaxError(
                "ultracache tag got a non-integer timeout value: %r" % expire_time
            )

        request = context["request"]

        # If request not GET or HEAD never cache
        if request.method.lower() not in ("get", "head"):
            return self.nodelist.render(context)

        # Set a list on the request. Django's template rendering is recursive
        # and single threaded so we can use a list to keep track of contained
        # objects.
        if not hasattr(_thread_locals, "ultracache_recorder"):
            setattr(_thread_locals, "ultracache_recorder", [])
            start_index = 0
        else:
            start_index = len(_thread_locals.ultracache_recorder)

        vary_on = []
        if "django.contrib.sites" in settings.INSTALLED_APPS:
            vary_on.append(str(get_current_site_pk(request)))

        for var in self.vary_on:
            try:
                r = var.resolve(context)
            except VariableDoesNotExist:
                pass
            if isinstance(r, Promise):
                r = force_str(r)
            vary_on.append(r)

        cache_key = make_template_fragment_key(self.fragment_name, vary_on)
        value = cache.get(cache_key)
        if value is None:
            value = self.nodelist.render(context)
            cache.set(cache_key, value, expire_time)
            cache_meta(_thread_locals.ultracache_recorder, cache_key, start_index, request=request)
        else:
            # A cached result was found. Set tuples in _ultracache manually so
            # outer template tags are aware of contained objects.
            for tu in cache.get(cache_key + "-objs", []):
                _thread_locals.ultracache_recorder.append(tu)

        return value


@register.tag("ultracache")
def do_ultracache(parser, token):
    """Based on Django's default cache template tag"""
    nodelist = parser.parse(("endultracache",))
    parser.delete_first_token()
    tokens = token.split_contents()
    if len(tokens) < 3:
        raise TemplateSyntaxError(""%r" tag requires at least 2 arguments." % tokens[0])
    return UltraCacheNode(nodelist,
        parser.compile_filter(tokens[1]),
        tokens[2], # fragment_name can"t be a variable.
        [parser.compile_filter(token) for token in tokens[3:]])
