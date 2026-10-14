from __future__ import annotations

# ---------------------------------------------------------------------------
# Leaf collections (defined first so composite collections can reference them)
# ---------------------------------------------------------------------------

SPEED_MATCH_PAIRS: list[dict] = [
    {"en": "Teacher", "uz": "O'qituvchi"},
    {"en": "Student", "uz": "Talaba"},
    {"en": "Knowledge", "uz": "Bilim"},
    {"en": "Success", "uz": "Muvaffaqiyat"},
    {"en": "Listen", "uz": "Eshitmoq"},
    {"en": "Speak", "uz": "Gapirmoq"},
    {"en": "Book", "uz": "Kitob"},
    {"en": "Friend", "uz": "Do'st"},
]

ALPHABET_EXERCISE: list[dict] = [
    {
        "prompt": "A [_] C D — tushurib qoldirilgan harfni alifbo tartibida tanlang",
        "options": ["A", "B", "C", "D"],
        "correct_index": 1,
        "explanation": "Alifbo tartibida A, B, C, D bo'ladi, shuning uchun to'g'ri javob — B.",
    },
    {
        "prompt": "E F [_] H — tushurib qoldirilgan harfni alifbo tartibida tanlang",
        "options": ["E", "F", "G", "H"],
        "correct_index": 2,
        "explanation": "E dan keyin F, so'ngra G, keyin H keladi. To'g'ri javob — G.",
    },
    {
        "prompt": "J [_] L M — tushurib qoldirilgan harfni alifbo tartibida tanlang",
        "options": ["J", "K", "L", "M"],
        "correct_index": 1,
        "explanation": "J va L orasida K harfi turadi. To'g'ri javob — K.",
    },
    {
        "prompt": "P Q [_] S — tushurib qoldirilgan harfni alifbo tartibida tanlang",
        "options": ["P", "Q", "R", "S"],
        "correct_index": 2,
        "explanation": "P, Q dan keyin R, oxirida S keladi. To'g'ri javob — R.",
    },
]

PLACEMENT_QUESTIONS: list[dict] = [
    {
        "prompt": '"She ______ to school every morning." Nuqtalar o\'rniga to\'g\'ri so\'zni tanlang:',
        "options": ["A) go", "B) goes", "C) going", "D) wented"],
        "correct_index": 1,
        "explanation": "Uchinchi shaxs birlik (she) bilan fe'lga -es qo'shiladi: she goes.",
    },
    {
        "prompt": '"I don\'t have ______ money in my wallet." Qaysi so\'z mos keladi?',
        "options": ["A) some", "B) many", "C) any", "D) a"],
        "correct_index": 2,
        "explanation": "Inkor gapda sanalmaydigan otlar bilan 'any' ishlatiladi: I don't have any money.",
    },
    {
        "prompt": '"Yesterday, we ______ a great movie at the cinema."',
        "options": ["A) see", "B) saw", "C) seen", "D) was seeing"],
        "correct_index": 1,
        "explanation": "'Yesterday' o'tgan zamonni bildiradi, shuning uchun 'saw' (Past Simple) to'g'ri.",
    },
]

STARTING_VOCABULARY: list[dict] = [
    {
        "word": "Hello",
        "translation": "salom",
        "example": "Hello! How are you?",
        "part_of_speech": "so'z",
        "level_tag": "starter",
    },
    {
        "word": "Goodbye",
        "translation": "xayr",
        "example": "Goodbye, see you tomorrow!",
        "part_of_speech": "so'z",
        "level_tag": "starter",
    },
    {
        "word": "Thank you",
        "translation": "rahmat",
        "example": "Thank you very much!",
        "part_of_speech": "ibora",
        "level_tag": "starter",
    },
    {
        "word": "Please",
        "translation": "iltimos",
        "example": "Please help me.",
        "part_of_speech": "ibora",
        "level_tag": "starter",
    },
    {
        "word": "Good morning",
        "translation": "xayrli tong",
        "example": "Good morning, class!",
        "part_of_speech": "ibora",
        "level_tag": "starter",
    },
]

