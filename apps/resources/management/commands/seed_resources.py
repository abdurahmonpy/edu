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
- Baholarni va diplomlarni shunchaki sanab o'tish (buning uchun rezyume bor).
- Grammatik xatolarga beparvolik qilish.
- Haddan tashqari umumlashgan gaplar yozish.
- Boshqa birovning inshosini ko'chirish yoki AI matnini tahrirsiz qoldirish.
- O'zbekistonga qaytish rejasini unutib qo'yish.""",
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
            },
            {
                "title": "IELTS Reading: True/False/Not Given va Skimming Strategiyasi (8.0+ Band)",
                "category": "ielts_reading",
                "summary": "Akademik matnlarni 20 daqiqada tahlil qilish, kalit so'zlarni parafraza qilish va chalg'ituvchi variantlarni aniqlash qoidalari.",
                "content": """### 1. Skimming va Scanning nima?

- **Skimming (Ko'z yugurtirish):** Matnning umumiy mazmuni va har bir xatboshining asosiy fikrini 2-3 daqiqada tushunib olish.
- **Scanning (Kalit so'z qidirish):** Savoldagi sanalar, ismlar, ilmiy atamalar yoki raqamlarni matndan tezkor topish.

---

### 2. True / False / Not Given — Oltin Qoidalar:

- **TRUE:** Matndagi fakt savoldagi ma'lumot bilan 100% bir xil ma'noni bersa (sinonimlar orqali).
- **FALSE:** Matndagi fakt savoldagi ma'lumotga mutlaqo zid yoki teskari bo'lsa.
- **NOT GIVEN:** Matnda ushbu fakt haqida umuman gapirilmagan bo'lsa yoki tasdiqlash uchun ma'lumot yetarli bo'lmasa (o'zingizdan fakt qo'shmang!).""",
            },
            {
                "title": "IELTS Writing Task 2: 7.5+ Band Akademik Insho Strukturasi",
                "category": "ielts_writing",
                "summary": "Agree/Disagree, Discuss Both Views va Problem-Solution turlari uchun 4 paragraflik shablon, akademik linking words va argumentatsiya usullari.",
                "content": """### 1. 4 Paragraflik Standart Insho Tuzilishi:

1. **Introduction (Kirish — 40-50 so'z):**
   - Paraphrase the prompt (Mavzuni sinonimlar bilan qayta yozish).
   - Thesis statement (O'z shaxsiy pozitsiyangizni aniq ko'rsatish).
2. **Body Paragraph 1 (1-Asosiy xatboshi — 90-100 so'z):**
   - Topic sentence (Asosiy argument).
   - Explanation & Reasoning (Mantiqiy tushuntirish — nima uchun?).
   - Concrete Example (Aniq hayotiy yoki statistik misol).
3. **Body Paragraph 2 (2-Asosiy xatboshi — 90-100 so'z):**
   - Ikkinchi kuchli argument, izoh va natija.
4. **Conclusion (Xulosa — 30-40 so'z):**
   - Fikrlarni qisqa umumlashtirish (yangi g'oya qo'shilmaydi).""",
            },
            {
                "title": "IELTS Listening: Section 3 & 4 Akademik Audio Tahlili",
                "category": "ielts_listening",
                "summary": "Spikerlar o'rtasidagi bahs, ma'ruzalardagi 'distractor' (chalg'ituvchi so'zlar) va imlo xatolaridan qochish choralari.",
                "content": """### 1. Chalg'ituvchi (Distractor) So'zlar:

Spikerlar ko'pincha biror ma'lumotni aytib, keyin tuzatadilar:
- *"I'll take the 3 PM bus... actually, no, let's go at 4:30 PM."* (To'g'ri javob: 4:30).
- *"Although we considered Option A, we finally decided on Option B."*

---

### 2. Oldindan O'qib Olish (Prediction):
Audio boshlanishidan oldin berilgan 30 soniyadan unumli foydalaning:
- Qaysi so'z turkumi (ot, fe'l, son, sifat) tushib qolganini oldindan taxmin qiling.""",
            },
            {
                "title": "IELTS Speaking Part 2: 2 Daqiqalik Monolog Formulasi (PPF Metodi)",
                "category": "ielts_speaking",
                "summary": "Cue Card savollarida to'xtab qolmaslik, Past-Present-Future metodi orqali boy so'z boyligi va turli zamonlarni ko'rsatish.",
                "content": """### 1. PPF (Past, Present, Future) Usuli:

Cue card mavzusi bo'yicha 2 daqiqa tinimsiz gapirish uchun vaqt chizig'idan foydalaning:
1. **Past (O'tmish):** Barchasi qanday boshlangan edi? Ilk taassurotlar.
2. **Present (Hozirgi holat):** Hozir bu haqda nima deb o'ylaysiz va nima qilyapsiz?
3. **Future (Kelajak):** Kelajakda bu qanday rivojlanadi yoki nima qilishni rejalashtiryapsiz?

Bu usul sizga avtomatik ravishda turli grammatik zamonlarni (Past Simple, Present Perfect, Future Continuous) qo'llash imkonini beradi.""",
            },
            {
                "title": "Grammatika: C1 Darajadagi Murakkab Gaplar va Akademik Bog'lovchilar",
                "category": "grammar_vocab",
                "summary": "Inversiya, shart mayllari (Conditionals), Cleft sentences va IELTS Writing/Speaking'da ballni oshiruvchi sintaktik tuzilmalar.",
                "content": """### 1. Yuqori Band Uchun Grammatik Strukturalar:

1. **Inversion (Inversiya):**
   - *"Not only did the project reduce costs, but it also improved student engagement."*
2. **Mixed Conditionals (Aralash shart mayli):**
   - *"If I had not prepared thoroughly, I would not be studying abroad today."*
3. **Cleft Sentences (Urg'u beruvchi gaplar):**
   - *"It is their dedication that drives real innovation in modern education."*""",
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
