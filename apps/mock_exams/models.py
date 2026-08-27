from django.db import models
from django.utils import timezone
from apps.accounts.models import Student


class MockExam(models.Model):
    EXAM_TYPE_CHOICES = [
        ('ielts', 'IELTS Academic (Listening, Reading, Writing)'),
        ('sat', 'SAT Digital (Reading & Writing, Math)'),
        ('toefl', 'TOEFL iBT'),
    ]

    STATUS_CHOICES = [
        ('in_progress', 'Jarayonda (In Progress)'),
        ('completed', 'Tugallangan (Completed)'),
        ('abandoned', 'Tashlab ketilgan (Abandoned)'),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='mock_exams',
        verbose_name="O'quvchi"
    )
    exam_type = models.CharField(
        max_length=20,
        choices=EXAM_TYPE_CHOICES,
        default='ielts',
        verbose_name="Imtihon turi"
    )
    started_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Boshlangan vaqt"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Tugallangan vaqt"
    )
    total_duration_seconds = models.IntegerField(
        default=9000,
        verbose_name="Rejalashtirilgan jami vaqt (soniya)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_progress',
        verbose_name="Holat"
    )
    overall_band_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Umumiy ball (Band Score)"
    )
    ai_summary_feedback = models.TextField(
        blank=True,
        verbose_name="AI umumiy xulosasi"
    )

    class Meta:
        verbose_name = "Mock Imtihon"
        verbose_name_plural = "Mock Imtihonlar"
        ordering = ['-started_at']

    def __str__(self):
        score_str = f"Band {self.overall_band_score}" if self.overall_band_score is not None else "Jarayonda"
        return f"{self.get_exam_type_display()} — {self.student} ({score_str})"


class MockExamSection(models.Model):
    SECTION_TYPE_CHOICES = [
        ('listening', 'Listening (Eshitish)'),
        ('reading', 'Reading (O\'qish)'),
        ('writing', 'Writing (Insho va yozish)'),
        ('speaking', 'Speaking (Nutq)'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('in_progress', 'Jarayonda'),
        ('completed', 'Tugallangan'),
        ('skipped', 'O\'tkazib yuborilgan'),
    ]

    mock_exam = models.ForeignKey(
        MockExam,
        on_delete=models.CASCADE,
        related_name='sections',
        verbose_name="Mock Imtihon"
    )
    section_type = models.CharField(
        max_length=20,
        choices=SECTION_TYPE_CHOICES,
        verbose_name="Bo'lim turi"
    )
    order = models.PositiveIntegerField(
        default=1,
        verbose_name="Ketma-ketlik tartibi"
    )
    time_limit_seconds = models.IntegerField(
        default=3600,
        verbose_name="Vaqt chegarasi (soniya)"
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Boshlangan vaqt"
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Yakunlangan vaqt"
    )
    content = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Bo'lim savollari va matnlari (JSON)"
    )
    student_response = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="O'quvchi javoblari (JSON/Text)"
    )
    section_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Bo'lim bali (Band 0.0 - 9.0)"
    )
    ai_feedback = models.TextField(
        blank=True,
        verbose_name="AI tahlili va xatolar izohi"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Bo'lim holati"
    )

    class Meta:
        verbose_name = "Mock Imtihon Bo'limi"
        verbose_name_plural = "Mock Imtihon Bo'limlari"
        ordering = ['order']

    def __str__(self):
        return f"{self.mock_exam.get_exam_type_display()} - {self.get_section_type_display()} ({self.section_score or 'Kutilmoqda'})"
