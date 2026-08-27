from django.contrib import admin
from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'doc_type', 'version', 'status', 'updated_at')
    list_filter = ('doc_type', 'status', 'created_at')
    search_fields = ('title', 'student__user__first_name', 'student__user__phone_number', 'content')
    raw_id_fields = ('student', 'linked_program')
