from django.contrib import admin
from .models import Resource

@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author_name', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('title', 'summary', 'content', 'author_name')
    filter_horizontal = ('related_programs',)
