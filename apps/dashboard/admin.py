"""
Admin configuration for SkillScore and ProgressLog with superuser-only access control.
"""
from django.contrib import admin
from apps.core.admin import SuperuserOnlyAdminMixin
from .models import SkillScore, ProgressLog

@admin.register(SkillScore)
class SkillScoreAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'skill', 'current_score', 'last_updated')
    list_filter = ('skill', 'last_updated')
    search_fields = ('student__user__phone_number', 'student__user__first_name')
    readonly_fields = ('last_updated',)


@admin.register(ProgressLog)
class ProgressLogAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'date', 'overall_ready_score', 'streak_count', 'delta', 'created_at')
    list_filter = ('date', 'created_at')
    search_fields = ('student__user__phone_number', 'student__user__first_name', 'delta')
    readonly_fields = ('created_at',)
