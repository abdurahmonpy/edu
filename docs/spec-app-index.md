# Technical Spec — `app.html` (Englify Student App) & `index.html` (Englify.uz marketing site)

Read-only analysis. Source files were **not** modified.
Scope: exactly two files — `app.html` (427 lines) and `index.html` (853 lines).

- `app.html` = single-page student application shell (4 tab panes, desktop sidebar + mobile bottom nav, 1 inline script at L409–425).
- `index.html` = single-page public marketing/landing site (11 `<section>` + footer, 1 inline script at L806–851).

---

## 0. Platform-wide facts

- **No build step, no framework, no external JS.** All styling is inline `style="..."` + two `<style>` blocks per file. Only external resource: Google Fonts (Outfit; + Bebas Neue on `index.html`) — `app.html` L9–10, `index.html` L9–10.
- **No network code at all.** Zero `fetch`/`XMLHttpRequest`/`localStorage`/`sessionStorage`/`WebSocket`/`FormData` in either file. Everything is static or faked client-side.
- **No `<form>` in `app.html`.** `index.html` has exactly one `<form>` (L137) with `onsubmit="return false"` — the browser's native submit is deliberately neutered.
- Lang `uz` on both. Theme color `#0A93F5` (`app.html` L8) / `#0A93F5` (`index.html` L8).
- Design tokens: `--sky:#0A93F5` (app) / `#0A82EA` (index), `--ink:#2A0B5C`, `--violet:#6B3FD8`, `--mint:#35F59A`, `--mintdk:#17C877`, `--line:#DDE3FF`.
- "3D pressed card" pattern: `.p3` (`app.html` L51–55) — pure CSS, no JS.
- Reduced-motion support: `@media (prefers-reduced-motion: reduce)` kills all animation/transition — `app.html` L133–135, `index.html` L102–104.
- All page-to-page links are plain relative `.html` files. All referenced targets **exist on disk** (`chat.html`, `dars.html`, `jang.html`, `kitoblar.html`, `level.html`, `lugat.html`, `notifications.html`, `oyinlar.html`, `peshqadam.html`, `podcastlar.html`, `zoom.html`) → **no broken links**, but several UI affordances point nowhere (see §5, §6).

---

# PART 1 — `index.html` (Englify.uz marketing site)

## 1.1 Distinct UI features / screens / sections (in DOM order)

| # | Section `.rv > section:nth-of-type(n)` | Lines | Heading (Uzbek) | English gloss |
|---|---|---|---|---|
| 0 | Floating sticky nav (`#nhead`) + scroll progress bar (`#prog`) | L111–125 | — | Pill navbar: logo, 4 anchors, "Student App" CTA, top scroll-progress bar that shrinks nav padding after 24px scroll |
| 1 | `#top` — Hero / "General English" | L131–174 | General English | Hero: headline + subtitle, **lead registration form**, teacher illustration, tilted phone mockup |
| 2 | (no id) Student stories | L177–211 | O'quvchilarimiz hikoyalari | "Our students' stories" — horizontal scroll strip of 4 video-testimonial cards, each with a play button |
| 3 | `#natijalar` | L212–375 | O'quvchilarimizning natijalari | "Our students' results" — 12-card auto-scrolling marquee mixing certificate and IELTS-score images |
| 4 | `#izohlar` | L378–485 | O'quvchilarning izohlari | "Student reviews" — 10-card reverse-scrolling marquee of chat/app screenshot cards |
| 5 | (no id) Opportunities | L488–511 | Imkoniyatlar — ajoyib! | "Opportunities — great!" — 6 benefit cards + green CTA |
| 6 | `#maktab` | L514–570 | Sizni nima kutmoqda? | "What awaits you?" — 6 feature cards + green CTA (this is the "About the school" target of the nav) |
| 7 | (no id) Audience | L573–611 | Kurslarimiz aynan siz uchun | "Our courses are exactly for you" — 6 colored persona cards + green CTA |
| 8 | (no id) Mentors | L614–672 | Mentorlarimiz | "Our mentors" — 4 mentor profile cards in a horizontal scroller |
| 9 | `#ilova` | L675–698 | Englify (app block) | "App" promo: brand, blurb, App Store / Google Play QR cards, tilted phone mockup |
| 10 | `#tariflar` | L701–737 | Hamma uchun qulay tarif turlari va narxlar | "Convenient plans and prices for everyone" — 3 pricing cards (Standart / Premium / Individual) |
| 11 | (no id) FAQ | L740–787 | Ko'p beriladigan savollar | FAQ accordion, 4 questions |
| — | `footer#aloqa` | L790–804 | Aloqa | Contact/footer with brand, tagline, 4 contact lines (not a `<section>`) |

Notes:
- Sections 2 and 4 are force-visible (`.rv>#natijalar>div,.rv>#izohlar>div{opacity:1}`, L80); all others use the `.rv[data-seen~=n]` IntersectionObserver reveal mechanism (L44–64).
- Sections 5, 6, 7, 8, 11 have **no `id`** → cannot be deep-linked (nav only reaches `#top`, `#maktab`, `#tariflar`, `#aloqa`, `#natijalar`).

## 1.2 Hardcoded / placeholder data (exact strings + purpose)

**Hero (`#top`)**
- L160 `[O'QITUVCHI RASMI]` — white pill label over the SVG teacher silhouette; placeholder for the instructor hero photo.
- L163–170 phone mockup content: L165 `Salom, [Ism]` (greeting placeholder for user first name), L166 `Zoom darslar` (card label), L167 `Uy vazifalari` (card label), L168 `Yangi so'zlar` (card label).
- L137–151 the whole registration form is a static mock (see §1.4).
- L157 decorative blob `background:#3DA2F6`; L159 generic SVG person (no real photo).

**Student stories (L177–211)**
- 4 identical cards; L186, L193, L200, L207 name pill = `[Ism]` (4×) — placeholder for student name.
- L185, L192, L199, L206 play buttons `aria-label="Videoni ko'rish"` (no `data-*`, no video source) — placeholder for testimonial video.
- L184/191/198/205 generic SVG silhouettes; L183/190/197/204 flat background colors stand in for poster images.

**Results (`#natijalar`, L212–375) — 12 cards**
- Certificate-type cards (6×): L218, L231, L244, L296, L309, L322 → `[SERTIFIKAT RASMI]` — placeholder caption for a certificate image.
- IELTS-type cards (6×): L257, L270, L283, L335, L348, L361 → `[IELTS NATIJASI]` — placeholder caption for an IELTS result image.
- Every card (12×): L227, L240, L253, L266, L279, L292, L305, L318, L331, L344, L357, L370 → `[F.I.SH.]` — placeholder for full name (F.I.Sh. = Familiya, Ism, Sharif).
- L220–226, L233–239, … repeated grey bars / 4-cell grid = fake certificate-layout skeleton, no real content.

**Reviews (`#izohlar`, L378–485) — 10 cards**
- L390, L400, L410, L420, L430, L440, L450, L460, L470, L480 → `[IZOH SKRINSHOTI]` — placeholder for a review screenshot.
- L384–389 etc. = fake chat bubbles (alternating left/right colored bars), no text at all.

