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
    
    # Speaking Practice
    path('speaking/start/', views.speaking_start_view, name='speaking_start'),
    path('speaking/record/<int:session_id>/', views.speaking_record_view, name='speaking_record'),
    path('speaking/submit/<int:session_id>/', views.speaking_submit_view, name='speaking_submit'),
    path('speaking/result/<int:session_id>/', views.speaking_result_view, name='speaking_result'),
]
