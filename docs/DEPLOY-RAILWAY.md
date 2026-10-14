# Railway'ga joylash — qadam-baqadam qo'llanma

> Bu hujjat loyihani Vercel + statik holatdan **Railway'da ishlaydigan to'liq
> stack**ga (FastAPI + PostgreSQL, bitta servis) ko'chirishni tushuntiradi.

---

## 0. Avval bilib qo'ying: Railway'ning "tekin" tarifi

Railway'da doimiy **bepul** tarif yo'q. Hozirgi holat
([rasmiy hujjat](https://docs.railway.com/pricing/free-trial)):

| Tarif | Nima beradi | Cheklovlar |
|---|---|---|
| **Free Trial** (yangi hisob) | bir martalik **$5**, 30 kun | 1 GB RAM, umumiy (shared) vCPU, loyihada 5 servis |
| **Free** (trial tugagach) | oyiga **$1** kredit (o'tmaydi) | o'sha cheklovlar |
| **Hobby** | $5/oy, kredit tugagach to'lov | to'liq imkoniyat |

Muhim ikkita ogohlantirish:

1. **$5 krediti tugagach yoki 30 kun o'tgach** Free tarifga tushadi. Kichik
   ilova + Postgres odatda **$1/oydan ko'proq** iste'mol qiladi, ya'ni Free
   tarifda uzoq muddat ishlash kafolatlanmagan.
2. **Trial akkauntining volume'lari (ya'ni Postgres ma'lumotlari) kredit
   tugaganidan 30 kun o'tib o'chiriladi.** Ma'lumotni saqlab qolish uchun
   akkauntni Hobby'ga o'tkazish kerak. Shu sababli **doimiy backup** qiling
   (7-bo'limga qarang).

Xulosa: demo/portfolio uchun trial bepul, lekin haqiqiy o'quvchilar uchun
Hobby ($5/oy) tarifini rejalashtiring.

---

## 1. Reponi tayyorlash

Loyiha allaqachon Railway uchun tayyor:

| Fayl | Vazifasi |
|---|---|
| `Dockerfile` | konteyner: Python 3.12 + bog'lanishlar + butun frontend |
| `railway.json` | Eski Railway servislarida deploy sozlamalari uchun moslik fayli |
| `.dockerignore` | `.venv`, `*.db`, `.env` konteynerga tushmasligi uchun |
| `Procfile` + `requirements.txt` | Docker o'rniga **Nixpacks** ishlatmoqchi bo'lsangiz |
| `.python-version` | Nixpacks uchun Python 3.12 |
| `backend/.env.example` | barcha muhit o'zgaruvchilari |

Repo ildizidagi Dockerfile Railway tomonidan avtomatik aniqlanadi. Railway
`railway.json` Config as Code formatini **2026-12-01** dan keyin to'xtatadi va
yangi servislar unga tayanmasligi kerak. Yangi servisda Settings → Deploy
bo'limidan healthcheck path'ni `/health/ready`, timeout'ni `60` soniya qilib
qo'ying; start command'ni bo'sh qoldiring, shunda Dockerfile `CMD` ishlaydi.
[Railway konfiguratsiya yo'riqnomasi](https://docs.railway.com/config-as-code/reference).

Avval o'zgarishlarni GitHub'ga yuboring:

```powershell
git add .
git commit -m "feat: FastAPI backend, auth, PostgreSQL va Railway deploy"
git push origin main
```

> `.gitignore` `.env`, `*.db` va `.venv/` ni allaqachon istisno qiladi —
> ularni commit qilmang. `git status` bilan tekshiring.

---

## 2. Railway loyihasi va PostgreSQL

1. <https://railway.com> da GitHub bilan kiring (**GitHub'ni ulash muhim**:
   aks holda "Limited Trial" bo'lib, tashqi tarmoq cheklanadi).
2. **New Project → Deploy from GitHub repo** → `abdurahmonpy/edu` ni tanlang.
3. Loyiha ichida **+ Create → Database → Add PostgreSQL** ni bosing.
4. Endi loyihada 2 servis bor: repongiz va `Postgres`.

---

## 3. Servis o'zgaruvchilari

Repo servisiga o'tib **Variables** bo'limiga quyidagilarni kiriting:

| O'zgaruvchi | Qiymat | Izoh |
|---|---|---|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Railway havolasidan nusxa olish shart emas — bu shablon o'zi to'ldiradi |
| `SECRET_KEY` | uzun tasodifiy satr | **majburiy**, pastga qarang |
| `ENVIRONMENT` | `production` | xato tafsilotlarini yashiradi |
| `PUBLIC_BASE_URL` | `https://<Railway domeni>` | SMTP bilan parol tiklash emaili yuborilsa kerak |
| `CORS_ORIGINS` | `https://<sizning-vercel-domeningiz>` | Vercel'ni ishlatishda; aks holda `*` |
| `SEED_DEMO_DATA` | `true` | prototip kontenti (kurslar, kitoblar, jang savollari); idempotent |
| `SEED_DEMO_ACCOUNTS` | `false` | **productionda `false` qoldiring**; demo parollar bilan hisoblar yaratmaydi |
| `AUTO_CREATE_TABLES` | `true` | jadvallarni avtomatik yaratadi |
| `SERVE_FRONTEND` | `true` | HTML sahifalarni ham shu servis beradi |
| `EXPOSE_RESET_TOKEN` | `false` | **productionda albatta `false`** |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` | email provayderingizdan | Parol tiklash havolasini email orqali yuborish uchun |

`SECRET_KEY` yaratish:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

> **`DATABASE_URL` haqida:** kod `postgres://`, `postgresql://` va
> `postgresql+asyncpg://` ko'rinishlarini avtomatik to'g'rilaydi, shuningdek
> `sslmode=require` ni `asyncpg` tushunadigan ko'rinishga o'giradi. Railway'dagi
> ichki (`postgres.railway.internal`) va tashqi (`…railway.app`) manzillar
> ikkalasi ham ishlaydi.

---

## 4. Deploy va domen

1. **Deploy** tugmasini bosing (yoki `git push` bilan avtomatik boshlanadi).
2. **Settings → Networking → Generate Domain** orqali ommaviy domen oling:
   `https://edu-production-xxxx.up.railway.app`
3. Deploy tugagach quyidagilarni tekshiring:

```
https://<domen>/health        → {"status":"ok","database":"postgresql",...}
https://<domen>/health/ready  → {"status":"ready","database":"up"}
https://<domen>/docs          → Swagger UI (barcha endpointlar)
https://<domen>/              → landing sahifa
https://<domen>/app           → student app (kirish sahifasiga yo'naltiradi)
https://<domen>/kirish        → login sahifasi
```

Agar `/health/ready` `"database":"down"` qaytarsa — `DATABASE_URL`
o'zgaruvchisi va Postgres servisi holatini tekshiring (Deploy Logs).

---

## 5. Birinchi kirish

Production'da `/kirish` orqali foydalanuvchi hisobini ro'yxatdan o'tkazing.
`SEED_DEMO_ACCOUNTS=false` bo'lgani uchun hammaga ma'lum demo parollar ishlab
turgan servisda yaratilmaydi. Lokal muhitda `.env.example` demo hisoblarni
yoqadi:

| Email | Parol |
|---|---|
| `abdurahmon@englify.uz` | `englify1234` |
| `englify@englify.uz` | `englify1234` |

Production admin hisobini birinchi foydalanuvchi hisobingizni ro'yxatdan
o'tkazgandan keyin `create-admin` CLI bilan yarating.
Demo katalog kontenti kerak bo'lmasa `SEED_DEMO_DATA=false` qilib qo'ying.

Admin yaratish (Railway'da **Shell** yoki lokalda `DATABASE_URL` bilan):

```bash
python -m backend.manage create-admin siz@englify.uz "KuchliParol123!" "Ali Valiyev"
```

---

## 6. Vercel'dan ko'chish

Ikki yo'l bor.

### A) Hammasi Railway'da (tavsiya etiladi — eng sodda)

Railway bitta servisda ham API, ham HTML beradi. Vercel'dagi `vercel.json` shart
emas. Domen sifatida Railway domenini ishlating yoki o'z domeningizni
(`englify.uz`) CNAME bilan Railway'ga bog'lang:

```
A     @      <Railway bergan IP yoki ALIAS>
CNAME www    <domen>.up.railway.app
```

Vercel loyihasini o'chirib qo'yishingiz mumkin.

### B) Frontend Vercel'da qoladi, API Railway'da

Bu holda sahifalar API manzilini bilishi kerak. `index.html` va boshqa
sahifalardagi `<meta name="englify-api" content="">` tegiga Railway domenini
yozing:

```html
<meta name="englify-api" content="https://edu-production-xxxx.up.railway.app">
```

Shundan keyin:

1. Railway'da `CORS_ORIGINS` ga Vercel domenini qo'shing:
   `CORS_ORIGINS=https://edu-eng.vercel.app`
2. Vercel'dagi `vercel.json` ni shunday qilib qo'ying (API va WebSocket'ni
   proksi qilish shart emas, lekin xohlasangiz):

   ```json
   {
     "cleanUrls": true,
     "rewrites": [
       { "source": "/api/:path*", "destination": "https://edu-production-xxxx.up.railway.app/api/:path*" }
     ]
   }
   ```

> `CORS_ORIGINS=*` qo'yilganda `allow_credentials` o'chiriladi — bu to'g'ri,
> chunki autentifikatsiya `Authorization: Bearer` sarlavhasi orqali ishlaydi,
> cookie ishlatilmaydi.

---

## 7. Backup va ma'lumot xavfsizligi

Trial volume'lari o'chirilishi mumkinligi sababli muntazam backup qiling.

**Qo'lda dump olish** (Railway Postgres servisidagi `DATABASE_URL` bilan,
lokal kompyuterda):

```powershell
# pg_dump o'rnatilgan bo'lishi kerak (PostgreSQL client)
pg_dump "postgresql://postgres:PAROL@HOST:PORT/railway" -Fc -f englify-backup.dump
```

**Tiklash:**

```powershell
pg_restore -d "postgresql://postgres:PAROL@HOST:PORT/railway" --clean --if-exists englify-backup.dump
```

**Avtomatlashtirish:** Railway'da Cron servis qo'shib yoki GitHub Actions
workflow bilan kunlik `pg_dump`ni S3/Google Drive'ga saqlang.

Bundan tashqari:

* `SECRET_KEY`ni xavfsiz saqlang — u bilan barcha refresh tokenlar bog'liq.
  O'zgartirsangiz hamma foydalanuvchi qaytadan kiritishi kerak bo'ladi.
* `EXPOSE_RESET_TOKEN=false` bo'lsin. Parol tiklash emaili ishlashi uchun
  `SMTP_HOST`, `SMTP_FROM_EMAIL` va `PUBLIC_BASE_URL` sozlangan bo'lsin.
* `backend/.env` faylini repoga hech qachon qo'shmang.

---

## 8. Muammolarni bartaraf etish

| Belgi | Sabab / yechim |
|---|---|
| Deploy logida `ModuleNotFoundError: backend` | Ildiz katalog noto'g'ri. Railway **Root Directory** ni bo'sh (repo ildizi) qoldiring. |
| `/health/ready` → `database: down` | `DATABASE_URL` yo'q yoki Postgres hali ko'tarilmagan. `DATABASE_URL=${{Postgres.DATABASE_URL}}` ekanini tekshiring, keyin qayta deploy qiling. |
| `InvalidPasswordError` / `password authentication failed` | Parolda `@` yoki `:` kabi belgilar bo'lsa URL-encode qilinishi kerak. Railway bergan havolani to'g'ridan-to'g'ri ishlatsangiz bu muammo bo'lmaydi. |
| `ssl is required` xatosi | `DATABASE_URL` oxiriga `?sslmode=require` qo'shing — kod uni avtomatik `ssl` ga o'giradi. |
| Sahifa ochiladi, lekin ma'lumot kelmaydi | Brauzer konsolida API xatosini ko'ring. Vercel'dan foydalansangiz `CORS_ORIGINS` va `<meta name="englify-api">` to'g'rimi? |
| `/app` 404 qaytaradi | Statik handler `cleanUrls`ni qo'llab-quvvatlaydi; bu xato bo'lsa `SERVE_FRONTEND=true` va `static_dir` to'g'riligini tekshiring. |
| Login ishlamaydi, `401` | Production'da demo hisoblar ataylab o'chirilgan. `/kirish` orqali o'zingiz ro'yxatdan o'ting. |
| WebSocket ulanmaydi | Railway HTTPS'da `wss://` ishlatiladi — `api.js` buni avtomatik qiladi. Proksi orqasida `--proxy-headers` yoqilgan (Dockerfile'da bor). |
| 429 `Juda ko'p so'rov` | Rate limit ishlayapti. Kerak bo'lsa `RATE_LIMIT_REQUESTS` ni oshiring. |

Foydali buyruqlar (Railway CLI):

```bash
railway login
railway link
railway logs                 # real vaqtda loglar
railway variables            # o'zgaruvchilarni ko'rish
railway run python -m backend.manage routes
railway up                   # lokal papkadan deploy
```

---

## 9. Build sozlamasi

Repo ildizidagi `Dockerfile` Railway'da avtomatik aniqlanadi. Docker image
Python 3.12 asosidan quriladi; Python kutubxonalari `backend/requirements.txt`
dan o'rnatiladi. Build'ni GitHub branch'ga ulab avtomatlashtirish yoki CLI'dan
`railway up` bilan bajarish mumkin. Ilk deploy uchun Railway rasmiy yo'riqnomasiga
qarang: [Dockerfile deploy](https://docs.railway.com/builds/dockerfiles).