**Opportunities (L488–511)** — 6 real Uzbek sentences, L496–506 (benefits). Static copy, no placeholders.

**What awaits (`#maktab`, L514–570)** — 6 real feature cards:
- L522 `Onlayn format`; L530 `Uy vazifasi bo'yicha doimiy fikr-mulohaza`; L538 `Guruhlar`; L546 `Sertifikatlar`; L554 `Interaktiv platforma va shaxsiy akkaunt`; L562 `Haqiqiy amerikancha darslar`.
- **L564 placeholder inside body copy:** `Serial ko'rinishidagi qisqa videodarslar: [5–10] daqiqa.` — `[5–10]` is an unfilled duration range.
- All 6 cards reuse the same decorative star SVG icon (L521, 529, 537, 545, 553, 561) → real icons are planned per-card.

**Audience (L573–611)** — 6 real persona cards: L579 `Abituriyentlar`, L584 `Havaskorlar`, L589 `Ma'lum kasb egalari`, L594 `Maktab o'quvchilari`, L599 `Talabalar`, L604 `Chet eldagi yurtdoshlarimiz`. Hardcoded pastel `background`/`border` colors per card.

**Mentors (L614–672) — 4 cards, fully placeholder identity data:**
- L627, L639, L651, L663 → `MR. [ISM]` — mentor name placeholder (note: "MR." prefix hardcoded, no gender handling).
- L628, L640, L652, L664 → `English Instructor` — role (same for all 4).
- L629, L641, L653, L665 → `Teaching Experience: [N]+ years` — placeholder for years of experience.
- L630, L642, L654, L666 → `Certifications: IELTS [X.X]` — placeholder for IELTS band score (e.g. 8.5).
- L624, L636, L648, L660 → generic silhouette SVG; backgrounds `#7CC8F5`, `#E04747`, `#F5B52E`, `#7FE0F2`; watermark text `ENGLIFY` (L623 etc.).

**App block (`#ilova`, L675–698)**
- L682 App Store QR: `role="img" aria-label="[QR-KOD]"` + checkerboard `repeating-conic-gradient` CSS pattern → placeholder for a real QR image.
- L683 Google Play QR: same `[QR-KOD]` placeholder.
- L689 `Hi, [Ism]!` — phone-mockup greeting placeholder.
- L690 `Zoom events`, L691 `Leaderboard`, L692 `Yangi so'zlar` — mockup card labels (English/Uzbek mixed).
- No store links (`href`) on either QR card — they are `<div>`s.

**Pricing (`#tariflar`, L701–737) — 3 plans:**
- L706 `Standart`, L716 `Premium` (+ L716 badge `Ommabop` = "Popular"), L726 `Individual`.
- Price placeholders `[NARX]` at L707 (`Standart`), L717 (`Premium`), L727 (`Individual`), each followed by `so'm / oy` (L707, L717, L727).
- Feature bullets L709–711, L719–721, L729–731 are hardcoded text.
- CTAs `Tanlash` (L713, L723, L733) all link to `#top` only — no checkout.

**FAQ (L740–787) — 4 items:**
- Q L747 `Darajam past bo'lsa ham boshlay olamanmi?` / A L751 `Ha. Birinchi bosqichda darajangiz aniqlanadi va sizni noldan boshlaydigan guruhga qo'shamiz.`
- Q L757 `Darslar qaysi platformada o'tadi?` / A L761 `Darslar Zoom orqali jonli o'tadi, video darslar va vazifalar Englify ilovasida joylashgan.`
- Q L767 `Darsni o'tkazib yuborsam nima bo'ladi?` / A L771 `Darsni ilovadan qayta ko'rishingiz mumkin. [SHARTLARNI TEKSHIRING]` ← **placeholder `[SHARTLARNI TEKSHIRING]`** ("check the terms").
- Q L777 `To'lov qanday amalga oshiriladi?` / A L781 `To'lov usullari: [Payme / Click / bank kartasi].` ← **placeholder payment-method list**.

**Footer / contact (`#aloqa`, L790–804) — all 4 contact values are placeholders:**
- L798 `Telefon: [+998 __ ___ __ __]`
- L799 `Telegram: [@englify]`
- L800 `Instagram: [@englify.uz]`
- L801 `Manzil: [MANZIL]`
- L794 tagline mentions the hardcoded domain `englify.uz`.

**Hardcoded layout values that leak into markup (must be replaced by dynamic layout data):**
- L178 `<h2 … height: 123px>` and the wrapper `width: 991px; height: 597px` — fixed pixel box for the stories strip, will break with a different number of cards.
- L182/189/196/203 `width:224px;height:400px`; L217+ `width:224px;height:320px`; L383+ `width:190px;height:400px`; L622+ `width:250px;height:420px` — fixed card sizes, counts are hardcoded (4 / 12 / 10 / 4).
- L623, 635, 647, 659 watermark `ENGLIFY`, colours `#7CC8F5 #E04747 #F5B52E #7FE0F2`.

## 1.3 Interactive JS behaviour (`index.html` L806–851, one IIFE)

| Line | Handler | What it does |
|---|---|---|
| L810–816 | `onScroll()` (function) | Computes `y/max*100`, writes `prog.style.width` (0–100%); when `y>24` switches `#nhead` padding from `12px 14px 12px 28px` to `7px 10px 7px 22px`; early-returns if `max<200`. |
| L817 | `window.addEventListener('scroll', onScroll, {passive:true})` | Binds the above; also calls `onScroll()` once on load. |
| L820–829 | IntersectionObserver over `.rv > section` | Builds a `seen` map of visible section indices and writes `data-seen="1 2 5 …"` on `.rv` (L821). `threshold:0.1`, `rootMargin:'0px 0px -6% 0px'` (L827). Each section observed once then unobserved (L825). Fallback without IO (L829): marks **all** sections seen → no reveal animation. This drives the `.rv[data-seen~="n"]>section:nth-of-type(n)>div` CSS reveal (L47–56) and `.hov` pop-in (L59–64). |
| L832–841 | `document.querySelectorAll('.faqb')` + `click` listener per button | FAQ accordion. On click: closes **all** `.faqb` (sets `aria-expanded=false`, swaps last-child glyph to `+`, hides the sibling `<p>`), then if the clicked one was not already open, opens it (`aria-expanded=true`, glyph `−`, unhide `<p>`). Behaviour is **single-open / exclusive**. State lives only in `aria-expanded` + `hidden`; no URL/deep-link. |
| L844–849 | `btn = #send`, `click` listener | Fake form submit. Sets button text to `Yuborildi! Tez orada bog'lanamiz` (`data-sent="yes"`), then after **3200 ms** restores `Ro'yxatdan o'tish` / `data-sent="no"`. **Does not read `#f-name` or `#f-phone`, does not validate, does not send anything.** |
| — | `<form onsubmit="return false">` (L137) | Blocks native submit so Enter/press-submit does nothing (dead path, see §5). |
| — | CSS-only interactions | `.mq:hover .mt{animation-play-state:paused}` (L77) pauses marquees; `.hov:hover` lift (L71); `.hovc:hover` lift+shadow (L79); green CTA `:hover/:active` transform (L84–85); `a[href="#ilova"]` hover (L90); `html{scroll-behavior:smooth}` (L15) for anchor nav; `[data-sent="yes"]{animation:popBtn}` (L88). |
| — | **Marquee implementation vs comment mismatch** | L73 comment claims results/reviews do **not** auto-rotate, but `.mt{animation:marquee 50s linear infinite}` (L75) auto-scrolls both; `.mt.rev` (L76) reverses the review strip. Documented as an inconsistency. |

