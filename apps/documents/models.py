from django.db import models
from apps.accounts.models import Student
from apps.programs.models import Program


class Document(models.Model):
    DOC_TYPE_CHOICES = [
        ('essay', 'Insho (SOP / Personal Statement)'),
        ('motivation_letter', 'Motivatsion xat (Motivation Letter)'),
        ('recommendation', 'Tavsiyanoma (Recommendation Letter)'),
        ('transcript', 'Baholar tabeli (Academic Transcript)'),
        ('certificate', 'Sertifikat (IELTS / SAT / Boshqa)'),
        ('other', 'Boshqa hujjat'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Qoralama (Draft)'),
        ('under_review', 'Tekshiruvda (AI Review)'),
        ('final', 'Tayyor (Final)'),
    ]

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name="O'quvchi"
    )
    doc_type = models.CharField(
        max_length=50,
        choices=DOC_TYPE_CHOICES,
        default='essay',
        verbose_name="Hujjat turi"
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Hujjat nomi"
    )
    linked_program = models.ForeignKey(
        Program,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_documents',
        verbose_name="Bog'langan dastur"
    )
    file = models.FileField(
        upload_to='documents/',
        null=True,
        blank=True,
        verbose_name="Fayl"
    )
    content = models.TextField(
        blank=True,
        verbose_name="Hujjat matni (Insho/Xat)"
    )
    version = models.IntegerField(
        default=1,
        verbose_name="Versiya"
    )
    ai_feedback = models.TextField(
        blank=True,
        verbose_name="AI tahlili va tavsiyalari"
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Holat"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Yangilangan vaqt"
    )

    class Meta:
        verbose_name = "Hujjat"
        verbose_name_plural = "Hujjatlar"
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} (v{self.version}) — {self.get_doc_type_display()}"
