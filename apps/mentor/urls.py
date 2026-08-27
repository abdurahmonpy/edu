"""
URL configuration for mentor chat app.
"""
from django.urls import path
from . import views

app_name = 'mentor'

urlpatterns = [
    path('', views.chat_view, name='chat'),
    path('clear/', views.clear_chat_view, name='clear'),
]
