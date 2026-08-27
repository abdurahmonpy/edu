"""
Seed command populating verified, expert guides for high school scholarship applicants.
"""
from django.core.management.base import BaseCommand
from apps.resources.models import Resource
from apps.programs.models import Program

class Command(BaseCommand):
    help = "Seed verified study abroad and scholarship guides into Resource library."

    def handle(self, *args, **options):
        guides = [
            {
                "title": "Grant Inshosi (Statement of Purpose / Motivation Letter) Yozish Bo'yicha To'liq Qo'llanma",
                "category": "essay_writing",
                "summary": "Global UGRAD, DAAD va xalqaro universitetlar uchun qabul komissiyasini lol qoldiruvchi insho tuzilmasi, STAR metodi va uchraydigan 5 ta asosiy xato.",
                "content": """### 1. Insho Nima Uchun Eng Muhim Hujjat?

Xalqaro grantlarda qabul komissiyasi minglab arizachilarning baholarini ko'radi. Ammo faqat insho orqali sizning shaxsiyatingiz, qiyinchiliklarni yengish mahoratingiz va kelajakdagi yetakchilik salohiyatingiz namoyon bo'ladi.

---

### 2. Standart Insho Tuzilmasi (4 Qismli Formula):

1. **Kirish (Hook & Passion):** 
   - Birinchi jumlada o'z sohangizga bo'lgan qiziqishingiz qanday boshlanganini real hayotiy voqea orqali tasvirlang.
   - *"Men bolaligimdan kompyuterga qiziqardim"* kabi shablon so'zlardan qoching.
2. **Akademik va Amaliy Tajriba (STAR Metodi):**
   - **Situation (Vaziyat):** Qanday muammoga duch kelgansiz?
   - **Task (Vazifa):** Sizning oldingizda qanday maqsad turgan edi?
   - **Action (Harakat):** Qanday aniq chora ko'rdingiz (tashabbus, loyiha, tadqiqot)?
   - **Result (Natija):** Qanday o'lchanadigan natijaga erishdingiz?
3. **Nima Uchun Aynan Shu Dastur / Universitet?**
   - Tanlagan dasturingizning aniq professorlari, laboratoriyalari yoki almashinuv imkoniyatlarini tilga oling.
4. **Kelajak Rejalari va Vatan taraqqiyotiga hissa:**
   - O'qishni tamomlab O'zbekistonga qaytgach, qaysi sohada qanday loyihalarni amalga oshirmoqchisiz?

---

### 3. Eng Ko'p Uchraydigan 5 Ta Xato:
- ❌ Baholarni va diplomlarni shunchaki sanab o'tish (buning uchun rezyume bor).
- ❌ Grammatik xatolarga beparvolik qilish.
- ❌ Haddan tashqari umumlashgan gaplar yozish.
- ❌ Boshqa birovning inshosini ko'chirish yoki AI matnini tahrirsiz qoldirish.
- ❌ O'zbekistonga qaytish rejasini unutib qo'yish.""",
            },
            {
                "title": "Xalqaro Grant Intervyusidan Muvaffaqiyatli O'tish Sirlari",
                "category": "interview_prep",
                "summary": "Elchixona va xalqaro komissiya suhbatlarida beriladigan 10 ta eng qiyin savol va ularga javob berish strategiyalari.",
                "content": """### 1. Intervyuga Tayyorgarlik Poydevori

Intervyu — komissiya sizning inshoda yozgan ma'lumotlaringiz haqiqat ekanligini va jonli muloqotda o'zingizni qanday tutishingizni tekshirish bosqichidir.

---

### 2. Ko'p Beriladigan 5 Ta Savol:

1. **"Tell me about yourself" (O'zingiz haqingizda gapirib bering):**
   - Rezyumeni qaytarib o'qimang. Qiziqishlaringiz, asosiy qadriyatlaringiz va nima sizni ilhomlantirishini 90 soniyada so'zlab bering.
2. **"Why should we choose you over other candidates?" (Nega aynan sizni tanlashimiz kerak?):**
   - Kamtarlik bilan, lekin ishonch bilan o'zingizning jamoaviy ishlash va jamiyatga foyda keltirish ishtiyoqingizni ayting.
3. **"Describe a time you failed and what you learned" (Qachon xatoga yo'l qo'ygansiz va undan nima o'rgandingiz?):**
   - Xatoni tan olishdan qo'rqmang, asosiy urg'uni undan chiqargan xulosangizga qarating.

---

### 3. Suhbatdagi Tana Tili (Body Language):
- Kameraga qarab gapiring (onlayn suhbatda).
- Tabassum qiling va gapirayotganda qisqa pauzalar bilan fikringizni jamlang.
- Ovoz balandligi va intonatsiyangiz ishonchli bo'lsin.""",
            },
            {
                "title": "AQSh (F-1 / J-1) va Shengen Talabalik Vizasiga Hujjat Topshirish Tartibi",
                "category": "visa_process",
                "summary": "DS-160 anketasi, elchixona intervyusi, moliyaviy kafillik va vizaga topshirishda kerak bo'ladigan barcha hujjatlar.",
                "content": """### 1. Talaba Vizasining Asosiy Turlari

- **J-1 Vizasi:** Global UGRAD va boshqa davlat almashinuv dasturlari ishtirokchilari uchun.
- **F-1 Vizasi:** AQSh universitetlarida to'liq bakalavr yoki magistratura o'quvchilari uchun.

---

### 2. Bosqichma-bosqich Hujjat Topshirish:

1. **DS-2019 / I-20 Formasini olish:** Grant dasturi yoki universitet sizga rasmiy taklifnoma yuboradi.
2. **SEVIS to'lovini to'lash:** AQSh immigratsiya tizimida ro'yxatdan o'tish (I-901 to'lovi).
3. **DS-160 Anketasini to'ldirish:** Barcha shaxsiy va sayohat ma'lumotlarini xatosiz kiritish.
4. **Elchixonaga intervyu belgilash:** Toshkentdagi AQSh elchixonasiga navbat olish.

---

### 3. Viza Suhbatida Eng Muhim Qoida:
Siz qabul qiluvchi konsulga o'qishni tamomlagandan so'ng **O'zbekistonga qaytishingizni (Strong ties to home country)** isbotlab berishingiz shart!""",
            },
            {
                "title": "9-11 Sinf O'quvchilari Uchun Kuchli Profil (Extracurricular) Yaratish",
                "category": "general_tips",
                "summary": "Maktab davridayoq olimpiadalar, ijtimoiy loyihalar, IT startaplar va yetakchilik tajribalarini to'plash bo'yicha amaliy yo'riqnoma.",
                "content": """### 1. Extracurricular (Darsdan Tashqari Faoliyat) Nega Muhim?

Top universitetlar faqat "5" bahoga o'qiydigan o'quvchini emas, balki atrofiga ijobiy ta'sir ko'rsata oladigan yetakchilarni qidiradi.

---

### 2. 4 Ta Kuchli Yo'nalish:

1. **Jamiyat uchun foydali loyihalar (Volunteering):**
   - O'z maktabingiz yoki mahallangizda bepul to'garaklar (ingliz tili, shaxmat, dasturlash) tashkil qiling.
2. **Olimpiada va Tanlovlar:**
   - Respublika va xalqaro fan olimpiadalari, robototexnika yoki esse tanlovlarida qatnashing.
3. **Mustaqil Loyihalar (Passion Projects):**
   - Shaxsiy blog, podcast, ilova yoki ijtimoiy aksiyani yo'lga qo'ying.
4. **Yetakchilik (Leadership):**
   - Maktab sardorlar kengashi, Yoshlar Ittifoqi yoki debat klublarida rahbarlik qiling.""",
            }
        ]

        created_count = 0
        for item in guides:
            r, created = Resource.objects.get_or_create(
                title=item['title'],
                defaults={
                    'category': item['category'],
                    'summary': item['summary'],
                    'content': item['content'],
                }
            )
            if created:
                created_count += 1

        # Link related programs
        chevening = Program.objects.filter(name__icontains='Chevening').first()
        ugrad = Program.objects.filter(name__icontains='UGRAD').first()
        if ugrad or chevening:
            for r in Resource.objects.all():
                if 'insho' in r.title.lower() and ugrad:
                    r.related_programs.add(ugrad)
                if 'intervyu' in r.title.lower() and chevening:
                    r.related_programs.add(chevening)

        self.stdout.write(self.style.SUCCESS(f"{created_count} ta yangi resurs qo'llanmasi yaratildi."))
