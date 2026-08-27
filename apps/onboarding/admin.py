"""
Admin configuration for DiagnosticResult with superuser-only access control.
"""
from django.contrib import admin
from apps.core.admin import SuperuserOnlyAdminMixin
from .models import DiagnosticResult

@admin.register(DiagnosticResult)
class DiagnosticResultAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'skill', 'score', 'taken_at')
    list_filter = ('skill', 'taken_at')
    search_fields = ('student__user__phone_number', 'student__user__first_name')
    readonly_fields = ('taken_at',)
