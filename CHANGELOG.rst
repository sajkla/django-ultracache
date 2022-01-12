Changelog
=========

2.2
---
#. Django 4.0 compatibility.

2.1.1
-----
#. Ensure cache coherency should a purger fail.

2.1.0
-----
#. Django 3 compatibility.
#. Fix potential thread local residual data issue.

2.0.0
-----
#. Remove dependency on the sites framework everywhere. The sites framework is still automatically
   considered if an installed app.
#. Do not store metadata in the request anymore but in a list on thread locals.
#. Introduce class utils.Ultracache to subject arbitrary pieces of Python code to caching.
#. Drop Django 1 support.

1.11.12
-------
#. Simpler class based decorator.
#. Add Django 2.1 and Python 3.6 tests.

1.11.11
-------
#. Add a test for tasks.

1.11.10
-------
#. Ensure a working error message if pika is not found.
#. `cached_get` now considers any object accessed in get_context_data and not just objects accessed in the view template.
#. The original request headers are now sent to the purgers along with the path. This enables fine-grained proxy invalidation.
#. Django 2.0 and Python 3 compatibility. Django 1.9 support has been dropped.

1.11.9
------
#. Simplify the DRF caching implementation. It also now considers objects touched by sub-serializers.

1.11.8
------
#. The DRF settings now accept dotted names.
#. The DRF setting now accepts a callable whose result forms part of the cache key.

1.11.7
------
#. Use pickle to cache DRF data because DRF uses a Decimal type that isn't recognized by Python's json library.

1.11.6
------
#. Adjust the DRF decorator so it can be used in more places.

1.11.5
------
#. Django Rest Framework caching does not cache the entire response anymore, only the data and headers.

1.11.4
------
#. Move the twisted work to `django-ultracache-twisted`.
#. Clearly raise exception if libraries are not found.

1.11.3
------
#. Move the twisted directory one lower.

1.11.2
------
#. Package the product properly so all directories are included.

1.11.1
------
#. More defensive code to ensure we don't interfere during migrations in a test run.

1.11.0
------
#. Introduce `rabbitmq-url` setting for use by `broadcast_purge` task.
#. Django 1.11 support.
#. Deprecate Django 1.6 support.

1.10.2
------
#. Remove logic that depends on SITE_ID so site can also be inferred from the request.

1.10.1
------
#. Add caching for Django Rest Framework viewsets.
#. Django 1.10 compatibility.

1.9.1
-----
#. Add missing import only surfacing in certain code paths.
#. `Invalidate` setting was not being loaded properly. Fixed.
#. Handle content types RuntimeError when content types have not been migrated yet.

1.9.0
-----
#. Move to tox for tests.
#. Django 1.9 compatibility.

0.3.8
-----
#. Honor the `raw` parameter send along by loaddata. It prevents redundant post_save handling.

0.3.7
-----
#. Revert the adding of the template name. It introduces a performance penalty in a WSGI environment.
#. Further reduce the number of writes to the cache.

0.3.6
-----
#. Add template name (if possible) to the caching key.
#. Reduce number of calls to set_many.

0.3.5
-----
#. Keep the metadata cache size in check to prevent possibly infinite growth.

0.3.4
-----
#. Prevent redundant sets.
#. Work around an apparent Python bug related to `di[k].append(v)` vs `di[k] = di[k] + [v]`. The latter is safe.

0.3.3
-----
#. Handle case where one cached view renders another cached view inside it, thus potentially sharing the same cache key.

0.3.2
-----
#. The `ultracache` template tag now only caches HEAD and GET requests.

0.3.1
-----
#. Trivial release to work around Pypi errors of the day.

0.3
---
#. Replace `cache.get` in for loop with `cache.get_many`.

0.2
---
#. Do not automatically add `request.get_full_path()` if any of `request.get_full_path()`, `request.path` or `request.path_info` is an argument for `cached_get`.

0.1.6
-----
#. Also cache response headers.

0.1.5
-----
#. Explicitly check for GET and HEAD request method and cache only those requests.

0.1.4
-----
#. Rewrite decorator to be function based instead of class based so it is easier to use in urls.py.

0.1.3
-----
#. `cached_get` decorator now does not cache if request contains messages.

0.1.2
-----
#. Fix HTTPResponse caching bug.

0.1.1
-----
#. Handle case where a view returns an HTTPResponse object.

0.1
---
#. Initial release.