## 1.4 Forms & inputs (`index.html`)

Single form at **L137–151** (`onsubmit="return false"`):

| Element | Line | Type | Name/id | Label | Purpose |
|---|---|---|---|---|---|
| `<input id="f-name">` | L140 | `text` | `f-name` (no `name` attr) | `Ismingiz va Familiyangiz` (L139 `<label for="f-name">`) + `placeholder="Ismingiz va Familiyangiz"` | Full name of the lead |
| `<select aria-label="Davlat kodi">` | L145 | select | none (`name`/`id` absent) | `aria-label="Davlat kodi"` = "country code" | Phone country dialing code. **Only one `<option>UZ</option>`** — no other countries, no value attribute |
| `<input id="f-phone">` | L146 | `tel` | `f-phone` (no `name` attr) | none (label `Telefon raqamingiz` at L143 wraps the whole composite field, not `for=`) | Phone number; `value="+998"` hardcoded prefix |
| `<button type="button" id="send" data-sent="no">` | L149 | button (not submit) | `send` | text `Ro'yxatdan o'tish` = "Register" | Triggers the fake-success handler (L845). **`type="button"` → never submits the form** |
| Consent text | L150 | — | — | `Tugmani bosish orqali siz <a href="#top">ommaviy offertamizga</a> rozilik bildirasiz!` | Consent notice; the offer link points to `#top` (self) — **no offer/terms page** |

Submit behaviour: nothing is sent; no validation; no error/required states (`required` attribute absent); no phone mask. Enter key inside `#f-name`/`#f-phone` triggers form submit → suppressed by `onsubmit="return false"` → **no-op**.

Other clickable-but-non-functional controls on `index.html`:
- L185/192/199/206 — 4× `button[aria-label="Videoni ko'rish"]` ("watch video"): **NO handler, no video, dead UI**.
- 12× results marquee cards, 10× review cards are `<div class="hovc">` with `cursor:pointer` and hover lift but **no click handler** (dead UI).
- L509, L568, L609 `Ishtirok etish!` ("Participate!"), L713/723/733 `Tanlash` ("Choose"), L150 offer link → all only `href="#top"` (scroll to hero; the pricing/CTA links do **not** preselect a plan or scroll to the form).
- QR cards L682/L683 are non-interactive `<div>`s (no store links).

## 1.5 Navigation links (`index.html`)

| Line | Label | Target | Type |
|---|---|---|---|
| L115 | `Englify` (logo) | `#top` | in-page anchor |
| L117 | `Maktab haqida` ("About the school") | `#maktab` | in-page anchor |
| L118 | `Tariflar` ("Plans") | `#tariflar` | in-page anchor |
| L119 | `Aloqa` ("Contact") | `#aloqa` | in-page anchor |
| L120 | `Natijalar` ("Results") | `#natijalar` | in-page anchor |
| L122 | `Student App` (primary CTA) | **`app.html`** | cross-page |
| L150 | `ommaviy offertamizga` ("public offer") | `#top` | in-page anchor — **wrong target; an offer/terms page is planned but absent** |
| L509, L568, L609 | `Ishtirok etish!` | `#top` | in-page anchor |
| L713, L723, L733 | `Tanlash` | `#top` | in-page anchor |
| L89–90 | CSS selector `a[href="#ilova"]` exists | — | **no element in the document actually links to `#ilova`** — a nav "App" link is planned but missing (§6) |

## 1.6 Missing / planned pages & anchors referenced but absent (`index.html`)

- No page for the **public offer / terms** (`ommaviy oferta`) — consent link is a dead self-anchor (L150).
- No page for **payment** (`Payme / Click / bank kartasi` unresolved, L781).
- No **App Store / Google Play** URLs anywhere (L682–683 are div mockups).
- No `id` on the Opportunities (L488), Audience (L573), Mentors (L614) or FAQ (L740) sections → not linkable from nav.
- No nav entry for `#izohlar` or `#ilova` even though those ids exist.
- No "login" / "sign in" entry point anywhere — only "Student App" → `app.html`.
- No phone-country list beyond `UZ` (L145).
- No privacy policy / personal-data-consent page.

---

# PART 2 — `app.html` (Englify Student App)

## 2.1 Distinct UI features / screens / sections

Structure: `.app[data-tab="0"]` (L141) contains `aside.side` (desktop ≥960px, L145–176) + `.main` (L178–394, holding 4 panes) + bottom floating nav `.bnav` (mobile <960px, L397–407).

### Navigation chrome
| Feature | Lines | Uzbek | English gloss |
|---|---|---|---|
| Desktop sidebar + logo | L145–176 | `englify`, `MENYU`, `TEZKOR HAVOLALAR` | Sidebar: logo → index, "MENU" nav with sliding blue indicator (`.sind` L150), "QUICK LINKS" list, green CTA, user chip, back link |
| Desktop nav items | L151–154 | `Asosiy`, `Darslar`, `Resurslar`, `Ko'proq` | Home / Lessons / Resources / More — `data-go` = 0,1,2,3 |
| Quick links | L159–164 | `Jang`, `Mening lug'atim`, `Suhbatxona (Chat)`, `Bildirishnomalar`, `Zoom tadbirlar`, `Peshqadamlar` | Battle, My dictionary, Chat, Notifications, Zoom events, Leaderboard |
| Sidebar CTA | L169 | `Darsni davom ettirish` | "Continue lesson" → `data-go="1"` (Lessons tab) |
| User chip | L171–174 | `Talaba` / `0 ball · Starter` | Student avatar + name + points & level |
| Back link | L175 | `← englify.uz saytiga qaytish` | Back to marketing site → `index.html` |
| Mobile bottom nav | L397–407 | `Asosiy/Darslar/Resurslar/Ko'proq` | Floating pill bottom nav with sliding circular indicator (`.nind` L400) |

