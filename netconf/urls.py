from django.urls import path
from . import views

urlpatterns = [
    path('connect/', views.connect, name='connect'),
    path('select_config/', views.select_config, name='select_config'),
    path('edit-filter/', views.edit_filter, name='edit_filter'),
    path('create_xml/', views.create_xml, name='create_xml'),


]