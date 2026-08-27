"""
URL patterns for onboarding flow.
"""
from django.urls import path
from . import views

app_name = 'onboarding'

urlpatterns = [
    path('', views.step_1_view, name='index'),
    path('step-1/', views.step_1_view, name='step_1'),
    path('diagnostic/', views.diagnostic_view, name='diagnostic'),
    path('diagnostic/submit/', views.diagnostic_view, name='diagnostic_submit'),
    path('results/', views.results_view, name='results'),
]
