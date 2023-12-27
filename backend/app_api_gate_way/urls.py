from django.urls import include,path

urlpatterns = [
    path('', include('app_account.urls')),
    path('', include('app_core.urls'))
]