BATTLE_QUESTIONS: list[dict] = [
    {
        "topic": "grammar",
        "level": "starter",
        "prompt": '"He/She/It" uchun to be fe\'li qaysi shaklda bo\'ladi?',
        "options": ["am", "is", "are", "be"],
        "correct_index": 1,
        "explanation": "He/She/It olmoshlari bilan to be fe'li 'is' shaklida ishlatiladi.",
    },
    {
        "topic": "grammar",
        "level": "starter",
        "prompt": '"They ______ playing football now."',
        "options": ["is", "are", "am", "was"],
        "correct_index": 1,
        "explanation": "'They' ko'plik, shuning uchun 'are' — They are playing.",
    },
    {
        "topic": "grammar",
        "level": "starter",
        "prompt": '"Yesterday I ______ a great book."',
        "options": ["read", "reads", "reading", "will read"],
        "correct_index": 0,
        "explanation": "'Yesterday' o'tgan zamon; 'read' ning Past Simple shakli ham 'read' bo'ladi.",
    },
    {
        "topic": "grammar",
        "level": "starter",
        "prompt": '"She doesn\'t ______ coffee."',
        "options": ["likes", "like", "liked", "liking"],
        "correct_index": 1,
        "explanation": "'doesn't' dan keyin fe'l asosiy shaklda keladi: doesn't like.",
    },
    {
        "topic": "grammar",
        "level": "starter",
        "prompt": '"We have ______ friends in London."',
        "options": ["much", "many", "any", "little"],
        "correct_index": 1,
        "explanation": "Sanaladigan otlar (friends) bilan 'many' ishlatiladi.",
    },
    {
        "topic": "vocabulary",
        "level": "starter",
        "prompt": '"Teacher" so\'zining tarjimasi nima?',
        "options": ["Talaba", "O'qituvchi", "Shifokor", "Muhandis"],
        "correct_index": 1,
        "explanation": "'Teacher' — o'qituvchi; 'student' esa talaba.",
    },
    {
        "topic": "vocabulary",
        "level": "starter",
        "prompt": '"Knowledge" so\'zining ma\'nosi?',
        "options": ["Bilim", "Kitob", "Maktab", "Kutubxona"],
        "correct_index": 0,
        "explanation": "'Knowledge' — bilim degani.",
    },
    {
        "topic": "vocabulary",
        "level": "starter",
        "prompt": '"Success" so\'zi nimani anglatadi?',
        "options": ["Omad", "Muvaffaqiyat", "Mehnat", "Orzu"],
        "correct_index": 1,
        "explanation": "'Success' — muvaffaqiyat; 'luck' esa omad.",
    },
    {
        "topic": "vocabulary",
        "level": "starter",
        "prompt": '"Friend" so\'zining tarjimasi?',
        "options": ["Birodar", "Do'st", "Qo'shni", "Hamkasb"],
        "correct_index": 1,
        "explanation": "'Friend' — do'st; 'brother' birodar, 'neighbour' qo'shni.",
    },
    {
        "topic": "vocabulary",
        "level": "starter",
        "prompt": '"Listen" fe\'lining ma\'nosi?',
        "options": ["Gapirmoq", "Yozmoq", "Eshitmoq / Tinglamoq", "O'qimoq"],
        "correct_index": 2,
        "explanation": "'Listen' — eshitmoq/tinglamoq; 'speak' gapirmoq, 'read' o'qimoq.",
    },
]

