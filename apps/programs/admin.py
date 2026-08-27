"""
Admin configuration for Program model with strict source_url and last_verified_date validation.
"""
from django.contrib import admin
from .models import Program, StudentProgram

@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'type', 'deadline', 'last_verified_date', 'verified_by')
    list_filter = ('type', 'country', 'last_verified_date')
    search_fields = ('name', 'country', 'requirements', 'verified_by')
    
    fieldsets = (
        ("Asosiy ma'lumotlar", {
            'fields': ('name', 'country', 'type', 'deadline')
        }),
        ("Talablar va Hujjatlar", {
            'fields': ('requirements',)
        }),
        ("Tasdiqlash va Manba (Majburiy)", {
            'fields': ('source_url', 'last_verified_date', 'verified_by')
        }),
    )


@admin.register(StudentProgram)
class StudentProgramAdmin(admin.ModelAdmin):
    list_display = ('student', 'program', 'tracked_at')
    list_filter = ('tracked_at', 'program__country', 'program__type')
    search_fields = ('student__user__phone_number', 'student__user__first_name', 'program__name')

