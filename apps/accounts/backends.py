"""
Custom authentication backend for phone-number based login.
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .utils import normalize_uzbek_phone

UserModel = get_user_model()

class PhoneAuthBackend(ModelBackend):
    """
    Authenticates users using their Uzbek phone number (+998XXXXXXXXX) and password.
    """
    def authenticate(self, request, username=None, password=None, phone_number=None, **kwargs):
        raw_phone = phone_number or username or kwargs.get('phone')
        if not raw_phone or not password:
            return None
        
        try:
            normalized_phone = normalize_uzbek_phone(raw_phone)
        except ValidationError:
            return None
        
        try:
            user = UserModel.objects.get(phone_number=normalized_phone)
        except UserModel.DoesNotExist:
            # Timing attack mitigation
            UserModel().set_password(password)
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
