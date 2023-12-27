from .views import *
from django.urls import path, include
from rest_framework import routers

routers = routers.DefaultRouter()
routers.register('user', UserCustomAPIView, 'user')

urlpatterns = [
    path('', include(routers.urls)),
    path('login/', TokenView.as_view()),
]