from django.urls import path
from . import views

app_name = 'resources'

urlpatterns = [
    path('', views.resource_list_view, name='list'),
    path('<int:resource_id>/', views.resource_detail_view, name='detail'),
]
