"""
Models for onboarding and diagnostic testing.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class DiagnosticResult(models.Model):
    """
    Stores baseline test score per skill (reading, writing, listening, speaking, grammar).
    """
    SKILL_CHOICES = [
        ('reading', 'Reading'),
        ('writing', 'Writing'),
        ('listening', 'Listening'),
        ('speaking', 'Speaking'),
        ('grammar', 'Grammar'),
    ]

    student = models.ForeignKey(
        'accounts.Student',
        on_delete=models.CASCADE,
        related_name='diagnostic_results',
        verbose_name="O'quvchi"
    )
    skill = models.CharField(
        max_length=50,
        choices=SKILL_CHOICES,
        verbose_name="Ko'nikma"
    )
    score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Ball (0-100)"
    )
    raw_response = models.TextField(
        blank=True,
        default="",
        verbose_name="O'quvchi javobi"
    )
    taken_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Topshirilgan vaqt"
    )

    class Meta:
        verbose_name = "Diagnostika natijasi"
        verbose_name_plural = "Diagnostika natijalari"
        ordering = ['-taken_at']

    def __str__(self):
        return f"{self.student.user.first_name} — {self.get_skill_display()}: {self.score} ball"


class TestCertificate(models.Model):
    """
    Standardized language and academic test certificates (IELTS, TOEFL, SAT, Duolingo, CEFR).
    Stores overall score and section breakdown with 3-year validity tracking.
    """
    CERTIFICATE_TYPE_CHOICES = [
        ('ielts', 'IELTS'),
        ('toefl', 'TOEFL iBT'),
        ('sat', 'SAT'),
        ('duolingo', 'Duolingo English Test (DET)'),
        ('cefr', 'CEFR / Milliy sertifikat'),
    ]

    student = models.ForeignKey(
        'accounts.Student',
        on_delete=models.CASCADE,
        related_name='test_certificates',
        verbose_name="O'quvchi"
    )
    certificate_type = models.CharField(
        max_length=50,
        choices=CERTIFICATE_TYPE_CHOICES,
        verbose_name="Sertifikat turi"
    )
    test_date = models.DateField(
        verbose_name="Imtihon topshirilgan sana"
    )
    overall_score = models.FloatField(
        verbose_name="Umumiy ball"
    )
    section_scores = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Bo'limlar bo'yicha ballar"
    )
    is_valid = models.BooleanField(
        default=True,
        verbose_name="Amal qilish muddati to'g'ri (<= 3 yil)"
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Tasdiqlangan vaqt"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt"
    )

    class Meta:
        verbose_name = "Test sertifikati"
        verbose_name_plural = "Test sertifikatlari"
        ordering = ['-test_date', '-created_at']

    def __str__(self):
        student_name = self.student.user.first_name if self.student and self.student.user else "O'quvchi"
        return f"{student_name} — {self.get_certificate_type_display()}: {self.overall_score}"

    @property
    def age_in_days(self):
        from django.utils import timezone
        if not self.test_date:
            return 0
        return (timezone.localdate() - self.test_date).days

    @property
    def is_expired(self):
        return self.age_in_days > (365 * 3)  # > 3 years (1095 days)