### Pane 0 — `data-pane="0"` "Asosiy" (Home), L181–271
1. **Blue hero header** (L183–203): decorative cloud SVGs (L184–185); mobile back pill `← englify.uz` (L187); avatar + greeting `Salom, Talaba!` (L189–190); chat icon button → `chat.html` (L191); notifications icon button → `notifications.html` with red unread dot (L192).
2. **5 skill progress bars** (L195–201): `VOCABULARY`(L196) / `WRITING`(L197) / `READING`(L198) / `LISTENING`(L199) / `GRAMMAR`(L200). Labels collapse to `VOCAB`/`LISTEN` on mobile via `.lfull`/`.lshort`. Each has a `[%]` readout + an animated bar with a **fixed decorative height** (46 %, 72 %, 58 %, 84 %, 64 %).
3. **Quick-launch tile grid** (L209–218, 8 tiles): `Suhbatxona`→chat.html (L210), `Bildirishnoma`→notifications.html (L211), `Level Podcast`→podcastlar.html (L212), `Marketplace` (L213, button — no handler), `Alomat bot` (L214, button — no handler), `Tarjimon` (L215, button — no handler), `System Control` (L216, button — no handler), `Exclusive` (L217, button — no handler). Animations deliberately disabled by `.tgrid` CSS (L76–78).
4. **Feature card grid** (L220–267):
   - **Jang** card L222–231 → `jang.html`; stat pill L225–229: `Janglar:` `0` (L226), `Yutuqlar:` `0` (L227), `Mag'lubiyat:` `0` (L228).
   - **Mening lug'atim** card L234–242 → `lugat.html`; badge L236 `Hali so'zlar yo'q` ("No words yet"); decorative sample word card L239: `001 · [noun]`, `Teacher`, `A teacher inspires students.`
   - **Zoom tadbirlar** card L245–249 → `zoom.html` (title only, **no event data at all**).
   - **Peshqadamlar** card L252–266 → `peshqadam.html`; title L254 `Peshqadamlar jadvali`; 3 floating avatars L256–258 (2 silhouettes + 1 `Englify` circle); row #1 L261–265: silhouette avatar, `Talaba` (L263), lightning icon + `0` (L264).

### Pane 1 — `data-pane="1"` "Darslar" (Lessons), L274–351
1. **Header bar** L276–285: `h1 Darslar` L278; three stat chips — streak flame with title `Kunlik seriya` and value `0` (L280), `0 ball` (L281, points), `0 tanga` (L282, coins).
2. **Lesson path** L286–330: SVG 460×1000 dashed connector path (L289–296); level header `Starter` / `0%` (L297); decorative clouds/stars (L299–306).
   - `Unit 1.1` **active** L309–311 → `dars.html`, inner label `4%` (L310), pulsing ring (`.pulse`).
   - Tooltip L312 `Sizning darsingiz shu yerda` ("Your lesson is here") + hand-drawn arrow L313.
   - **Locked** nodes (grey + padlock badge, `.lock` = `cursor:not-allowed` + shake on hover): `Unit 1.2` L316–317, `Unit 1.3` L320–321, `Unit 2.1` L324–325, `Unit 2.2` L328–329.
3. **Desktop aside** `.laside` L333–348 (hidden <960px):
   - `JORIY DARAJA` (Current level) L334–339: `Starter` + `0%`, progress bar `width:4%` (L337), `Keyingi daraja: Elementary` (L338).
   - `KEYINGI DARS` (Next lesson) L341–347: `Unit 1.1` (L344), `Greetings & Introductions · ~10 daqiqa` (L345), CTA `Darsni boshlash` (L346) → `dars.html`.

### Pane 2 — `data-pane="2"` "Resurslar" (Resources), L354–374
- `h1 Resurslar` L357. Four big cards: `O'yinlar` → `oyinlar.html` (L360), `Level` → `level.html` (L363), `Kitoblar` → `kitoblar.html` (L366), `Podkastlar` → `podcastlar.html` (L369). No sub-counts, no content lists.

### Pane 3 — `data-pane="3"` "Ko'proq" (More), L377–391
- `h1 Ko'proq` L380. Six rows, **five of them dead**:
  - L383 `Xaridlar` (Purchases) — `<button>`, no handler.
  - L384 `Tarjimon` (Translator) — `<button>`, no handler.
  - L385 `FAQ` — `<button>`, no handler.
  - L386 `Biz haqimizda` (About us) — `<button>`, no handler.
  - L387 `Sozlamalar` (Settings) — `<button>`, no handler.
  - L388 `Chiqish` (Log out) — the only `<a href="index.html">`; **no auth/session logic**, just navigates to the marketing site.

## 2.2 Hardcoded / placeholder data (exact strings + purpose) — `app.html`

| Line(s) | Exact placeholder | Purpose / element |
|---|---|---|
| L173 | `Talaba` | Sidebar user chip display name (generic "Student"); **not** a real logged-in user. |
| L173 | `0 ball · Starter` | Sidebar user chip subtitle — points total + CEFR level, both hardcoded. |
| L190 | `Salom, Talaba!` | Home hero greeting; name is hardcoded, no first-name interpolation. |
| L192 | red dot `<span>` (no text) | Notification unread badge — **always rendered, never conditional**. |
| L196, L197, L198, L199, L200 | `[%]` (5×) | Skill-percentage readout for VOCABULARY / WRITING / READING / LISTENING / GRAMMAR. |
| L196–L200 | bar heights `46%`, `72%`, `58%`, `84%`, `64%` | Decorative fake progress values; must be driven by real per-skill progress. |
| L226 | `Janglar:` / `0` | Total battles played = 0. |
| L227 | `Yutuqlar:` / `0` | Battles won = 0. |
| L228 | `Mag'lubiyat:` / `0` | Battles lost = 0. |
| L236 | `Hali so'zlar yo'q` | Empty-state for "My dictionary" (no saved words) — the empty state itself is the only state implemented. |
| L239 | `001 · [noun]` | Fake dictionary card: ordinal `001` + part-of-speech `[noun]` placeholder. |
| L239 | `Teacher` | Fake dictionary headword. |
| L239 | `A teacher inspires students.` | Fake example sentence. |
| L257 | `Englify` | Placeholder avatar in the leaderboard preview (brand circle instead of a user avatar). |
| L263 | `Talaba` | Leaderboard row #1 display name (same generic placeholder as L173). |
| L264 | `0` | Leaderboard row #1 score (lightning icon = points). |
| L280 | `0` (with `title="Kunlik seriya"`) | Daily streak counter. |
| L281 | `0 ball` | Points balance chip in Lessons header. |
| L282 | `0 tanga` | Coin balance chip in Lessons header. |
| L297 | `Starter` | Level path header title. |
| L297 | `0%` | Level progress readout in the path header — **inconsistent with** the `4%` on the active node (L310) and the `4%`-wide bar (L337). |
| L310 | `4%` | Progress of the active unit `Unit 1.1`. |
| L316, L320, L324, L328 | `Unit 1.2`, `Unit 1.3`, `Unit 2.1`, `Unit 2.2` | Locked unit IDs — the only course content that exists; titles/lessons beyond the code are absent. |
| L336 | `Starter` + `0%` | "JORIY DARAJA" card values — again `0%` while the bar shows `4%`. |
| L337 | `width: 4%` | Level progress bar width (hardcoded). |
| L338 | `Keyingi daraja: Elementary` | Next level name, hardcoded. |
| L344 | `Unit 1.1` | "Next lesson" unit code, hardcoded. |
| L345 | `Greetings & Introductions · ~10 daqiqa` | Next lesson title + duration, hardcoded; `~10 daqiqa` is a placeholder estimate. |
| L312 | `Sizning darsingiz shu yerda` | Onboarding tooltip text on the path (static, never dismissible). |
| L256, L258, L262, L172, L189 | inline `<svg>` silhouettes | Avatar placeholders (`fill:#A0A0A0` / `#8CA0B5`) where real profile photos belong. |
| L222–231, L234–242, L245–249, L252–266 | `Jang`, `Mening lug'atim`, `Zoom tadbirlar`, `Peshqadamlar` | Card titles/data hardcoded; no counts, no dates, no previews. |
| L220 | `grid-template-columns: repeat(auto-fit, minmax(min(440px,100%),1fr))` | Card grid expects exactly 4 children — count is hardcoded in markup. |
| L209–217 | 8 tiles, 5 dead | Tile set is hardcoded; the 5 dead tiles imply planned screens (§6). |

