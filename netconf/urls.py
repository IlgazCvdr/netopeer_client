from django.urls import path
from . import views

urlpatterns = [
    path('connect/', views.connect, name='connect'),
    path('connect_success/', views.connect_success, name='connect_success'),
    path('select_config/', views.select_config, name='select_config'),
    path('get_config/', views.get_config, name='get_config'),
]
