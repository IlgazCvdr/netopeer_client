from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('connect/', views.connect, name='connect'),
    path('connect-success/', views.connect_success, name='connect_success'),

]
