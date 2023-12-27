from .views import *
from django.urls import path, include
from rest_framework import routers

from .views.create_layer import api_create_models_from_geojson, api_create_models_from_shapefile
from .views.view_layer import get_sqlquery_geo

routers = routers.DefaultRouter()
routers.register('layer', DynamicAPIView, 'layer')

urlpatterns = [
    path('', include(routers.urls)),
    path('import-geojsonfile/', api_create_models_from_geojson),
    path('import-shapefile/', api_create_models_from_shapefile),
    path('geo/<str:model_name>/', get_sqlquery_geo)
]
