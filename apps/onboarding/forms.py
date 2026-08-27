"""
Forms for multi-step onboarding wizard.
"""
from django import forms
from apps.accounts.models import Student

COUNTRY_CHOICES = [
    ('AQSh', 'AQSh (Global UGRAD, Universitet Grantlari)'),
    ('Buyuk Britaniya', 'Buyuk Britaniya (Chevening, Foundation)'),
    ('Germaniya', 'Germaniya (DAAD, Davlat Universitetlari)'),
    ('Turkiya', 'Turkiya (Türkiye Bursları)'),
    ('Janubiy Koreya', 'Janubiy Koreya (GKS / KGSP)'),
    ('Kanada', 'Kanada (Universitet Grantlari)'),
    ('Yaponiya', 'Yaponiya (MEXT)'),
    ('Boshqa', 'Boshqa davlatlar'),
]


class OnboardingStep1Form(forms.Form):
    grade = forms.TypedChoiceField(
        choices=Student.GRADE_CHOICES,
        coerce=int,
        label="Hozir nechanchi sinfda o'qiysiz?",
        widget=forms.RadioSelect(attrs={'class': 'peer hidden'}),
        error_messages={'required': "Iltimos, o'qiydigan sinfingizni tanlang."}
    )
    target_countries = forms.MultipleChoiceField(
        choices=COUNTRY_CHOICES,
        label="Qaysi davlatlarda ta'lim olishni rejalashtiryapsiz?",
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'peer hidden'}),
        required=True,
        error_messages={'required': "Kamida bitta davlatni tanlang."}
    )
    target_program_type = forms.ChoiceField(
        choices=Student.PROGRAM_TYPE_CHOICES,
        label="Sizni qiziqtirgan dastur turi qanday?",
        widget=forms.RadioSelect(attrs={'class': 'peer hidden'}),
        initial='grant',
        required=True,
        error_messages={'required': "Dastur turini tanlang."}
    )
    english_level = forms.ChoiceField(
        choices=Student.ENGLISH_LEVEL_CHOICES,
        label="Hozirgi ingliz tili darajangiz qanday?",
        widget=forms.RadioSelect(attrs={'class': 'peer hidden'}),
        initial='beginner',
        required=True,
        error_messages={'required': "Ingliz tili darajangizni tanlang."}
    )

    def save(self, student: Student) -> Student:
        student.grade = int(self.cleaned_data['grade'])
        student.target_countries = self.cleaned_data['target_countries']
        student.target_program_type = self.cleaned_data['target_program_type']
        student.english_level = self.cleaned_data['english_level']
        student.save()
        return student
