"""
Admin configuration for User and Student models with superuser-only privacy enforcement.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.core.admin import SuperuserOnlyAdminMixin
from .models import User, Student

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('phone_number', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('phone_number', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ("Shaxsiy ma'lumotlar", {'fields': ('first_name', 'last_name', 'email')}),
        ("Ruxsatlar", {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ("Muhim sanalar", {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'first_name', 'password', 'is_staff', 'is_superuser'),
        }),
    )


@admin.register(Student)
class StudentAdmin(SuperuserOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('user', 'grade', 'region', 'target_field_of_study', 'budget_preference', 'english_level', 'onboarding_completed', 'created_at')
    list_filter = ('grade', 'region', 'target_field_of_study', 'budget_preference', 'english_level', 'onboarding_completed')
    search_fields = ('user__phone_number', 'user__first_name', 'user__last_name', 'city', 'target_career')
    readonly_fields = ('created_at',)
