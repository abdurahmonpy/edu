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
        ('portfolio', 'Portfolio (Art / Design / Architecture)'),
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


class PortfolioItem(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='portfolio_items',
        verbose_name="Portfolio"
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Asar/Loyiha nomi"
    )
    file = models.FileField(
        upload_to='portfolio_items/',
        verbose_name="Fayl (rasm/video/pdf)"
    )
    medium = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Muhit/Material (Medium)"
    )
    completion_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Tugatilgan sana"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Loyiha tavsifi"
    )
    ai_feedback = models.TextField(
        blank=True,
        verbose_name="AI tahlili va tavsiyalari"
    )

    class Meta:
        verbose_name = "Portfolio qismi"
        verbose_name_plural = "Portfolio qismlari"
    
    def __str__(self):
        return self.title
