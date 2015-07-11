# -*- coding: utf-8 -*-

from django.test import TestCase
from django.test.client import Client, RequestFactory
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django import template
from django.conf import settings

from ultracache.tests.models import DummyModel, DummyForeignModel


class DummyProxy(dict):

    def cache(self, path, value):
        self[path] = value

    def is_cached(self, path):
        return path in self

    def purge(self, path):
        if path in self:
            del self[path]

dummy_proxy = DummyProxy()


def dummy_purger(path):
    dummy_proxy.purge(path)


class TemplateTagsTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.request = RequestFactory()
        cls.request.method = 'GET'
        cls.request._path = '/'
        cls.request.get_full_path = lambda: cls.request._path
        cls.client = Client()

        # Add sites
        cls.first_site = Site.objects.create(name='first', domain='first.com')
        cls.second_site = Site.objects.create(name='second', domain='second.com')

    def test_sites(self):
        # Caching on same site
        t = template.Template("{% load ultracache_tags %}\
            {% ultracache 1200 'test_ultracache' %}1{% endultracache %}"
        )
        context = template.Context({'request' : self.request})
        result1 = t.render(context)
        t = template.Template("{% load ultracache_tags %}\
            {% ultracache 1200 'test_ultracache' %}2{% endultracache %}"
        )
        context = template.Context({'request' : self.request})
        result2 = t.render(context)
        self.failUnlessEqual(result1, result2)

        # Caching on different sites
        t = template.Template("{% load ultracache_tags %}\
            {% ultracache 1200 'test_ultracache' %}1{% endultracache %}"
        )
        context = template.Context({'request' : self.request})
        result1 = t.render(context)
        settings.SITE_ID = 2
        Site.objects.clear_cache()
        t = template.Template("{% load ultracache_tags %}\
            {% ultracache 1200 'test_ultracache' %}2{% endultracache %}"
        )
        context = template.Context({'request' : self.request})
        result2 = t.render(context)
        settings.SITE_ID = 2
        Site.objects.clear_cache()
        self.failIfEqual(result1, result2)

    def test_variables(self):
        # Check that undefined variables do not break caching
        t = template.Template("{% load ultracache_tags %}\
            {% ultracache 1200 'test_ultracache_undefined' aaa %}1{% endultracache %}"
        )
        context = template.Context({'request' : self.request})
        result1 = t.render(context)
        t = template.Template("{% load ultracache_tags %}\
            {% ultracache 1200 'test_ultracache_undefined' bbb %}2{% endultracache %}"
        )
        context = template.Context({'request' : self.request})
        result2 = t.render(context)
        self.failUnlessEqual(result1, result2)

        # Check that translation proxies are valid variables
        t = template.Template("{% load ultracache_tags %}\
            {% ultracache 1200 'test_ultracache_xlt' _('aaa') %}1{% endultracache %}"
        )
        context = template.Context({'request' : self.request})
        result1 = t.render(context)
        t = template.Template("{% load ultracache_tags %}\
            {% ultracache 1200 'test_ultracache_xlt' _('aaa') %}2{% endultracache %}"
        )
        context = template.Context({'request' : self.request})
        result2 = t.render(context)
        self.failUnlessEqual(result1, result2)

        # Check that large integer variables do not break caching
        t = template.Template("{% load ultracache_tags %}\
            {% ultracache 1200 'test_ultracache_large' 565417614189797377 %}1{% endultracache %}"
        )
        context = template.Context({'request' : self.request})
        result1 = t.render(context)
        t = template.Template("{% load ultracache_tags %}\
            {% ultracache 1200 'test_ultracache_large' 565417614189797377 %}2{% endultracache %}"
        )
        context = template.Context({'request' : self.request})
        result2 = t.render(context)
        self.failUnlessEqual(result1, result2)

    def test_context_without_request(self):
        t = template.Template("{% load ultracache_tags %}\
            {% ultracache 1200 'test_ultracache_undefined' aaa %}1{% endultracache %}"
        )
        context = template.Context({})
        try:
            t.render(context)
        except:
            self.fail("Code is not handling missing request properly")

    def test_invalidation(self):
        one = DummyModel.objects.create(title='One', code='one')
        two = DummyModel.objects.create(title='Two', code='two')
        three = DummyForeignModel.objects.create(title='Three', points_to=one, code='three')
        t = template.Template("""{% load ultracache_tags ultracache_test_tags %}
            {% ultracache 1200 'test_ultracache_invalidate_outer' %}
                {% ultracache 1200 'test_ultracache_invalidate_one' %}
                    title = {{ one.title }}
                    counter one = {{ counter }}
                {% endultracache %}
                {% ultracache 1200 'test_ultracache_invalidate_two' %}
                    title = {{ two.title }}
                    counter two = {{ counter }}
                {% endultracache %}
                {% ultracache 1200 'test_ultracache_invalidate_three' %}
                    title = {{ three.title }}
                    {{ three.points_to.title }}
                    counter three = {{ counter }}
                {% endultracache %}
                {% ultracache 1200 'test_ultracache_invalidate_render_view' %}
                    <!-- renders one's title but remains unaffected by invalidation -->
                    {% render_view 'aview' %}
                {% endultracache %}
                {% ultracache 1200 'test_ultracache_invalidate_include %}
                    <!-- renders one's title and is affected by invalidation -->
                    {% include "ultracache/include_me.html" %}
                {% endultracache %}
            {% endultracache %}"""
        )
        context = template.Context({
            'request' : self.request,
            'one': one,
            'two': two,
            'three': three,
            'counter': 1
        })
        self.request._path = '/aaa/'
        result = t.render(context)
        dummy_proxy.cache('/aaa/', result)
        self.failUnless('title = One' in result)
        self.failUnless('title = Two' in result)
        self.failUnless('counter one = 1' in result)
        self.failUnless('counter two = 1' in result)
        self.failUnless('counter three = 1' in result)
        self.failUnless('render_view = One' in result)
        self.failUnless('include = One' in result)
        self.failUnless(dummy_proxy.is_cached('/aaa/'))

        # Change object one
        one.title = 'Onxe'
        one.save()
        context = template.Context({
            'request' : self.request,
            'one': one,
            'two': two,
            'three': three,
            'counter': 2
        })
        self.request._path = '/bbb/'
        result = t.render(context)
        self.failUnless('title = Onxe' in result)
        self.failIf('title = One' in result)
        self.failUnless('title = Two' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 1' in result)
        self.failUnless('counter three = 2' in result)
        self.failUnless('render_view = One' in result)
        self.failUnless('include = Onxe' in result)
        self.failIf(dummy_proxy.is_cached('/aaa/'))

        # Change object two
        two.title = 'Twxo'
        two.save()
        context = template.Context({
            'request' : self.request,
            'one': one,
            'two': two,
            'three': three,
            'counter': 3
        })
        self.request._path = '/ccc/'
        result = t.render(context)
        self.failUnless('title = Onxe' in result)
        self.failIf('title = One' in result)
        self.failUnless('title = Twxo' in result)
        self.failIf('title = Two' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 3' in result)
        self.failUnless('counter three = 2' in result)
        self.failUnless('render_view = One' in result)
        self.failUnless('include = Onxe' in result)
        self.failIf(dummy_proxy.is_cached('/bbb/'))

        # Change object three
        three.title = 'Threxe'
        three.save()
        context = template.Context({
            'request' : self.request,
            'one': one,
            'two': two,
            'three': three,
            'counter': 4
        })
        self.request._path = '/ddd/'
        result = t.render(context)
        self.failUnless('title = Onxe' in result)
        self.failIf('title = One' in result)
        self.failUnless('title = Twxo' in result)
        self.failIf('title = Two' in result)
        self.failUnless('title = Threxe' in result)
        self.failIf('title = Three' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 3' in result)
        self.failUnless('counter three = 4' in result)
        self.failUnless('render_view = One' in result)
        self.failUnless('include = Onxe' in result)
        self.failIf(dummy_proxy.is_cached('/ccc/'))