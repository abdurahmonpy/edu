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
