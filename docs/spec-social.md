# Englify — Social / Realtime Surfaces: Technical Spec

Source of truth: static prototypes `chat.html` (331 lines), `notifications.html` (201), `jang.html` (455), `peshqadam.html` (342), `zoom.html` (243).
Language: UI copy is Uzbek (`<html lang="uz">`); file encoding UTF-8; no build step, no framework — plain HTML + inline `<script>`, font `Outfit` from Google Fonts.
All five pages are standalone documents with **no shared JS/CSS bundle** and **no fetch/XHR anywhere** — 100% of dynamic behaviour is in-page DOM mutation + `alert()`.

Global conventions observed in all five files
- Palette: `--sky:#0A93F5` (chat/notifications/jang), `--sky:#00A3FF` (peshqadam), `--ink:#220846`, `--bg:#F5F7FD`, `--border:#E8EBF5`; zoom uses `#ABA3E0/#C3BCEE` purple and `#2A0B5C` text.
- Header pattern: `.top-nav` 68px sticky white bar, left back button, centered `<div>` title, right action button (chat.html:189-197, notifications.html:126-134, jang.html:228-236).
- Static hosting assumption: every nav target is a sibling `.html` file (`app.html`, `zoom.html`, `dars.html`).

---

## 1. chat.html — "Suhbatlar" (Chats / Messages)

### 1.0 Screens
- **Screen 1 — `#chatListView`** (chat.html:200-242): *Suhbatlar ro'yxati* (conversation list). Rendered by default (`display` not set → block).
- **Screen 2 — `#chatRoomContainer`** (chat.html:245-257) wrapping **`#chatRoomView`** (chat.html:125-137): *Suhbat xonasi* (single conversation room). Hidden initially via inline `style="display: none"` on the container (chat.html:245).
- Both are `.container` (chat.html:55-63, max-width 600px); the room view itself is max-width 700px (chat.html:129) so the room visibly widens vs. the list.
- Header title `#chatHeaderTitle` (chat.html:193) is **mode-dependent**: `Suhbatlar` on the list, the contact name inside a room (chat.html:290).

### 1.1 UI features
- *Suhbatlar* (Chats) — page title / header (chat.html:193) + `<title>` (chat.html:6).
- *Suhbatlar ro'yxati* (Conversation list) — `.chats-box` white rounded 28px container (chat.html:66-72) holding `.chat-row` items.
- *Suhbat qatori* (Conversation row) — 52px round blue `.avatar-badge` with a single capital letter, bold title, one-line ellipsized preview, right-aligned relative timestamp (chat.html:74-122).
- *Orqaga* (Back) — top-left `.nav-btn`, arrow SVG, `aria-label="Orqaga"` (chat.html:190-192).
- *O'qilgan deb belgilash* (Mark all as read) — top-right `.nav-btn`, double-check SVG, `aria-label="O'qilgan deb belgilash"` (chat.html:194-196).
- *Suhbat xonasi* (Chat room) — scrollable `.messages-box` (chat.html:138-147, `min-height:420px`, `background:#F8FAFE`) + pinned `.input-row` composer.
- *Xabar pufagi* (Message bubble) — two variants: `.msg-bubble.bot` (white, left, flat bottom-left corner, chat.html:155-160) and `.msg-bubble.user` (blue `#0A93F5`, white text, right, flat bottom-right corner, chat.html:161-166).
- *Xabar yozing...* (Message input) — `#chatInput` text input, `placeholder="Xabar yozing..."`, `autocomplete="off"` (chat.html:251).
- *Yuborish* (Send) — `<button type="submit">` inside the composer form (chat.html:252-254).

### 1.2 Hardcoded / demo data
Conversation list rows (exactly three, in this order; the row is fully static markup, the JS DB only supplies the room contents):

| # | Title | Avatar letter | `.chat-time` | `.chat-preview` (truncated by CSS) |
|---|---|---|---|---|
| 1 (chat.html:205-214) | `Support Service` | `S` | `08 avg 15:52` | `Assalom alaykum! Sizni EN...` |
| 2 (chat.html:217-226) | `Englify` | `E` | `11 may 09:25` | `👋 Welcome! Your first ste...` |
| 3 (chat.html:229-238) | `Alomat (Bot)` | `A` | `Hozir` (now) | `Savollaringiz bo'lsa marhamat...` |

`chatMessagesDB` (chat.html:262-273) — keyed by exact row title (must match the `openChatRoom(title, letter)` string):
- `'Support Service'` → 1 message: `from:'bot'`, text `Assalom alaykum! Sizni Englify qo'llab-quvvatlash xizmati qutlaydi. Darslar yoki platforma bo'yicha qanday savolingiz bor?` (chat.html:264).
- `'Englify'` → 2 messages, both `bot`:
  1. `👋 Welcome! Your first step to speaking English fluently starts right here.` (chat.html:267)
  2. `Darslar bo'limidan Unit 1.1 ni boshlashingiz mumkin!` (chat.html:268)
- `'Alomat (Bot)'` → 1 message: `Salom! Men Alomat — sizning sun'iy intellekt repetitoringizman. Grammatika, so'zlar yoki darslar bo'yicha xohlagan savolingizni bering!` (chat.html:271).
- **No timestamps are stored per message** — only the list-level `chat-time` strings above.
- Auto-reply placeholder injected 800 ms after any user send (chat.html:321): `Xabaringiz qabul qilindi! Tez orada mutaxassis yoki AI javob beradi.`
- Alert strings: `Barcha suhbatlar o'qilgan deb belgilandi! ✓✓` (chat.html:327).
- Note: the avatar `letter` argument (`'S'`,`'E'`,`'A'` from chat.html:205/217/229) is **accepted but never used** — `openChatRoom(title, letter)` ignores it (chat.html:286); the badge lives only in the list markup.

