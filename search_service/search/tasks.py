import logging
from django.db import connection

logger = logging.getLogger(__name__)

def refresh_facet_bitmaps():
    """
    Refreshes the mv_facet_bitmaps materialized view in the background.
    Uses CONCURRENTLY so the search API is not locked during the refresh.
    """
    logger.info("Starting concurrent refresh of mv_facet_bitmaps...")
    try:
        with connection.cursor() as cursor:
            # CONCURRENTLY requires the unique index we created in the migration
            cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_facet_bitmaps;")
        logger.info("Successfully refreshed mv_facet_bitmaps.")
    except Exception as e:
        logger.error(f"Failed to refresh mv_facet_bitmaps: {e}")
