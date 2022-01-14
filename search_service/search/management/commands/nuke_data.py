from django.core.management.base import BaseCommand
from iiif_search.models import IIIFResource, Indexables
import logging


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Management command to add a nuke data"

    def handle(self, *args, **options):
        logger.warning("Deleting all the things")
        IIIFResource.objects.all().delete()
        Indexables.objects.all().delete()

