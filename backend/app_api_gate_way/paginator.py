from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.conf import settings


class BasePaginator(PageNumberPagination):
    page_size = 10


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_query_param = 'page'
    page_size_query_param = 'per_page'
    max_page_size = 1000

    def paginate_queryset(self, queryset, request, view=None):
        if 'all' in request.query_params:
            self.page_size = len(queryset)
            return super().paginate_queryset(queryset, request, view)
        return super().paginate_queryset(queryset, request, view)

    # custom thêm để hiện thêm total_pages với current_page_number
    def get_paginated_response(self, data):
        return Response({
            'page_size': len(data),
            'total_objects': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page_number': self.page.number,
            'next': f'{settings.BASE_URL}{self.get_next_link()[21:]}' if self.get_next_link() else None,
            'previous': f'{settings.BASE_URL}{self.get_previous_link()[21:]}' if self.get_previous_link() else None,
            'results': data,
        })

