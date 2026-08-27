from django.urls import path
from . import views

app_name = 'mock_exams'

urlpatterns = [
    path('', views.mock_exam_intro_view, name='intro'),
    path('start/<str:exam_type>/', views.start_mock_exam_view, name='start'),
    path('<int:exam_id>/section/<int:section_id>/', views.mock_exam_section_view, name='section'),
    path('<int:exam_id>/section/<int:section_id>/submit/', views.submit_mock_section_view, name='submit_section'),
    path('<int:exam_id>/results/', views.mock_exam_result_view, name='results'),
]
