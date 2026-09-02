"""
URL configuration for dashboard app.
"""
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_view, name='index'),
    path('home/', views.dashboard_view, name='home'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('stats/', views.stats_view, name='stats'),
    path('strategy/', views.strategy_view, name='strategy'),
]
