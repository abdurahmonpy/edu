"""
URL configuration for study plans app.
"""
from django.urls import path
from . import views

app_name = 'study_plans'

urlpatterns = [
    path('', views.plan_detail_view, name='detail'),
]
