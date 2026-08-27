"""
Admin configuration for DiagnosticResult with superuser-only access control.
"""
from django.contrib import admin
from apps.core.admin import SuperuserOnlyAdminMixin
from .models import DiagnosticResult, TestCertificate

@admin.register(DiagnosticResult)
class DiagnosticResultAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'skill', 'score', 'taken_at')
    list_filter = ('skill', 'taken_at')
    search_fields = ('student__user__phone_number', 'student__user__first_name')
    readonly_fields = ('taken_at',)


@admin.register(TestCertificate)
class TestCertificateAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('student', 'certificate_type', 'overall_score', 'test_date', 'is_valid', 'created_at')
    list_filter = ('certificate_type', 'is_valid', 'test_date')
    search_fields = ('student__user__phone_number', 'student__user__first_name')
    readonly_fields = ('created_at',)

