from django.urls import path
from . import views

urlpatterns = [
    path('connect/', views.connect, name='connect'),
    path('select_config/', views.select_config, name='select_config'),
    path('create_xml/', views.create_xml, name='create_xml'),

    
]
#path('get_config/', views.get_config, name='get_config'),
#path('connect_success/', views.connect_success, name='connect_success'),
