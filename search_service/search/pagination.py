import logging

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class MuyaPagination(PageNumberPagination):
    """
    Initial pass at a custom pagination class for Muya.
    """

    def get_paginated_response(self, data):

        return Response(
            {
                "pagination": {
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "totalResults": self.page.paginator.count,
                    "totalPages": self.page.paginator.num_pages,
                    "page": self.page.number
                },
                "results": data,
            }
        )


class MuyaBootstrapPagination(PageNumberPagination):
    """
    Initial pass at a custom pagination class for Muya for use in Bootstrap templates.
    """

    def get_paginated_response(self, data):

        return Response(
            {
                "pagination": {
                    "page_obj": self.page,
                    "current_page_number": self.page.number,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "total_results": self.page.paginator.count,
                    "results_from": self.page.start_index(),
                    "results_to": self.page.end_index(),
                },
                "results": data,
            }
        )


class MadocPagination(PageNumberPagination):
    """

    Pagination class for Madoc results

    "pagination": {
        "page": 1,
        "totalPages": 35,
        "totalResults": 830
      }
    """

    def get_paginated_response(self, data):
        return Response(
            {
                "pagination": {
                    "page": self.page.number,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "totalPages": self.page.paginator.num_pages,
                    "totalResults": self.page.paginator.count,
                },
                "results": data,
            }
        )
