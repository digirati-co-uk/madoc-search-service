from django.apps import AppConfig


class SearchConfig(AppConfig):
    name = "search"

    def ready(self):
        # We wrap this in a try-except to avoid issues if the DB isn't migrated yet
        try:
            from django_q.models import Schedule
            Schedule.objects.get_or_create(
                func='search.tasks.refresh_facet_bitmaps',
                defaults={
                    'schedule_type': Schedule.CRON,
                    'cron': '*/5 * * * *',  # Every 5 minutes
                    'repeats': -1  # Infinite repeats
                }
            )
        except Exception:
            pass
