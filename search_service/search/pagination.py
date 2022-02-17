import logging
from django.conf import settings

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class MadocPagination(PageNumberPagination):
    """

    Pagination class for Madoc results

    "pagination": {
        "page": 1,
        "totalPages": 35,
        "totalResults": 830
      }
    """
    page_size_query_param = "page_size"
    max_page_size = settings.MAX_PAGE_SIZE

    def get_paginated_response(self, data):
        return Response(
            {
                "pagination": {
                    "page": self.page.number,
                    "pageSize": self.page.paginator.per_page,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "totalPages": self.page.paginator.num_pages,
                    "totalResults": self.page.paginator.count,
                },
                "results": data,
            }
        )
