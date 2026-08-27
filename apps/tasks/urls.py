"""
URL configuration for tasks app.
"""
from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('', views.task_list_view, name='list'),
    path('exam-prep/', views.exam_prep_view, name='exam_prep'),
    path('application-prep/', views.application_prep_view, name='application_prep'),
    path('<int:task_id>/', views.task_detail_view, name='detail'),
    path('<int:task_id>/result/', views.task_result_view, name='result'),
]
