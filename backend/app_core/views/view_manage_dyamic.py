import re

# login
from rest_framework import viewsets, generics
from rest_framework.parsers import MultiPartParser, FormParser

from app_api_gate_way.paginator import CustomPagination
from app_core.models import ModelDynamicFolder
from app_core.serializers import ModelDynamicFolderSerializerOverView, ModelDynamicFolderSerializer
from backend.cores import no_accent_vietnamese

class DynamicAPIView(viewsets.ViewSet, generics.ListAPIView, generics.RetrieveAPIView,
                        generics.UpdateAPIView, generics.DestroyAPIView):
    # parser_classes = [MultiPartParser, FormParser]
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return ModelDynamicFolderSerializerOverView
        else:
            return ModelDynamicFolderSerializer
    def get_queryset(self):
        list_obj = ModelDynamicFolder.objects.filter(is_active=True)
        q = self.request.query_params.get('q')
        if q is not None:
            custom_list = [obj.id for obj in list_obj if
                           re.search(no_accent_vietnamese(q).lower(), no_accent_vietnamese(obj.name_display).lower())]
            list_obj = list_obj.filter(id__in=custom_list)
        return list_obj