ACHIEVEMENTS: list[dict] = [
    {
        "slug": "birinchi-dars",
        "title": "Birinchi qadam",
        "description": "Birinchi darsni muvaffaqiyatli tamomladingiz!",
        "icon": "🎯",
        "points": 10,
        "threshold": 1,
        "metric": "lessons",
    },
    {
        "slug": "7-kunlik-seriya",
        "title": "7 kunlik seriya",
        "description": "7 kun ketma-ket o'qib, kunlik seriyani saqlab qoldingiz!",
        "icon": "🔥",
        "points": 50,
        "threshold": 7,
        "metric": "streak",
    },
    {
        "slug": "100-soz",
        "title": "100 so'z ustasi",
        "description": "Lug'atingizga 100 ta so'z qo'shdingiz!",
        "icon": "📚",
        "points": 100,
        "threshold": 100,
        "metric": "words",
    },
    {
        "slug": "1000-ball",
        "title": "1000 ball",
        "description": "Platformada 1000 ball to'pladingiz!",
        "icon": "⭐",
        "points": 100,
        "threshold": 1000,
        "metric": "points",
    },
    {
        "slug": "10-jang-galabasi",
        "title": "Jangchi",
        "description": "10 ta jangda g'alaba qozondingiz!",
        "icon": "⚔️",
        "points": 150,
        "threshold": 10,
        "metric": "battles_won",
    },
    {
        "slug": "10-dars",
        "title": "Tinimsiz o'quvchi",
        "description": "10 ta darsni tamomladingiz!",
        "icon": "🎓",
        "points": 100,
        "threshold": 10,
        "metric": "lessons",
    },
    {
        "slug": "30-kunlik-seriya",
        "title": "30 kunlik seriya",
        "description": "Bir oy davomida har kuni mashq qildingiz!",
        "icon": "🏆",
        "points": 300,
        "threshold": 30,
        "metric": "streak",
    },
    {
        "slug": "5000-ball",
        "title": "Englify yulduzi",
        "description": "5000 ball to'plab, peshqadamlar safiga qo'shildingiz!",
        "icon": "💎",
        "points": 300,
        "threshold": 5000,
        "metric": "points",
    },
]

DEMO_USERS: list[dict] = [
    {
        "email": "englify@englify.uz",
        "full_name": "Englify",
        "password": "englify1234",
        "points": 3406,
        "level": "starter",
        "streak_days": 21,
        "role": "student",
    },
    {
        "email": "sigma@englify.uz",
        "full_name": "SIGMA",
        "password": "englify1234",
        "points": 3146,
        "level": "starter",
        "streak_days": 17,
        "role": "student",
    },
    {
        "email": "adhamjon@englify.uz",
        "full_name": "Adhamjon",
        "password": "englify1234",
        "points": 3110,
        "level": "starter",
        "streak_days": 14,
        "role": "student",
    },
    {
        "email": "abror@englify.uz",
        "full_name": "Abror",
        "password": "englify1234",
        "points": 2651,
        "level": "starter",
        "streak_days": 11,
        "role": "student",
    },
    {
        "email": "gulbaxor@englify.uz",
        "full_name": "Gulbaxor",
        "password": "englify1234",
        "points": 2636,
        "level": "starter",
        "streak_days": 9,
        "role": "student",
    },
    {
        "email": "gulnoza@englify.uz",
        "full_name": "Gulnoza",
        "password": "englify1234",
        "points": 2515,
        "level": "starter",
        "streak_days": 8,
        "role": "student",
    },
    {
        "email": "boximboyev@englify.uz",
        "full_name": "Boximboyev",
        "password": "englify1234",
        "points": 2346,
        "level": "starter",
        "streak_days": 6,
        "role": "student",
    },
    {
        "email": "abdurahmon@englify.uz",
        "full_name": "Abdurahmon",
        "password": "englify1234",
        "points": 0,
        "level": "starter",
        "streak_days": 0,
        "role": "student",
    },
]

# ---------------------------------------------------------------------------
# Course tree
# ---------------------------------------------------------------------------

