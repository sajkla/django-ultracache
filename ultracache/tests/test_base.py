## -*- coding: utf-8 -*-

from django import template
from django.conf import settings
from django.core.cache import cache
from django.http.cookie import SimpleCookie
from django.test import TestCase
from django.test.client import Client, RequestFactory
from django.test.utils import override_settings
from django.urls import reverse

from ultracache.tests.models import DummyModel, DummyForeignModel, \
    DummyOtherModel
from ultracache.tests import views
from ultracache.tests.utils import dummy_proxy


class TemplateTagsTestCase(TestCase):
    if "django.contrib.sites" in settings.INSTALLED_APPS:
        fixtures = ["sites.json"]

    @classmethod
    def setUpClass(cls):
        super(TemplateTagsTestCase, cls).setUpClass()
        cls.factory = RequestFactory()
        cls.request = cls.factory.get('/')
        cache.clear()
        dummy_proxy.clear()

    if "django.contrib.sites" in settings.INSTALLED_APPS:
        def test_sites(self):
            from django.contrib.sites.models import Site

            first_site = Site.objects.all().first()
            second_site = Site.objects.all().last()

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
            with override_settings(SITE_ID=second_site.id):
                t = template.Template("{%% load ultracache_tags %%}\
                    {%% ultracache 1200 'test_ultracache' %%}%s{%% endultracache %%}" % second_site.id
                )
                context = template.Context({'request' : self.request})
                result2 = t.render(context)
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
            {% ultracache 1200 'test_ultracache_large' 565417614189797377 %}abcde{% endultracache %}"
        )
        context = template.Context({'request' : self.request})
        result1 = t.render(context)
        t = template.Template("{% load ultracache_tags %}\
            {% ultracache 1200 'test_ultracache_large' 565417614189797377 %}abcde{% endultracache %}"
        )
        context = template.Context({'request' : self.request})
        result2 = t.render(context)
        self.failUnlessEqual(result1, result2)

    def test_context_without_request(self):
        t = template.Template("{% load ultracache_tags %}\
            {% ultracache 1200 'test_ultracache_undefined' aaa %}abcde{% endultracache %}"
        )
        context = template.Context()
        self.assertRaises(KeyError, t.render, context)

    def test_invalidation(self):
        """Directly render template
        """
        one = DummyModel.objects.create(title='One', code='one')
        two = DummyModel.objects.create(title='Two', code='two')
        three = DummyForeignModel.objects.create(title='Three', points_to=one, code='three')
        four = DummyOtherModel.objects.create(title='Four', code='four')
        # The counter is used to track the iteration that a cached block was
        # last rendered.
        t = template.Template("""{% load ultracache_tags ultracache_test_tags %}
            {% ultracache 1200 'test_ultracache_invalidate_outer' %}
                    counter outer = {{ counter }}
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
                    {% render_view 'render-view' %}
                {% endultracache %}
                {% ultracache 1200 'test_ultracache_invalidate_include %}
                    {% include "ultracache/include_me.html" %}
                {% endultracache %}
            {% endultracache %}"""
        )

        # Initial render
        request = self.factory.get('/aaa/')
        context = template.Context({
            'request' : request,
            'one': one,
            'two': two,
            'three': three,
            'counter': 1
        })
        result = t.render(context)
        dummy_proxy.cache(request, result)
        self.failUnless('title = One' in result)
        self.failUnless('title = Two' in result)
        self.failUnless('counter outer = 1' in result)
        self.failUnless('counter one = 1' in result)
        self.failUnless('counter two = 1' in result)
        self.failUnless('counter three = 1' in result)
        self.failUnless('render_view = One' in result)
        self.failUnless('include = One' in result)
        self.failUnless(dummy_proxy.is_cached('/aaa/'))

        # Change object one
        one.title = 'Onxe'
        one.save()
        request = self.factory.get('/bbb/')
        context = template.Context({
            'request' : request,
            'one': one,
            'two': two,
            'three': three,
            'counter': 2
        })
        result = t.render(context)
        dummy_proxy.cache(request, result)
        self.failUnless('title = Onxe' in result)
        self.failIf('title = One' in result)
        self.failUnless('title = Two' in result)
        self.failUnless('counter outer = 2' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 1' in result)
        self.failUnless('counter three = 2' in result)
        self.failUnless('render_view = Onxe' in result)
        self.failUnless('include = Onxe' in result)
        self.failIf(dummy_proxy.is_cached('/aaa/'))

        # Change object two
        two.title = 'Twxo'
        two.save()
        request = self.factory.get('/ccc/')
        context = template.Context({
            'request' : request,
            'one': one,
            'two': two,
            'three': three,
            'counter': 3
        })
        result = t.render(context)
        dummy_proxy.cache(request, result)
        self.failUnless('title = Onxe' in result)
        self.failIf('title = One' in result)
        self.failUnless('title = Twxo' in result)
        self.failIf('title = Two' in result)
        self.failUnless('counter outer = 3' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 3' in result)
        self.failUnless('counter three = 2' in result)
        self.failUnless('render_view = Onxe' in result)
        self.failUnless('include = Onxe' in result)
        self.failIf(dummy_proxy.is_cached('/bbb/'))

        # Change object three
        three.title = 'Threxe'
        three.save()
        request = self.factory.get('/ddd/')
        context = template.Context({
            'request' : request,
            'one': one,
            'two': two,
            'three': three,
            'counter': 4
        })
        result = t.render(context)
        dummy_proxy.cache(request, result)
        self.failUnless('title = Onxe' in result)
        self.failIf('title = One' in result)
        self.failUnless('title = Twxo' in result)
        self.failIf('title = Two' in result)
        self.failUnless('title = Threxe' in result)
        self.failIf('title = Three' in result)
        self.failUnless('counter outer = 4' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 3' in result)
        self.failUnless('counter three = 4' in result)
        self.failUnless('render_view = Onxe' in result)
        self.failUnless('include = Onxe' in result)
        self.failIf(dummy_proxy.is_cached('/ccc/'))

        # Add a DummyOtherModel object five
        five = DummyOtherModel.objects.create(title='Five', code='five')
        request = self.factory.get('/eee/')
        context = template.Context({
            'request' : request,
            'one': one,
            'two': two,
            'three': three,
            'counter': 5
        })
        result = t.render(context)
        dummy_proxy.cache(request, result)
        # RenderView is only view aware of DummyOtherModel. That means
        # test_ultracache_invalidate_outer and
        # test_ultracache_invalidate_render_view are expired.
        self.failUnless('render_view = Five' in result)
        self.failUnless('counter outer = 5' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 3' in result)
        self.failUnless('counter three = 4' in result)
        self.failIf(dummy_proxy.is_cached('/ddd/'))

        # Delete object two
        two.delete()
        request = self.factory.get('/fff/')
        context = template.Context({
            'request' : request,
            'one': one,
            'two': None,
            'three': three,
            'counter': 6
        })
        result = t.render(context)
        dummy_proxy.cache(request, result)
        self.failUnless('title = Onxe' in result)
        self.failIf('title = Twxo' in result)
        self.failIf('title = Two' in result)
        self.failUnless('counter outer = 6' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 6' in result)
        self.failUnless('counter three = 4' in result)
        self.failIf(dummy_proxy.is_cached('/eee/'))


class DecoratorTestCase(TestCase):
    if "django.contrib.sites" in settings.INSTALLED_APPS:
        fixtures = ["sites.json"]

    def setUp(self):
        super(DecoratorTestCase, self).setUp()
        cache.clear()
        dummy_proxy.clear()

    def test_method(self):
        """Render template through a view with get method decorated with
        cached_get."""
        one = DummyModel.objects.create(title='One', code='one')
        two = DummyModel.objects.create(title='Two', code='two')
        three = DummyForeignModel.objects.create(title='Three', points_to=one, code='three')
        four = DummyModel.objects.create(title='Four', code='four')
        five = DummyModel.objects.create(title='Five', code='five')
        url = reverse('method-cached-view')

        # Initial render
        cache.set("counter", 1)
        response = self.client.get(url)
        result = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.failUnless('title = One' in result)
        self.failUnless('title = Two' in result)
        self.failUnless('title = Three' in result)
        self.failUnless('render_view = One' in result)
        self.failUnless('include = One' in result)
        self.failUnless('counter one = 1' in result)
        self.failUnless('counter two = 1' in result)
        self.failUnless('counter three = 1' in result)
        self.failUnless('counter four = 1' in result)
        self.failUnless('title = Four' in result)

        # Change object one
        cache.set("counter", 2)
        one.title = 'Onxe'
        one.save()
        response = self.client.get(url)
        result = response.content.decode("utf-8")
        self.failUnless('title = Onxe' in result)
        self.failIf('title = One' in result)
        self.failUnless('title = Two' in result)
        self.failUnless('title = Three' in result)
        self.failUnless('render_view = Onxe' in result)
        self.failUnless('include = Onxe' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 1' in result)
        self.failUnless('counter three = 2' in result)
        self.failUnless('counter four = 2' in result)
        self.failUnless('title = Four' in result)

        # Change object two
        cache.set("counter", 3)
        two.title = 'Twxo'
        two.save()
        response = self.client.get(url)
        result = response.content.decode("utf-8")
        self.failUnless('title = Onxe' in result)
        self.failIf('title = One' in result)
        self.failUnless('title = Twxo' in result)
        self.failIf('title = Two' in result)
        self.failUnless('title = Three' in result)
        self.failUnless('render_view = Onxe' in result)
        self.failUnless('include = Onxe' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 3' in result)
        self.failUnless('counter three = 2' in result)
        self.failUnless('counter four = 3' in result)
        self.failUnless('title = Four' in result)

        # Change object three
        cache.set("counter", 4)
        three.title = 'Threxe'
        three.save()
        response = self.client.get(url)
        result = response.content.decode("utf-8")
        self.failUnless('title = Onxe' in result)
        self.failIf('title = One' in result)
        self.failUnless('title = Twxo' in result)
        self.failIf('title = Two' in result)
        self.failUnless('title = Threxe' in result)
        self.failIf('title = Three' in result)
        self.failUnless('render_view = Onxe' in result)
        self.failUnless('include = Onxe' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 3' in result)
        self.failUnless('counter three = 4' in result)
        self.failUnless('counter four = 4' in result)
        self.failUnless('title = Four' in result)

        # Change object four
        cache.set("counter", 5)
        four.title = 'Fouxr'
        four.save()
        response = self.client.get(url)
        result = response.content.decode("utf-8")
        self.failUnless('title = Onxe' in result)
        self.failIf('title = One' in result)
        self.failUnless('title = Twxo' in result)
        self.failIf('title = Two' in result)
        self.failUnless('title = Threxe' in result)
        self.failIf('title = Three' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 3' in result)
        self.failUnless('counter three = 4' in result)
        self.failUnless('counter four = 5' in result)
        self.failUnless('render_view = Onxe' in result)
        self.failUnless('include = Onxe' in result)
        self.failUnless('title = Fouxr' in result)
        self.failIf('title = Four' in result)

        # Change object five. This object is never accessed in the template,
        # only get_context_data of CachedView. "counter four" and "counter
        # five" are under cached_get and not in any ultracache tag, and are
        # thus the only counters incremented.
        cache.set("counter", 6)
        five.title = 'Fivxe'
        five.save()
        response = self.client.get(url)
        result = response.content.decode("utf-8")
        self.failUnless('title = Onxe' in result)
        self.failIf('title = One' in result)
        self.failUnless('title = Twxo' in result)
        self.failIf('title = Two' in result)
        self.failUnless('title = Threxe' in result)
        self.failIf('title = Three' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 3' in result)
        self.failUnless('counter three = 4' in result)
        self.failUnless('counter four = 6' in result)
        self.failUnless('counter five = 6' in result)
        self.failUnless('render_view = Onxe' in result)
        self.failUnless('include = Onxe' in result)
        self.failUnless('title = Fouxr' in result)
        self.failIf('title = Four' in result)

    def test_class(self):
        """Render template through a view decorated with ultracache
        """
        one = DummyModel.objects.create(title='One', code='one')
        two = DummyModel.objects.create(title='Two', code='two')
        three = DummyForeignModel.objects.create(title='Three', points_to=one, code='three')
        four = DummyModel.objects.create(title='Four', code='four')
        five = DummyModel.objects.create(title='Five', code='five')
        url = reverse('class-cached-view')

        # Initial render
        cache.set("counter", 1)
        response = self.client.get(url)
        result = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.failUnless('title = One' in result)
        self.failUnless('title = Two' in result)
        self.failUnless('title = Three' in result)
        self.failUnless('render_view = One' in result)
        self.failUnless('include = One' in result)
        self.failUnless('counter one = 1' in result)
        self.failUnless('counter two = 1' in result)
        self.failUnless('counter three = 1' in result)
        self.failUnless('counter four = 1' in result)
        self.failUnless('title = Four' in result)

        # Change object one
        cache.set("counter", 2)
        one.title = 'Onxe'
        one.save()
        response = self.client.get(url)
        result = response.content.decode("utf-8")
        self.failUnless('title = Onxe' in result)
        self.failIf('title = One' in result)
        self.failUnless('title = Two' in result)
        self.failUnless('title = Three' in result)
        self.failUnless('render_view = Onxe' in result)
        self.failUnless('include = Onxe' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 1' in result)
        self.failUnless('counter three = 2' in result)
        self.failUnless('counter four = 2' in result)
        self.failUnless('title = Four' in result)

        # Change object two
        cache.set("counter", 3)
        two.title = 'Twxo'
        two.save()
        response = self.client.get(url)
        result = response.content.decode("utf-8")
        self.failUnless('title = Onxe' in result)
        self.failIf('title = One' in result)
        self.failUnless('title = Twxo' in result)
        self.failIf('title = Two' in result)
        self.failUnless('title = Three' in result)
        self.failUnless('render_view = Onxe' in result)
        self.failUnless('include = Onxe' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 3' in result)
        self.failUnless('counter three = 2' in result)
        self.failUnless('counter four = 3' in result)
        self.failUnless('title = Four' in result)

        # Change object three
        cache.set("counter", 4)
        three.title = 'Threxe'
        three.save()
        response = self.client.get(url)
        result = response.content.decode("utf-8")
        self.failUnless('title = Onxe' in result)
        self.failIf('title = One' in result)
        self.failUnless('title = Twxo' in result)
        self.failIf('title = Two' in result)
        self.failUnless('title = Threxe' in result)
        self.failIf('title = Three' in result)
        self.failUnless('render_view = Onxe' in result)
        self.failUnless('include = Onxe' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 3' in result)
        self.failUnless('counter three = 4' in result)
        self.failUnless('counter four = 4' in result)
        self.failUnless('title = Four' in result)

        # Change object four
        cache.set("counter", 5)
        four.title = 'Fouxr'
        four.save()
        response = self.client.get(url)
        result = response.content.decode("utf-8")
        self.failUnless('title = Onxe' in result)
        self.failIf('title = One' in result)
        self.failUnless('title = Twxo' in result)
        self.failIf('title = Two' in result)
        self.failUnless('title = Threxe' in result)
        self.failIf('title = Three' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 3' in result)
        self.failUnless('counter three = 4' in result)
        self.failUnless('counter four = 5' in result)
        self.failUnless('render_view = Onxe' in result)
        self.failUnless('include = Onxe' in result)
        self.failUnless('title = Fouxr' in result)
        self.failIf('title = Four' in result)

        # Change object five. This object is never accessed in the template,
        # only get_context_data of CachedView. "counter four" and "counter
        # five" are under cached_get and not in any ultracache tag, and are
        # thus the only counters incremented.
        cache.set("counter", 6)
        five.title = 'Fivxe'
        five.save()
        response = self.client.get(url)
        result = response.content.decode("utf-8")
        self.failUnless('title = Onxe' in result)
        self.failIf('title = One' in result)
        self.failUnless('title = Twxo' in result)
        self.failIf('title = Two' in result)
        self.failUnless('title = Threxe' in result)
        self.failIf('title = Three' in result)
        self.failUnless('counter one = 2' in result)
        self.failUnless('counter two = 3' in result)
        self.failUnless('counter three = 4' in result)
        self.failUnless('counter four = 6' in result)
        self.failUnless('counter five = 6' in result)
        self.failUnless('render_view = Onxe' in result)
        self.failUnless('include = Onxe' in result)
        self.failUnless('title = Fouxr' in result)
        self.failIf('title = Four' in result)

    def test_header(self):
        """Test that decorator preserves headers
        """
        url = reverse('cached-header-view')

        # Initial render
        response = self.client.get(url)
        self.assertEqual(response._headers['content-type'], ('Content-Type', 'application/json'))
        self.assertEqual(response._headers['foo'], ('foo', 'bar'))

        # Second pass is cached
        response = self.client.get(url)
        self.assertEqual(response._headers['content-type'], ('Content-Type', 'application/json'))
        self.assertEqual(response._headers['foo'], ('foo', 'bar'))

    def test_cache_busting(self):
        """Test cache busting with and without random querystring param
        """
        url = reverse('bustable-cached-view')
        response = self.client.get(url + '?aaa=1')
        self.failUnless('aaa=1' in response.content.decode("utf-8"))
        response = self.client.get(url + '?aaa=2')
        self.failUnless('aaa=2' in response.content.decode("utf-8"))

        url = reverse('non-bustable-cached-view')
        response = self.client.get(url + '?aaa=1')
        self.failUnless('aaa=1' in response.content.decode("utf-8"))
        response = self.client.get(url + '?aaa=2')
        self.failIf('aaa=2' in response.content.decode("utf-8"))
