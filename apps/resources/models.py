from django.db import models
from apps.programs.models import Program


class Resource(models.Model):
    CATEGORY_CHOICES = [
        # University Application Categories
        ('essay_writing', 'Insho va SOP yozish'),
        ('interview_prep', 'Intervyuga tayyorgarlik'),
        ('visa_process', 'Viza va elchixona jarayoni'),
        ('general_tips', 'Foydali maslahatlar va strategiyalar'),
        # IELTS & Exam Prep Categories
        ('ielts_reading', "IELTS: Reading strategiyalari"),
        ('ielts_writing', "IELTS: Writing (Task 1 & 2)"),
        ('ielts_listening', "IELTS: Listening ko'nikmalari"),
        ('ielts_speaking', "IELTS: Speaking (Part 1-3)"),
        ('grammar_vocab', "Grammatika va lug'at boyligi"),
        # Expanded Domains
        ('dtm_prep', "DTM tayyorgarligi va yo'nalish tanlash"),
        ('top_university_strategy', "TOP universitetlarga tayyorlash strategiyasi"),
        ('portfolio_prep', "Portfolio tayyorlash (Art/Design)"),
        ('europe_admissions', "Yevropa universitetlari (DAAD, Campus France, va boshqalar)"),
        ('east_asia_admissions', "Osiyo (Koreya, Yaponiya, Xitoy) universitetlari"),
    ]

    title = models.CharField(
        max_length=255,
        verbose_name="Qo'llanma sarlavhasi"
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='general_tips',
        verbose_name="Kategoriya"
    )
    summary = models.CharField(
        max_length=400,
        blank=True,
        verbose_name="Qisqacha mazmun"
    )
    content = models.TextField(
        verbose_name="To'liq matn / Qo'llanma"
    )
    related_programs = models.ManyToManyField(
        Program,
        blank=True,
        related_name='resources',
        verbose_name="Tegishli grant dasturlari"
    )
    related_resources = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        verbose_name="Tegishli resurslar (o'qish ketma-ketligi)"
    )
    author_name = models.CharField(
        max_length=100,
        default="Kelajak Ekspertlar Guruhi",
        verbose_name="Muallif / Ekspert"
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
        verbose_name = "Resurs / Qo'llanma"
        verbose_name_plural = "Resurslar kutubxonasi"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"