## 2.3 All interactive JS behaviour (`app.html` L409–425, one IIFE)

| Line | Code | Effect |
|---|---|---|
| L411 | `document.querySelector('.app')` + `querySelectorAll('[data-pane]')` | Caches host + 4 panes. |
| L412 | `var names=['asosiy','darslar','resurslar','koproq']` | Tab id ↔ hash-string map (ASCII, **no apostrophe** in `koproq`). Index 0–3. |
| L413–418 | `function go(i, scroll)` | Sets `app[data-tab]=i` (drives all CSS: indicator slide L67–70/110–113, active icon colour L65/109); sets `p.hidden = (+p.dataset.pane !== i)` for every pane (CSS L138 `[data-pane][hidden]{display:none}`); if `scroll` then `window.scrollTo({top:0,behavior:'smooth'})`; then `history.replaceState(null,'','#'+names[i])` inside `try/catch`. **Note: pane switching is `hidden`-attribute based — panes are never destroyed, so any future live data would need explicit refresh logic.** |
| L419–421 | `document.querySelectorAll('[data-go]').forEach(b => b.addEventListener('click', () => go(+b.dataset.go, true)))` | Single delegated-style binding for **all 10** `data-go` elements: sidebar `Asosiy/Darslar/Resurslar/Ko'proq` (L151–154), sidebar CTA `Darsni davom ettirish` (L169), and mobile `ni0..ni3` (L401–404). |
| L422–423 | `var h = location.hash.slice(1), k = names.indexOf(h); if (k>0) go(k,false)` | Deep-link on load. **Only `k>0` triggers** — `#asosiy` (index 0) is a no-op because pane 0 is the default; unknown hash → `k=-1` → no-op (no 404/fallback). |
| — | **No `hashchange` listener** | Browser Back/Forward does not change tabs; `replaceState` also means tab changes never create history entries. |
| — | **No handler at all** | `Marketplace` (L213), `Alomat bot` (L214), `Tarjimon` (L215), `System Control` (L216), `Exclusive` (L217), `Xaridlar` (L383), `Tarjimon` (L384), `FAQ` (L385), `Biz haqimizda` (L386), `Sozlamalar` (L387) — **10 dead buttons** (§5). |
| — | CSS-only interactions | `.p3` press/lift (L51–55), `.lock:hover` shake via `@keyframes wig` (L57), `.tile:hover` scale (L59), `.si:hover`/`.ql:hover` (L106–107, L115), `.cta` press (L116–118), `.ni:hover` colour (L71–72) — all visual only. |

## 2.4 Forms & inputs (`app.html`)

- **None.** Zero `<form>`, `<input>`, `<select>`, `<textarea>` elements exist. There is nothing to submit anywhere in the app shell.
- All user-data surfaces are read-only placeholders (§2.2). The only user-triggered state change in the entire file is the tab switch (§2.3).

## 2.5 Navigation links (`app.html`)

| Line | Label (Uzbek) | Target |
|---|---|---|
| L146 | `englify` (sidebar logo) | `index.html` |
| L159 | `Jang` | `jang.html` |
| L160 | `Mening lug'atim` | `lugat.html` |
| L161 | `Suhbatxona (Chat)` | `chat.html` |
| L162 | `Bildirishnomalar` | `notifications.html` |
| L163 | `Zoom tadbirlar` | `zoom.html` |
| L164 | `Peshqadamlar` | `peshqadam.html` |
| L175 | `← englify.uz saytiga qaytish` | `index.html` |
| L187 | `← englify.uz` (mobile back pill) | `index.html` |
| L191 | chat icon (`aria-label="Xabarlar"`) | `chat.html` |
| L192 | bell icon (`aria-label="Bildirishnomalar"`) | `notifications.html` |
| L210 | `Suhbatxona` tile | `chat.html` |
| L211 | `Bildirishnoma` tile | `notifications.html` |
| L212 | `Level Podcast` tile | `podcastlar.html` |
| L222 | `Jang` feature card | `jang.html` |
| L234 | `Mening lug'atim` feature card | `lugat.html` |
| L245 | `Zoom tadbirlar` feature card | `zoom.html` |
| L252 | `Peshqadamlar` feature card | `peshqadam.html` |
| L309 | `Unit 1.1` active node | `dars.html` |
| L346 | `Darsni boshlash` CTA | `dars.html` |
| L360 | `O'yinlar` resource card | `oyinlar.html` |
| L363 | `Level` resource card | `level.html` |
| L366 | `Kitoblar` resource card | `kitoblar.html` |
| L369 | `Podkastlar` resource card | `podcastlar.html` |
| L388 | `Chiqish` (Log out) | `index.html` — **no logout endpoint/session handling** |

**Tab navigation (in-page, not links):** 10 `data-go` buttons (L151–154, L169, L401–404) → panes 0–3; hash names `#asosiy`, `#darslar`, `#resurslar`, `#koproq`.

## 2.6 Missing / planned pages & screens referenced but absent (`app.html`)

These are referenced by UI with **no destination** — every one needs a planned page/route:
- `Marketplace` (L213) — listed twice (also `Xaridlar` L383) → a marketplace + purchases screen is planned.
- `Alomat bot` (L214) — AI/assistant chatbot screen planned.
- `Tarjimon` (L215 and L384) — translator screen planned.
- `System Control` (L216) — appears to be an internal/admin/debug panel.
- `Exclusive` (L217) — premium/exclusive content area.
- `FAQ` (L385) — no FAQ screen inside the app (only on `index.html` L740).
- `Biz haqimizda` / About (L386) — no about screen.
- `Sozlamalar` / Settings (L387) — no settings screen.
- No **login/auth screen** anywhere (app assumes an already-authenticated `Talaba`).
- No **profile edit** screen (user chip L171–174 is static).
- No screen for the **streak** (L280), **coins** (L282) or **points** (L281/173) — displayed but unclickable/undetailed.
- Tab-level "Ko'proq" is the only in-app hub, and 5 of its 6 entries are dead.

---

# PART 3 — REST API suggestion by domain entity

Conventions: JSON only, `Authorization: Bearer <token>`, base `/api/v1`. Uzbek UI labels map to the fields noted. Every endpoint below is required because the corresponding UI element exists in the HTML (line refs given).

