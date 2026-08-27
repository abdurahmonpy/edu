"""
Core admin security mixins for data privacy and role-based access control.
"""
from django.contrib import admin

class SuperuserOnlyAdminMixin:
    """
    Strict security mixin for student personal data and sensitive models.
    Guarantees that only users with is_superuser=True can view, add,
    change, or delete records in Django Admin.
    Standard staff members (is_staff=True, is_superuser=False) are strictly denied access.
    """
    def has_module_permission(self, request):
        return bool(request.user and request.user.is_active and request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user and request.user.is_active and request.user.is_superuser)

    def has_add_permission(self, request):
        return bool(request.user and request.user.is_active and request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user and request.user.is_active and request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and request.user.is_active and request.user.is_superuser)
