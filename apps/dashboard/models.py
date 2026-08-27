"""
Models for student dashboard, skill scores, and progress tracking.
"""
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

class SkillScore(models.Model):
    """
    Tracks dynamic mastery score (0-100) per skill for each student.
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
        related_name='skill_scores',
        verbose_name="O'quvchi"
    )
    skill = models.CharField(
        max_length=50,
        choices=SKILL_CHOICES,
        verbose_name="Ko'nikma"
    )
    current_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Joriy ball (0-100)"
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name="Oxirgi yangilanish"
    )

    class Meta:
        verbose_name = "Ko'nikma bali"
        verbose_name_plural = "Ko'nikma ballari"
        unique_together = ('student', 'skill')
        ordering = ['student', 'skill']

    def __str__(self):
        return f"{self.student.user.first_name} — {self.get_skill_display()}: {self.current_score}%"


class ProgressLog(models.Model):
    """
    Daily snapshot log of overall Ready Score, streak count, and change delta.
    """
    student = models.ForeignKey(
        'accounts.Student',
        on_delete=models.CASCADE,
        related_name='progress_logs',
        verbose_name="O'quvchi"
    )
    date = models.DateField(
        default=timezone.localdate,
        verbose_name="Sana"
    )
    overall_ready_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Tayyorgarlik bali (0-100)"
    )
    streak_count = models.IntegerField(
        default=0,
        verbose_name="Ketma-ketlik (streak)"
    )
    delta = models.CharField(
        max_length=100,
        default='0',
        verbose_name="O'zgarish miqdori va sababi"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt"
    )

    class Meta:
        verbose_name = "Rivojlanish jurnali"
        verbose_name_plural = "Rivojlanish jurnallari"
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.student.user.first_name} — {self.date}: Ready {self.overall_ready_score}% (Streak {self.streak_count})"
