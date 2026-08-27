"""
Admin configuration for DailyTask with superuser-only access control.
"""
from django.contrib import admin
from apps.core.admin import SuperuserOnlyAdminMixin
from .models import DailyTask

@admin.register(DailyTask)
class DailyTaskAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'task_type', 'date', 'completed', 'score', 'completed_at')
    list_filter = ('task_type', 'completed', 'date')
    search_fields = ('student__user__phone_number', 'student__user__first_name', 'ai_feedback')
    readonly_fields = ('completed_at',)
