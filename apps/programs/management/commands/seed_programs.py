"""
Django management command to seed verified study abroad programs.
Idempotent execution with required verified metadata.
"""
from datetime import date
from django.core.management.base import BaseCommand
from apps.programs.models import Program

PROGRAMS_SEED_DATA = [
    {
        "name": "Global UGRAD (AQSh Almashinuv Dasturi)",
        "country": "AQSH",
        "type": "exchange",
        "deadline": "Har yili dekabr oyi oxiri",
        "source_url": "https://uz.usembassy.gov/education-culture/exchange-programs/global-ugrad/",
        "last_verified_date": date(2026, 1, 15),
        "verified_by": "admin",
        "requirements": {
            "sinf_daraja": "Akademik litsey / maktab bitiruvchisi yoki universitet 1-2 bosqich talabalari (18 yoshdan)",
            "til_talabi": "TOEFL iBT 61+ yoki IELTS 6.0+",
            "akademik_baho": "A'lo baholar (GPA 3.0+)",
            "hujjatlar": ["Motivatsiya inshosi (Essay)", "2 ta tavsiyanoma", "Akademik baholar tabeli (Transkript)"],
            "qamrovi": "To'liq: Aviachipta, o'qish to'lovi, turar joy, oylik stipendiya va tibbiy sug'urta"
        }
    },
    {
        "name": "DAAD — Germaniya Akademik Almashinuv Xizmati",
        "country": "Germaniya",
        "type": "grant",
        "deadline": "Har yili oktyabr — noyabr oylari",
        "source_url": "https://www.daad.de/en/study-and-research-in-germany/scholarships/",
        "last_verified_date": date(2026, 1, 20),
        "verified_by": "admin",
        "requirements": {
            "sinf_daraja": "Bakalavriat va Magistratura bosqichlariga nomzodlar",
            "til_talabi": "IELTS 6.5+ yoki Nemis tili TestDaF (B2/C1 daraja)",
            "akademik_baho": "Yuqori o'zlashtirish ko'rsatkichi (GPA 3.2+)",
            "hujjatlar": ["Rezyume (CV / Europass)", "Motivatsiya xati", "Tavsiyanomalar", "Diplom yoki shahodatnoma"],
            "qamrovi": "To'liq: Oylik yashash stipendiyasi (€934-€1300), tibbiy sug'urta, safar xarajatlari"
        }
    },
    {
        "name": "Chevening — Buyuk Britaniya Hukumati Granti",
        "country": "Buyuk Britaniya",
        "type": "grant",
        "deadline": "Har yili noyabr oyi boshi",
        "source_url": "https://www.chevening.org/scholarship/uzbekistan/",
        "last_verified_date": date(2026, 1, 10),
        "verified_by": "admin",
        "requirements": {
            "sinf_daraja": "Magistratura bosqichi (Bakalavr darajasiga ega nomzodlar)",
            "ish_tajribasi": "Kamida 2 yillik (2800 soat) ish yoki jamoatchilik tajribasi",
            "til_talabi": "IELTS 6.5+ (har bir komponent kamida 5.5)",
            "hujjatlar": ["4 ta yetakchilik va maqsad inshosi", "2 ta professional tavsiyanoma", "Buyuk Britaniya universitetidan qabul xati"],
            "qamrovi": "To'liq: 100% o'qish to'lovi, oylik turar joy stipendiyasi, borish-kelish aviachiptalari"
        }
    },
    {
        "name": "Türkiye Bursları — Turkiya Hukumat Granti",
        "country": "Turkiya",
        "type": "grant",
        "deadline": "Har yili 10-yanvardan 20-fevralgacha",
        "source_url": "https://www.turkiyeburslari.gov.tr",
        "last_verified_date": date(2026, 2, 1),
        "verified_by": "admin",
        "requirements": {
            "sinf_daraja": "Bakalavriat uchun 11-sinf yoki litsey bitiruvchilari (21 yoshgacha)",
            "akademik_baho": "Bakalavr uchun kamida 70%, tibbiyot yo'nalishlari uchun 90%",
            "til_talabi": "Ingliz tili (IELTS) yoki 1 yillik bepul turk tili tayyorlov kursi (TÖMER)",
            "hujjatlar": ["Shahodatnoma / Baholar tabeli", "Motivatsiya xati", "Sertifikatlar va olimpiada diplomlari"],
            "qamrovi": "To'liq: Kontrakt to'lovi, bepul talabalar yotoqxonasi, oylik stipendiya, aviachipta, tibbiy sug'urta"
        }
    },
    {
        "name": "El-Yurt Umidi Jamg'armasi Stipendiyasi",
        "country": "Xalqaro",
        "type": "grant",
        "deadline": "Har yili may — iyun oylari",
        "source_url": "https://eyuf.uz",
        "last_verified_date": date(2026, 2, 10),
        "verified_by": "admin",
        "requirements": {
            "sinf_daraja": "Dunyoning Top-300 / Top-500 xalqaro reytingidagi universitetlariga qabul qilingan o'quvchi va talabalar",
            "til_talabi": "IELTS 6.5+ / TOEFL iBT 79+ yoki chet tili bilish milliy/xalqaro sertifikati",
            "hujjatlar": ["Top xorijiy universitetdan shartsiz qabul xati (Unconditional Offer)", "Ariza", "Transkript"],
            "qamrovi": "To'liq: Universitet kontrakt to'lovi, yashash, ovqatlanish, aviachiptalar va viza xarajatlari"
        }
    }
]


class Command(BaseCommand):
    help = "Tasdiqlangan xalqaro ta'lim va grant dasturlarini ma'lumotlar bazasiga yuklaydi (Idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help="Mavjud dasturlarni tozalab, qaytadan yuklash",
        )

    def handle(self, *args, **options):
        if options.get('clear'):
            count, _ = Program.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"{count} ta dastur o'chirildi."))

        created_count = 0
        updated_count = 0

        for prog_data in PROGRAMS_SEED_DATA:
            program, created = Program.objects.update_or_create(
                name=prog_data['name'],
                defaults=prog_data
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        total_programs = Program.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Muvaffaqiyatli yakunlandi: {created_count} ta yangi dastur yaratildi, "
                f"{updated_count} ta yangilandi. Jami tasdiqlangan dasturlar: {total_programs} ta."
            )
        )
