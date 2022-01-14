from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import IIIFResource
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=IIIFResource)
def update_thumbnail(sender, instance, **kwargs):
    if not instance.madoc_thumbnail:
        logger.info("No thumbnail")
