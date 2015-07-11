from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db.models import Model
from django.core.cache import cache
from django.contrib.contenttypes.models import ContentType
try:
    from django.utils.module_loading import import_string as importer
except ImportError:
    from django.utils.module_loading import import_by_path as importer
from django.conf import settings

import ultracache.monkey


try:
    purger = importer(settings.ULTRACACHE['purge']['method'])
except (AttributeError, KeyError):
    purger = None


@receiver(post_save)
def on_post_save(sender, **kwargs):
    """Expire ultracache cache keys affected by this object
    """
    if issubclass(sender, Model):
        obj = kwargs['instance']
        if isinstance(obj, Model):
            # get_for_model itself is cached
            ct = ContentType.objects.get_for_model(sender)

            # Expire cache keys
            key = 'ucache-%s-%s' % (ct.id, obj.pk)
            to_delete = cache.get(key, [])
            if to_delete:
                try:
                    cache.delete_many(to_delete)
                except NotImplementedError:
                    for k in to_delete:
                        cache.delete(k)

            # Invalidate paths in reverse caching proxy
            key = 'ucache-pth-%s-%s' % (ct.id, obj.pk)
            if purger is not None:
                for path in cache.get(key, []):
                    purger(path)
            cache.delete(key)