### 1.3 Interactive JS (chat.html:259-329)
| Symbol | Lines | Trigger | Behaviour |
|---|---|---|---|
| `curChatTitle` | 260 | state | String; current conversation key. Empty before any `openChatRoom`. |
| `handleChatBack()` | 275-284 | onclick chat.html:190 | If room visible (`#chatRoomContainer.style.display === 'flex'`) → hide room, show list (`display='flex'`), reset title to `Suhbatlar`. Else → `window.location.href = 'app.html#asosiy'`. **Note:** reads/writes inline `style.display` only, so the initial state must be `display:none` inline (it is, chat.html:245). |
| `openChatRoom(title, letter)` | 286-293 | onclick `chat.html:205,217,229` | Sets `curChatTitle`, hides list, shows room as `flex`, sets header title to `title`, calls `renderRoomMessages()`. |
| `renderRoomMessages()` | 295-307 | internal | Clears `#messagesArea`, appends one `div.msg-bubble.<from>` per DB entry with `textContent = m.text` (XSS-safe by construction — preserve that on backend-rendered HTML), then scrolls to bottom. |
| `sendChatMessage(e)` | 309-324 | `<form onsubmit>` chat.html:250 | `preventDefault()`; trims `#chatInput`; no-op if empty; pushes `{from:'user', text}`; clears input; re-renders; after **800 ms** pushes the canned bot reply and re-renders again. No server round-trip, no failure path, no optimistic/pending state, no pagination. |
| `markAllChatRead()` | 326-328 | onclick chat.html:194 | `alert("Barcha suhbatlar o'qilgan deb belgilandi! ✓✓")`. **No unread state exists anywhere** — no badge counters, no read flags; pure dead UI. |

### 1.4 Dead UI (no handler)
- Chat message send is **client-only**: no network call, reply is a hardcoded string (chat.html:320-323).
- `markAllChatRead()` is alert-only — nothing is marked (chat.html:326-328).
- `.chat-row` has `cursor:pointer` + hover style (chat.html:79,86-88) but no keyboard/ARIA role, no `tabindex` — accessibility gap, not a handler gap.

### 1.5 Auth / identity assumptions
- No user identity in the DOM at all: no "me" avatar, no user id, no name. The current user is only implied by `.msg-bubble.user` alignment (chat.html:161-166).
- Composer has no attachment/typing/online indicator.
- Author names are not rendered per bubble — the room shows only bot/user styling, so the backend can omit `sender_name` from message rendering but still needs `conversation_id`.

### 1.6 Navigation
- Back (chat.html:190) → in-page to list, else `app.html#asosiy` (chat.html:282).
- No outbound links to any other prototype page from the list rows (rows only open the in-page room).
- Not linked *from* the analysed set except conceptually by `app.html` (out of scope).

---

## 2. notifications.html — "Bildirishnoma" (Notifications)

### 2.0 Screens
- Single screen: white sticky header + centered `.container` (max-width 640px, chat.html-analogue at notifications.html:53-61) with a vertical stack of 3 `.notif-card` cards, `gap:20px`.
- `<title>Bildirishnoma — Englify</title>` (notifications.html:6); header title `Bildirishnoma` (notifications.html:130).

### 2.1 UI features
- *Bildirishnoma* (Notification) — header title.
- *Orqaga* (Back) — header-left `<a href="app.html#asosiy">` (notifications.html:127-129) — a real link, not a JS button (unlike chat.html).
- *Barchasini o'qish / O'qilgan deb belgilash* (Mark all read) — header-right button with double-check SVG and `title="O'qilgan deb belgilash"` (notifications.html:131-133).
- *Bildirishnoma kartasi* (Notification card) — `.notif-card` (notifications.html:64-70): rounded 26px, 1px border, soft shadow.
- `.notif-date` (notifications.html:72-77) — grey 14px relative/absolute date line at the top of each card.
- `.notif-banner` (notifications.html:79-92) — 16:8 aspect-ratio promo banner, inline `background` gradient per card, badge/marketing copy on the left, emoji on the right.
- `.notif-title` (notifications.html:94-100) + `.notif-desc` (notifications.html:102-107) — bold headline and grey body.
- `.notif-action-btn` (notifications.html:109-120) — floating-right blue CTA anchor.
- No empty state, no unread/read styling, no grouping by date, no infinite scroll, no pull-to-refresh.

### 2.2 Hardcoded / demo data (3 cards, verbatim)

**Card 1** (notifications.html:139-154)
- `.notif-date`: `2026.07.15 21:01`
- Banner: gradient `linear-gradient(135deg, #421C16, #78351B)`; badge text `MILLAT UMIDI` (white bg, brown text `#421C16`); headline `To'g'ri universitet tanlash!`; subline `Online bepul vebinarga qo'shiling!`; emoji `👨‍💼`
- `.notif-title`: `🎓 Bugun kelajak uchun qaror qabul qilinadigan kun!`
- `.notif-desc`: `Abituriyentlar va ota-onalar uchun Umidjon Ishmuhammedov bilan maxsus master-klass bo'lib o'tadi...`
- CTA: label `Bepul qo'shiling` → `href="zoom.html"` (notifications.html:152)

**Card 2** (notifications.html:157-170)
- `.notif-date`: `2026.07.14 10:18`
- Banner: `linear-gradient(135deg, #5C3D32, #8F6656)`; multiline copy `Millat Umidi Universiteti` + line break + `1 000 000 000` (highlighted `#FFE58F`) + ` grant e'lon qildi`; emoji `✉️`
- `.notif-title`: `🎓 Universitet tanlashdagi bitta to'g'ri qaror`
- `.notif-desc`: `Universitet tanlashdagi bitta to'g'ri qaror kelajagingizni belgilaydi. Grant tanlovlarida qatnashing...`
- CTA: label `Qo'shilish` → `href="zoom.html"` (notifications.html:168)

