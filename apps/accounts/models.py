"""
User and Student models for the study abroad platform.
"""
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.validators import RegexValidator
from .utils import normalize_uzbek_phone

class UserManager(BaseUserManager):
    """
    Custom user manager where phone_number is the unique identifier for authentication.
    """
    def create_user(self, phone_number, password=None, first_name="", **extra_fields):
        if not phone_number:
            raise ValueError("Telefon raqami kiritilishi shart.")
        
        normalized_phone = normalize_uzbek_phone(phone_number)
        extra_fields.setdefault('is_active', True)
        user = self.model(
            phone_number=normalized_phone,
            first_name=first_name,
            **extra_fields
        )
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        
        # Auto-create student profile if not exists
        Student.objects.get_or_create(user=user)
        return user

    def create_superuser(self, phone_number, password=None, first_name="Admin", **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser is_staff=True bo'lishi kerak.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser is_superuser=True bo'lishi kerak.")

        return self.create_user(phone_number, password, first_name=first_name, **extra_fields)


class User(AbstractUser):
    """
    Custom User model using phone_number as primary authentication identifier.
    """
    username = None  # Remove username field
    phone_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        validators=[
            RegexValidator(
                regex=r'^\+998\d{9}$',
                message="Telefon raqami +998XXXXXXXXX formatida bo'lishi kerak."
            )
        ],
        verbose_name="Telefon raqami"
    )
    first_name = models.CharField(max_length=150, blank=True, default="", verbose_name="Ism")
    last_name = models.CharField(max_length=150, blank=True, default="", verbose_name="Familiya")
    email = models.EmailField(blank=True, default="", verbose_name="Email manzili")
    
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    is_staff = models.BooleanField(default=False, verbose_name="Xodim maqomi")
    is_superuser = models.BooleanField(default=False, verbose_name="Superuser maqomi")
    date_joined = models.DateTimeField(default=timezone.now, verbose_name="Ro'yxatdan o'tgan sana")

    objects = UserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['first_name']

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        ordering = ['-date_joined']

    def __str__(self):
        name_part = self.first_name if self.first_name else "Foydalanuvchi"
        return f"{name_part} ({self.phone_number})"


class Student(models.Model):
    """
    Student profile linked OneToOne with User, storing academic and onboarding data.
    """
    GRADE_CHOICES = [
        (9, '9-sinf'),
        (10, '10-sinf'),
        (11, '11-sinf'),
    ]

    PROGRAM_TYPE_CHOICES = [
        ('grant', "To'liq Grant / Stipendiya"),
        ('partial_grant', "Qisman Grant"),
        ('paid', "To'lovli"),
        ('exchange', "Almashinuv dasturi"),
    ]

    ENGLISH_LEVEL_CHOICES = [
        ('beginner', "Beginner (A1-A2)"),
        ('intermediate', "Intermediate (B1-B2)"),
        ('advanced', "Advanced (C1-C2)"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name="Foydalanuvchi"
    )
    grade = models.IntegerField(
        choices=GRADE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Sinf"
    )
    target_countries = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Maqsad qilingan davlatlar"
    )
    target_program_type = models.CharField(
        max_length=100,
        choices=PROGRAM_TYPE_CHOICES,
        default='grant',
        blank=True,
        verbose_name="Maqsad qilingan dastur turi"
    )
    english_level = models.CharField(
        max_length=50,
        choices=ENGLISH_LEVEL_CHOICES,
        default='beginner',
        blank=True,
        verbose_name="Ingliz tili darajasi"
    )
    onboarding_completed = models.BooleanField(
        default=False,
        verbose_name="Onboarding yakunlangan"
    )
    notification_reminder_time = models.CharField(
        max_length=10,
        default="20:00",
        blank=True,
        verbose_name="Eslatma vaqti"
    )
    notification_email_enabled = models.BooleanField(
        default=True,
        verbose_name="Email eslatmalari"
    )
    notification_daily_reminders = models.BooleanField(
        default=True,
        verbose_name="Kunlik vazifa eslatmalari"
    )
    preferred_language = models.CharField(
        max_length=10,
        default="uz",
        verbose_name="Afzal ko'rilgan til"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt"
    )

    class Meta:
        verbose_name = "O'quvchi profili"
        verbose_name_plural = "O'quvchilar profillari"
        ordering = ['-created_at']

    def __str__(self):
        grade_str = f"{self.grade}-sinf" if self.grade else "Sinf belgilanmagan"
        return f"{self.user.first_name or self.user.phone_number} — {grade_str}"

    @property
    def overall_ready_score(self):
        try:
            from apps.services.score_service import calculate_overall_ready_score
            return calculate_overall_ready_score(self)
        except Exception:
            return 0

    @property
    def streak_days(self):
        try:
            from apps.services.score_service import get_student_streak
            return get_student_streak(self)
        except Exception:
            return 0


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def ensure_student_profile_exists(sender, instance, created, **kwargs):
    if created:
        Student.objects.get_or_create(user=instance)


