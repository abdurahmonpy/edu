"""
Registration and Login forms with Uzbek phone number normalization and validation.
"""
from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from .utils import normalize_uzbek_phone

User = get_user_model()

class UserRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        label="Ismingiz",
        widget=forms.TextInput(attrs={
            'placeholder': 'Masalan: Malika',
            'class': 'w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition text-slate-800'
        }),
        error_messages={'required': "Ismingizni kiriting."}
    )
    phone_number = forms.CharField(
        max_length=25,
        label="Telefon raqami",
        widget=forms.TextInput(attrs={
            'placeholder': '+998 90 123 45 67',
            'type': 'tel',
            'class': 'w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition text-slate-800'
        }),
        error_messages={'required': "Telefon raqami kiritilishi shart."}
    )
    password = forms.CharField(
        label="Parol",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Kamida 6 ta belgi',
            'class': 'w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition text-slate-800'
        }),
        error_messages={'required': "Parol kiritilishi shart."}
    )
    password_confirm = forms.CharField(
        label="Parolni tasdiqlang",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Parolni qayta kiriting',
            'class': 'w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition text-slate-800'
        }),
        error_messages={'required': "Parolni tasdiqlash shart."}
    )

    class Meta:
        model = User
        fields = ['first_name', 'phone_number', 'password']

    def clean_phone_number(self):
        raw_phone = self.cleaned_data.get('phone_number')
        try:
            normalized_phone = normalize_uzbek_phone(raw_phone)
        except ValidationError:
            raise forms.ValidationError("Telefon raqami noto'g'ri kiritildi (+998XXXXXXXXX formatida bo'lishi kerak).")
        
        if User.objects.filter(phone_number=normalized_phone).exists():
            raise forms.ValidationError("Ushbu telefon raqami allaqachon ro'yxatdan o'tgan.")
        
        return normalized_phone

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password and len(password) < 6:
            raise forms.ValidationError("Parol kamida 6 ta belgidan iborat bo'lishi kerak.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Parollar bir-biriga mos kelmadi.")

        return cleaned_data

    def save(self, commit=True):
        user = User.objects.create_user(
            phone_number=self.cleaned_data['phone_number'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name']
        )
        return user


class UserLoginForm(forms.Form):
    phone_number = forms.CharField(
        label="Telefon raqami",
        widget=forms.TextInput(attrs={
            'placeholder': '+998 90 123 45 67',
            'type': 'tel',
            'class': 'w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition text-slate-800'
        }),
        error_messages={'required': "Telefon raqami kiritilishi shart."}
    )
    password = forms.CharField(
        label="Parol",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Parolingizni kiriting',
            'class': 'w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition text-slate-800'
        }),
        error_messages={'required': "Parol kiritilishi shart."}
    )

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        raw_phone = cleaned_data.get('phone_number')
        password = cleaned_data.get('password')

        if raw_phone and password:
            try:
                normalized_phone = normalize_uzbek_phone(raw_phone)
            except ValidationError:
                raise forms.ValidationError("Telefon raqami noto'g'ri kiritildi (+998XXXXXXXXX formatida bo'lishi kerak).")

            self.user = authenticate(
                self.request,
                username=normalized_phone,
                password=password
            )

            if self.user is None:
                raise forms.ValidationError("Telefon raqami yoki parol noto'g'ri.")
            
            if not self.user.is_active:
                raise forms.ValidationError("Foydalanuvchi hisobi faol emas.")

        return cleaned_data


class ProfileSettingsForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        label="Ismingiz",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm'
        })
    )
    email = forms.EmailField(
        required=False,
        label="Email manzili",
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm'
        })
    )

    class Meta:
        from .models import Student
        model = Student
        fields = [
            'grade', 'target_program_type', 'english_level',
            'notification_reminder_time', 'notification_email_enabled',
            'notification_daily_reminders', 'preferred_language'
        ]
        widgets = {
            'grade': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm'
            }),
            'target_program_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm'
            }),
            'english_level': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm'
            }),
            'notification_reminder_time': forms.TextInput(attrs={
                'placeholder': 'Masalan: 20:00',
                'class': 'w-full px-4 py-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm'
            }),
            'notification_email_enabled': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500'
            }),
            'notification_daily_reminders': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500'
            }),
            'preferred_language': forms.Select(choices=[('uz', "O'zbekcha"), ('en', "English")], attrs={
                'class': 'w-full px-4 py-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm'
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['email'].initial = user.email
