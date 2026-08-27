"""
Models for verified study abroad and scholarship programs catalog.
"""
from django.db import models
from django.core.exceptions import ValidationError

class Program(models.Model):
    """
    Verified international study abroad scholarships, exchange programs, and grants.
    Requires verified source_url and last_verified_date to prevent hallucinated data.
    """
    TYPE_CHOICES = [
        ('grant', "To'liq Grant / Stipendiya"),
        ('partial_grant', "Qisman Grant"),
        ('paid', "To'lovli"),
        ('exchange', "Almashinuv dasturi"),
    ]

    name = models.CharField(
        max_length=255,
        verbose_name="Dastur nomi"
    )
    country = models.CharField(
        max_length=100,
        verbose_name="Davlat"
    )
    type = models.CharField(
        max_length=100,
        choices=TYPE_CHOICES,
        default='grant',
        verbose_name="Dastur turi"
    )
    requirements = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Talablar"
    )
    deadline = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Topshirish muddati"
    )
    source_url = models.URLField(
        max_length=500,
        blank=False,
        null=False,
        verbose_name="Rasmiy manba havolasi"
    )
    last_verified_date = models.DateField(
        blank=False,
        null=False,
        verbose_name="Oxirgi tekshirilgan sana"
    )
    verified_by = models.CharField(
        max_length=150,
        default='admin',
        verbose_name="Tekshiruvchi admin"
    )

    class Meta:
        verbose_name = "Ta'lim dasturi"
        verbose_name_plural = "Ta'lim dasturlari"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.country}) — {self.get_type_display()}"

    def clean(self):
        super().clean()
        errors = {}
        if not self.source_url or not str(self.source_url).strip():
            errors['source_url'] = "Rasmiy manba havolasi (source_url) kiritilishi shart."
        if not self.last_verified_date:
            errors['last_verified_date'] = "Oxirgi tekshirilgan sana (last_verified_date) ko'rsatilishi shart."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class StudentProgram(models.Model):
    """
    Through model linking Student (accounts.Student) and Program (programs.Program)
    for tracking and bookmarking study abroad programs.
    """
    student = models.ForeignKey(
        'accounts.Student',
        on_delete=models.CASCADE,
        related_name='tracked_programs',
        verbose_name="O'quvchi"
    )
    program = models.ForeignKey(
        'programs.Program',
        on_delete=models.CASCADE,
        related_name='student_tracking',
        verbose_name="Dastur"
    )
    tracked_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Kuzatuvga olingan vaqt"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt"
    )

    class Meta:
        verbose_name = "Kuzatilayotgan dastur"
        verbose_name_plural = "Kuzatilayotgan dasturlar"
        unique_together = ('student', 'program')
        ordering = ['-tracked_at']

    def __str__(self):
        return f"{self.student} — {self.program.name}"

