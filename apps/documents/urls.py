from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.document_list_view, name='list'),
    path('create/', views.document_create_view, name='create'),
    path('<int:doc_id>/', views.document_detail_view, name='detail'),
    path('<int:doc_id>/edit/', views.document_edit_view, name='edit'),
    path('<int:doc_id>/ai-review/', views.document_ai_review_view, name='ai_review'),
    path('<int:doc_id>/delete/', views.document_delete_view, name='delete'),
    
    # Portfolio views
    path('<int:doc_id>/portfolio/upload/', views.portfolio_upload_view, name='portfolio_upload'),
    path('portfolio/<int:item_id>/', views.portfolio_item_detail_view, name='portfolio_item_detail'),
    path('portfolio/<int:item_id>/evaluate/', views.portfolio_evaluate_view, name='portfolio_evaluate'),
]