## 3.1 Domain: Auth & session (`app.html` L173, L190, L388; `index.html` L122)
- `POST /auth/login` — body `{phone, password}` → `{accessToken, refreshToken, expiresIn, user}`. *(Needed: no login screen exists yet; `app.html` assumes auth.)*
- `POST /auth/register` — body `{fullName, phone, password, offerAccepted:true}` → `{userId, accessToken}`.
- `POST /auth/refresh` — body `{refreshToken}` → `{accessToken, expiresIn}`.
- `POST /auth/logout` — body `{}` → `204`. *(`app.html` L388 `Chiqish` currently just navigates to `index.html`.)*
- `GET /me` — → `{id, fullName, avatarUrl, level:{code,title,percent,nextLevelTitle}, points, coins, streakDays, unreadNotifications}`. Fills L173 `Talaba`/`0 ball · Starter`, L190 `Salom, Talaba!`, L280–L282 streak/ball/tanga, L336–L338 level card, L192 unread dot.
- `PATCH /me` — body `{fullName?, avatarUrl?}` → `{...user}`. *(Planned: Settings L387.)*
- `GET /me/settings` / `PATCH /me/settings` — `{language, timezone, notificationChannels, theme}`. *(Planned: L387.)*

## 3.2 Domain: Lead / registration (`index.html` L137–151) — **highest priority, only real form**
- `POST /marketing/leads` — body `{fullName: string (from #f-name), phoneCountry:"UZ" (select L145), phone: string ("+998…" from #f-phone), source:"hero_form", offerAccepted:true, utm?}` → `{leadId, status:"new"|"duplicate", message}`.
  - Validation needed: `fullName` 2–100 chars; `phone` must be normalized to E.164 starting `+998` (9 digits after prefix); deduplicate on `phone` within N days.
  - Error shape: `{error:{code:"VALIDATION_ERROR", fields:{phone:"..."}}}` — the UI currently shows only an optimistic fake success (L845–848), so error rendering is a **new requirement**.
- `GET /marketing/site-settings` → `{phone, telegram, instagram, address, offerUrl, appStoreUrl, googlePlayUrl, appStoreQrUrl, googlePlayQrUrl}`. Fills L798–L801 placeholders, L150 offer link, L682–683 QR codes + store links.
- `GET /marketing/faqs` → `[{id, question, answer, order}]`. Fills L746–787 (and the planned in-app FAQ L385).
- `GET /marketing/plans` → `[{id, code:"standart"|"premium"|"individual", name, priceUzs, period:"month", features:[string], badge?:string, highlighted:bool, order}]`. Fills L707/717/727 `[NARX]`, L709–711/719–721/729–731 bullets, L716 `Ommabop`.
- `POST /checkout/sessions` — body `{planCode, fullName, phone}` → `{checkoutUrl, sessionId}`. *(Planned: `Tanlash` L713/723/733 currently only scrolls to `#top`; payment methods from L781 `[Payme / Click / bank kartasi]`.)*
- `GET /payment-methods` → `[{code:"payme"|"click"|"card", title, logoUrl}]`. Resolves L781.

## 3.3 Domain: Marketing content (all cards currently hardcoded)
- **Student stories** (L182–L208, 4 cards): `GET /marketing/stories?limit=&cursor=` → `{items:[{id, studentName, posterUrl, videoUrl, durationSec, order}], nextCursor}`. Fills `[Ism]` L186/193/200/207, play buttons L185/192/199/206, L184/191/198/205 posters.
- **Results / certificates** (L217–L372, 12 cards): `GET /marketing/results?type=certificate|ielts&limit=&cursor=` → `{items:[{id, type:"certificate"|"ielts", fullName, imageUrl, ieltsScore?, issuedAt, order}], nextCursor}`. Fills `[SERTIFIKAT RASMI]`, `[IELTS NATIJASI]`, `[F.I.SH.]`.
- **Reviews** (L383–L482, 10 cards): `GET /marketing/reviews?limit=&cursor=` → `{items:[{id, imageUrl, source:"telegram"|"whatsapp"|"app", order}], nextCursor}`. Fills `[IZOH SKRINSHOTI]`.
- **Opportunities / benefits** (L496–L506, 6 cards): `GET /marketing/benefits` → `[{id, text, accentColor, order}]`.
- **Features "what awaits"** (L519–L565, 6 cards): `GET /marketing/features` → `[{id, title, description, iconKey, iconBg, order}]`. Also resolves L564 `[5–10] daqiqa` by putting the real duration in `description` (or a dedicated `durationMinutes`).
- **Audience personas** (L578–L606, 6 cards): `GET /marketing/audiences` → `[{id, title, description, bgColor, borderColor, order}]`.
- **Mentors** (L622–L668, 4 cards): `GET /marketing/mentors` → `[{id, name, role, photoUrl, experienceYears, ieltsScore, cardColor, watermark, order}]`. Fills `MR. [ISM]` L627/639/651/663, `English Instructor` L628/640/652/664, `Teaching Experience: [N]+ years` L629/641/653/665, `Certifications: IELTS [X.X]` L630/642/654/666.

## 3.4 Domain: Learning progress & course (`app.html` pane 0 + pane 1)
- `GET /me/progress/skills` → `[{skill:"vocabulary"|"writing"|"reading"|"listening"|"grammar", percent:0-100}]`. Fills the 5× `[%]` (L196–200) **and** the bar heights (currently 46/72/58/84/64 %).
- `GET /me/progress/level` → `{levelCode:"starter", levelTitle:"Starter", percent, nextLevelTitle:"Elementary", completedUnits, totalUnits}`. Fills L297, L336–L338, and reconciles the `0%` vs `4%` inconsistency.
- `GET /courses/current/units` → `[{id, code:"Unit 1.1", title, status:"available"|"locked"|"completed", percent, order, pathXY:{x,y}}]`. Fills the 5 path nodes L309–L329 + lock states + the `4%` on L310. (Recommend the server own `status`/`percent`; keep `pathXY` optional since the layout is currently hardcoded absolute positions.)
- `GET /courses/current/next-lesson` → `{lessonId, unitCode:"Unit 1.1", title:"Greetings & Introductions", durationMinutes:10, exercisesCount}`. Fills L344–L345, the `Darsni boshlash` CTA L346, and the sidebar `Darsni davom ettirish` CTA L169.
- `GET /lessons/:lessonId` → `{id, unitId, title, description, type:"video"|"exercise"|"test", durationMinutes, videoUrl, audioUrl, materials:[{id,title,url}], exercises:[...]}`. *(Consumer: `dars.html`, launched from L309/L346.)*
- `POST /lessons/:lessonId/complete` — body `{score, durationSpentSec, answers?}` → `{pointsAwarded, coinsAwarded, newStreakDays, unitPercent, nextLessonId}`. *(No submission UI exists yet — required to make progress non-fake.)*
- `GET /me/wallet` → `{points, coins, streakDays, lastActivityDate}`. Fills L280/L281/L282 and the sidebar chip L173.
- `GET /me/quests` (optional) → `[{id,title,reward,progress,status}]`. *(Planned: `Exclusive` L217.)*

