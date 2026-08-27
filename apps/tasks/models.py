"""
Models for daily tasks and AI-generated grading.
"""
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

class DailyTask(models.Model):
    """
    Daily practice tasks (grammar drill, reading comprehension) targeting the student's weakest skill.
    """
    TASK_TYPE_CHOICES = [
        ('grammar_drill', 'Grammar Drill'),
        ('reading_comprehension', 'Reading Comprehension'),
    ]

    student = models.ForeignKey(
        'accounts.Student',
        on_delete=models.CASCADE,
        related_name='daily_tasks',
        verbose_name="O'quvchi"
    )
    study_plan = models.ForeignKey(
        'study_plans.StudyPlan',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='daily_tasks',
        verbose_name="O'quv rejasi"
    )
    date = models.DateField(
        default=timezone.localdate,
        verbose_name="Vazifa sanasi"
    )
    task_type = models.CharField(
        max_length=50,
        choices=TASK_TYPE_CHOICES,
        verbose_name="Vazifa turi"
    )
    content = models.JSONField(
        default=dict,
        verbose_name="Vazifa mazmuni"
    )
    completed = models.BooleanField(
        default=False,
        verbose_name="Bajarildi"
    )
    score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Natija bali (0-100)"
    )
    student_answer = models.TextField(
        blank=True,
        default="",
        verbose_name="O'quvchi javobi"
    )
    ai_feedback = models.TextField(
        blank=True,
        default="",
        verbose_name="AI tahlili va tushuntirishi"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Bajarilgan vaqt"
    )

    class Meta:
        verbose_name = "Kunlik vazifa"
        verbose_name_plural = "Kunlik vazifalar"
        ordering = ['-date', '-id']

    def __str__(self):
        status = "Bajarilgan" if self.completed else "Kutilmoqda"
        return f"{self.student.user.first_name} — {self.get_task_type_display()} ({self.date}) [{status}]"
