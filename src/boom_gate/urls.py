"""
Boom Gate URL Configuration
"""
from django.urls import path
from . import views

app_name = 'boom_gate'

urlpatterns = [
    path('', views.boom_gate_control, name='control'),
    path('status/', views.gate_status_api, name='status_api'),
    path('control/', views.gate_control_api, name='control_api'),
]
