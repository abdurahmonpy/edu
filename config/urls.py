"""
URL configuration for study abroad platform MVP.
"""
from django.contrib import admin
from django.urls import path, include
from apps.core.views import landing_page_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('onboarding/', include('apps.onboarding.urls', namespace='onboarding')),
    path('tasks/', include('apps.tasks.urls', namespace='tasks')),
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),
    path('mentor/', include('apps.mentor.urls', namespace='mentor')),
    path('programs/', include('apps.programs.urls', namespace='programs')),
    path('', landing_page_view, name='home'),
]
