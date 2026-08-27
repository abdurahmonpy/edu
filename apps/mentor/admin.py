"""
Admin configuration for MentorMessage with superuser-only access control.
"""
from django.contrib import admin
from apps.core.admin import SuperuserOnlyAdminMixin
from .models import MentorMessage

@admin.register(MentorMessage)
class MentorMessageAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'role', 'content_preview', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('student__user__phone_number', 'student__user__first_name', 'content')
    readonly_fields = ('created_at',)

    def content_preview(self, obj):
        return obj.content[:60] if obj.content else ""
    content_preview.short_description = "Xabar matni"
