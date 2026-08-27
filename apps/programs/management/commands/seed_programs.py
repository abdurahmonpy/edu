"""
Django management command to seed verified study abroad universities and scholarship programs.
Idempotent execution with verified metadata and official source URLs.
"""
from datetime import date
from django.core.management.base import BaseCommand
from apps.programs.models import University, Program

UNIVERSITIES_SEED_DATA = [
    {
        "name": "University of Toronto",
        "country": "Kanada",
        "city": "Toronto",
        "world_ranking": 21,
        "website_url": "https://www.utoronto.ca",
        "acceptance_rate": 43.0,
        "average_cost_usd": 45000,
        "description": "Kanadaning yetakchi tadqiqot universiteti, dunyoning eng nufuzli top oliygohlaridan biri."
    },
    {
        "name": "Technical University of Munich (TUM)",
        "country": "Germaniya",
        "city": "Myunxen",
        "world_ranking": 37,
        "website_url": "https://www.tum.de",
        "acceptance_rate": 28.0,
        "average_cost_usd": 1500,
        "description": "Germaniyadagi eng nufuzli texnika universiteti, muhandislik va axborot texnologiyalari markazi."
    },
    {
        "name": "KAIST (Korea Advanced Institute of Science and Technology)",
        "country": "Janubiy Koreya",
        "city": "Daejeon",
        "world_ranking": 56,
        "website_url": "https://www.kaist.ac.kr",
        "acceptance_rate": 15.0,
        "average_cost_usd": 8000,
        "description": "Osiyoning eng ilg'or texnologiya va sun'iy intellekt bo'yicha yetakchi ilmiy-tadqiqot universiteti."
    },
    {
        "name": "University of Oxford",
        "country": "Buyuk Britaniya",
        "city": "Oxford",
        "world_ranking": 3,
        "website_url": "https://www.ox.ac.uk",
        "acceptance_rate": 14.0,
        "average_cost_usd": 42000,
        "description": "Dunyoning eng qadimiy va eng nufuzli universitetlaridan biri, akademik yetakchilik cho'qqisi."
    },
    {
        "name": "Middle East Technical University (METU)",
        "country": "Turkiya",
        "city": "Anqara",
        "world_ranking": 336,
        "website_url": "https://www.metu.edu.tr",
        "acceptance_rate": 20.0,
        "average_cost_usd": 3000,
        "description": "Turkiyaning xalqaro miqyosdagi eng nufuzli davlat texnika universiteti."
    },
    {
        "name": "University of Tokyo",
        "country": "Yaponiya",
        "city": "Tokio",
        "world_ranking": 28,
        "website_url": "https://www.u-tokyo.ac.jp",
        "acceptance_rate": 34.0,
        "average_cost_usd": 5000,
        "description": "Yaponiyaning 1-raqamli milliy universiteti, yuqori texnologiyalar va fanlar bo'yicha global yetakchi."
    },
    {
        "name": "National University of Singapore (NUS)",
        "country": "Singapur",
        "city": "Singapur",
        "world_ranking": 8,
        "website_url": "https://www.nus.edu.sg",
        "acceptance_rate": 12.0,
        "average_cost_usd": 22000,
        "description": "Osiyo qit'asining eng yuqori reytingli global universiteti."
    },
    {
        "name": "Eötvös Loránd University (ELTE)",
        "country": "Vengriya",
        "city": "Budapesht",
        "world_ranking": 564,
        "website_url": "https://www.elte.hu",
        "acceptance_rate": 35.0,
        "average_cost_usd": 4000,
        "description": "Markaziy Yevropaning nufuzli qadimiy universiteti, Stipendium Hungaricum asosiy hamkori."
    },
    {
        "name": "Tsinghua University",
        "country": "Xitoy",
        "city": "Pekin",
        "world_ranking": 20,
        "website_url": "https://www.tsinghua.edu.cn",
        "acceptance_rate": 10.0,
        "average_cost_usd": 6000,
        "description": "Xitoyning yetakchi texnologiya, kompyuter fanlari va iqtisodiyot universiteti."
    },
    {
        "name": "KTH Royal Institute of Technology",
        "country": "Shvetsiya",
        "city": "Stokgolm",
        "world_ranking": 73,
        "website_url": "https://www.kth.se",
        "acceptance_rate": 32.0,
        "average_cost_usd": 16000,
        "description": "Skandinaviyaning eng ilg'or texnologiya va barqaror muhandislik universiteti."
    },
    {
        "name": "Constructor University (Jacobs University)",
        "country": "Germaniya",
        "city": "Bremen",
        "world_ranking": 450,
        "website_url": "https://constructor.university",
        "acceptance_rate": 40.0,
        "average_cost_usd": 20000,
        "description": "Xalqaro xususiy ingliziyzabon tadqiqot universiteti, IT va dasturlash yo'nalishlarida kuchli."
    },
    {
        "name": "INHA University in Tashkent",
        "country": "O'zbekiston",
        "city": "Toshkent",
        "world_ranking": 500,
        "website_url": "https://inha.uz",
        "acceptance_rate": 25.0,
        "average_cost_usd": 3500,
        "description": "Janubiy Koreya Inha Universiteti bilan hamkorlikdagi axborot texnologiyalari va logistika universiteti."
    }
]