**Card 3** (notifications.html:173-191)
- `.notif-date`: `2026.06.27 19:01`
- Banner: `linear-gradient(135deg, #0A1C3E, #1F4287)`; two chips `NAQDGA:` (bg `#0A93F5`) and `NASIYAGA:` (bg `#2ED573`); headline `Yangi mavsum aksiyasi!`; subline `Barcha o'quv modullari uchun 40% chegirma`; emoji `🎁`
- `.notif-title`: `🔥 Ingliz tili kurslariga ro'yxatdan o'tish ochildi!`
- `.notif-desc`: `Individual va guruh mashg'ulotlarida zamonaviy metodika asosida ta'lim oling...`
- CTA: label `Batafsil ma'lumot` → `href="dars.html"` (notifications.html:189)
- Alert string: `Barcha bildirishnomalar o'qilgan deb belgilandi! ✓✓` (notifications.html:197)
- Consistency notes for seeding: dates are 2026 (future-dated relative to the prototype's other 2026 dates), listed **newest-first**, and the two card-1/card-2 CTAs both point at `zoom.html` although card 3 points at `dars.html`.

### 2.3 Interactive JS (notifications.html:195-199)
| Symbol | Lines | Trigger | Behaviour |
|---|---|---|---|
| `markAllRead()` | 196-198 | onclick notifications.html:131 | `alert("Barcha bildirishnomalar o'qilgan deb belgilandi! ✓✓")`. Nothing persisted; the DOM has **no unread marker** to clear. |

- No other JS: no click handler on cards, no dismiss/swipe, no detail view, no pagination, no real-time push.

### 2.4 Dead UI
- *Barchasini o'qish* → `alert()` only (notifications.html:196-198).
- Notification cards themselves are **not clickable** (only the inner CTA anchors are).
- No "read/unread" rendering exists, so an unread-count API would have nowhere to display.

### 2.5 Auth / identity assumptions
- None visible: no recipient name/avatar, no per-user header. Cards are identical for every user; the backend must key notifications by authenticated user.

### 2.6 Navigation
- Back → `app.html#asosiy` (notifications.html:127).
- Card 1 CTA → `zoom.html` (notifications.html:152).
- Card 2 CTA → `zoom.html` (notifications.html:168).
- Card 3 CTA → `dars.html` (**file not in the analysed set**; notifications.html:189).

---

## 3. jang.html — "Jangni boshlang" (Start a Battle / quiz duel)

### 3.0 Screens
- **Lobby** — `#lobbyView` (jang.html:239-292), the `.container` shown by default.
- **Arena** — `#gameArena` (jang.html:186-194 CSS, jang.html:295-326 markup), initially `display:none`, toggled to `flex` by `startBattle()` (jang.html:368-369).
- Header title `Jangni boshlang` (jang.html:232); `<title>Jangni boshlang — Englify</title>` (jang.html:6).

### 3.1 UI features
- *Jang turlarini tanlang:* (Choose battle types) — `.section-label` (jang.html:242).
- *AI ga Qarshi* (Vs. AI) — `.mode-card.card-ai`, subtitle `Sun'iy intellekt bilan bellashing`, emoji 🤖, **selected by default** (jang.html:245-251).
- *Duel* (1v1 duel) — `.mode-card.card-duel`, subtitle `Birga bir jang`, emoji ⚔️ (jang.html:254-260).
- *Guruhli o'yin* (Group game) — `.mode-card.card-group`, subtitle `4 yoki undan ortiq o'yinchi bilan o'ynang`, emoji 👥 (jang.html:263-269).
- *Lobby turlarini tanlang:* (Choose lobby types) — second `.section-label` (jang.html:272).
- *Grammar* lobby — `.lobby-card` 📕, **selected by default** (jang.html:276-279).
- *Vocabulary* lobby — `.lobby-card.vocab` 💬 (jang.html:282-285).
- Selection styling: `.mode-card.selected` (blue border `#0A93F5` + `#EFF6FF` bg, jang.html:93-117) and `.lobby-card.selected` (brown `#7D481C` border for grammar, blue `#0A93F5` for vocab, jang.html:144-156).
- *Jangni boshlang* (Start the battle) — full-width `.start-btn`, blue with 3D `box-shadow: 0 6px 0 #076FC2` and press animation (jang.html:159-183, markup jang.html:288-290).
- *Tarix* (History) — header-right clock button (jang.html:233-235).
- Arena score bar (jang.html:195-204, markup 296-314): *Siz* (You) on the left with 👤, `#playerScore` default `0 ball`; center pill `⏱️ <span id="roundTimer">15</span>s`; opponent on the right, `#opponentName` default `AI Robot`, `#opponentScore` default `0 ball`, `#opponentAvatar` default 🤖.
- Question panel (jang.html:316-321): kicker `SAVOL` + progress `#qCount` default `1/5`; `#questionText` default `"To be" fe'lining 'He/She/It' uchun shakli qaysi?` (note: this static default does **not** match question #1 of either bank).
- Answer options — `#optionsWrap` (jang.html:323-325), empty in markup; four `.option-btn`s generated per question, `text-align:left`, hover blue border (jang.html:205-222).

### 3.2 Hardcoded / demo data
Selection state defaults (jang.html:329-330): `selectedModeType = 'ai'`, `selectedLobbyType = 'grammar'`.
Opponent presets written by `startBattle()` (jang.html:371-380):
- `duel` → `#opponentName = 'Azizbek'`, `#opponentAvatar = '⚔️'`
- `group` → `#opponentName = 'Jamoa (4 kishi)'` ("Team of 4"), `#opponentAvatar = '👥'`
- anything else (i.e. `ai`) → `#opponentName = 'AI Bot'`, `#opponentAvatar = '🤖'` — **this overwrites the markup default `AI Robot`**, a pre-existing inconsistency worth deciding on for the API.

`battleQuestions` (jang.html:332-347) — 2 banks × 5 questions, each `{q, opts[4], correct: index}`:

*`grammar`* (jang.html:334-338)
1. `"He/She/It" uchun to be fe'li qaysi shaklda bo'ladi?` — `am` / `is` / `are` / `be` — correct `1` (`is`)
2. `"They ______ playing football now."` — `is` / `are` / `am` / `was` — correct `1` (`are`)
3. `"Yesterday I ______ a great book."` — `read` / `reads` / `reading` / `will read` — correct `0` (`read`)
4. `"She doesn't ______ coffee."` — `likes` / `like` / `liked` / `liking` — correct `1` (`like`)
5. `"We have ______ friends in London."` — `much` / `many` / `any` / `little` — correct `1` (`many`)

*`vocabulary`* (jang.html:341-345)
1. `"Teacher" so'zining tarjimasi nima?` — `Talaba` / `O'qituvchi` / `Shifokor` / `Muhandis` — correct `1`
2. `"Knowledge" so'zining ma'nosi?` — `Bilim` / `Kitob` / `Maktab` / `Kutubxona` — correct `0`
3. `"Success" so'zi nimani anglatadi?` — `Omad` / `Muvaffaqiyat` / `Mehnat` / `Orzu` — correct `1`
4. `"Friend" so'zining tarjimasi?` — `Birodar` / `Do'st` / `Qo'shni` / `Hamkasb` — correct `1`
5. `"Listen" fe'lining ma'nosi?` — `Gapirmoq` / `Yozmoq` / `Eshitmoq / Tinglamoq` / `O'qimoq` — correct `2`

Scoring / timing constants: round time `15`s (jang.html:353, 411); correct answer `+20` points (jang.html:427); opponent gains `+20` with probability 0.7 (`Math.random() > 0.3`, jang.html:432-435); `600 ms` delay between questions (jang.html:438); 5 questions per match (jang.html:317, 398).

`openHistory()` alert string (jang.html:451): `Janglar tarixi: Hozircha sizda 5 ta g'alaba va 120 ball mavjud!` — i.e. hardcoded **5 wins / 120 points**; a placeholder history view.

Battle-counter placeholders `Janglar: 0`, `Yutuqlar: 0`, `Mag'lubiyat: 0` (battles / wins / losses = 0) are **not in jang.html** — they live in `app.html:226-228` (out of the analysed set). They are the natural home for the history API below.

### 3.3 Interactive JS (jang.html:328-453)
| Symbol | Lines | Trigger | Behaviour |
|---|---|---|---|
| `selectedModeType` / `selectedLobbyType` | 329-330 | state | Defaults `'ai'` / `'grammar'`. |
| `currentQIdx`, `userScore`, `oppScore`, `timerInt`, `timeLeft` | 349-353 | state | Match state, reset in `startBattle`. |
| `selectMode(mode, el)` | 355-359 | onclick jang.html:245,254,263 | Sets `selectedModeType`; removes `.selected` from all `.mode-card`; adds to clicked card. |
| `selectLobby(lobby, el)` | 361-365 | onclick jang.html:276,282 | Sets `selectedLobbyType`; removes `.selected` from all `.lobby-card`; adds to clicked card. |
| `startBattle()` | 367-386 | onclick jang.html:288 | Hides `#lobbyView`, shows `#gameArena` as `flex`; sets opponent name/avatar from mode; resets counters; `loadNextQuestion()`. **No matchmaking, no queue, no auth, no opponent fetch.** |
| `loadNextQuestion()` | 388-421 | internal | Clears timer; if `currentQIdx >= qList.length` → `finishGame()`; else writes `#qCount` as `${currentQIdx+1}/${qList.length}`, writes `#questionText`, rebuilds `.option-btn`s and binds `onclick = () => submitAnswer(idx, q.correct)`, resets `timeLeft = 15`, starts `setInterval` 1 Hz decrement that calls `submitAnswer(-1, q.correct)` on timeout. |
| `submitAnswer(chosen, correct)` | 423-439 | option click or timeout | Stops timer; if `chosen === correct` → `userScore += 20` and updates `#playerScore` as `"<n> ball"`; simulated opponent: `if (Math.random() > 0.3) oppScore += 20` and updates `#opponentScore`; `currentQIdx++`; `setTimeout(loadNextQuestion, 600)`. Win/lose is **local + random**. |
| `finishGame()` | 441-448 | internal | `isWin = userScore >= oppScore` (ties count as a win). Win alert: `` `🎉 G'ALABA! Siz ${userScore} ball bilan g'olib bo'ldingiz!` ``; lose alert: `` `O'yin tugadi. Siz: ${userScore} ball, Raqib: ${oppScore} ball. Yana urinib ko'ring!` `` Then `location.reload()` — **result is never persisted**. |
| `openHistory()` | 450-452 | onclick jang.html:233 | `alert(...)` with the hardcoded 5 wins / 120 points string. |

### 3.4 Dead UI
- *Jangni boshlang* — starts a purely client-side simulation; **no matchmaking / lobby-join / websocket / opponent handshake** (jang.html:367).
- *Tarix* — `alert()` only; no history screen exists (jang.html:450-452).
- Timer and opponent scoring are local `setInterval` + `Math.random()` — no server authority (jang.html:413-420, 432-435).
- No answer-feedback state (no correct/incorrect colouring), no "waiting for opponent", no rematch/exit button, no score submission.
- Missing for a real backend: no `battle_id`, no room code, no player identity, no round sync.

### 3.5 Auth / identity assumptions
- The player is hardcoded as `Siz` ("You") with a static 👤 emoji (jang.html:298-301); no name, no id, no avatar image, no rank/level, no auth token.
- Opponent identity is a local string (`Azizbek`, `Jamoa (4 kishi)`, `AI Bot`); in `duel`/`group` there is **no real second player** — the API must supply real matchmaking for those two modes.

### 3.6 Navigation
- Back → `app.html#asosiy` (jang.html:229).
- No other outbound links; the arena is in-page only.

---

## 4. peshqadam.html — "Peshqadamlar jadvali" (Leaderboard)

### 4.0 Screens
- Single screen: blue `.leader-header` (peshqadam.html:30-34, markup 192-227) + white `.container#leaderboardList` (peshqadam.html:123-131, markup 230-333).
- `<title>Peshqadamlar jadvali — Englify</title>` (peshqadam.html:6); `theme-color` `#00A3FF` (peshqadam.html:7).

### 4.1 UI features
- *Peshqadamlar jadvali* (Leaders table) — `<h1>` inside the blue header (peshqadam.html:198).
- *Orqaga* (Back) — header-left `<a href="app.html#asosiy">` (peshqadam.html:195-197).
- *Foydalanuvchi kartasi* (Current-user card) — `.user-profile-row` (peshqadam.html:52-57, markup 202-216): 64px `.user-avatar-circle` containing an inline grey person SVG, `.user-name-text`, right-aligned `.level-badge-pill` and `.score-pill`.
- *Daraja yorlig'i* (Level badge) — pill reading `Starter` (peshqadam.html:211).
- *Ball yorlig'i* (Score pill) — `⭐ 1` with green star `#2ED573` (peshqadam.html:212-214).
- *Daraja tablari* (Level tabs) — horizontally scrollable `.tabs-scroll` (peshqadam.html:98-104, markup 219-225) with 5 pills: `Starter`, `Beginner`, `Elementary`, `Pre-Intermediate`, `Intermediate`; `.level-tab.active` = white bg, blue text (peshqadam.html:117-120). `Starter` is active by default (peshqadam.html:220).
- *Peshqadam kartasi* (Leaderboard row) — `.leader-card` (peshqadam.html:134-147): `.rank-num` (24px, centered), 50px `.player-avatar` circle (SVG avatar or emoji, sometimes a 👑 overlay), `.player-name`, and a right-aligned `.player-score` pill (`⭐ <n>`) (peshqadam.html:149-186).

### 4.2 Hardcoded / demo data
Current user (peshqadam.html:202-216): name `Abdurahmon`, level badge `Starter`, score `1`; avatar = default grey SVG silhouette (`fill:#8CA0B5`), not an image.
Level tabs: `Starter` / `Beginner` / `Elementary` / `Pre-Intermediate` / `Intermediate` (peshqadam.html:220-224) — the tab bar only restyles itself, the list never changes.

Leaderboard rows, exactly 7, in this order (all under the `Starter` tab — the list is **not** filtered per level):

| Rank | Name | Score | Avatar rendering | Line |
|---|---|---|---|---|
| 1 | `Englify` | 3406 | text avatar, bg `#00A3FF`, white text, 👑 overlay | peshqadam.html:233-245 |
| 2 | `SIGMA` | 3146 | grey SVG silhouette | 248-259 |
| 3 | `Adhamjon` | 3110 | grey SVG silhouette + 👑 overlay | 262-274 |
| 4 | `Abror` | 2651 | grey SVG silhouette + 👑 overlay | 277-289 |
| 5 | `Gulbaxor` | 2636 | grey SVG silhouette | 292-303 |
| 6 | `Gulnoza` | 2515 | emoji 👧 on bg `#FFD180` | 306-317 |
| 7 | `Boximboyev` | 2346 | grey SVG silhouette | 320-331 |

Notes for seeding: `Englify` ranks #1 with a text avatar (5000-point scale implied). 👑 overlays appear on ranks **1, 3, 4** — inconsistent demo data; no tier/medal column exists. No pagination, no "your rank" highlight, no time-range selector (week/month/all) and no empty/loading state.

### 4.3 Interactive JS (peshqadam.html:335-340)
| Symbol | Lines | Trigger | Behaviour |
|---|---|---|---|
| `switchLevelTab(level, btn)` | 336-339 | onclick peshqadam.html:220-224 | Removes `.active` from every `.level-tab`, adds it to the clicked button. The `level` argument is **accepted but unused** — **the leaderboard list is never re-fetched or filtered**. |

- No other JS: no search, no profile click, no follow/compare.

### 4.4 Dead UI
- All five level tabs switch only the visual state; the underlying rows never change (peshqadam.html:336-339) — this is the prime candidate for the first real backend call (`GET /leaderboard?level=`).
- Leader cards have `cursor` hover lift only; not clickable to a profile (peshqadam.html:145-147).

### 4.5 Auth / identity assumptions
- Current user is hardcoded `Abdurahmon`, level `Starter`, score `1` (peshqadam.html:207,211,213) — must become the authenticated user's profile; note this score (`1`) is wildly inconsistent with the leaderboard values (2346–3406).
- All avatars are either an inline grey person SVG (no `src`, no user id) or an emoji; **no avatar URLs exist anywhere** — the API should return an optional `avatar_url` plus an initials/emoji fallback.
- Rank numbers are literal text (`1`..`7`), not computed.

### 4.6 Navigation
- Back → `app.html#asosiy` (peshqadam.html:195). No other outbound links.

---

## 5. zoom.html — "Zoom tadbirlar" (Zoom events)

### 5.0 Screens
- Single screen: purple gradient hero header (zoom.html:42-93) overlapping a white content column (`max-width:780px`, `margin:-56px auto 0`, zoom.html:96).
- Sections: *Kelgusi tadbirlar* (upcoming), *Zoom havolasi* (single shared link), *O'tgan tadbirlar* (past events), footer back link.
- `<title>Zoom tadbirlar — Englify</title>` (zoom.html:6); `theme-color` `#ABA3E0` (zoom.html:7).
- Entrance animations: `.fade` (`fadeUp .5s`), `.pop` (staggered `.07s` per child, zoom.html:20-24), `.hov` hover lift (zoom.html:25-26); `prefers-reduced-motion` disables all animation (zoom.html:36).

### 5.1 UI features
- *Zoom tadbirlar* (Zoom events) — hero `<h1>`, font-size `clamp(38px,9vw,58px)` (zoom.html:47).
- *Jonli darslar va maxsus tadbirlar* (Live lessons and special events) — hero subtitle (zoom.html:48).
- Animated Zoom camera SVG (`.bob2`, 4s infinite bob) (zoom.html:51-55).
- *Hafta qatori* (Week row) — 7 `.day-card`s `Du 13`, `Se 14` (today, purple gradient + `#7A70B8` shadow), `Chor 15`, `Pay 16`, `Ju 17`, `Sha 18`, `Yak 19` (zoom.html:58-91); each may carry a coloured event dot: green `#35F59A` (Du), white (today), blue `#0A93F5` (Pay 16, Sha 18) (zoom.html:62,67,76,85).
- *Kelgusi tadbirlar* (Upcoming events) — white card section title (zoom.html:100).
- *Tadbir kartasi* (Event card) — `.evt-card` (zoom.html:35): white, 24px radius, coloured 5px left border via `--ac`, layered shadow (zoom.html:35).
- Event meta row: 28px host avatar circle with inline grey SVG + text `MR. [ISM] · <subject>` (zoom.html:108-113, 124-129, 140-145).
- *Qatnashish* (Join / Attend) — `.cta` button, green striped gradient `repeating-linear-gradient(115deg,#35F59A 0 30px,#55FFB0 30px 60px)` with `border-bottom:4px solid #17C877` and press animation (zoom.html:29-31; markup 115, 131, 147).
- *Zoom havolasi* (Zoom link) block — purple gradient card (zoom.html:154-167) with subtitle `Barcha darslar uchun yagona havola` (one link for all lessons).
- *Meeting ID* — label `Meeting ID` + value `[000 0000 0000]` with `letter-spacing:.08em` (zoom.html:159-160).
- *Nusxa olish* (Copy) — white pill button with copy SVG (zoom.html:162-165).
- *O'tgan tadbirlar* (Past events) — 2 dimmed rows (`opacity:.75`) each with a *Ko'rish* (View) button (zoom.html:173-186).
- Footer link *← Asosiy sahifaga qaytish* (Back to main page) (zoom.html:190).

### 5.2 Hardcoded / demo data
Upcoming events (3):

| Title | Date/time text | Host text | Accent `--ac` | Line |
|---|---|---|---|---|
| `Grammar Masterclass` | `Bugun · 18:00 – 19:30` | `MR. [ISM] · Grammar` | `#35F59A` | zoom.html:103-117 |
| `Speaking Club` | `Shanba · 16:00 – 17:00` | `MR. [ISM] · Speaking` | `#0A93F5` | 119-133 |
| `Vocabulary Challenge` | `Payshanba · 19:00 – 20:00` | `MR. [ISM] · Vocabulary` | `#FFB26F` | 135-149 |

- Host name is a literal placeholder `MR. [ISM]` ("MR. [NAME]") — not a real user; the host avatar is an inline grey SVG, no URL.
- Past events (2): `Grammar Masterclass` — `5-Oktyabr · 18:00`; `Speaking Club` — `2-Oktyabr · 16:00` (zoom.html:175-176, 182-183). Year is absent (ambiguous for a real `starts_at`).
- Zoom link block: label `Meeting ID`, value `[000 0000 0000]` — placeholder, stored in **no** variable; it is read back from the DOM by the copy handler (zoom.html:221).
- Week row: static labels/dates `Du 13, Se 14, Chor 15, Pay 16, Ju 17, Sha 18, Yak 19` (zoom.html:59-90) — **overwritten on load** by the dynamic week script (zoom.html:195-215), which recomputes Mon–Sun from `new Date()`; `Se` is marked `today` (zoom.html:64) but the script re-applies `.today` by real date, and the event dots are **not** recomputed.
- Toast string on join (zoom.html:235): `🔗 Zoom havolasi brauzerda ochildi!` ("Zoom link opened in browser"); copy-success label `✓ Nusxalandi!` for 2s (zoom.html:224-225).

### 5.3 Interactive JS (zoom.html:193-241)
| Symbol | Lines | Trigger | Behaviour |
|---|---|---|---|
| Dynamic week-row IIFE | 195-215 | `DOMContentLoaded`-equivalent (inline, runs at parse) | Builds Mon-anchored week from `new Date()`; writes weekday names via `days = ['Yak','Du','Se','Chor','Pay','Ju','Sha']` indexed as `days[(d.getDay()+6)%7]` and day-of-month into each `.day-card`; toggles `.today` class. Selectors are **attribute-substring based**: `[style*="font-size:12px"]` and `[style*="font-size:15px"]` (zoom.html:207-208) — fragile; do not restructure the inline styles. |
| Copy handler | 217-229 | click on `document.querySelector('[style*="color:#6B3FD8"]')` (zoom.html:218) — i.e. the *Nusxa olish* button | Reads `document.querySelector('[style*="letter-spacing:.08em"]').textContent.trim()` (the Meeting ID), calls `navigator.clipboard.writeText(id)`, on success swaps button text to `✓ Nusxalandi!` and restores the original SVG+label after 2000 ms. **No `.catch()`** → clipboard denial/rejection is silent; no fallback for missing `navigator.clipboard`. |
| CTA handlers | 232-240 | `document.querySelectorAll('button.cta')` → each of the 3 *Qatnashish* buttons | Creates a fixed bottom-center purple toast div with the join string, appends to `body`, removes after 2200 ms. **Opens no URL, no Zoom client, no new tab** — purely cosmetic. |

### 5.4 Dead UI
- *Qatnashish* (×3, zoom.html:115,131,147) — **no real join**: no `window.open`, no deep link, no redirect, no room id, no attendance record (zoom.html:232-240).
- *Ko'rish* (View, ×2 past events, zoom.html:178,185) — **no handler at all** (dead buttons; also missing a `type="button"`, harmless inside no form).
- `.day-card`s look clickable (`cursor:pointer`, hover, zoom.html:32,34) but have **no click handler** — selecting a day does not filter the event list.
- The week-row dots (zoom.html:62,67,76,85) are static and are never derived from the event data.
- Meeting ID is a visible placeholder `[000 0000 0000]` and is **not** an actual `https://zoom.us/j/...` link.

### 5.5 Auth / identity assumptions
- None: no user, no "registered" badge, no participant count, no "you are registered" state. Registration/attendance is entirely absent and must be introduced by the API.

### 5.6 Navigation
- Back pill `← Asosiy` → `app.html` (zoom.html:44) — **no `#asosiy` hash**, unlike chat/notifications/jang/peshqadam.
- Footer `← Asosiy sahifaga qaytish` → `app.html` (zoom.html:190).
- Inbound: `notifications.html` cards 1 and 2 → `zoom.html` (notifications.html:152,168).

---

## 6. Cross-page navigation matrix

| From | Control (line) | To |
|---|---|---|
| chat.html | `handleChatBack()` back button (190) | `app.html#asosiy` (unless in a room → back to list) |
| notifications.html | back `<a>` (127) | `app.html#asosiy` |
| notifications.html | `Bepul qo'shiling` (152) | `zoom.html` |
| notifications.html | `Qo'shilish` (168) | `zoom.html` |
| notifications.html | `Batafsil ma'lumot` (189) | `dars.html` (not analysed) |
| jang.html | back `<a>` (229) | `app.html#asosiy` |
| peshqadam.html | back `<a>` (195) | `app.html#asosiy` |
| zoom.html | `← Asosiy` (44) + footer link (190) | `app.html` |
| zoom.html / jang.html / peshqadam.html | — | no links to chat.html or notifications.html from the analysed set (those two are reached from `app.html`, out of scope) |

---

## 7. Backend API specification

Realtime legend: **WS** = needs a websocket/push channel; **REST** = plain request/response is sufficient.

### 7.1 Users (current identity)
Identity assumption to replace: no page shows a user id or token; `peshqadam.html` hardcodes `Abdurahmon` (line 207), and jang.html hardcodes `Siz` (line 300). Assume a bearer/session token and an `id` the client stores at login.
- `GET /api/me` — REST. Response: `{ id, full_name, avatar_url|null, avatar_emoji|null, level: "Starter|Beginner|Elementary|Pre-Intermediate|Intermediate", points: number, rank: number }`. Feeds peshqadam.html:207/211/213 and jang.html:300.
- `GET /api/users/:id` — REST. Response: `{ id, full_name, avatar_url|null, avatar_emoji|null, level, points }`. Used for leader cards (peshqadam.html:233-331) and duel opponents (jang.html:372).
- `PATCH /api/me` — REST. Request: `{ full_name?, avatar_url?, avatar_emoji? }`.

### 7.2 Conversations
- `GET /api/conversations` — REST. Response: `[{ id, title, kind: "support|system|bot|direct", avatar: { letter|url|emoji }, last_message: { text, sender: "user|bot|other", created_at }, unread_count, updated_at }]`. Feeds chat.html:202-240 (current `chat-time` strings `08 avg 15:52`, `11 may 09:25`, `Hozir` are relative-time renders of `last_message.created_at`).
- `GET /api/conversations/:id` — REST. Response: conversation meta + participants + `{ id, title, kind }`.
- `POST /api/conversations/:id/read` — REST. Empty body → `204`. Backs `markAllChatRead()` (chat.html:326) — the response must also return the new unread total, or `GET /api/notifications/unread-count` must be refetched; **the prototype shows no badge, so an unread indicator must be added to the UI before this is visible.**
- `POST /api/conversations/read-all` — REST (alternative to the per-conversation call, matching the current one-button UI).

### 7.3 Messages — **realtime (WS)**
- `GET /api/conversations/:id/messages?before=<cursor>&limit=50` — REST (history/pagination). Response: `[{ id, conversation_id, sender_id|null, sender: "user|bot|other", text, created_at }]`. Seeds `chatMessagesDB` (chat.html:262-273). Note: the prototype stores **no per-message timestamps**, so `created_at` is a new field and the current UI cannot display it without a template change.
- `POST /api/conversations/:id/messages` — REST (send; supports optimistic UI). Request: `{ text, client_message_id }`. Response: `{ id, client_message_id, conversation_id, sender_id, text, created_at }`. Replaces the local push at chat.html:316.
- `WS /ws/chat` (or `GET /api/conversations/:id/stream` via SSE) — **realtime required**. Client → `{ type: "subscribe", conversation_id }`, `{ type: "typing", conversation_id }`; server → `{ type: "message.created", message }`, `{ type: "message.read", conversation_id, read_at }`, `{ type: "typing", conversation_id, user_id }`. Replaces the 800 ms fake bot reply (chat.html:320-323) and the list-level preview/time updates.
- Bot auto-reply behaviour currently faked at chat.html:321 (`Xabaringiz qabul qilindi! Tez orada mutaxassis yoki AI javob beradi.`) must come from the server if kept.

### 7.4 Notifications — **realtime (WS)**
- `GET /api/notifications?status=all|unread&before=<cursor>&limit=20` — REST. Response: `[{ id, title, body, created_at, is_read, banner: { gradient:[from,to], badge?: string, headline: string, subline?: string, emoji: string, chips?: [{label, color}] }, action: { label, url } }]`. Seeds the 3 cards, notifications.html:139-191 (exact strings in §2.2). The banner copy `MILLAT UMIDI`, `1 000 000 000`, `NAQDGA:`, `NASIYAGA:`, gradients and emojis are content, not layout, so they belong in the payload.
- `GET /api/notifications/unread-count` — REST. Response: `{ count }`.
- `POST /api/notifications/:id/read` — REST. Backs per-card read (not wired today).
- `POST /api/notifications/read-all` — REST. Backs `markAllRead()` (notifications.html:196).
- `WS /ws/notifications` — **realtime required** (push). Server → `{ type: "notification.created", notification }`, `{ type: "notification.read", id }`, `{ type: "unread.count", count }`. Nothing in the current markup reacts to a new notification (no toast/badge), so the UI must gain a badge/toast.
- Optional `DELETE /api/notifications/:id` — REST, for a dismiss action that does not exist yet.

### 7.5 Battles (jang) — **realtime (WS) for duel/group; REST for AI**
- `GET /api/battles/questions?lobby=grammar|vocabulary&limit=5` — REST. Response: `[{ id, text, options: [4 strings], correct_index }]`. Seeds `battleQuestions` (jang.html:332-347). **Security note:** return `correct_index` only to a trusted client, or validate answers server-side (preferred) and omit the key.
- `POST /api/battles` — REST (create/join a match). Request: `{ mode: "ai|duel|group", lobby: "grammar|vocabulary" }`. Response: `{ battle_id, mode, lobby, status: "waiting|active|finished", players: [{ id, name, avatar, score }], current_round, total_rounds: 5, round_seconds: 15 }`. Replaces `startBattle()` (jang.html:367).
- `POST /api/battles/:id/start` — REST (host starts; also used to force-start vs AI).
- `POST /api/battles/:id/answers` — REST or WS. Request: `{ round, question_id, chosen_index|null (null = timeout), answered_at }`. Response: `{ is_correct, points_awarded (+20 per jang.html:427), your_score, opponent_score, next: { round, question_id } | { finished: true } }`. Replaces `submitAnswer()` (jang.html:423) — score must become server-authoritative; the `Math.random() > 0.3` opponent simulation (jang.html:432) exists only because there is no opponent.
- `POST /api/battles/:id/finish` — REST. Response: `{ battle_id, result: "win|loss|draw", your_score, opponent_score, points_delta, stats: { battles, wins, losses } }`. Replaces the local `finishGame()` + `location.reload()` (jang.html:441-448); `result` feeds the counters at app.html:226-228 (`Janglar`/`Yutuqlar`/`Mag'lubiyat`, currently `0/0/0`).
- `GET /api/battles/history?limit=20` — REST. Response: `[{ battle_id, mode, lobby, result, your_score, opponent_score, finished_at, opponent: { name, avatar } }]`. Backs `openHistory()` (jang.html:450), whose placeholder text is `Janglar tarixi: Hozircha sizda 5 ta g'alaba va 120 ball mavjud!`.
- `GET /api/battles/stats` — REST. Response: `{ battles, wins, losses, points }` (the `0` placeholders in app.html:226-228 and the `5 wins / 120 ball` demo string).
- `GET /api/battles/matchmaking/queue` / `POST /api/battles/matchmaking/join` — REST, for `duel` (jang.html:372 `Azizbek`) and `group` (jang.html:375 `Jamoa (4 kishi)`) — no queue exists today; opponents are hardcoded.
- `WS /ws/battles/:id` — **realtime required** for `duel` and `group`. Client → `{ type: "answer", round, chosen_index }`, `{ type: "ready" }`; server → `{ type: "battle.state", players, round, total_rounds }`, `{ type: "round.started", round, question, seconds }` (replaces the local 15 s `setInterval`, jang.html:413-420), `{ type: "round.ended", round, correct_index, scores }`, `{ type: "opponent.answered", player_id }`, `{ type: "battle.finished", result, scores }`. AI mode (`mode: "ai"`) can stay REST/local because there is no second human.

### 7.6 Leaderboard
- `GET /api/leaderboard?level=starter|beginner|elementary|pre|inter&period=all|week|month&limit=50` — REST. Response: `{ level, period, me: { rank, user_id, name, points }, entries: [{ rank, user_id, name, points, avatar_url|null, avatar_emoji|null, is_crown?: boolean }] }`. Seeds the 7 rows (peshqadam.html:233-331) and finally makes `switchLevelTab()` (peshqadam.html:336) meaningful. The 👑 overlays on ranks 1/3/4 (peshqadam.html:238,267,282) should become an explicit field rather than markup.
- `GET /api/users/:id/points` — REST (optional), for the `⭐ 1` current-user pill (peshqadam.html:213) vs. leaderboard points.
- No realtime needed: ranks change slowly; a plain refetch (or 30–60 s poll) suffices.

### 7.7 Zoom events
- `GET /api/zoom/events?scope=upcoming|past&from=&to=` — REST. Response: `[{ id, title, subject, host: { id, name, avatar_url|null }, starts_at, ends_at, accent_color, status }]`. Seeds the 3 upcoming events (zoom.html:103-149; `Grammar Masterclass` `18:00–19:30`, `Speaking Club` `16:00–17:00`, `Vocabulary Challenge` `19:00–20:00`) and the 2 past events (`5-Oktyabr · 18:00`, `2-Oktyabr · 16:00`, zoom.html:176,183). `accent_color` captures `#35F59A`, `#0A93F5`, `#FFB26F`.
- `GET /api/zoom/calendar?week_start=` — REST. Response: `[{ date, day_of_week, event_count, has_event }]`. Needed because the week row's dots (zoom.html:62,67,76,85) are currently static while the dates are recomputed client-side (zoom.html:195-215).
- `GET /api/zoom/link` — REST. Response: `{ meeting_id: "000 0000 0000", join_url: "https://zoom.us/j/...", passcode?: string }`. Replaces the `[000 0000 0000]` placeholder (zoom.html:160).
- `POST /api/zoom/events/:id/register` — REST. Response: `{ registration_id, join_url, registered_at }`. Backs *Qatnashish* (zoom.html:115,131,147), which today only shows a toast.
- `POST /api/zoom/events/:id/unregister` — REST (optional, for a cancel action with no UI yet).
- `GET /api/zoom/events/:id/recording` — REST. Response: `{ recording_url, duration, available_at }`. Backs the dead *Ko'rish* buttons (zoom.html:178,185).
- No realtime needed: event lists, the shared link, registration and recordings are all plain request/response. A live "session started" push is optional and would need `WS /ws/zoom` if added.
- `host` is the placeholder `MR. [ISM]` in all three cards (zoom.html:112,128,144) and the host avatar is an inline SVG with no URL — the API must supply a real `host.name` + optional `avatar_url`.

### 7.8 Realtime summary
- **Needs realtime:** chat messages + typing/read receipts (§7.3); notification push + unread counts (§7.4); duel/group battle round sync, scores and finish events (§7.5).
- **Plain request/response is enough:** identity/profile (§7.1); conversation list + mark-read (§7.2); notification history/read (§7.4 REST half); AI-mode battle question bank, answering, finish, history and stats (§7.5 REST half); leaderboard (§7.6); all Zoom event data, link, registration and recordings (§7.7). The prototype has **zero polling and zero sockets**, so every realtime channel is net-new work.

---

## 8. Gaps a backend implementation must resolve (prototype inconsistencies)
- `chat.html` list rows and `chatMessagesDB` are two independent sources of truth keyed by title string (chat.html:205-238 vs 262-273) — an API must unify them under conversation ids; `openChatRoom`'s `letter` argument is unused (chat.html:286).
- `jang.html` markup default opponent is `AI Robot` (jang.html:309) but `startBattle()` writes `AI Bot` (jang.html:378); the static question default (jang.html:319) matches neither question bank.
- `jang.html` battle counters `Janglar: 0 / Yutuqlar: 0 / Mag'lubiyat: 0` and the current-user card live in `app.html` (lines 226-228), while the jang.html history alert claims `5 ta g'alaba va 120 ball` (jang.html:451) — the stats API should be the single source.
- `peshqadam.html` current user score `1` (line 213) vs. leaderboard 2346–3406 (lines 243-330) is inconsistent demo data; 👑 appears on ranks 1, 3 and 4.
- `zoom.html` week-row dates are dynamic (JS) but the event dots are static, and the *today* highlight is set twice (markup line 64, script lines 209-213).
- `zoom.html` selects DOM nodes by inline-style substrings (`[style*="color:#6B3FD8"]` line 218, `[style*="letter-spacing:.08em"]` line 221, `[style*="font-size:12px"]`/`[style*="font-size:15px"]` lines 207-208) — any template refactor silently breaks the copy button and the week row.
- `zoom.html` past-event dates have no year; `notifications.html` dates are `2026.*` (future-dated).
- No page has an unread badge, loading, error or empty state — the API contract can return these fields, but the UI cannot display them yet.
