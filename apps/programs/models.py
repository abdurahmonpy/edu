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
    image_url = models.URLField(
        max_length=500,
        blank=True,
        default='',
        verbose_name="Universitet rasmi (Campus Photo)"
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
        ('application_system', "Qabul tizimi / Portal"),
    ]

    SCOPE_CHOICES = [
        ('international', "Xalqaro"),
        ('domestic', "O'zbekiston ichida"),
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
    scope = models.CharField(
        max_length=20,
        choices=SCOPE_CHOICES,
        default='international',
        verbose_name="Dastur miqyosi"
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
    image_url = models.URLField(
        max_length=500,
        blank=True,
        default='',
        verbose_name="Dastur muqova rasmi (Cover Photo)"
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

    @property
    def cover_image(self):
        """Returns the cover image URL with fallback to high-quality curated campus photography."""
        return self.get_cover_image()

    def get_cover_image(self):
        if self.image_url and self.image_url.strip():
            return self.image_url.strip()
        if self.university and hasattr(self.university, 'image_url') and self.university.image_url and self.university.image_url.strip():
            return self.university.image_url.strip()
        return self._resolve_fallback_image()

    def _resolve_fallback_image(self):
        name_lower = (self.name or '').lower()
        uni_name = (self.university.name.lower() if self.university else '')
        country_lower = (self.country or '').lower()

        # 1. Iconic world scholarship programs
        if 'chevening' in name_lower:
            return "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?q=80&w=800&auto=format&fit=crop"
        if 'daad' in name_lower:
            return "https://images.unsplash.com/photo-1562774053-701939374585?q=80&w=800&auto=format&fit=crop"
        if 'ugrad' in name_lower:
            return "https://images.unsplash.com/photo-1541339907198-e08756dedf3f?q=80&w=800&auto=format&fit=crop"
        if 'turkiya' in name_lower or 'turkiye' in name_lower or 'burslari' in name_lower:
            return "https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?q=80&w=800&auto=format&fit=crop"
        if 'gks' in name_lower or 'koreya' in country_lower or 'korea' in country_lower or 'seoul' in uni_name:
            return "https://images.unsplash.com/photo-1538485399081-7191377e8241?q=80&w=800&auto=format&fit=crop"
        if 'mext' in name_lower or 'yaponiya' in country_lower or 'japan' in country_lower or 'tokyo' in uni_name:
            return "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?q=80&w=800&auto=format&fit=crop"
        if 'stipendium' in name_lower or 'vengriya' in country_lower or 'hungary' in country_lower:
            return "https://images.unsplash.com/photo-1549877452-9c387954fbc2?q=80&w=800&auto=format&fit=crop"

        # 2. Specific elite universities
        if 'oxford' in uni_name or 'cambridge' in uni_name or 'imperial' in uni_name:
            return "https://images.unsplash.com/photo-1544717305-2782549b5136?q=80&w=800&auto=format&fit=crop"
        if any(w in uni_name for w in ['harvard', 'mit', 'columbia', 'stanford', 'princeton', 'yale']):
            return "https://images.unsplash.com/photo-1498243691581-b145c3f54a5a?q=80&w=800&auto=format&fit=crop"
        if any(w in uni_name for w in ['toronto', 'mcgill', 'ubc', 'waterloo']):
            return "https://images.unsplash.com/photo-1564981797816-1043664bf78d?q=80&w=800&auto=format&fit=crop"
        if any(w in uni_name for w in ['melbourne', 'sydney', 'anu', 'queensland']):
            return "https://images.unsplash.com/photo-1519452635265-7b1fbfd1e4e0?q=80&w=800&auto=format&fit=crop"
        if any(w in uni_name for w in ['amsterdam', 'delft', 'erasmus', 'leiden']):
            return "https://images.unsplash.com/photo-1512470876302-972faa2aa9a4?q=80&w=800&auto=format&fit=crop"

        # 3. Country-specific verified campus photography
        if "o'zbekiston" in country_lower or "uzbekistan" in country_lower:
            return "https://images.unsplash.com/photo-1523240795612-9a054b0db644?q=80&w=800&auto=format&fit=crop"
        if 'buyuk britaniya' in country_lower or 'uk' in country_lower:
            return "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?q=80&w=800&auto=format&fit=crop"
        if 'germaniya' in country_lower or 'germany' in country_lower:
            return "https://images.unsplash.com/photo-1467269204594-9661b134dd2b?q=80&w=800&auto=format&fit=crop"
        if 'aqsh' in country_lower or 'usa' in country_lower:
            return "https://images.unsplash.com/photo-1541339907198-e08756dedf3f?q=80&w=800&auto=format&fit=crop"
        if 'turkiya' in country_lower or 'turkey' in country_lower:
            return "https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?q=80&w=800&auto=format&fit=crop"
        if 'kanada' in country_lower or 'canada' in country_lower:
            return "https://images.unsplash.com/photo-1564981797816-1043664bf78d?q=80&w=800&auto=format&fit=crop"
        if 'avstraliya' in country_lower or 'australia' in country_lower:
            return "https://images.unsplash.com/photo-1519452635265-7b1fbfd1e4e0?q=80&w=800&auto=format&fit=crop"
        if 'shveytsariya' in country_lower or 'switzerland' in country_lower:
            return "https://images.unsplash.com/photo-1530122037265-a5f1f91d3b99?q=80&w=800&auto=format&fit=crop"
        if 'fransiya' in country_lower or 'france' in country_lower:
            return "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?q=80&w=800&auto=format&fit=crop"
        if 'xitoy' in country_lower or 'china' in country_lower:
            return "https://images.unsplash.com/photo-1508804185872-d7badad00f7d?q=80&w=800&auto=format&fit=crop"
        if 'italiya' in country_lower or 'italy' in country_lower:
            return "https://images.unsplash.com/photo-1516483638261-f4dbaf036963?q=80&w=800&auto=format&fit=crop"
        if 'singapur' in country_lower or 'singapore' in country_lower:
            return "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?q=80&w=800&auto=format&fit=crop"
        if 'baa' in country_lower or 'uae' in country_lower or 'dubai' in uni_name:
            return "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?q=80&w=800&auto=format&fit=crop"

        return "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?q=80&w=800&auto=format&fit=crop"

    @property
    def country_code(self):
        """Returns 2-letter country code for vector flag rendering."""
        c = (self.country or '').strip().lower()
        codes = {
            'buyuk britaniya': 'gb',
            'aqsh': 'us',
            'germaniya': 'de',
            'turkiya': 'tr',
            'janubiy koreya': 'kr',
            'koreya': 'kr',
            'yaponiya': 'jp',
            'japan': 'jp',
            "o'zbekiston": 'uz',
            'uzbekistan': 'uz',
            'kanada': 'ca',
            'avstraliya': 'au',
            'niderlandiya': 'nl',
            'fransiya': 'fr',
            'france': 'fr',
            'xitoy': 'cn',
            'italiya': 'it',
            'shveytsariya': 'ch',
            'shvetsiya': 'se',
            'vengriya': 'hu',
            'singapur': 'sg',
            'baa': 'ae',
            'saudiya arabistoni': 'sa',
            'belgiya': 'be',
            'gonkong': 'hk',
            'yangi zelandiya': 'nz',
            'finlyandiya': 'fi',
            'qatar': 'qa',
            'malayziya': 'my',
            'polsha': 'pl',
            'avstriya': 'at',
            'ispaniya': 'es',
        }
        for k, v in codes.items():
            if k in c:
                return v
        return 'world'

    @property
    def country_flag(self):
        """Returns real vector SVG flag HTML instead of emoji."""
        from django.utils.safestring import mark_safe
        code = self.country_code
        c_name = self.country or ""
        return mark_safe(f'<img src="/static/images/flags/{code}.svg" class="w-4 h-3 inline-block rounded-[2px] object-cover shadow-sm align-middle" alt="{c_name}">')

    @property
    def parsed_details(self):
        """
        Parses requirements and database fields into a structured, elegant dictionary
        ready for template rendering without raw JSON syntax.
        """
        reqs = self.requirements or {}

        # 1. Degree level
        degree = reqs.get('sinf_daraja', '')
        if not degree:
            if 'magistr' in self.name.lower():
                degree = "Magistratura bosqichi"
            elif any(w in self.name.lower() for w in ['bakalavr', 'bachelor', 'bsc', 'b.tech', 'undergraduate']):
                degree = "Bakalavriat bosqichi"
            elif self.type == 'exchange':
                degree = "Talabalar almashinuvi"
            else:
                degree = "Bakalavriat va Magistratura"

        # 2. Language Requirement
        lang = reqs.get('til_talabi', '')
        if not lang:
            if self.min_ielts:
                lang = f"IELTS {self.min_ielts}+"
            elif reqs.get('IELTS'):
                lang = f"IELTS {reqs.get('IELTS')}+"
            elif reqs.get('TOPIK'):
                lang = f"TOPIK {reqs.get('TOPIK')}"
            else:
                lang = "IELTS 6.0+ yoki ekvivalent"

        # 3. Grant Coverage
        cov = reqs.get('qamrovi', '')
        if not cov:
            if self.type == 'grant' or self.grant_coverage == 'toliq_grant':
                cov = "To'liq 100% grant: Kontrakt to'lovi, turar joy va oylik stipendiya"
            elif self.type == 'partial_grant' or self.grant_coverage == 'qisman_grant':
                cov = "Qisman grant: 50% dan 100% gacha kontrakt to'lovi chegirmasi"
            elif self.type == 'exchange':
                cov = "To'liq qoplanadi: Aviachipta, o'qish to'lovi va turar joy"
            else:
                cov = "To'lovli dastur / Universitet ichki grantlari mavjud"

        # 4. Clean documents list
        raw_docs = reqs.get('hujjatlar', [])
        clean_docs = []
        if isinstance(raw_docs, str):
            import ast
            try:
                raw_docs = ast.literal_eval(raw_docs)
            except Exception:
                raw_docs = [raw_docs]
        if isinstance(raw_docs, list):
            for d in raw_docs:
                clean_d = str(d).strip().strip("[]'\"")
                if clean_d:
                    clean_docs.append(clean_d)

        # 5. Experience
        experience = reqs.get('ish_tajribasi', '')

        # 6. GPA
        gpa = reqs.get('akademik_baho', '')
        if not gpa and self.min_gpa:
            gpa = f"GPA {self.min_gpa}+"

        # 7. SAT
        sat = ''
        if self.min_sat:
            sat = f"SAT {self.min_sat}+"

        return {
            'degree': degree,
            'language': lang,
            'coverage': cov,
            'documents': clean_docs,
            'experience': experience,
            'gpa': gpa,
            'sat': sat,
        }

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
    Through model linking Student and Program for application status tracking and bookmarking.
    """
    STATUS_CHOICES = [
        ('tracking', "Kuzatilmoqda"),           # default, current behavior
        ('preparing', "Hujjatlar tayyorlanmoqda"),
        ('submitted', "Ariza topshirildi"),
        ('interview', "Suhbatga taklif qilindi"),
        ('accepted', "Qabul qilindi"),
        ('rejected', "Rad etildi"),
        ('waitlisted', "Kutish ro'yxatida"),
        ('withdrawn', "Bekor qilindi"),
    ]

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
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='tracking',
        verbose_name="Holat"
    )
    status_updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Holat yangilangan vaqt"
    )
    submitted_at = models.DateField(
        null=True,
        blank=True,
        verbose_name="Topshirilgan sana"
    )
    decision_at = models.DateField(
        null=True,
        blank=True,
        verbose_name="Qaror sanasi"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Shaxsiy izohlar"
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
        verbose_name = "Kuzatilayotgan dastur / Ariza holati"
        verbose_name_plural = "Kuzatilayotgan dasturlar / Arizalar"
        unique_together = ('student', 'program')
        ordering = ['-status_updated_at']

    def __str__(self):
        return f"{self.student} — {self.program.name} ({self.get_status_display()})"


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


