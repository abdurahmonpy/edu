"""
URL configuration for programs app.
"""
from django.urls import path
from . import views

app_name = 'programs'

urlpatterns = [
    path('', views.program_list_view, name='catalog'),
    path('list/', views.program_list_view, name='list'),
    path('<int:program_id>/', views.program_detail_view, name='detail'),
    path('<int:program_id>/track/', views.toggle_track_program, name='toggle_track'),
]