## 3.5 Domain: Vocabulary / "Mening lug'atim" (`app.html` L234–L242, L236)
- `GET /me/words?limit=&cursor=&q=&partOfSpeech=` → `{items:[{id, ordinal, partOfSpeech, word, translation, example, audioUrl, createdAt}], total, nextCursor}`. Fills L239 `001 · [noun]`, `Teacher`, `A teacher inspires students.`; drives the empty state `Hali so'zlar yo'q` (L236) when `total == 0`.
- `POST /me/words` — body `{word, translation, partOfSpeech, example?, sourceLessonId?}` → `{...word}`.
- `PATCH /me/words/:id` — body `{translation?, example?, partOfSpeech?}` → `{...word}`.
- `DELETE /me/words/:id` → `204`.
- `GET /dictionary/lookup?word=` → `{word, partOfSpeech, translations:[string], examples:[string], audioUrl}`. *(For the planned translator/quick-add, L215/L384.)*

## 3.6 Domain: Battles / "Jang" (`app.html` L222–L231)
- `GET /me/battles/stats` → `{total, wins, losses, currentStreak, rank}`. Fills `Janglar: 0`, `Yutuqlar: 0`, `Mag'lubiyat: 0` (L226–L228).
- `GET /battles?status=active|finished` / `GET /battles/:id` → `{id, opponent:{id,fullName,avatarUrl}, topic, status, myScore, opponentScore, startedAt, finishedAt}`. *(Consumer: `jang.html`.)*
- `POST /battles` — body `{topic, opponentId?}` → `{battleId, matchStatus:"searching"|"ready"}`.

## 3.7 Domain: Leaderboard / "Peshqadamlar" (`app.html` L252–L266)
- `GET /leaderboards?scope=global|class|friends&period=week|all&limit=20&cursor=` → `{items:[{rank, userId, fullName, avatarUrl, points, isMe, trend}], me:{rank, points}, updatedAt}`. Fills L256–L264 (placeholder `Talaba` + `0`).
- *(Consumer: `peshqadam.html`.)*

## 3.8 Domain: Resources (`app.html` L354–L372)
- `GET /resources?type=games|level|books|podcasts&limit=&cursor=` → `{items:[{id, type, title, subtitle, coverUrl, href, progressPercent?, meta}], nextCursor}`. Fills the 4 cards L360–L372 and backs the referenced pages `oyinlar.html` / `level.html` / `kitoblar.html` / `podcastlar.html`.
- `GET /resources/:id` → resource detail `{id, title, description, mediaUrl, durationMinutes, level, tags, attachments}`.

## 3.9 Domain: Notifications (`app.html` L192, L211; badge on L192)
- `GET /me/notifications?unread=true&limit=&cursor=` → `{items:[{id, type, title, body, deepLink, isRead, createdAt}], unreadCount, nextCursor}`. Fills the always-on red dot (L192) — the dot must become conditional on `unreadCount > 0`.
- `POST /me/notifications/:id/read` → `204`; `POST /me/notifications/read-all` → `204`.
- *(Consumer: `notifications.html`.)*

## 3.10 Domain: Chat / "Suhbatxona" (`app.html` L191, L210, L161)
- `GET /me/chats?limit=&cursor=` → `{items:[{id, type:"group"|"direct", title, avatarUrl, lastMessage:{text, senderName, createdAt}, unreadCount}], nextCursor}`.
- `GET /me/chats/:chatId/messages?limit=&cursor=` → `{items:[{id, senderId, senderName, avatarUrl, text, attachments:[], createdAt}], nextCursor}`.
- `POST /me/chats/:chatId/messages` — body `{text, attachments?:[fileId]}` → `{...message}`.
- Realtime: `WS /me/realtime` (events `message.created`, `notification.created`, `battle.updated`). *(Required for a real chat; the HTML has no transport at all.)*

## 3.11 Domain: Zoom events (`app.html` L163, L245–L249)
- `GET /zoom-events?status=upcoming|past&limit=&cursor=` → `{items:[{id, title, startsAt, durationMinutes, joinUrl, teacherId, teacherName, level, seatsLeft, isRegistered}], nextCursor}`. The card L245–L249 currently shows **no event data at all** — this is a new requirement.
- `POST /zoom-events/:id/register` → `{registrationId, joinUrl}`; `DELETE /zoom-events/:id/register` → `204`.

## 3.12 Domain: Marketplace & purchases (`app.html` L213, L383)
- `GET /marketplace/items?category=&limit=&cursor=` → `{items:[{id, title, description, imageUrl, priceCoins, priceUzs, stock, category}], nextCursor}`.
- `POST /marketplace/orders` — body `{itemId, quantity, paymentMethod:"coins"|"payme"|"click"|"card"}` → `{orderId, status, totalCoins?, totalUzs?, checkoutUrl?}`.
- `GET /me/purchases?limit=&cursor=` → `{items:[{id, orderId, title, imageUrl, purchasedAt, amount, currency, status:"paid"|"pending"|"failed", receiptUrl}], nextCursor}`.

## 3.13 Domain: AI assistant / translator (`app.html` L214, L215)
- `POST /assistant/messages` — body `{conversationId?, text, locale:"uz"}` → `{conversationId, reply:{text, actions?:[]}}`. Backs `Alomat bot`.
- `POST /translate` — body `{text, from:"uz"|"en"|"auto", to:"en"|"uz"}` → `{translatedText, detectedSource, alternatives?}`. Backs both `Tarjimon` entries (L215, L384).
- `GET /assistant/conversations` → `[{id, title, updatedAt, lastMessage}]`; `GET /assistant/conversations/:id/messages`.

## 3.14 Domain: Admin / content management (implied by all placeholder data)
Every `[ ]`-placeholder above implies an authoring surface. Minimum admin endpoints:
- `GET|POST|PATCH|DELETE /admin/marketing/{mentors,plans,faqs,stories,results,reviews,benefits,features,audiences}` and `PATCH /admin/site-settings`.
- `GET|POST|PATCH|DELETE /admin/courses`, `/admin/courses/:id/units`, `/admin/units/:id/lessons`, `/admin/lessons/:id/exercises`.
- `GET /admin/leads?status=&q=&cursor=` → lead inbox for the hero form (L137–151).
- `GET /admin/users/:id/progress`, `POST /admin/users/:id/points` (manual grants for `0 ball` L173/L281).

## 3.15 Client-side state the backend must own (replacing hardcoded values)

