"""
Admin configuration for StudyPlan with superuser-only access control.
"""
from django.contrib import admin
from apps.core.admin import SuperuserOnlyAdminMixin
from .models import StudyPlan

@admin.register(StudyPlan)
class StudyPlanAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'timeline_months', 'start_date', 'target_date', 'active', 'created_at')
    list_filter = ('active', 'timeline_months', 'start_date', 'target_date')
    search_fields = ('student__user__phone_number', 'student__user__first_name', 'goal')
    readonly_fields = ('created_at',)
