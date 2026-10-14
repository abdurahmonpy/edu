# Englify — onlayn ingliz tili platformasi

Statik HTML frontend + **FastAPI** backend. Bitta servisda ishlaydi: backend
ham API, ham HTML sahifalarni beradi, shuning uchun Railway'da bitta servis
yetarli.

```
┌──────────────────────────── Railway (bitta servis) ────────────────────────────┐
│  uvicorn backend.app.main:app                                                  │
│                                                                                │
│   /                → index.html        (static, cleanUrls)                     │
│   /app  /dars  …   → *.html            (static, cleanUrls)                     │
│   /api/v1/…        → REST API (FastAPI)                                        │
│   /api/v1/ws/…     → WebSocket (chat, jang, bildirishnoma)                     │
│   /docs            → interaktiv API hujjati (Swagger UI)                       │
│   /health          → healthcheck                                               │
└────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
                          PostgreSQL (Railway plugin)
```

---

## 1. Nima qilindi

Loyiha avval **butunlay statik prototip** edi: hech qanday backend, autentifikatsiya
yoki saqlash yo'q edi. Barcha raqamlar (`Talaba`, `0 ball`, `[%]`, reyting
jadvali, bildirishnomalar, chat, jang savollari) HTML ichida qotib qolgan edi.

Endi:

* **To'liq backend** — 80+ REST endpoint + 3 WebSocket kanali.
* **Auth** — email/parol bilan ro'yxatdan o'tish va kirish, JWT access token
  (1 kun) + rotatsiyalanuvchi refresh token (30 kun), bcrypt parol xeshlash,
  parolni tiklash, parolni almashtirish, hisobni bloklash (brute-force himoyasi).
* **Ma'lumotlar bazasi** — PostgreSQL (Railway), SQLite'ga avtomatik qaytish
  (lokal ishlab chiqish uchun sozlash shart emas).
* **Seed ma'lumotlar** — prototipdagi barcha kontent (kurs, 8 dars, 7 kitob,
  5 podkast, 10 jang savoli, reyting jadvalidagi 8 foydalanuvchi, Zoom tadbirlar,
  bildirishnomalar, chat, 5 boshlang'ich so'z) bazaga ko'chirildi.
* **Frontend API qatlami** — `assets/js/{config,ui,api,auth}.js` va
  `kirish.html` (kirish / ro'yxatdan o'tish / parolni tiklash).
* **Testlar** — 100+ avtomatik test (`pytest`), barchasi yashil.

---

## 2. Papka tuzilishi

```
.
├── *.html                    # sahifalar (index, app, dars, lugat, chat, …)
├── kirish.html               # login / register / parolni tiklash
├── 404.html                  # xato sahifasi
├── assets/js/
│   ├── config.js             # API manzili
│   ├── ui.js                 # DOM/format yordamchilari
│   ├── api.js                # fetch + token + avtomatik refresh
│   ├── auth.js               # sessiya, sahifa qo'riqchisi, badge/WS
│   └── pages/*.js            # har bir sahifaning o'z logikasi
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI ilovasi + statik fayllar
│   │   ├── config.py         # barcha sozlamalar (.env orqali)
│   │   ├── database.py       # async engine / session
│   │   ├── models.py         # 25+ ORM model
│   │   ├── schemas.py        # Pydantic so'rov/javob modellari
│   │   ├── security.py       # bcrypt + JWT
│   │   ├── deps.py           # auth dependency, rate limit
│   │   ├── services.py       # ball, streak, daraja, SRS, bildirishnoma
│   │   ├── realtime.py       # WebSocket hub
│   │   ├── seed.py           # seed logikasi (idempotent)
│   │   ├── seed_data.py      # prototipdagi kontent
│   │   └── routers/          # auth, users, courses, vocabulary, chat, …
│   ├── tests/                # pytest to'plami
│   ├── manage.py             # CLI (serve, seed, reset-db, …)
│   ├── requirements.txt
│   └── .env.example
├── Dockerfile                # Railway uchun (Docker build)
├── railway.json              # eski Railway servislar uchun moslik sozlamasi
├── Procfile                  # Nixpacks alternativasi
└── docs/
    ├── DEPLOY-RAILWAY.md     # Railway'ga joylash (o'zbekcha, qadam-baqadam)
    ├── FRONTEND_CONTRACT.md  # frontend ↔ backend shartnomasi
    └── spec-*.md             # prototip tahlili (prototipdagi barcha qiymatlar)
```