| UI location | Current literal | Source of truth |
|---|---|---|
| `app.html` L173 | `Talaba`, `0 ball · Starter` | `GET /me` |
| `app.html` L190 | `Salom, Talaba!` | `GET /me` |
| `app.html` L196–200 | `[%]` ×5 + bar heights 46/72/58/84/64 | `GET /me/progress/skills` |
| `app.html` L226–228 | `0`, `0`, `0` | `GET /me/battles/stats` |
| `app.html` L236 | `Hali so'zlar yo'q` | `GET /me/words` (`total===0`) |
| `app.html` L239 | `001 · [noun]` / `Teacher` / `A teacher inspires students.` | `GET /me/words` first item |
| `app.html` L264, L263 | `0`, `Talaba` | `GET /leaderboards` |
| `app.html` L280–282 | `0`, `0 ball`, `0 tanga` | `GET /me/wallet` |
| `app.html` L297, L336–338 | `Starter`, `0%`, `4%`, `Elementary` | `GET /me/progress/level` |
| `app.html` L310, L316–L328 | `4%`, `Unit 1.1`…`Unit 2.2` + lock states | `GET /courses/current/units` |
| `app.html` L344–345 | `Unit 1.1`, `Greetings & Introductions · ~10 daqiqa` | `GET /courses/current/next-lesson` |
| `index.html` L186/193/200/207 | `[Ism]` | `GET /marketing/stories` |
| `index.html` L218/231/…/L370 | `[SERTIFIKAT RASMI]`, `[IELTS NATIJASI]`, `[F.I.SH.]` | `GET /marketing/results` |
| `index.html` L390–L480 | `[IZOH SKRINSHOTI]` | `GET /marketing/reviews` |
| `index.html` L627/639/651/663 | `MR. [ISM]` | `GET /marketing/mentors` |
| `index.html` L629/641/653/665 | `Teaching Experience: [N]+ years` | `GET /marketing/mentors` |
| `index.html` L630/642/654/666 | `Certifications: IELTS [X.X]` | `GET /marketing/mentors` |
| `index.html` L707/717/727 | `[NARX]` | `GET /marketing/plans` |
| `index.html` L771 | `[SHARTLARNI TEKSHIRING]` | `GET /marketing/faqs` (real answer text) |
| `index.html` L781 | `[Payme / Click / bank kartasi]` | `GET /payment-methods` |
| `index.html` L798–L801 | `[+998 __ ___ __ __]`, `[@englify]`, `[@englify.uz]`, `[MANZIL]` | `GET /marketing/site-settings` |
| `index.html` L682–683 | `[QR-KOD]` ×2 | `GET /marketing/site-settings` (`appStoreQrUrl`, `googlePlayQrUrl`) |
| `index.html` L160 | `[O'QITUVCHI RASMI]` | hero image from `GET /marketing/site-settings` or a hero-content endpoint |
| `index.html` L564 | `[5–10] daqiqa` | `GET /marketing/features` (`durationMinutes`) |
| `index.html` L165, L689 | `Salom, [Ism]`, `Hi, [Ism]!` | static mockups — replace with fixed copy or drop interpolation |

---

# PART 4 — Dead UI (element exists, NO handler, NO navigation)

## `index.html`
- L185, L192, L199, L206 — 4× `<button aria-label="Videoni ko'rish">`: no listener, no `data-*`, no video element.
- L217–L372 — 12 results cards (`div.hovc`, `cursor:pointer`, hover lift): no click handler, not links.
- L383–L482 — 10 review cards (`div.hovc`): no click handler, not links.
- L682, L683 — App Store / Google Play "QR" cards: plain `<div>`s, no link, no QR image.
- L137 `<form onsubmit="return false">` — native submit path permanently disabled.
- L509, L568, L609, L713, L723, L733 — CTAs that only self-anchor to `#top` (technically live, functionally no-op for their label: no plan selection, no scroll-to-form).
- L150 — offer link points to `#top` (self) instead of a terms/offer page.

## `app.html`
- L213 `Marketplace`, L214 `Alomat bot`, L215 `Tarjimon`, L216 `System Control`, L217 `Exclusive` — 5 tile `<button>`s, no handler, no `href`.
- L383 `Xaridlar`, L384 `Tarjimon`, L385 `FAQ`, L386 `Biz haqimizda`, L387 `Sozlamalar` — 5 "More" `<button>`s, no handler, no `href`.
- L316, L320, L324, L328 — locked unit nodes are `div.lock` (correctly non-interactive by design).
- L192 — notification red dot is unconditionally rendered (no data binding), so it can never reflect real unread state.
- L312 tooltip `Sizning darsingiz shu yerda` — static, no dismiss, no positioning logic.

Summary: **10 dead buttons in `app.html`**, **4 dead buttons + 22 dead pointer-cards + 2 dead QR cards in `index.html`**.

---

# PART 5 — Navigation map & missing/planned routes

## Existing pages (all present on disk, referenced by both files)
`index.html` ⇄ `app.html`; from `app.html`: `dars.html`, `jang.html`, `lugat.html`, `chat.html`, `notifications.html`, `zoom.html`, `peshqadam.html`, `oyinlar.html`, `level.html`, `kitoblar.html`, `podcastlar.html`.

## Cross-file links
- `index.html` L122 → `app.html` (only entry into the app).
- `app.html` L146, L175, L187, L388 → `index.html`.

## Missing / planned pages (referenced by UI but no destination)
1. `marketplace.html` — from `app.html` L213 (`Marketplace`) and L383 (`Xaridlar`).
2. `alomat-bot.html` (or `assistant.html`) — from `app.html` L214.
3. `tarjimon.html` — from `app.html` L215 and L384.
4. `system-control.html` (admin/debug) — from `app.html` L216.
5. `exclusive.html` — from `app.html` L217.
6. `faq.html` — from `app.html` L385.
7. `biz-haqimizda.html` — from `app.html` L386.
8. `sozlamalar.html` — from `app.html` L387.
9. `login.html` / `kirish.html` — implied; `app.html` assumes an authenticated `Talaba`.
10. `oferta.html` (public offer / terms) — from `index.html` L150.
11. `tolov.html` (payment/checkout) — implied by `index.html` L713/723/733 + L781.
12. `profil.html` (profile edit) — implied by the static user chip `app.html` L171–174.

## Anchor gaps
- `index.html`: sections at L488, L573, L614, L740 have no `id`; nav has no entry for `#izohlar` or `#ilova` although `a[href="#ilova"]` styling exists (L89–90).
- `app.html`: mobile/desktop nav cannot deep-link anything inside `dars.html`, `lugat.html`, etc.; tab state uses `replaceState` so it is not bookmarkable as history (though `#darslar` etc. work on fresh load, `#asosiy` does not — L423 `if(k>0)`).

---

# PART 6 — Backend implementer checklist (derived)

1. **Only one genuine data submission exists**: `POST /marketing/leads` from `index.html` L137–151. Everything else in both files is read-only rendering.
2. **No auth UI exists** — build `login.html` + `POST /auth/login`, then replace `Talaba` (L173) and `Salom, Talaba!` (L190) from `GET /me`.
3. **`app.html` has 4 read-only data surfaces to wire**: `GET /me`, `GET /me/progress/skills`, `GET /courses/current/units` + `/next-lesson`, `GET /me/wallet` (+ `GET /me/words` for the dictionary empty state).
4. **`index.html` has 8 content collections to wire**: stories, results, reviews, benefits, features, audiences, mentors, plans — each currently a fixed-count hardcoded list with fixed card dimensions (L178's `width:991px;height:597px` must be removed when counts change).
5. **Content management is mandatory** — ~30 distinct `[ ]` placeholders must be authored somewhere; no admin surface exists in either file.
6. **Fix the two data inconsistencies while wiring**: level shows `0%` at L297/L336 but the bar and node say `4%` (L310/L337); the notification badge L192 is always on.
7. **Add error/loading/empty states** — the only "empty state" in either file is `Hali so'zlar yo'q` (L236); there is no error rendering, no loading skeleton, no validation messaging, and the form's success is faked with a 3.2 s timer (L848).
