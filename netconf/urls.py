from django.urls import path
from . import views

urlpatterns = [
    path('netconf/', views.netconf_operation, name='netconf_operation'),
]