---

## 3. Lokal ishga tushirish

Hech narsa sozlash shart emas — baza sifatida SQLite ishlatiladi.

```powershell
# 1) virtual muhit
cd backend
uv venv .venv
uv pip install -r requirements-dev.txt --python .venv
#   (yoki: python -m venv .venv; .\.venv\Scripts\pip install -r backend\requirements-dev.txt)

# 2) ishga tushirish (repo ildizidan)
cd ..
$env:PYTHONPATH="."
.\backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

Ochish: <http://127.0.0.1:8000> · API hujjati: <http://127.0.0.1:8000/docs>

**Demo hisoblar** (seed avtomatik yaratiladi):

| Email | Parol | Izoh |
|---|---|---|
| `abdurahmon@englify.uz` | `englify1234` | talaba (0 ball, 5 so'z, chat va bildirishnomalar bilan) |
| `englify@englify.uz` | `englify1234` | peshqadamlar jadvali 1-o'rni (3406 ball) |
| `sigma@englify.uz` … | `englify1234` | jadvaldagi qolgan demo hisoblar |

### CLI

```powershell
$env:PYTHONPATH="."
.\backend\.venv\Scripts\python.exe -m backend.manage serve            # dev server
.\backend\.venv\Scripts\python.exe -m backend.manage init-db          # jadvallarni yaratish
.\backend\.venv\Scripts\python.exe -m backend.manage seed             # seed (idempotent)
.\backend\.venv\Scripts\python.exe -m backend.manage reset-db         # tozalab qayta seed
.\backend\.venv\Scripts\python.exe -m backend.manage create-admin siz@englify.uz "Parol1234!" "Ali Valiyev"
.\backend\.venv\Scripts\python.exe -m backend.manage routes           # routelar ro'yxati
```

### Testlar

```powershell
$env:PYTHONPATH="."
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q
```

`backend/requirements-dev.txt` runtime kutubxonalar bilan birga pytest, httpx
va ruff'ni ham o'rnatadi. Ishlayotgan serverni tekshirish uchun
`GET /health/ready`, API shartnomasi uchun `/openapi.json` dan foydalaning.

Testlar vaqtinchalik SQLite bazasida ishlaydi va real serverga muhtoj emas.

---

## 4. Konfiguratsiya

Barcha sozlamalar muhit o'zgaruvchilari orqali. To'liq ro'yxat:
[`backend/.env.example`](backend/.env.example).

Eng muhimlari:

| O'zgaruvchi | Majburiy | Izoh |
|---|---|---|
| `DATABASE_URL` | productionda ✅ | `postgres://…` / `postgresql://…` — avtomatik `asyncpg`ga o'giriladi, `sslmode=require` qo'llab-quvvatlanadi |
| `PUBLIC_BASE_URL` | SMTP ishlatilganda ✅ | Railway domeni (`https://…`); parol tiklash havolalari shu manzilga boradi |
| `SECRET_KEY` | productionda ✅ | JWT imzosi. `python -c "import secrets;print(secrets.token_urlsafe(64))"` bilan yarating |
| `ENVIRONMENT` | — | `production` bo'lsa xato tafsilotlari yashiriladi |
| `CORS_ORIGINS` | — | `*` yoki vergul bilan ajratilgan ro'yxat (Vercel domeni va h.k.) |
| `AUTO_CREATE_TABLES` | — | default `true` — jadvallarni avtomatik yaratadi |
| `SEED_DEMO_DATA` | — | default `true` — demo kontentni yuklaydi |
| `SEED_DEMO_ACCOUNTS` | — | default `false`; Railway production’da demo parolli hisoblar yaratilmaydi |
| `EXPOSE_RESET_TOKEN` | — | **faqat lokal**. SMTP o'rnatilmagan ishlab chiqish muhitida tokenni javobda qaytaradi |
| `SERVE_FRONTEND` | — | default `true` — HTML sahifalarni ham shu servis beradi |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM_EMAIL` | — | Parol tiklash havolasini email orqali yuboradi; productionda email provayderi bilan sozlang |

> ⚠️ `SECRET_KEY`ni hech qachon repoga qo'ymang va `EXPOSE_RESET_TOKEN`ni
> productionda `true` qilmang.

---

## 5. API haqida qisqacha

To'liq, har doim aktual hujjat: **`/docs`** (Swagger UI) va `/openapi.json`.

| Guruh | Endpointlar |
|---|---|
| Auth | `POST /api/v1/auth/register` · `login` · `refresh` · `logout` · `change-password` · `forgot-password` · `reset-password`, `GET/PATCH /auth/me` |
| Foydalanuvchi | `GET /users/me/stats` · `/activity` · `/achievements` · `/streak` |
| Kurslar | `GET /courses` · `/courses/{slug}` · `POST /courses/{slug}/enroll` · `GET /lessons/{id}` · `POST /lessons/{id}/progress` · `GET/POST /lessons/{id}/quiz` · `GET /progress/continue` |
| Lug'at | `GET/POST /vocabulary` · `PATCH/DELETE /vocabulary/{id}` · `POST /vocabulary/{id}/review` · `/favorite` · `GET /vocabulary/stats` · `/due` · `POST /vocabulary/bulk` |
| Bildirishnoma | `GET /notifications` · `/unread-count` · `POST /notifications/{id}/read` · `/read-all` · `DELETE /notifications/{id}` |
| Chat | `GET/POST /chat/conversations` · `GET/POST /chat/conversations/{id}/messages` · `POST .../read` · `GET /chat/unread-count` |
| Reyting | `GET /leaderboard?period=all\|week&level=` |
| Jang | `POST /battles` · `GET /battles/{id}` · `POST /battles/{id}/join` · `/answer` · `/finish` · `/cancel` · `GET /battles/stats` · `/history` · `/{id}/result` |
| Tadbirlar | `GET /events` · `/week` · `/registrations` · `POST/DELETE /events/{slug}/register` |
| Kutubxona | `GET /books` · `/podcasts` · `/games` · `/levels` · `/library/summary` · `POST /games/{slug}/score` · `GET /games/{slug}/leaderboard` |
| Lead (landing forma) | `POST /api/v1/leads` (ochiq) |
| Realtime | `WS /api/v1/ws/chat/{id}` · `/ws/battles/{id}` · `/ws/notifications` |

Muhim xavfsizlik qarorlari:

* Test savollarining to'g'ri javoblari **clientga yuborilmaydi** — baholash
  faqat serverda (`POST /lessons/{id}/quiz`, `POST /battles/{id}/answer`).
* Jangda ball ham serverda hisoblanadi; AI raqibning javobi serverda generatsiya
  qilinadi.
* Zoom havolasi faqat tadbirga yozilgan foydalanuvchiga ko'rinadi.
* Login uchun bir xil xato xabari (email mavjudligini aniqlab bo'lmaydi) va
  ketma-ket xato urinishlardan keyin vaqtincha bloklash.
* Statik fayl serveri faqat ruxsat etilgan kengaytmalarni beradi va
  `backend/`, `.env`, `.git/` kabi yo'llarni to'sadi (testlar bilan qoplangan).

---

## 6. Railway'ga joylash

To'liq qo'llanma: **[`docs/DEPLOY-RAILWAY.md`](docs/DEPLOY-RAILWAY.md)**.

Qisqasi:

1. Railway'da loyiha yaratib, GitHub reponi ulang.
2. **Postgres** plugin qo'shing (`DATABASE_URL` avtomatik beriladi).
3. Servisga o'zgaruvchilarni qo'ying: `SECRET_KEY`, `ENVIRONMENT=production`,
   `SEED_DEMO_DATA=true` (demo kontent kerak bo'lsa).
4. Deploy. Healthcheck: `/health/ready` (PostgreSQL readiness tekshiruvi).

---

## 7. Litsenziya / egalik

Loyiha `abdurahmonpy/edu` repozitoriyasiga tegishli.
