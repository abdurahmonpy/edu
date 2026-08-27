"""
Admin configuration for Program model with strict source_url and last_verified_date validation.
"""
from django.contrib import admin
from .models import University, Program, StudentProgram, StudentTargetSelection

@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'city', 'world_ranking', 'acceptance_rate', 'created_at')
    list_filter = ('country',)
    search_fields = ('name', 'country', 'city')


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'university', 'country', 'type', 'field_of_study', 'min_ielts', 'deadline', 'last_verified_date', 'verified_by')
    list_filter = ('type', 'country', 'field_of_study', 'last_verified_date')
    search_fields = ('name', 'country', 'field_of_study', 'requirements', 'verified_by')
    
    fieldsets = (
        ("Asosiy ma'lumotlar", {
            'fields': ('name', 'university', 'country', 'type', 'field_of_study', 'deadline', 'grant_coverage', 'description')
        }),
        ("Minimal mezonlar", {
            'fields': ('min_ielts', 'min_toefl', 'min_sat', 'min_gpa')
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


@admin.register(StudentTargetSelection)
class StudentTargetSelectionAdmin(admin.ModelAdmin):
    list_display = ('student', 'primary_program', 'match_score', 'selected_at')
    list_filter = ('selected_at',)
    search_fields = ('student__user__phone_number', 'student__user__first_name', 'primary_program__name')