COURSES: list[dict] = [
    {
        "slug": "general-english",
        "title": "General English",
        "subtitle": "Noldan ingliz tilini o'rganish kursi",
        "description": (
            "Englify'ning asosiy kursi: ingliz alifbosidan boshlab kundalik muloqotga qadar "
            "video darslar, interaktiv mashqlar va majburiy uy vazifalari."
        ),
        "level": "starter",
        "emoji": "🇬🇧",
        "color": "#0A93F5",
        "order_index": 0,
        "units": [
            {
                "slug": "unit-1-1",
                "code": "1.1",
                "title": "Unit 1.1",
                "description": "Ingliz alifbosi, salomlashish va o'zini tanishtirish iboralari.",
                "emoji": "🔤",
                "order_index": 0,
                "lessons": [
                    {
                        "slug": "greetings-and-introductions",
                        "title": "Greetings & Introductions",
                        "description": "Salomlashish va o'zini tanishtirishni o'rganamiz.",
                        "kind": "video",
                        "video_url": None,
                        "duration_sec": 600,
                        "xp_reward": 20,
                        "content": None,
                        "questions": [],
                    },
                    {
                        "slug": "alphabet-1",
                        "title": "Alphabet 1",
                        "description": "Ingliz alifbosining birinchi qismi: A dan J gacha.",
                        "kind": "video",
                        "video_url": "https://www.youtube.com/embed/HQ3APZJj4qY?autoplay=1&rel=0&modestbranding=1",
                        "duration_sec": 300,
                        "xp_reward": 10,
                        "content": None,
                        "questions": [],
                    },
                    {
                        "slug": "alphabet-2",
                        "title": "Alphabet 2",
                        "description": "Ingliz alifbosining ikkinchi qismi: K dan S gacha.",
                        "kind": "video",
                        "video_url": "https://www.youtube.com/embed/ccEpTTZXSi8?autoplay=1&rel=0&modestbranding=1",
                        "duration_sec": 300,
                        "xp_reward": 10,
                        "content": None,
                        "questions": [],
                    },
                    {
                        "slug": "alphabet-3",
                        "title": "Alphabet 3",
                        "description": "Ingliz alifbosining uchinchi qismi: T dan Z gacha.",
                        "kind": "video",
                        "video_url": "https://www.youtube.com/embed/wpffswm5l9s?autoplay=1&rel=0&modestbranding=1",
                        "duration_sec": 300,
                        "xp_reward": 10,
                        "content": None,
                        "questions": [],
                    },
                    {
                        "slug": "alphabet-exercise",
                        "title": "Alphabet mashqi",
                        "description": "Tushurib qoldirilgan harfni alifbo tartibida yozing.",
                        "kind": "quiz",
                        "video_url": None,
                        "duration_sec": 300,
                        "xp_reward": 50,
                        "content": {
                            "exercise": "alphabet",
                            "example": "Example: A B C D",
                            "total_questions": 4,
                        },
                        "questions": ALPHABET_EXERCISE,
                    },
                ],
            },
            {
                "slug": "unit-1-2",
                "code": "1.2",
                "title": "Unit 1.2",
                "description": "Oila, raqamlar va asosiy so'zlar.",
                "emoji": "👨‍👩‍👧",
                "order_index": 1,
                "lessons": [
                    {
                        "slug": "family-and-numbers",
                        "title": "Family & Numbers",
                        "description": "Oila a'zolarini va 1 dan 20 gacha raqamlarni o'rganamiz.",
                        "kind": "video",
                        "video_url": None,
                        "duration_sec": 600,
                        "xp_reward": 20,
                        "content": None,
                        "questions": [],
                    },
                ],
            },
            {
                "slug": "unit-2-1",
                "code": "2.1",
                "title": "Unit 2.1",
                "description": "Kundalik tartib va oddiy kundalik gaplar.",
                "emoji": "⏰",
                "order_index": 2,
                "lessons": [
                    {
                        "slug": "daily-routines",
                        "title": "Daily Routines",
                        "description": "Kundalik ishlar haqida gapirishni o'rganamiz.",
                        "kind": "video",
                        "video_url": None,
                        "duration_sec": 600,
                        "xp_reward": 20,
                        "content": None,
                        "questions": [],
                    },
                ],
            },
            {
                "slug": "unit-2-2",
                "code": "2.2",
                "title": "Unit 2.2",
                "description": "Xarid qilish, sayohat va ob-havo mavzulari.",
                "emoji": "🧳",
                "order_index": 3,
                "lessons": [
                    {
                        "slug": "shopping-and-travel",
                        "title": "Shopping & Travel",
                        "description": "Do'konda va sayohatda ishlatiladigan iboralar.",
                        "kind": "video",
                        "video_url": None,
                        "duration_sec": 600,
                        "xp_reward": 20,
                        "content": None,
                        "questions": [],
                    },
                ],
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------------

BOOKS: list[dict] = [
    {
        "slug": "the-alchemist",
        "title": "The Alchemist",
        "author": "Paulo Coelho",
        "level": "Upper-Intermediate",
        "description": (
            "The boy's name was Santiago. Dusk was falling as he arrived with his herd at an "
            "abandoned church. The roof had fallen in long ago, and an enormous sycamore had grown "
            "on the spot where the sacristy had once stood. He decided to spend the night there."
        ),
        "pages": 208,
        "category": "Fantasy",
        "tags": ["fantasy", "adventure", "classic"],
        "order_index": 0,
        "cover_url": None,
        "file_url": None,
    },
    {
        "slug": "eragon",
        "title": "Eragon",
        "author": "Christopher Paolini",
        "level": "Upper-Intermediate",
        "description": (
            "Wind howled through the night, carrying a scent that would change the world. A tall "
            "Shade lifted his head and sniffed the air. He looked human except for his crimson hair "
            "and maroon eyes. He was waiting for the dragon egg."
        ),
        "pages": 509,
        "category": "Fantasy",
        "tags": ["fantasy", "adventure", "dragons"],
        "order_index": 1,
        "cover_url": None,
        "file_url": None,
    },
    {
        "slug": "coraline",
        "title": "Coraline",
        "author": "Neil Gaiman",
        "level": "Pre-Intermediate",
        "description": (
            "Coraline discovered the door a little after they moved into the house. It was a very "
            "old house, with an attic under the roof and a cellar under the ground. There were "
            "twenty-one windows and a mysterious small wooden door in the drawing room."
        ),
        "pages": 162,
        "category": "Fantasy",
        "tags": ["fantasy", "horror", "novella"],
        "order_index": 2,
        "cover_url": None,
        "file_url": None,
    },
    {
        "slug": "the-diary-of-a-young-girl",
        "title": "The Diary of a Young Girl",
        "author": "Anne Frank",
        "level": "Upper-Intermediate",
        "description": (
            "I hope I will be able to confide everything to you, as I have never been able to "
            "confide in anyone, and I hope you will be a great source of comfort and support. "
            "Sunday, 14 June 1942: On Friday, 12 June, I woke up at six o'clock and it was my birthday."
        ),
        "pages": 283,
        "category": "Biography",
        "tags": ["biography", "war", "diary"],
        "order_index": 3,
        "cover_url": None,
        "file_url": None,
    },
    {
        "slug": "cant-hurt-me",
        "title": "Can't Hurt Me: Master Your Mind and Defy the Odds",
        "author": "David Goggins",
        "level": "Intermediate 2 (B1+)",
        "description": (
            "For the first twenty-four years of my life, I was depressed, insecure, and overweight. "
            "But everything changed when I realized that nobody was coming to save me. I had to "
            "become my own hero."
        ),
        "pages": 364,
        "category": "Biography",
        "tags": ["biography", "motivation", "memoir"],
        "order_index": 4,
        "cover_url": None,
        "file_url": None,
    },
    {
        "slug": "the-city-of-ember",
        "title": "The City of Ember",
        "author": "Jeanne DuPrau",
        "level": "Intermediate",
        "description": (
            "When the city of Ember was built, the Builders made sure that it would have everything "
            "necessary to survive for two hundred years in the underground darkness."
        ),
        "pages": 270,
        "category": "Science Fiction",
        "tags": ["science-fiction", "dystopia", "adventure"],
        "order_index": 5,
        "cover_url": None,
        "file_url": None,
    },
    {
        "slug": "i-robot",
        "title": "I, Robot",
        "author": "Isaac Asimov",
        "level": "Upper-Intermediate",
        "description": (
            "Rule One: A robot may not injure a human being or, through inaction, allow a human "
            "being to come to harm. Dr. Susan Calvin looked at the mechanical worker with quiet "
            "determination."
        ),
        "pages": 253,
        "category": "Science Fiction",
        "tags": ["science-fiction", "robots", "classic"],
        "order_index": 6,
        "cover_url": None,
        "file_url": None,
    },
]

PODCASTS: list[dict] = [
    {
        "slug": "ep-1-how-to-introduce-yourself-like-a-native",
        "title": "Ep 1: How to introduce yourself like a native",
        "host": "Nilufar Karimova",
        "level": "A1-A2",
        "episode_number": 1,
        "description": "Salomlashish va o'zini tanishtirishning jonli iboralari • A1-A2",
        "duration_sec": 195,
        "audio_url": None,
        "cover_url": None,
        "transcript": (
            "Hello everyone and welcome to the Englify Podcast! Today we are talking about how to "
            "introduce yourself naturally. Instead of just saying 'My name is John and I am fine', "
            "native speakers often say: 'Hey, I'm John, great to meet you! How's your day going?' "
            "Remember, a warm smile and confident tone are just as important as the words!"
        ),
        "tags": ["speaking", "introductions", "a1"],
        "order_index": 0,
    },
    {
        "slug": "ep-2-10-common-english-mistakes",
        "title": "Ep 2: 10 Common English Mistakes and how to avoid them",
        "host": "Jasur Toshmatov",
        "level": "A2-B1",
        "episode_number": 2,
        "description": "Ko'p uchraydigan 10 ta grammatik xato va ularning yechimi • A2-B1",
        "duration_sec": 280,
        "audio_url": None,
        "cover_url": None,
        "transcript": (
            "Welcome back! Today's top mistake is saying 'I am agree with you'. In English, 'agree' "
            "is already a verb, so you simply say: 'I agree with you'. Another common slip is 'She "
            "don't know' instead of 'She doesn't know'. Practice these everyday to build automatic "
            "fluency!"
        ),
        "tags": ["grammar", "mistakes", "a2"],
        "order_index": 1,
    },
    {
        "slug": "ep-3-ordering-food-at-a-restaurant",
        "title": "Ep 3: Ordering Food at a Restaurant",
        "host": "Malika Yusupova",
        "level": "A1",
        "episode_number": 3,
        "description": "Restoranda ovqat buyurtma qilish va hisob so'rash • A1",
        "duration_sec": 170,
        "audio_url": None,
        "cover_url": None,
        "transcript": (
            "Imagine you are sitting at a cozy café in London. The waiter approaches: 'Are you ready "
            "to order?' You can politely reply: 'Yes, please! Could I have the chicken salad and a "
            "cup of black coffee?' Never say 'I want this', always use 'Could I have' or 'I would "
            "like'."
        ),
        "tags": ["speaking", "restaurant", "a1"],
        "order_index": 2,
    },
    {
        "slug": "ep-4-job-interview-tell-me-about-yourself",
        "title": "Ep 4: Job Interview — Tell Me About Yourself",
        "host": "Bekzod Rahimov",
        "level": "B1-B2",
        "episode_number": 4,
        "description": "Ish suhbatida o'zingiz haqingizda muvaffaqiyatli gapirish • B1-B2",
        "duration_sec": 310,
        "audio_url": None,
        "cover_url": None,
        "transcript": (
            "The classic job interview opening: 'Tell me about yourself'. Don't recite your entire "
            "life story! Use the Present-Past-Future formula. Talk about where you are right now, "
            "one key past accomplishment, and why you are excited about this specific opportunity."
        ),
        "tags": ["business", "interview", "b1"],
        "order_index": 3,
    },
    {
        "slug": "ep-5-travel-english-at-the-airport",
        "title": "Ep 5: Travel English — At the Airport & Check-in",
        "host": "Dilnoza Saidova",
        "level": "A2",
        "episode_number": 5,
        "description": "Aeroportda ro'yxatdan o'tish va parvoz qoidalari • A2",
        "duration_sec": 225,
        "audio_url": None,
        "cover_url": None,
        "transcript": (
            "At the check-in desk, the agent will ask: 'Can I see your passport and booking "
            "reference?' Then they will ask: 'Would you prefer a window seat or an aisle seat?' "
            "Learn these phrases so your next international journey is smooth and stress-free!"
        ),
        "tags": ["travel", "airport", "a2"],
        "order_index": 4,
    },
]

# ---------------------------------------------------------------------------
# Games
# ---------------------------------------------------------------------------

GAMES: list[dict] = [
    {
        "slug": "sozlar-jangi",
        "title": "So'zlar jangi",
        "kind": "battle",
        "description": "Vaqt bilan poyga: 30 ta so'z tarjimasini eng tez toping!",
        "emoji": "⚔️",
        "color": "#2D72BF",
        "play_url": "jang.html",
        "config": {
            "rounds": 5,
            "seconds": 15,
            "points_per_correct": 20,
            "max_points_per_session": 100,
            "pairs": [],
        },
        "order_index": 0,
    },
    {
        "slug": "speed-match",
        "title": "Speed Match",
        "kind": "match",
        "description": "Inglizcha va o'zbekcha so'z juftliklarini eng tez toping.",
        "emoji": "🧩",
        "color": "#DE5CE2",
        "play_url": "oyinlar.html#gameSection",
        "config": {
            "rounds": 4,
            "seconds": None,
            "points_per_correct": 15,
            "max_points_per_session": 110,
            "pairs": SPEED_MATCH_PAIRS,
        },
        "order_index": 1,
    },
    {
        "slug": "sentence-builder",
        "title": "Sentence Builder",
        "kind": "builder",
        "description": "Aralash so'zlardan to'g'ri inglizcha gap tuzing.",
        "emoji": "📝",
        "color": "#2ED573",
        "play_url": None,
        "config": {
            "rounds": 5,
            "seconds": 60,
            "points_per_correct": 10,
            "max_points_per_session": 50,
            "pairs": [],
        },
        "order_index": 2,
    },
]

# ---------------------------------------------------------------------------
# Events, notifications, chats
# ---------------------------------------------------------------------------

EVENTS: list[dict] = [
    {
        "slug": "grammar-masterclass",
        "title": "Grammar Masterclass",
        "description": "Ingliz grammatikasining asosiy qoidalari bo'yicha jonli master-klass.",
        "host_name": "Umidjon Ishmuhammedov",
        "level": "starter",
        "kind": "masterclass",
        "starts_in_days": 0,
        "start_hour": "18:00",
        "duration_minutes": 90,
        "meeting_id": "823 4410 9921",
        "join_url": "https://zoom.us/j/82344109921",
        "color": "#35F59A",
        "emoji": "📘",
        "recording_url": None,
    },
    {
        "slug": "speaking-club",
        "title": "Speaking Club",
        "description": "Har haftalik jonli suhbat klubi: erkin muloqot va talaffuz mashqlari.",
        "host_name": "Nilufar Karimova",
        "level": "elementary",
        "kind": "club",
        "starts_in_days": 2,
        "start_hour": "16:00",
        "duration_minutes": 60,
        "meeting_id": "915 7732 4480",
        "join_url": "https://zoom.us/j/91577324480",
        "color": "#0A93F5",
        "emoji": "🗣️",
        "recording_url": None,
    },
    {
        "slug": "vocabulary-challenge",
        "title": "Vocabulary Challenge",
        "description": "Yangi so'zlarni o'yin shaklida yodlaydigan jonli bellashuv.",
        "host_name": "Jasur Toshmatov",
        "level": "starter",
        "kind": "challenge",
        "starts_in_days": 4,
        "start_hour": "19:00",
        "duration_minutes": 60,
        "meeting_id": "760 2058 3314",
        "join_url": "https://zoom.us/j/76020583314",
        "color": "#FFB26F",
        "emoji": "📚",
        "recording_url": None,
    },
    {
        "slug": "grammar-masterclass-october",
        "title": "Grammar Masterclass",
        "description": "O'tgan Grammatika master-klassining yozuvi.",
        "host_name": "Umidjon Ishmuhammedov",
        "level": "starter",
        "kind": "masterclass",
        "starts_in_days": -5,
        "start_hour": "18:00",
        "duration_minutes": 90,
        "meeting_id": "823 4410 9921",
        "join_url": "https://zoom.us/j/82344109921",
        "color": "#35F59A",
        "emoji": "📘",
        "recording_url": "https://zoom.us/rec/share/englify-grammar-masterclass",
    },
    {
        "slug": "speaking-club-october",
        "title": "Speaking Club",
        "description": "O'tgan Speaking Club yig'ilishining yozuvi.",
        "host_name": "Nilufar Karimova",
        "level": "elementary",
        "kind": "club",
        "starts_in_days": -8,
        "start_hour": "16:00",
        "duration_minutes": 60,
        "meeting_id": "915 7732 4480",
        "join_url": "https://zoom.us/j/91577324480",
        "color": "#0A93F5",
        "emoji": "🗣️",
        "recording_url": "https://zoom.us/rec/share/englify-speaking-club",
    },
]

NOTIFICATIONS: list[dict] = [
    {
        "kind": "event",
        "title": "🎓 Bugun kelajak uchun qaror qabul qilinadigan kun!",
        "body": (
            "Abituriyentlar va ota-onalar uchun Umidjon Ishmuhammedov bilan maxsus master-klass "
            "bo'lib o'tadi..."
        ),
        "banner": {
            "gradient": "linear-gradient(135deg, #421C16, #78351B)",
            "badge": "MILLAT UMIDI",
            "headline": "To'g'ri universitet tanlash!",
            "subline": "Online bepul vebinarga qo'shiling!",
            "emoji": "👨‍💼",
        },
        "link": "zoom.html",
        "cta_label": "Bepul qo'shiling",
        "icon": "🎓",
        "days_ago": 0,
    },
    {
        "kind": "grant",
        "title": "🎓 Universitet tanlashdagi bitta to'g'ri qaror",
        "body": (
            "Universitet tanlashdagi bitta to'g'ri qaror kelajagingizni belgilaydi. Grant "
            "tanlovlarida qatnashing..."
        ),
        "banner": {
            "gradient": "linear-gradient(135deg, #5C3D32, #8F6656)",
            "headline": "Millat Umidi Universiteti",
            "subline": "1 000 000 000 grant e'lon qildi",
            "emoji": "✉️",
        },
        "link": "zoom.html",
        "cta_label": "Qo'shilish",
        "icon": "✉️",
        "days_ago": 1,
    },
    {
        "kind": "promo",
        "title": "🔥 Ingliz tili kurslariga ro'yxatdan o'tish ochildi!",
        "body": (
            "Individual va guruh mashg'ulotlarida zamonaviy metodika asosida ta'lim oling..."
        ),
        "banner": {
            "gradient": "linear-gradient(135deg, #0A1C3E, #1F4287)",
            "headline": "Yangi mavsum aksiyasi!",
            "subline": "Barcha o'quv modullari uchun 40% chegirma",
            "emoji": "🎁",
            "chips": [
                {"label": "NAQDGA:", "color": "#0A93F5"},
                {"label": "NASIYAGA:", "color": "#2ED573"},
            ],
        },
        "link": "dars.html",
        "cta_label": "Batafsil ma'lumot",
        "icon": "🎁",
        "days_ago": 18,
    },
]

CHAT_SEED: list[dict] = [
    {
        "kind": "support",
        "title": "Support Service",
        "emoji": "S",
        "color": "#0A93F5",
        "messages": [
            {
                "from": "bot",
                "sender_name": "Support Service",
                "body": (
                    "Assalom alaykum! Sizni Englify qo'llab-quvvatlash xizmati qutlaydi. Darslar "
                    "yoki platforma bo'yicha qanday savolingiz bor?"
                ),
                "days_ago": 67,
            },
        ],
    },
    {
        "kind": "system",
        "title": "Englify",
        "emoji": "E",
        "color": "#2ED573",
        "messages": [
            {
                "from": "bot",
                "sender_name": "Englify",
                "body": "👋 Welcome! Your first step to speaking English fluently starts right here.",
                "days_ago": 156,
            },
            {
                "from": "bot",
                "sender_name": "Englify",
                "body": "Darslar bo'limidan Unit 1.1 ni boshlashingiz mumkin!",
                "days_ago": 156,
            },
        ],
    },
    {
        "kind": "bot",
        "title": "Alomat (Bot)",
        "emoji": "A",
        "color": "#9A3FEF",
        "messages": [
            {
                "from": "bot",
                "sender_name": "Alomat (Bot)",
                "body": (
                    "Salom! Men Alomat — sizning sun'iy intellekt repetitoringizman. Grammatika, "
                    "so'zlar yoki darslar bo'yicha xohlagan savolingizni bering!"
                ),
                "days_ago": 0,
            },
        ],
    },
]
