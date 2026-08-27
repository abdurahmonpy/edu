"""
Models for verified study abroad and scholarship programs catalog.
"""
from django.db import models
from django.core.exceptions import ValidationError

class University(models.Model):
    """
    Higher education institutions worldwide offering undergraduate and graduate programs.
    """
    name = models.CharField(
        max_length=255,
        verbose_name="Universitet nomi"
    )
    country = models.CharField(
        max_length=100,
        verbose_name="Davlat"
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="Shahar"
    )
    world_ranking = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Jahon reytingi (QS/THE)"
    )
    website_url = models.URLField(
        max_length=500,
        blank=True,
        default='',
        verbose_name="Rasmiy vebsayt"
    )
    acceptance_rate = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Qabul foizi (%)"
    )
    average_cost_usd = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="O'rtacha yillik xarajat ($)"
    )
    description = models.TextField(
        blank=True,
        default='',
        verbose_name="Universitet haqida"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Qo'shilgan vaqt"
    )

    class Meta:
        verbose_name = "Universitet"
        verbose_name_plural = "Universitetlar"
        ordering = ['world_ranking', 'name']

    def __str__(self):
        rank_str = f" (#{self.world_ranking})" if self.world_ranking else ""
        return f"{self.name} ({self.country}){rank_str}"


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

    university = models.ForeignKey(
        University,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='programs',
        verbose_name="Universitet"
    )
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
    field_of_study = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name="Yo'nalish sohasi"
    )
    min_ielts = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Minimal IELTS bali"
    )
    min_toefl = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Minimal TOEFL iBT bali"
    )
    min_sat = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Minimal SAT bali"
    )
    min_gpa = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Minimal GPA (4.0 shkala)"
    )
    grant_coverage = models.CharField(
        max_length=100,
        blank=True,
        default='toliq_grant',
        verbose_name="Grant qamrovi"
    )
    description = models.TextField(
        blank=True,
        default='',
        verbose_name="Dastur tavsifi"
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


class StudentTargetSelection(models.Model):
    """
    Stores student's selected primary target program and backup university options.
    """
    student = models.OneToOneField(
        'accounts.Student',
        on_delete=models.CASCADE,
        related_name='target_selection',
        verbose_name="O'quvchi"
    )
    primary_program = models.ForeignKey(
        'programs.Program',
        on_delete=models.CASCADE,
        related_name='primary_target_students',
        verbose_name="Asosiy maqsad dastur"
    )
    backup_programs = models.ManyToManyField(
        'programs.Program',
        blank=True,
        related_name='backup_target_students',
        verbose_name="Zaxira dasturlar"
    )
    backup_programs_data = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Zaxira dasturlar ro'yxati (JSON)"
    )
    match_score = models.IntegerField(
        default=0,
        verbose_name="Moslik ko'rsatkichi (%)"
    )
    selected_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Tanlangan vaqt"
    )
    notes = models.TextField(
        blank=True,
        default='',
        verbose_name="O'quvchi izohi"
    )

    class Meta:
        verbose_name = "O'quvchining maqsadli tanlovi"
        verbose_name_plural = "O'quvchilarning maqsadli tanlovlari"
        ordering = ['-selected_at']

    def __str__(self):
        student_name = self.student.user.first_name if self.student and self.student.user else "O'quvchi"
        return f"{student_name} — Asosiy: {self.primary_program.name}"