PROGRAMS_SEED_DATA = [
    {
        "university_name": None,
        "name": "Global UGRAD (AQSh Almashinuv Dasturi)",
        "country": "AQSH",
        "type": "exchange",
        "field_of_study": "cs_it",
        "min_ielts": 6.0,
        "min_toefl": 61,
        "min_sat": None,
        "min_gpa": 3.0,
        "grant_coverage": "toliq_grant",
        "deadline": "Har yili dekabr oyi oxiri",
        "source_url": "https://uz.usembassy.gov/education-culture/exchange-programs/global-ugrad/",
        "last_verified_date": date(2026, 1, 15),
        "verified_by": "admin",
        "description": "AQSh universitetlarida 1 semestr davomida to'liq grant asosida tahsil olish va madaniy almashinuv dasturi.",
        "requirements": {
            "sinf_daraja": "Akademik litsey / maktab bitiruvchisi yoki universitet 1-2 bosqich talabalari (18 yoshdan)",
            "til_talabi": "TOEFL iBT 61+ yoki IELTS 6.0+",
            "akademik_baho": "A'lo baholar (GPA 3.0+)",
            "hujjatlar": ["Motivatsiya inshosi (Essay)", "2 ta tavsiyanoma", "Akademik baholar tabeli (Transkript)"],
            "qamrovi": "To'liq: Aviachipta, o'qish to'lovi, turar joy, oylik stipendiya va tibbiy sug'urta"
        }
    },
    {
        "university_name": "Technical University of Munich (TUM)",
        "name": "DAAD — Germaniya Akademik Almashinuv Xizmati Granti",
        "country": "Germaniya",
        "type": "grant",
        "field_of_study": "engineering",
        "min_ielts": 6.5,
        "min_toefl": 80,
        "min_sat": None,
        "min_gpa": 3.2,
        "grant_coverage": "toliq_grant",
        "deadline": "Har yili oktyabr — noyabr oylari",
        "source_url": "https://www.daad.de/en/study-and-research-in-germany/scholarships/",
        "last_verified_date": date(2026, 1, 20),
        "verified_by": "admin",
        "description": "Germaniya davlat universitetlarida bakalavr va magistratura bosqichlarida bepul ta'lim va oylik yashash stipendiyasi.",
        "requirements": {
            "sinf_daraja": "Bakalavriat va Magistratura bosqichlariga nomzodlar",
            "til_talabi": "IELTS 6.5+ yoki Nemis tili TestDaF (B2/C1 daraja)",
            "akademik_baho": "Yuqori o'zlashtirish ko'rsatkichi (GPA 3.2+)",
            "hujjatlar": ["Rezyume (CV / Europass)", "Motivatsiya xati", "Tavsiyanomalar", "Diplom yoki shahodatnoma"],
            "qamrovi": "To'liq: Oylik yashash stipendiyasi (€934-€1300), tibbiy sug'urta, safar xarajatlari"
        }
    },
    {
        "university_name": "University of Oxford",
        "name": "Chevening — Buyuk Britaniya Hukumati Granti",
        "country": "Buyuk Britaniya",
        "type": "grant",
        "field_of_study": "international_law",
        "min_ielts": 6.5,
        "min_toefl": 92,
        "min_sat": None,
        "min_gpa": 3.3,
        "grant_coverage": "toliq_grant",
        "deadline": "Har yili noyabr oyi boshi",
        "source_url": "https://www.chevening.org/scholarship/uzbekistan/",
        "last_verified_date": date(2026, 1, 10),
        "verified_by": "admin",
        "description": "Buyuk Britaniyaning istalgan nufuzli oliygohida 1 yillik magistratura bosqichini to'liq bepul o'qish imkoniyati.",
        "requirements": {
            "sinf_daraja": "Magistratura bosqichi (Bakalavr darajasiga ega nomzodlar)",
            "ish_tajribasi": "Kamida 2 yillik (2800 soat) ish yoki jamoatchilik tajribasi",
            "til_talabi": "IELTS 6.5+ (har bir komponent kamida 5.5)",
            "hujjatlar": ["4 ta yetakchilik va maqsad inshosi", "2 ta professional tavsiyanoma", "Buyuk Britaniya universitetidan qabul xati"],
            "qamrovi": "To'liq: 100% o'qish to'lovi, oylik turar joy stipendiyasi, borish-kelish aviachiptalari"
        }
    },
    {
        "university_name": "Middle East Technical University (METU)",
        "name": "Türkiye Bursları — Turkiya Hukumat Granti",
        "country": "Turkiya",
        "type": "grant",
        "field_of_study": "cs_it",
        "min_ielts": 6.0,
        "min_toefl": 75,
        "min_sat": 1200,
        "min_gpa": 3.0,
        "grant_coverage": "toliq_grant",
        "deadline": "Har yili 10-yanvardan 20-fevralgacha",
        "source_url": "https://www.turkiyeburslari.gov.tr",
        "last_verified_date": date(2026, 2, 1),
        "verified_by": "admin",
        "description": "Turkiya nufuzli davlat universitetlarida bakalavr, magistratura va doktorantura uchun to'liq stipendiyali dastur.",
        "requirements": {
            "sinf_daraja": "Bakalavriat uchun 11-sinf yoki litsey bitiruvchilari (21 yoshgacha)",
            "akademik_baho": "Bakalavr uchun kamida 70%, tibbiyot yo'nalishlari uchun 90%",
            "til_talabi": "Ingliz tili (IELTS) yoki 1 yillik bepul turk tili tayyorlov kursi (TÖMER)",
            "hujjatlar": ["Shahodatnoma / Baholar tabeli", "Motivatsiya xati", "Sertifikatlar va olimpiada diplomlari"],
            "qamrovi": "To'liq: Kontrakt to'lovi, bepul talabalar yotoqxonasi, oylik stipendiya, aviachipta, tibbiy sug'urta"
        }
    },
    {
        "university_name": "KAIST (Korea Advanced Institute of Science and Technology)",
        "name": "GKS & KAIST Undergraduate International Scholarship",
        "country": "Janubiy Koreya",
        "type": "grant",
        "field_of_study": "ai_ds",
        "min_ielts": 6.5,
        "min_toefl": 83,
        "min_sat": 1350,
        "min_gpa": 3.4,
        "grant_coverage": "toliq_grant",
        "deadline": "Har yili oktyabr — noyabr (Bahorgi semestr) / may (Kuzgi)",
        "source_url": "https://www.studyinkorea.go.kr",
        "last_verified_date": date(2026, 2, 5),
        "verified_by": "admin",
        "description": "Janubiy Koreyaning KAIST va boshqa top universitetlarida IT, AI va muhandislik bo'yicha to'liq grantli bakalavr ta'limi.",
        "requirements": {
            "sinf_daraja": "11-sinf yoki litsey/kollej bitiruvchilari",
            "til_talabi": "IELTS 6.5+ yoki TOEFL iBT 83+",
            "akademik_baho": "A'lo baholar (GPA 3.4+ yoki yuqori 10% reyting)",
            "hujjatlar": ["1 ta tavsiyanoma xati", "Insho va rezyume", "Matematika/Fan sertifikatlari (SAT, olimpiada)"],
            "qamrovi": "To'liq kontrakt, oylik 350,000 KRW yashash puli, tibbiy sug'urta"
        }
    },
    {
        "university_name": None,
        "name": "El-Yurt Umidi Jamg'armasi Xalqaro Stipendiyasi",
        "country": "Xalqaro",
        "type": "grant",
        "field_of_study": "cs_it",
        "min_ielts": 6.5,
        "min_toefl": 79,
        "min_sat": 1300,
        "min_gpa": 3.5,
        "grant_coverage": "toliq_grant",
        "deadline": "Har yili may — iyun oylari",
        "source_url": "https://eyuf.uz",
        "last_verified_date": date(2026, 2, 10),
        "verified_by": "admin",
        "description": "O'zbekiston yoshlariga dunyoning Top-300 / Top-500 xalqaro universitetlarida bakalavr va magistraturada to'liq davlat granti.",
        "requirements": {
            "sinf_daraja": "Dunyoning Top-300 / Top-500 xalqaro reytingidagi universitetlariga qabul qilingan o'quvchi va talabalar",
            "til_talabi": "IELTS 6.5+ / TOEFL iBT 79+ yoki chet tili bilish milliy/xalqaro sertifikati",
            "hujjatlar": ["Top xorijiy universitetdan shartsiz qabul xati (Unconditional Offer)", "Ariza", "Transkript"],
            "qamrovi": "To'liq: Universitet kontrakt to'lovi, yashash, ovqatlanish, aviachiptalar va viza xarajatlari"
        }
    },
    {
        "university_name": "University of Toronto",
        "name": "Lester B. Pearson International Scholarship — University of Toronto",
        "country": "Kanada",
        "type": "grant",
        "field_of_study": "cs_it",
        "min_ielts": 7.0,
        "min_toefl": 100,
        "min_sat": 1450,
        "min_gpa": 3.8,
        "grant_coverage": "toliq_grant",
        "deadline": "Har yili noyabr oyi (Maktab nominatsiyasi) / yanvar (Ariza)",
        "source_url": "https://future.utoronto.ca/pearson/",
        "last_verified_date": date(2026, 1, 25),
        "verified_by": "admin",
        "description": "Kanadadagi eng nufuzli to'liq bakalavr granti. Akademik yetakchilik va ijodkorlikni rag'batlantiradi.",
        "requirements": {
            "sinf_daraja": "11-sinf bitiruvchisi (Maktab ma'muriyati tavsiyasi talab etiladi)",
            "til_talabi": "IELTS 7.0+ (har bir bo'lim 6.5+) yoki TOEFL 100+",
            "akademik_baho": "A'lo baholar (GPA 3.8+ / Top 5%)",
            "hujjatlar": ["Maktab nominatsiya xati", "Pearson Essay", "Faoliyatlar ro'yxati (Extracurriculars)"],
            "qamrovi": "4 yillik to'liq o'qish to'lovi, kitoblar, turar joy va yashash to'liq qoplanadi"
        }
    },
    {
        "university_name": "University of Tokyo",
        "name": "MEXT — Yaponiya Hukumati Davlat Granti (Monbukagakusho)",
        "country": "Yaponiya",
        "type": "grant",
        "field_of_study": "engineering",
        "min_ielts": 6.5,
        "min_toefl": 80,
        "min_sat": None,
        "min_gpa": 3.3,
        "grant_coverage": "toliq_grant",
        "deadline": "Har yili may — iyun oylari (Elchixona orqali tanlov)",
        "source_url": "https://www.uz.emb-japan.go.jp/itpr_ru/mext_scholarship.html",
        "last_verified_date": date(2026, 1, 30),
        "verified_by": "admin",
        "description": "Yaponiya milliy universitetlarida bepul 4-5 yillik bakalavr ta'limi va oylik stipendiya.",
        "requirements": {
            "sinf_daraja": "17-25 yosh oralig'idagi maktab/litsey bitiruvchilari",
            "til_talabi": "Ingliz tili (IELTS 6.0+) yoki Yapon tili (JLPT N2-N1)",
            "akademik_baho": "Matematika va fizika/kimyo fanlaridan a'lo baholar",
            "hujjatlar": ["Tavsiyanomalar", "Sog'liqni saqlash ma'lumotnomasi", "Yozma imtihon (Matematika/Ingliz tili)"],
            "qamrovi": "100% kontrakt to'lovi, 1 yillik yapon tili kursi, oylik 120,000 JPY stipendiya, aviachipta"
        }
    },
    {
        "university_name": "Eötvös Loránd University (ELTE)",
        "name": "Stipendium Hungaricum — Vengriya Hukumat Granti",
        "country": "Vengriya",
        "type": "grant",
        "field_of_study": "business_finance",
        "min_ielts": 5.5,
        "min_toefl": 70,
        "min_sat": None,
        "min_gpa": 2.8,
        "grant_coverage": "toliq_grant",
        "deadline": "Har yili 15-yanvargacha",
        "source_url": "https://stipendiumhungaricum.hu",
        "last_verified_date": date(2026, 2, 3),
        "verified_by": "admin",
        "description": "Yevropa Ittifoqining nufuzli Vengriya oliygohlarida to'liq bepul ingliz tilida bakalavr va magistratura ta'limi.",
        "requirements": {
            "sinf_daraja": "11-sinf / litsey bitiruvchilari va talabalar",
            "til_talabi": "IELTS 5.5+ yoki B2 sertifikat",
            "akademik_baho": "GPA 2.8+",
            "hujjatlar": ["Motivatsiya xati", "Baholar transkripti", "Tibbiy ma'lumotnoma"],
            "qamrovi": "100% o'qish to'lovi, bepul yotoqxona, oylik stipendiya va tibbiy sug'urta"
        }
    },
    {
        "university_name": "Tsinghua University",
        "name": "Chinese Government Scholarship (CSC) — Tsinghua & Peking",
        "country": "Xitoy",
        "type": "grant",
        "field_of_study": "ai_ds",
        "min_ielts": 6.5,
        "min_toefl": 85,
        "min_sat": None,
        "min_gpa": 3.3,
        "grant_coverage": "toliq_grant",
        "deadline": "Har yili dekabr — mart oylari",
        "source_url": "https://www.campuschina.org",
        "last_verified_date": date(2026, 1, 18),
        "verified_by": "admin",
        "description": "Xitoyning jahon reytingidagi Top-20 universitetlarida ingliz yoki xitoy tilida to'liq grantli ta'lim.",
        "requirements": {
            "sinf_daraja": "Maktab yoki litsey bitiruvchilari (25 yoshgacha)",
            "til_talabi": "IELTS 6.5+ yoki HSK 4-5 daraja",
            "akademik_baho": "GPA 3.3+",
            "hujjatlar": ["2 ta professor tavsiyanomasi", "O'qish rejasi (Study Plan)", "Notarial tasdiqlangan hujjatlar"],
            "qamrovi": "Kontrakt to'lovi, bepul universitet kampusi turar joyi, oylik 2,500-3,500 RMB stipendiya"
        }
    },
    {
        "university_name": "National University of Singapore (NUS)",
        "name": "NUS & NTU ASEAN / International Undergraduate Scholarship",
        "country": "Singapur",
        "type": "grant",
        "field_of_study": "cs_it",
        "min_ielts": 7.0,
        "min_toefl": 100,
        "min_sat": 1450,
        "min_gpa": 3.8,
        "grant_coverage": "toliq_grant",
        "deadline": "Har yili fevral oyi oxiri",
        "source_url": "https://nus.edu.sg/oam/scholarships/community/asean-undergraduate-scholarship",
        "last_verified_date": date(2026, 2, 8),
        "verified_by": "admin",
        "description": "Osiyoning eng yetakchi universiteti NUS da Kompyuter fanlari va sun'iy intellekt bo'yicha to'liq grant.",
        "requirements": {
            "sinf_daraja": "11-sinf yoki litsey bitiruvchilari",
            "til_talabi": "IELTS 7.0+ yoki TOEFL 100+",
            "akademik_baho": "Oliy akademik o'zlashtirish (SAT 1450+ yoki a'lo baholar)",
            "hujjatlar": ["Akademik yutuqlar portfoliosi", "Insholar", "Suhbat (Interview)"],
            "qamrovi": "To'liq kontrakt, yillik 5,800 SGD yashash stipendiyasi, turar joy ta'minoti"
        }
    },
    {
        "university_name": "KTH Royal Institute of Technology",
        "name": "Swedish Institute Scholarships for Global Professionals (SISGP)",
        "country": "Shvetsiya",
        "type": "grant",
        "field_of_study": "engineering",
        "min_ielts": 6.5,
        "min_toefl": 90,
        "min_sat": None,
        "min_gpa": 3.2,
        "grant_coverage": "toliq_grant",
        "deadline": "Har yili fevral oyi o'rtasi",
        "source_url": "https://si.se/en/apply/scholarships/swedish-institute-scholarships-for-global-professionals/",
        "last_verified_date": date(2026, 1, 28),
        "verified_by": "admin",
        "description": "Shvetsiyaning nufuzli oliygohlarida magistratura va ilg'or texnologiya sohalari uchun 100% grant.",
        "requirements": {
            "sinf_daraja": "Bakalavr bitiruvchilari",
            "til_talabi": "IELTS 6.5+ yoki TOEFL 90+",
            "ish_tajribasi": "Kamida 3000 soatlik ish/amaliyot tajribasi",
            "hujjatlar": ["Yetakchilik isboti (Leadership proof)", "2 ta tavsiyanoma", "Shvetsiya universitetiga qabul"],
            "qamrovi": "100% kontrakt, oylik 12,000 SEK yashash nafaqasi, aviachipta va sug'urta"
        }
    },
    {
        "university_name": "Constructor University (Jacobs University)",
        "name": "Constructor University Merit Scholarship & Tuition Reduction",
        "country": "Germaniya",
        "type": "partial_grant",
        "field_of_study": "cs_it",
        "min_ielts": 6.5,
        "min_toefl": 85,
        "min_sat": 1250,
        "min_gpa": 3.0,
        "grant_coverage": "qisman_grant",
        "deadline": "Har yili 1-iyungacha (Rolling admissions)",
        "source_url": "https://constructor.university/admission-aid/financial-aid",
        "last_verified_date": date(2026, 2, 12),
        "verified_by": "admin",
        "description": "Bremendagi Constructor xalqaro universitetida IT va Robototexnika yo'nalishlarida 50-75% gacha grant chegirmalari.",
        "requirements": {
            "sinf_daraja": "11-sinf / litsey bitiruvchilari",
            "til_talabi": "IELTS 6.5+ yoki Duolingo 110+",
            "akademik_baho": "GPA 3.0+ yoki SAT 1250+",
            "hujjatlar": ["Common App orqali ariza", "Motivatsiya inshosi", "1 ta o'qituvchi tavsiyanomasi"],
            "qamrovi": "Kontrakt to'lovidan 50% dan 75% gacha akademik chegirma (Merit scholarship)"
        }
    },
    {
        "university_name": "INHA University in Tashkent",
        "name": "INHA University Tashkent & Incheon Global Scholarship",
        "country": "O'zbekiston",
        "type": "grant",
        "field_of_study": "cs_it",
        "min_ielts": 5.5,
        "min_toefl": 71,
        "min_sat": None,
        "min_gpa": 3.0,
        "grant_coverage": "toliq_grant",
        "deadline": "Har yili iyul — avgust oylari",
        "source_url": "https://inha.uz",
        "last_verified_date": date(2026, 2, 14),
        "verified_by": "admin",
        "description": "Toshkentdagi Inha universitetida CSE (Dasturiy injiniring) va SOL (Logistika) bo'yicha to'liq davlat va homiylik grantlari.",
        "requirements": {
            "sinf_daraja": "11-sinf yoki litsey bitiruvchilari",
            "til_talabi": "IELTS 5.5+ yoki TOEFL 71+",
            "akademik_baho": "Matematika va fizika fanlaridan kirish imtihoni natijalari",
            "hujjatlar": ["Shahodatnoma / Diplom", "Pasport", "IELTS sertifikati"],
            "qamrovi": "To'liq 100% 4 yillik kontrakt to'lovi (Eng yuqori ball to'plagan talabalar uchun)"
        }
    }
]


