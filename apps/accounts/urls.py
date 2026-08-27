"""
URL patterns for accounts authentication.
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_settings_view, name='profile'),
    path('settings/', views.profile_settings_view, name='settings'),
]
