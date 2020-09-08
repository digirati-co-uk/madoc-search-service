from .models import PresentationAPIResource
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVectorField, SearchVector


@receiver(post_save, sender=PresentationAPIResource)
def update_searchvector(sender, instance, **kwargs):
    print("I updated the vectors")
    instance.search_vect = (
            SearchVector("label", weight="A")
            + SearchVector("description", weight="C")
            + SearchVector("attribution", weight="A")
            + SearchVector("m_summary", weight="B",
                           )
    )
    instance.save(update_fields=['search_vect'])