class Command(BaseCommand):
    help = "Tasdiqlangan xalqaro universitetlar va ta'lim/grant dasturlarini ma'lumotlar bazasiga yuklaydi (Idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help="Mavjud dasturlar va universitetlarni tozalab, qaytadan yuklash",
        )

    def handle(self, *args, **options):
        if options.get('clear'):
            p_count, _ = Program.objects.all().delete()
            u_count, _ = University.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"{p_count} ta dastur va {u_count} ta universitet o'chirildi."))

        # 1. Seed Universities
        universities_map = {}
        u_created_count = 0
        u_updated_count = 0

        for u_data in UNIVERSITIES_SEED_DATA:
            name = u_data['name']
            uni, created = University.objects.update_or_create(
                name=name,
                defaults=u_data
            )
            universities_map[name] = uni
            if created:
                u_created_count += 1
            else:
                u_updated_count += 1

        # 2. Seed Programs
        p_created_count = 0
        p_updated_count = 0

        for prog_data in PROGRAMS_SEED_DATA:
            data = prog_data.copy()
            uni_name = data.pop('university_name', None)
            if uni_name and uni_name in universities_map:
                data['university'] = universities_map[uni_name]
            else:
                data['university'] = None

            program, created = Program.objects.update_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                p_created_count += 1
            else:
                p_updated_count += 1

        total_universities = University.objects.count()
        total_programs = Program.objects.count()

        self.stdout.write(
            self.style.SUCCESS(
                f"Muvaffaqiyatli yakunlandi:\n"
                f"  - Universitetlar: {u_created_count} yangi, {u_updated_count} yangilandi (Jami: {total_universities})\n"
                f"  - Dasturlar: {p_created_count} yangi, {p_updated_count} yangilandi (Jami: {total_programs})"
            )
        )

