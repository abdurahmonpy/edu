# Englify — Learning Screens: Backend & Seed Spec

Source of truth: static prototypes `dars.html`, `level.html`, `kitoblar.html`, `podcastlar.html`, `oyinlar.html`, `lugat.html`.
Read-only analysis. All line numbers refer to the file named in the current section.

Shared conventions used below
- `lang="uz"` on all six pages; font `Outfit`; no framework, no fetch/XHR anywhere (zero network calls in all six files).
- All interactive state is either in-memory JS variables or `localStorage`; nothing is persisted server-side.
- Audio/TTS is browser `SpeechSynthesisUtterance` (`en-US`), never a real audio file.
- Auth is absent; every "me" endpoint below needs an authenticated user context (except `level.html` quiz, which is anonymous-capable).

---

# 1. `dars.html` — Unit 1.1 lesson flow (886 lines)

Page: title `Unit 1.1 — Englify` (L6). One HTML file containing 5 mutually exclusive screens toggled by the `.active` class + `showScreen()`.

## 1.1 Screens / sections (Uzbek name + English gloss)

| id | Line | Uzbek label | English gloss |
|---|---|---|---|
| `screenMenu` | 352 | Unit 1.1 (bosh menyu) | Unit 1.1 hub: "Video" + "Homework Compulsory" cards with % |
| `screenVideoList` | 377 | Video (darslar ro'yxati) | Video lesson list — 3 alphabet lesson cards |
| `screenPlayer` | 479 | Dars videosi (to'liq ekran pleyer) | Fullscreen video theater + finish CTA |
| `screenHwList` | 509 | Homework Compulsory | Compulsory homework list — 4 exercise cards |
| `screenExercise` | 604 | Mashq / Tekshirish | Single-letter fill-in exercise page |

- Sticky top nav (L341-349): back arrow `handleBackClick()` (L342), title `#pageHeaderTitle` default `Unit 1.1` (L345), headphone button `playAudioHint()` (L346).
- Screen 1 cards: `Video` (L355-362, `#menuVideoPercent` default `0%` L359) → `goToVideoList()`; `Homework Compulsory` (L365-372, `#menuHwPercent` default `0%` L369) → `goToHomeworkFlow()`.
- Screen 2 lesson cards: `Alphabet 1` (L381), `Alphabet 2` (L416), `Alphabet 3` (L446). Each has "Video:" row (⭐ 0/1, 🟡 0/1) and "Mashq:" row (⭐ 0/8, 🟡 0/8); only card 1 has live element ids.
- Screen 3 player: `#videoIframe` (L485, `src=""`), `#playerLessonTitle` = `Alphabet 1 • Dars videosi` (L491), caption "Video yakunlangach avtomatik ravishda uy ishi mashg'ulotiga yo'naltiriladi." (L492); buttons `⛶ To'liq ekran` (L496) and `Tugatish & Uy ishiga o'tish →` (L499).
- Screen 4 homework cards (tags: `Choose Answer`/`Write Answer` + `Listening`): items at L513, L535, L557, L579.
- Screen 5 exercise: step bar `#exProgressFill` default `width: 25%` (L609), heading `Tushurib qoldirilgan harfni alifbo tartibida yozing` (L612-614), `#exLettersBox` static `A [_] C D` (L617-622), `#exampleText` `Example: A B C D` (L624), `#checkBtn` `Tekshirish` (L630).

## 1.2 Hardcoded / placeholder data (seed me)

Lesson videos — L647-651:
```
'Alphabet 1': 'https://www.youtube.com/embed/HQ3APZJj4qY?autoplay=1&rel=0&modestbranding=1'
'Alphabet 2': 'https://www.youtube.com/embed/ccEpTTZXSi8?autoplay=1&rel=0&modestbranding=1'
'Alphabet 3': 'https://www.youtube.com/embed/wpffswm5l9s?autoplay=1&rel=0&modestbranding=1'
```
Unit / lesson identity: unit name `Unit 1.1` (L345, L713, L718, L871); playlist title `Alphabet 1|2|3`; player title suffix `• Dars videosi` (L742).
Progress denominators (hardcoded, never real): video `0/1` & `1/1`; mashq `0/8` & `8/8`; homework cards `0/10` (items 1 & 3) and `0/12` (items 2 & 4).
Homework card metadata (L512-598):

| # | Type tag | Skill tag | Title (uz) | Stars/coins |
|---|---|---|---|---|
| 1 | `Choose Answer` (tag-green) | `Listening` | `Tinglang va to'g'ri javobni tanglang` (L526) | 0/10 |
| 2 | `Write Answer` (tag-lightgreen) | `Listening` | `Tinglang va to'g'ri javobni yozing` (L548) | 0/12 |
| 3 | `Choose Answer` | `Listening` | `Tinglang va to'g'ri javobni tanglang` (L570, sic — duplicate of #1) | 0/10 |
| 4 | `Write Answer` | `Listening` | `Tinglang va tushirib qoldirilgan harflarni yozing` (L592) | 0/12 |

TTS hint string — L877: `"Welcome to Unit 1.1! Let's learn the English alphabet."`
Completion alert — L870: `"Tabriklaymiz! Barcha topshiriqlar muvaffaqiyatli bajarildi! +50 XP hisobingizga qo'shildi!"` (XP is never stored).

## 1.3 localStorage keys (exact code, with line numbers)

| Key | Read | Write |
|---|---|---|
| `unit1_video_watched` | L640 `let videoWatched = localStorage.getItem('unit1_video_watched') === 'true';` | L764 `localStorage.setItem('unit1_video_watched', 'true');` |
| `unit1_video_percent` | L641 `let videoPercent = localStorage.getItem('unit1_video_percent') \|\| (videoWatched ? 100 : 0);` | L765 `localStorage.setItem('unit1_video_percent', '100');` |
| `unit1_hw_percent` | L642 `let hwPercent = localStorage.getItem('unit1_hw_percent') \|\| 0;` | L867 `localStorage.setItem('unit1_hw_percent', '100');` |

Notes: values are strings (`'true'`, `'100'`); `videoPercent`/`hwPercent` are used as numbers only after assignment. No key is ever removed. `unit1_video_percent` is read but never written with an intermediate value — only `100` or absent.

## 1.4 REST endpoints needed (grouped by entity)

**courses / units / lessons**
- `GET /api/courses` → `[{id, slug, title, level, unitCount}]` (seed: `A1 Starter`).
- `GET /api/courses/{courseId}/units` → `[{id, code: "1.1", title, order, videoLessonCount, exerciseCount}]`.
- `GET /api/units/{unitId}` → `{id, code:"1.1", title:"Unit 1.1", videoWatchedReq, hwRequired:true}`.
- `GET /api/units/{unitId}/video-lessons` → `[{id, title:"Alphabet 1", order:1, videoProvider:"youtube", embedUrl, autoplay:true}]` (3 items).
- `GET /api/units/{unitId}/homework` → `[{id, order, type:"choose"|"write", tags:["Choose Answer","Listening"], titleUz, maxStars:10|12, maxCoins, required:true}]` (4 items).
- `GET /api/video-lessons/{id}` → `{id, title, embedUrl, durationSec, unitId}`.

**progress**
- `GET /api/me/units/{unitId}/progress` → `{videoWatched:boolean, videoPercent:number, hwPercent:number, videoStars:{earned:0,max:1}, videoCoins:{earned,max:1}, exerciseStars:{earned,max:8}, exerciseCoins:{earned,max:8}}`.
- `PUT /api/me/units/{unitId}/progress` → body `{videoWatched:true, videoPercent:100}` (mirrors L764-765) or `{hwPercent:100}` (L867); response = updated progress object.
- `POST /api/me/video-lessons/{id}/complete` → `{videoPercent:100}`.
- `POST /api/me/units/{unitId}/xp` → `{amount:50, reason:"unit_homework_complete"}` (mirrors L870 alert).
- `GET /api/me/xp` → `{xp, level}`.

**quizzes / exercises**
- `GET /api/exercises/{exerciseId}/questions` → `[{id, order, letters:["A","","C","D"], correct:"B", example:"Example: A B C D"}]`.
- `POST /api/me/exercises/{exerciseId}/answers` → `{questionId, answer:"B"}` → `{correct:boolean, correctAnswer:"B"}` (server must decide correctness; current client logic L824-863).
- `POST /api/me/exercises/{exerciseId}/complete` → `{stars:8, coins:8, xp:50}`.

## 1.5 Interactive JS behaviour & handlers

- `updateUI()` L679: writes `#menuVideoPercent`/`#menuHwPercent`; if `videoWatched` sets `#vStar`/`#vCoin` to `1/1` and `#vBar` 100%; if `hwPercent > 0` sets `#mStar`/`#mCoin` to `Math.round(8*hwPercent/100)+"/8"` (L689-690) and `#mBar` width.
- `showScreen(screenId, title)` L695: toggles `.active`, sets header title, `window.scrollTo({behavior:'smooth'})`, clears `#videoIframe.src` whenever leaving `screenPlayer` (L703-706).
- `handleBackClick()` L709: `screenMenu` → `window.location.href = 'app.html#darslar'` (L711); `screenVideoList|screenHwList` → `screenMenu`; `screenPlayer` → `screenVideoList`; `screenExercise` → `screenMenu` if `videoWatched` else `screenHwList` (L716-722).
- `goToVideoList()` L726 → `screenVideoList`.
- `goToHomeworkFlow()` L731 → `goToExercise(1)` if `videoWatched`, else `screenHwList`.
- `startLessonVideo(lessonName)` L740: sets `#playerLessonTitle = name + ' • Dars videosi'`, sets iframe src from `lessonVideos` (fallback `Alphabet 1`), shows player.
- `toggleCinemaFullscreen()` L750: `requestFullscreen`/`webkitRequestFullscreen` on `#videoTheaterContainer`, `exitFullscreen` to toggle.
- `finishVideoAndGoToHw()` L760: sets `videoWatched=true`, `videoPercent=100`, persists both keys, `updateUI()`, clears iframe, `setTimeout(...,200)` → `goToExercise(1)`.
- `goToExercise(exNum)` L778: **`exNum` is completely ignored** — always `currentQIndex = 0`, then `loadExerciseQuestion()`, then `showScreen('screenExercise','')`.
- `loadExerciseQuestion()` L784: renders `#exLettersBox` from `exerciseData[currentQIndex]`, sets `#exampleText`, sets `#exProgressFill` to `((i+1)/4*100)%`, resets `#checkBtn`, autofocuses `#letterInput` after 100 ms.
- `handleInputLetter(e)` L809: uppercases/trims the value, toggles `.ready` + colors on `#checkBtn`.
- `playAudioHint()` L874: `speechSynthesis.speak(...)` with text from L877, `lang='en-US'`.
- Boot: `updateUI()` at L883.

**Dead / broken UI (flag for backend/frontend)**
- `goToExercise(exNum)` ignores its argument (L778-782): all four homework cards (L513, L535, L557, L579) open the *same* 4-question alphabet exercise. Per-item stars/coins `0/10`, `0/12` (L521-522, 543-544, 565-566, 587-588) are never updated by any code.
- `.hw-progress-fill` bars (L530, L552, L574, L596) are hardcoded `width: 0%` and have no JS reference — permanently 0%.
- `Alphabet 2` / `Alphabet 3` cards have no ids on their pills/bars (L424-434, L454-464) and no inner fill div — cannot ever reflect progress.
- `#checkBtn` looks disabled via `cursor: not-allowed` (L291) but is still clickable; it silently no-ops when the input is empty (L826).
- No `.hw-card` / `.big-card` keyboard handlers, no aria roles on the main cards.
- The 4 homework items (L509-601) are static DOM with no data source; `Listening` tag is decorative — nothing is played.
- No correctness feedback per-question is persisted; only a single `unit1_hw_percent = 100` is written at the end (L867).

## 1.6 Quiz / exercise data + scoring logic

`exerciseData` — L654-675, exactly 4 questions:

| # | `letters` | `correct` | `example` |
|---|---|---|---|
| 0 | `['A','','C','D']` | `B` | `Example: A B C D` |
| 1 | `['E','F','','H']` | `G` | `Example: E F G H` |
| 2 | `['J','','L','M']` | `K` | `Example: J K L M` |
| 3 | `['P','Q','','S']` | `R` | `Example: P Q R S` |

Scoring / flow (`checkExerciseAnswer()` L824): input is uppercased and compared to `exerciseData[currentQIndex].correct` (L828-832).
- Correct: input border `#2ED573`, bg `#EAFBF1`, button `#2ED573` + text `"To'g'ri! 🎉 Keyingisi"` (L837); after **800 ms** advance `currentQIndex++`; if `>= 4` → `onExerciseComplete()` (L839-846).
- Wrong: border `#FF4757`, bg `#FFEAEA`, button `#FF4757` + text `"Noto'g'ri, qayta urinib ko'ring"` (L852); after **1000 ms** clears input, resets colors/button to `Tekshirish`, refocuses (L853-861).
- No score counter, no attempt limit, no per-question stars. `onExerciseComplete()` L865: `hwPercent=100`, `localStorage.setItem('unit1_hw_percent','100')`, `updateUI()`, `alert(...+50 XP...)`, then `showScreen('screenMenu','Unit 1.1')`.
- `#exProgressFill` is index-based `(i+1)/4` (L788), not correctness-based.

## 1.7 Navigation

- Back button when on hub: `app.html#darslar` (L711).
- `level.html` has a forward link **into** this page: `level.html` L223 `href="dars.html"`.
- Internal (JS): menu↔videoList↔player↔hwList↔exercise per L709-775. No `<a>` links inside `dars.html` besides none.

---

# 2. `level.html` — CEFR levels + placement test (305 lines)

Title `Englify Darajalar (Levels)` (L6); meta description L7.

## 2.1 Screens / sections

- Header (L98-115): link `← Resurslar` → `app.html#resurslar` (L101); `🏆 CEFR Darajalari` (L105); current-level pill `Joriy: A1 Starter` (L111, static).
- Hero (L120-129): badge `O'quv yo'li` (L122); h2 `Noldan C1 gacha bo'lgan rivojlanish bosqichlari` (L123); subtitle `Har bir darajada yangi lug'atlar, grammatik mavzular va sertifikatlar sizni kutmoqda.` (L124); CTA `🎯 Darajani aniqlash testini topshirish` → `scrollToQuiz()` (L125-127).
- Roadmap `O'quv bosqichlari` (L132) with 4 `.level-card`s (L137, 157, 171, 185).
- Placement test `#quizSection` (L201): heading `🎯 Darajani aniqlash testi (Placement Test)` (L203), subtitle `Qisqa 3 ta savolga javob bering va bilim darajangizni aniqlang.` (L204), `#quizContainer` (L207) with `#qNumber`/`#qText`/`#optionsContainer`, and hidden `#quizResult` (L219).

## 2.2 Hardcoded data (seed me)

Levels (exact strings):

| Code | Title | Status badge | Description (L) |
|---|---|---|---|
| `A1` | `Starter • Boshlang'ich` (L143) | `Hozir o'qilmoqda` (L144), card class `active`, progress `4%` (L149/151) | `Salomlashish, asosiy so'zlar, oila, raqamlar va oddiy kundalik gaplar.` (L146) |
| `A2` | `Elementary • Oddiy muloqot` (L163) | `🔒 500 ball kerak` (L164), class `locked` | `Xaridlar, sayohat, o'tmishdagi hodisalar, ob-havo va rejalashtirish.` (L166) |
| `B1` | `Pre-Intermediate • O'rta bosqich` (L177) | `🔒 1500 ball kerak` (L178) | `Erkin fikr bildirish, kitoblar o'qish, kinolar tomosha qilish va insho yozish.` (L180) |
| `B2` | `Intermediate • Ishonchli nutq` (L191) | `🔒 3000 ball kerak` (L192) | `IELTS 6.0-6.5 darajasi, murakkab grammatika, ravon bahs-munozaralar.` (L194) |

Unlock thresholds to seed: A2 = 500 ball, B1 = 1500 ball, B2 = 3000 ball. A1 progress = 4%.
Quiz initial DOM: `#qNumber` = `1-SAVOL (3 tadan)` (L208); `#qText` = `"She ______ to school every morning." nuqtalar o'rniga to'g'ri so'zni tanlang:` (L209); options L212-215 `A) go`, `B) goes`, `C) going`, `D) wented`.
Result defaults: `#resLevel` = `A1 Starter` (L221); `#resDesc` = `Siz uchun eng yaxshi boshlanish — Starter Unit 1.1 darslari!` (L222); CTA `Darsga o'tish →` → `dars.html` (L223-225).
Result texts produced by JS (L296-300) — quote these verbatim for seeding:
- score >= 3: level `A2 Elementary`, desc `Ajoyib natija! Boshlang'ich bilimlaringiz mustahkam. Elementary darslariga tayyorsiz!` (L297)
- else: level `A1 Starter`, desc `Siz uchun hozirgi A1 Starter darslari (Unit 1.1) ayni muddao. Darsni hoziroq davom ettiring!` (L300)

## 2.3 localStorage

**None.** `level.html` contains zero `localStorage` references — quiz score and resulting level are lost on reload (L255-302 only use in-memory `curQ`, `score`).

## 2.4 REST endpoints (grouped by entity)

**levels**
- `GET /api/levels` → `[{code:"A1", title:"Starter • Boshlang'ich", descriptionUz, state:"active"|"locked", progressPercent:4, unlockScore:null|500|1500|3000, order}]`.
- `GET /api/me/level` → `{currentLevel:"A1", currentLevelTitle:"A1 Starter", totalScore}` (backs the header pill L111).
- `PUT /api/me/level` → `{levelCode:"A2"}` (promotion; `unlockScore` thresholds from L164/178/192).
- `GET /api/levels/{code}` → level detail + certificate/grammar topics referenced in L124.

**quizzes (placement test)**
- `GET /api/placement-test/questions` → `[{id, order, promptUz, options:["A) go",...], correctIndex}]` (3 questions, L237-253). Note: `correct`/`correctIndex` must NOT be exposed to the client for a real backend, unlike the current client-side array.
- `POST /api/placement-test/answers` / `POST /api/placement-test/submit` → body `{answers:[1,2,1]}` → `{score:3, maxScore:3, recommendedLevelCode:"A2", recommendedLevelTitle:"A2 Elementary", descriptionUz, nextLessonUrl:"dars.html"}`.
- Scoring rule to reproduce server-side: 1 point per correct answer, **no partial credit**; `score >= 3` (i.e. 100%) → A2, otherwise A1 (L295-301).

## 2.5 Interactive JS / handlers

- `scrollToQuiz()` L233: `document.getElementById('quizSection').scrollIntoView({behavior:'smooth'})`. Bound to hero CTA L125.
- `selectQuizAnswer(optIdx)` L258: `if (optIdx === questions[curQ].correct) score++;` then `curQ++`, then `loadQuestion()` or `showResult()`. No visual feedback, no re-answer, options from the initial DOM are replaced after Q1.
- `loadQuestion()` L271: rewrites `#qNumber` as `${curQ+1}-SAVOL (${questions.length} tadan)`, sets `#qText`, rebuilds `#optionsContainer` with `button.quiz-opt` elements whose `onclick` is `() => selectQuizAnswer(idx)`.
- `showResult()` L287: hides `#quizContainer`, shows `#quizResult`, sets `#resLevel`/`#resDesc` per the thresholds above.

**Dead UI**
- All 4 `.level-card`s (L137-196) have **no onclick / no `<a>`** — a locked level cannot be inspected and the active A1 level cannot be entered from here. Progress bar (L148-152) is static `width: 4%`.
- Header pill `Joriy: A1 Starter` (L111) is non-interactive.
- No skip, no restart, no "back to question" in the quiz; no timer; no per-option correct/incorrect styling is applied (`.quiz-opt.selected` CSS L88 exists but `selected` class is never added).
- `.quiz-opt:hover` (L84) is the only quiz feedback.

## 2.6 Quiz data + scoring

`questions` — L237-253, exactly 3 items:

| # | Question (verbatim) | Options | `correct` index |
|---|---|---|---|
| 0 | `"She ______ to school every morning." Nuqtalar o'rniga to'g'ri so'zni tanlang:` | `A) go`, `B) goes`, `C) going`, `D) wented` | `1` (`B) goes`) |
| 1 | `"I don't have ______ money in my wallet." Qaysi so'z mos keladi?` | `A) some`, `B) many`, `C) any`, `D) a` | `2` (`C) any`) |
| 2 | `"Yesterday, we ______ a great movie at the cinema."` | `A) see`, `B) saw`, `C) seen`, `D) was seeing` | `1` (`B) saw`) |

Scoring: `score` starts 0 (L256); +1 per correct (L259-261); max 3; threshold `score >= 3` → `A2 Elementary`, else `A1 Starter` (L295-300).

## 2.7 Navigation

- `← Resurslar` → `app.html#resurslar` (L101).
- `Darsga o'tish →` → `dars.html` (L223).
- No links to `kitoblar.html`, `podcastlar.html`, `oyinlar.html`, `lugat.html` from this page.

---

# 3. `kitoblar.html` — Book library + reader modal (326 lines)

Title `Kitoblar — Englify` (L6).

## 3.1 Screens / sections

- Header (L174-179): back arrow → `app.html#resurslar` (L175); h1 `Kitoblar` (L178).
- Three genre sections, each `h2.genre-title` + `.books-row` (horizontal scroll, L70-77): `Fantasy` (L185), `Biography` (L223), `Science Fiction` (L251).
- Book card `.book-card` (L79-96): cover gradient + emoji + views pill `👁️ N` (`.views-pill` L113-125), `.book-level` (L127), `.book-name` (L136).
- Reader modal `#readerModal` (L280-298): `#modalTitle` default `Kitob nomi` (L284), `#modalAuthor` default `Muallif` (L285), button `🔊 Tinglash` → `speakCurrentBook()` (L288), `×` → `closeReader()` (L291), `#modalText` (L294, empty in DOM).

## 3.2 Hardcoded book data (seed me — 7 books, exact values)

| Genre | Title (display) | Author | Level label | Views | Cover gradient | Emoji | onclick args (line) |
|---|---|---|---|---|---|---|---|
| Fantasy | `The alchemist` | Paulo Coelho | `Upper-Intermediat...` (truncated) | `👁️ 54.5k` | `135deg, #FF9F1C, #E65100` | ☀️ | `openReader('The Alchemist','Paulo Coelho', ...)` L189 |
| Fantasy | `Eragon` | Christopher Paolini | `Upper-Intermediat...` | `👁️ 5.9k` | `135deg, #1B3B6F, #061A40` | 🐉 | L199 |
| Fantasy | `Coraline` | Neil Gaiman | `Pre-Intermediate` | `👁️ 12.1k` | `135deg, #6C5CE7, #341F97` | 🗝️ | L209 |
| Biography | `The Diary of a Young Girl` | Anne Frank | `Upper-Intermediat...` | `👁️ 9.3k` | `135deg, #3D3D3D, #1E272E` | 📖 | L227 |
| Biography | `Can't Hurt Me: Master Your...` | David Goggins | `Intermediate 2 (B1+)` | `👁️ 671` | `135deg, #74B9FF, #0984E3` | 📗 | L237 |
| Science Fiction | `The City of Ember` | Jeanne DuPrau | `Intermediate` | `👁️ 4.2k` | `135deg, #D35400, #962D00` | 💡 | L255 |
| Science Fiction | `I, Robot` | Isaac Asimov | `Upper-Intermediate` | `👁️ 8.5k` | `135deg, #2C3E50, #000000` | 🤖 | L265 |

Note the title vs. arg mismatch on book 1: display `The alchemist` (L195) but `openReader` arg `The Alchemist` (L189); `Can't Hurt Me` display is CSS-truncated, full title in L237 is `Can't Hurt Me` with author sentence implying `Master Your...`.

Reader sample texts (verbatim `openReader` text argument — these are the only "content" in the app):
1. L189: `The boy's name was Santiago. Dusk was falling as he arrived with his herd at an abandoned church. The roof had fallen in long ago, and an enormous sycamore had grown on the spot where the sacristy had once stood. He decided to spend the night there.`
2. L199: `Wind howled through the night, carrying a scent that would change the world. A tall Shade lifted his head and sniffed the air. He looked human except for his crimson hair and maroon eyes. He was waiting for the dragon egg.`
3. L209: `Coraline discovered the door a little after they moved into the house. It was a very old house, with an attic under the roof and a cellar under the ground. There were twenty-one windows and a mysterious small wooden door in the drawing room.`
4. L227: `I hope I will be able to confide everything to you, as I have never been able to confide in anyone, and I hope you will be a great source of comfort and support. Sunday, 14 June 1942: On Friday, 12 June, I woke up at six o'clock and it was my birthday.`
5. L237: `For the first twenty-four years of my life, I was depressed, insecure, and overweight. But everything changed when I realized that nobody was coming to save me. I had to become my own hero.`
6. L255: `When the city of Ember was built, the Builders made sure that it would have everything necessary to survive for two hundred years in the underground darkness.`
7. L265: `Rule One: A robot may not injure a human being or, through inaction, allow a human being to come to harm. Dr. Susan Calvin looked at the mechanical worker with quiet determination.`

## 3.3 localStorage

**None.** The reader has no bookmarking, progress, or last-read persistence.

## 3.4 REST endpoints (books)

- `GET /api/books?genre=fantasy|biography|science-fiction` or `GET /api/books` returning `[{id, title, author, genre, levelLabel, views, coverGradient, coverEmoji, sampleText, fullTextUrl}]`.
- `GET /api/books/genres` → `["Fantasy","Biography","Science Fiction"]` (section order L185/223/251).
- `GET /api/books/{id}` → full book detail incl. `chapters`.
- `GET /api/books/{id}/content?chapter=` → paginated reader text (replaces the 2-3-sentence `sampleText` placeholder).
- `POST /api/books/{id}/view` → increments the `👁️` counter (currently hardcoded, L192/202/212/230/240/258/268).
- `GET /api/me/books/{id}/progress` → `{chapter, scrollPercent}`; `PUT /api/me/books/{id}/progress`.
- `GET /api/me/books?status=reading|finished` → for a "my library" view (does not exist in UI yet).
- Optional: `GET /api/books/{id}/audio` (real narration) to replace `SpeechSynthesis` (L316-323).

## 3.5 Interactive JS / handlers

- `openReader(title, author, text)` L303: sets `#modalTitle`, `#modalAuthor`, `#modalText`, stores `currentTextToSpeak = text` (L307), `#readerModal.style.display = 'flex'`.
- `closeReader()` L311: hides modal, `speechSynthesis.cancel()`.
- `speakCurrentBook()` L316: `new SpeechSynthesisUtterance(currentTextToSpeak)`, `lang='en-US'`, `rate=0.9`, speak.
- State: `let currentTextToSpeak = ''` L301 (reset to `''` only on page load).

**Dead UI**
- Modal has **no click-outside / Esc handler** — only the `×` button (L291) closes it (contrast with `lugat.html` L357/L432).
- Every `.book-card` is a `div` with `onclick` (no keyboard/aria) and only ever opens the modal; no book detail route.
- `🔊 Tinglash` has no stop/pause counterpart, no speed control, no active-state indicator.
- Views counts are static text; no like/favourite/bookmark control despite `.views-pill` styling.
- No pagination, "see all", or genre filter UI — rows are horizontally scrollable only (CSS L70-77).

## 3.6 Quizzes / exercises

None on this page.

## 3.7 Navigation

- Back arrow → `app.html#resurslar` (L175).
- No outbound links to the other five analysed pages.

---

# 4. `podcastlar.html` — Podcast list + transcript + floating player (339 lines)

Title `Englify Podkastlar (Audio Podcasts)` (L6); meta description L7.

## 4.1 Screens / sections

- Header (L97-114): `← Resurslar` → `app.html#resurslar` (L100); h1 `🎙️ Podkastlar (Audio)` (L104); pill `5 ta epizod` (L110, hardcoded count).
- Hero (L119-125): badge `Listening • Tinglab tushunish`, h2 `Haqiqiy jonli ingliz tili podkastlari`, subtitle `Har kuni 5 daqiqa tinglang, quloqni o'rgating va nutqingizni tabiiy talaffuz bilan boyiting.`
- List heading `Epizodlar to'plami` (L128); list `#podList` (L130) with 5 `.podcast-item`s.
- Transcript box (L215-223): `📝 Epizod transkripti (Matni):` (L217), label `Ingliz tilida` (L218), `#transcriptText` default `Boshlash uchun yuqoridagi epizodlardan birini tanlang va tinglang!` (L221).
- Fixed player bar `.player-bar` (L228-246): `#playBtn` (L231) → `togglePlay()`; `#playerTitle` default `Ep 1: How to introduce yourself` (L235); `#playerStatus` default `Tinglashga tayyor` (L236); `#speedBtn` `1.0x` (L241) → `changeSpeed()`.

## 4.2 Hardcoded episode data (seed me — 5 episodes)

| idx | id | Title (verbatim) | Uzbek description | Duration | Icon bg | onclick |
|---|---|---|---|---|---|---|
| 0 | `ep-0` | `Ep 1: How to introduce yourself like a native` | `Salomlashish va o'zini tanishtirishning jonli iboralari • A1-A2` | `⏱️ 3:15` | `#587CF9` | `playEpisode(0)` L133 |
| 1 | `ep-1` | `Ep 2: 10 Common English Mistakes and how to avoid them` | `Ko'p uchraydigan 10 ta grammatik xato va ularning yechimi • A2-B1` | `⏱️ 4:40` | `#9A3FEF` | `playEpisode(1)` L149 |
| 2 | `ep-2` | `Ep 3: Ordering Food at a Restaurant` | `Restoranda ovqat buyurtma qilish va hisob so'rash • A1` | `⏱️ 2:50` | `#2ED573` | `playEpisode(2)` L165 |
| 3 | `ep-3` | `Ep 4: Job Interview — Tell Me About Yourself` | `Ish suhbatida o'zingiz haqingizda muvaffaqiyatli gapirish • B1-B2` | `⏱️ 5:10` | `#FF7A3D` | `playEpisode(3)` L181 |
| 4 | `ep-4` | `Ep 5: Travel English — At the Airport & Check-in` | `Aeroportda ro'yxatdan o'tish va parvoz qoidalari • A2` | `⏱️ 3:45` | `#0A93F5` | `playEpisode(4)` L197 |

Transcripts — `episodes` array L249-270 (title + transcript in JS; titles in JS match the DOM titles exactly, except `#playerTitle` default L235 which is the abbreviated `Ep 1: How to introduce yourself`). Verbatim transcripts:
1. `Hello everyone and welcome to the Englify Podcast! Today we are talking about how to introduce yourself naturally. Instead of just saying 'My name is John and I am fine', native speakers often say: 'Hey, I'm John, great to meet you! How's your day going?' Remember, a warm smile and confident tone are just as important as the words!` (L252)
2. `Welcome back! Today's top mistake is saying 'I am agree with you'. In English, 'agree' is already a verb, so you simply say: 'I agree with you'. Another common slip is 'She don't know' instead of 'She doesn't know'. Practice these everyday to build automatic fluency!` (L256)
3. `Imagine you are sitting at a cozy café in London. The waiter approaches: 'Are you ready to order?' You can politely reply: 'Yes, please! Could I have the chicken salad and a cup of black coffee?' Never say 'I want this', always use 'Could I have' or 'I would like'.` (L260)
4. `The classic job interview opening: 'Tell me about yourself'. Don't recite your entire life story! Use the Present-Past-Future formula. Talk about where you are right now, one key past accomplishment, and why you are excited about this specific opportunity.` (L264)
5. `At the check-in desk, the agent will ask: 'Can I see your passport and booking reference?' Then they will ask: 'Would you prefer a window seat or an aisle seat?' Learn these phrases so your next international journey is smooth and stress-free!` (L268)

## 4.3 localStorage

**None.** No `last played`, no listen progress, no speed preference persisted. All state is `curEp`, `isPlaying`, `curRate` (L272-274).

## 4.4 REST endpoints (podcasts)

- `GET /api/podcasts` → `[{id, episodeNumber:1, title, titleShort, descriptionUz, levelRange:"A1-A2", durationSec:195, durationLabel:"3:15", audioUrl, transcript}]` (5 items; pill L110 `5 ta epizod` should become `{count}`).
- `GET /api/podcasts/{id}` → detail incl. transcript.
- `GET /api/podcasts/{id}/transcript` → `{lang:"en", segments:[{start,end,text}]}` (server-side timing needed for a real player).
- `POST /api/me/podcasts/{id}/play` → `{positionSec}` (listen tracking); `PUT /api/me/podcasts/{id}/progress`.
- `POST /api/me/podcasts/{id}/complete` → grants XP/ball (no reward exists today — the games page is the only score holder).
- `GET /api/me/podcasts` → `{listenedIds, completedIds}`.

## 4.5 Interactive JS / handlers

- `playEpisode(idx)` L276: sets `curEp`, toggles `.playing` on all `.podcast-item` by index (L278-280), sets `#playerTitle` and `#transcriptText` from `episodes[idx]`, sets `#playerStatus` = `Ijro etilmoqda...`, calls `startAudio()`.
- `startAudio()` L290: cancels any speech, creates `SpeechSynthesisUtterance(episodes[curEp].transcript)` with `lang='en-US'` and `rate=curRate`; `onend` → `isPlaying=false`, playBtn `▶️`, status `Yakunlandi`; then `speak()` and `isPlaying=true`, playBtn `⏸️`.
- `togglePlay()` L309: if playing → `speechSynthesis.pause()`, `▶️`, status `Pauzada`; else if `speechSynthesis.paused` → `resume()`, `⏸️`, `Ijro etilmoqda...`; otherwise `playEpisode(curEp)`.
- `changeSpeed()` L327: cycles `1.0 → 1.25 → 1.5 → 1.0` (L328-330), writes `curRate.toFixed(1)+'x'` to `#speedBtn`, restarts audio if playing.

**Dead UI / gaps**
- **No `<audio>` element and no `audioUrl` anywhere** — "playback" is TTS of the transcript; durations (`3:15` etc.) are pure decoration.
- No seek bar, no elapsed/remaining time, no volume, no next/previous episode button in the player bar.
- No per-episode progress badge, no "listened" state, no completion tracking.
- `#playBtn` before any selection plays `episodes[0]` (since `curEp` defaults to 0, L272) while `#playerTitle` shows the abbreviated Ep 1 label.
- `.podcast-item` is a `div` (no keyboard/aria); no download/transcript-copy button.

## 4.6 Quizzes / exercises

None.

## 4.7 Navigation

- Back to `app.html#resurslar` (L100). No links to other analysed pages.

---

# 5. `oyinlar.html` — Games hub + live Speed Match (342 lines)

Title `Englify O'yinlar` (L6); meta description L7.

## 5.1 Screens / sections

- Header (L111-128): `← Resurslar` → `app.html#resurslar` (L114); h1 `🎮 O'yinlar olami` (L118); score badge `⭐ <span id="gameScore">0</span> ball` (L123-125).
- Hero (L133-140): badge `Zavqli ta'lim`, h2 `O'yin o'ynab ingliz tilini o'rganing!`, subtitle `So'z boyligingizni oshiring, tez fikrlang va boshqa talabalar bilan bellashing.`
- Section `Mavjud o'yinlar` (L143) with 3 game cards (L148, L158, L168).
- Live game `#gameSection` (L180) `Speed Match: So'z juftliklari` (L184) + subtitle `Inglizcha so'zni uning o'zbekcha tarjimasi bilan moslashtiring!` (L185); timer `#timerText` default `0s` (L190); reset `🔄 Yangilash` → `resetMatchGame()` (L192); grid `#matchGrid` (L199, JS-rendered); win banner `#winBanner` (L204-209) with `Qoyilmaqom! Barcha juftliklar topildi!` / `Siz +50 ball ishlab oldingiz!` / `Yana o'ynash` → `resetMatchGame()`.

## 5.2 Hardcoded game data (seed me)

Game catalogue cards (L147-175):

| # | Game name | Uzbek description | CTA label | Action |
|---|---|---|---|---|
| 1 | `So'zlar jangi` (L151) | `Vaqt bilan poyga: 30 ta so'z tarjimasini eng tez toping!` (L152) | `O'ynash →` | `<a href="jang.html">` L148 (separate page, out of scope) |
| 2 | `Speed Match` (L161) | `Inglizcha va o'zbekcha so'z juftliklarini eng tez toping.` (L162) | `Pastda o'ynash ↓` | `onclick="scrollToGame()"` L158 |
| 3 | `Sentence Builder` (L171) | `Aralash so'zlardan to'g'ri inglizcha gap tuzing.` (L172) | `Boshlash →` | `onclick="openSentenceGame()"` L168 → alert only (L335) |

Speed Match pair pool — `wordPairs` L216-225, exactly 8 pairs (only 4 are used per round, L246):
```
Teacher → O'qituvchi      Student → Talaba        Knowledge → Bilim
Success → Muvaffaqiyat    Listen  → Eshitmoq      Speak → Gapirmoq
Book    → Kitob           Friend  → Do'st
```
Stub message (L335): `"Sentence Builder: Tez orada yangi darajalar ochiladi! Hozircha Speed Match va So'zlar jangi rejimlarida bellashishingiz mumkin."`

## 5.3 localStorage

**None.** `score`, `timer`, `matchedCount` are in-memory only (L227-232) and reset on page reload; nothing is submitted anywhere.

## 5.4 REST endpoints (games)

- `GET /api/games` → `[{slug:"sozlar-jangi", name:"So'zlar jangi", descriptionUz, icon:"⚔️", ctaLabel, url:"jang.html", isLive:true}, {slug:"speed-match", ..., isLive:true}, {slug:"sentence-builder", ..., isLive:false, statusText:"Tez orada..."}]`.
- `GET /api/games/speed-match/round?pairs=4` → `{roundId, pairs:[{pairId, en, uz}], timeLimitSec:null}` (server-side shuffle replaces `Math.random()` L246/254).
- `POST /api/games/speed-match/rounds/{roundId}/submit` → `{matchedPairIds:[...], wrongAttempts, durationSec}` → `{score: 15*pairs + 50, breakdown:{perMatch:15, completionBonus:50}}`.
- `POST /api/me/games/{slug}/score` → `{score, durationSec, moves}` (the ⭐ ball counter, L124).
- `GET /api/me/games/score` → `{totalScore}` (hydrate `#gameScore` instead of 0).
- `GET /api/games/leaderboard` → referenced by the hero copy "boshqa talabalar bilan bellashing" (L137) but no UI exists.
- `POST /api/games/sentence-builder/{roundId}/submit` (for the future mode).

## 5.5 Interactive JS / handlers

- `scrollToGame()` L234: `#gameSection.scrollIntoView({behavior:'smooth'})` (bound L158).
- `initMatchGame()` L238: clears grid, resets `selectedCards`/`matchedCount`, hides `#winBanner`; shuffles and slices 4 pairs (L246), creates 2 cards per pair tagged `{id, text, type:'en'|'uz', pairId}` (L250-251), shuffles cards, renders `div.match-card` with `el.dataset.index` and `el.onclick = () => onCardClick(index, el)` (L256-262); resets and starts a 1-second `setInterval` timer updating `#timerText` as `Ns` (L266-272).
- `onCardClick(index, el)` L275: ignores matched/selected cards or when 2 are already selected; adds `.selected`; at 2 selections calls `checkMatch()`.
- `checkMatch()` L288: match condition `c1.card.pairId === c2.card.pairId && c1.card.type !== c2.card.type` (L291) → after 250 ms adds `.matched`, `matchedCount++`, `score += 15`, updates `#gameScore`, and if `matchedCount === 4` calls `onGameWin()`; mismatch → `.wrong` after 150 ms, removed after 700 ms.
- `onGameWin()` L323: `clearInterval(timerInterval)`, `score += 50`, updates `#gameScore`, shows `#winBanner`.
- `resetMatchGame()` L330 → `initMatchGame()`.
- `openSentenceGame()` L334 → `alert(...)` stub.
- Auto-start: `initMatchGame()` L339 — the timer starts on page load even before the user scrolls to the game.

**Issues to flag**
- No `.match-card` keyboard/aria support; no way to pause.
- Score has no persistence and no server validation; per-round score is fully client-computed and trivially forgeable.
- Timer is display-only — it never ends the round and is not shown in the win banner.
- `Sentence Builder` (L168) is a dead feature (alert stub); `So'zlar jangi` leaves the page to `jang.html` (L148, outside this spec's scope).
- Game card 1 is an `<a>`, cards 2-3 are `div`s with `onclick` — inconsistent semantics.

## 5.6 Quiz / game scoring logic

- +15 points per correctly matched pair (L301), 4 pairs per round → 60.
- +50 points bonus on completing all 4 pairs (L325).
- Maximum per round: **110** points, cumulative in-page only (`score` never reset by `resetMatchGame()` — it keeps growing across rounds).
- Wrong attempts: no penalty, only the shake animation (L99-105).

## 5.7 Navigation

- Back to `app.html#resurslar` (L114).
- `So'zlar jangi` → `jang.html` (L148).

---

# 6. `lugat.html` — Personal vocabulary ("Mening lug'atim") (446 lines)

Title `Mening lug'atim — Englify` (L6). This is the only page that persists user data.

## 6.1 Screens / sections

- Header gradient (L93-123): `← Asosiy` → `app.html` (L96); `▶ Flashcard` button → `openFlash()` (L97); title `Mening lug'atim` (L101); subtitle `So'zlaringizni saqlang va takrorlang` (L102); stat badge `Jami: <span id="total-count">0</span> ta so'z` (L120); decorative SVG book (L106-114).
- Search + filter card (L129-140): `#search-input` `type="search"` placeholder `So'z qidirish...` (L132); 4 `.pill` filter buttons (L135-138): `Hammasi` `data-filter="all"`, `Yangi` `="new"`, `O'rganilgan` `="learned"`, `Takrorlash kerak` `="review"`.
- Word list `#word-list` (L143) — rendered by JS.
- `Lug'at qanday ishlaydi?` (L149) with 3 info cards (L151-165): `📚 Darsdan` — `Darslar davomida yangi so'zlar avtomatik qo'shiladi`; `✏️ Qo'lda` — `+ tugmasi bilan o'zingiz so'z qo'shasiz`; `🔄 Takrorlash` — `Muntazam takrorlash eslatmalari yuboriladi`.
- Back link `← Asosiy sahifaga qaytish` → `app.html` (L169); FAB `+` `aria-label="So'z qo'shish"` → `openModal()` (L173).
- Add-word modal `#modal-overlay` (L176): heading `✚ So'z qo'shish` (L179); `#inp-en` label `Inglizcha so'z *` placeholder `e.g. Hello` (L185); `#inp-uz` label `O'zbekcha tarjima *` placeholder `e.g. Salom` (L189); `#inp-type` select (L193-200) options `so'z` (default), `ibora`, `ot` (Ot (noun)), `fe'l` (Fe'l (verb)), `sifat` (Sifat (adjective)), `ravish` (Ravish (adverb)); `#inp-ex` label `Misol gapcha (ixtiyoriy)` placeholder `e.g. Hello, how are you?` (L204); `#modal-error` (L206); `Salom`/`Saqlash` button → `addWord()` (L207).
- Flashcard overlay `#flash-overlay` (L213): counter `#fl-num` / `#fl-total` (L215); flip zone `#flash-card-wrap` → `flipCard()` (L216); front `INGLIZCHA` + `#fl-en` default `Hello` + `#fl-type` default `[so'z]` + hint `Bosing — ko'rish uchun`; back `O'ZBEKCHA` + `#fl-uz` default `Salom` + `#fl-ex`; buttons `← Oldingi` → `flashPrev()`, `Keyingi →` → `flashNext()` (L232-233), `Yopish` → `closeFlash()` (L235).

Word status badges: `badge-new` "Yangi", `badge-learned` "O'rganilgan", `badge-review` "Takrorlash kerak" (L280-282). Card classes `wcard`, `wcard.learned`, `wcard.review` (L46-49).

## 6.2 Hardcoded / seed data (exact — L247-256)

Prefilled **only when `lugat_words` is empty** (`if(words.length === 0)` L247):

| id | en | uz | type | ex | status |
|---|---|---|---|---|---|
| 1 | `Hello` | `salom` | `so'z` | `Hello! How are you?` | `learned` |
| 2 | `Goodbye` | `xayr` | `so'z` | `Goodbye, see you tomorrow!` | `learned` |
| 3 | `Thank you` | `rahmat` | `ibora` | `Thank you very much!` | `learned` |
| 4 | `Please` | `iltimos` | `ibora` | `Please help me.` | `new` |
| 5 | `Good morning` | `xayrli tong` | `ibora` | `Good morning, class!` | `new` |

All five get `date: Date.now()` (L249-253) — note this means the seeded `date` is "now", not a real acquisition date, and `date` is never read anywhere in the file.
Word object shape (from L375-379): `{ id:number, en:string, uz:string, type:string, ex:string, status:'new'|'learned'|'review', date:number }`.
Other fixed strings: empty-state (L276) `Hali so'z qo'shilmagan` + `+ tugmasi bilan so'z qo'shishni boshlang!`; delete confirm (L317) `"Bu so'zni o'chirasizmi?"`; flash-empty alert (L390) `"Ko'rsatish uchun so'zlar yo'q!"`; validation error (L369) `"Inglizcha va o'zbekcha so'zlarni kiriting!"`.

## 6.3 localStorage

Single key: **`lugat_words`** (JSON array of word objects).

| Line | Code |
|---|---|
| L241 | `var words = JSON.parse(localStorage.getItem('lugat_words') \|\| '[]');` |
| L259 | `localStorage.setItem('lugat_words', JSON.stringify(words));` (inside `save()`, L258-260) |

Write call sites: `save()` invoked at L255 (seed), L313 (`setStatus` — sets `w.status`, then `save(); render();`), L319 (`deleteWord` — `words = words.filter(...)`, `save(); render();`), L381 (after `words.unshift(newWord)` in `addWord`).
- `setStatus(id, status)` L311 is called only with literal `'learned'` (L292), `'review'` (L293), `'new'` (L294) — no arbitrary server-side statuses.
- `deleteWord(id)` L316 does **not** rebalance ids; ids come from `Date.now()` for new words (L376), so deletion is permanent and local-only.
- No key is ever removed; clearing site data re-seeds the 5 demo words.
- Other pages do **not** read `lugat_words` (no cross-page vocabulary sync).

## 6.4 REST endpoints (vocabulary)

- `GET /api/me/vocabulary?status=new|learned|review&q=<search>` → `[{id, en, uz, type, example, status, createdAt, source:"lesson"|"manual"}]` — replaces the client-side `getFiltered()` (L262-269), which filters on `w.status === curFilter` and case-insensitive substring match on `w.en` **or** `w.uz` (L264-266).
- `POST /api/me/vocabulary` → `{en, uz, type, example}` → created word with `status:"new"` (mirrors `addWord` L361-384, which prepends via `unshift` L380).
- `PATCH /api/me/vocabulary/{id}` → `{status:"learned"|"review"|"new"}` (mirrors `setStatus` L311-314).
- `DELETE /api/me/vocabulary/{id}` (mirrors `deleteWord` L316-320).
- `GET /api/me/vocabulary/stats` → `{total}` (backs `#total-count`, L120/L272).
- `GET /api/me/vocabulary/flashcards?status=&order=random` → deck for the flashcard overlay (client currently cycles the filtered array with wrap-around, L416-425).
- `POST /api/vocabulary/{id}/review` → spaced-repetition event (the UI copy promises "Muntazam takrorlash eslatmalari yuboriladi", L164, with no implementation).
- `GET /api/vocabulary/types` → `["so'z","ibora","ot","fe'l","sifat","ravish"]` (L194-199).
- Auto-import from lessons ("Darslar davomida yangi so'zlar avtomatik qo'shiladi", L154): `POST /api/me/vocabulary/import` `{lessonId, wordIds}`.

## 6.5 Interactive JS / handlers

- `getFiltered()` L262, `render()` L271 (writes `#total-count` = `words.length` — total, not filtered; renders cards with inline status buttons and per-word speak/delete buttons; empty state L276), `escHtml()` L309 (escapes `& < > "` — injection-safe), `speak(text)` L322 (TTS `en-US`, `rate 0.9`).
- Event listeners: `.pill` click → set `curFilter = btn.dataset.filter` and re-render (L332-339); `#search-input` `input` → `curSearch` + re-render (L340-343); `#modal-overlay` click on backdrop → `closeModal()` (L357-359); `#flash-overlay` click on backdrop → `closeFlash()` (L426-428).
- Inline `onclick` in rendered HTML: `setStatus(id,'learned'|'review'|'new')` (L292-294), `speak('<en>')` (L298), `deleteWord(id)` (L301).
- Modal: `openModal()` L346 (adds `.active`, focuses `#inp-en`, hides `#modal-error`, clears `#inp-en`, `#inp-uz`, `#inp-ex` — **`#inp-type` is not reset**, L350-352), `closeModal()` L354, `addWord()` L361 (trims all fields, validates `en`/`uz` non-empty else shows `#modal-error` L369, builds `{id: Date.now(), ..., status:'new', date: Date.now()}`, `unshift`, `save()`, `render()`, `closeModal()`).
- Flashcards: `openFlash()` L387 (uses `getFiltered()`, alerts if empty, `flashIdx = 0`, adds `.active`, unflips), `closeFlash()` L398, `flipCard()` L401 (`classList.toggle('flipped')`), `showFlash(fw)` L404 (sets `#fl-num` = `flashIdx+1`, `#fl-total`, `#fl-en`, `#fl-type` = `'['+w.type+']'`, `#fl-uz`, `#fl-ex` or `''`, unflips), `flashNext()` L416 / `flashPrev()` L421 (modulo wrap-around over the **filtered** list).
- Keyboard: `document.addEventListener('keydown', ...)` L431-441 — `Escape` closes both modal and flashcard; when flash overlay is active `ArrowRight` → next, `ArrowLeft` → prev, `' '` (preventDefault) → flip.
- Boot: `render()` L443.

**Dead UI / gaps**
- Flashcard speaks nothing automatically; no audio button inside the card; no "I know it / don't know" action, so flashcards do not update `status`.
- No edit-word feature (only status change + delete).
- `#inp-type` value is not cleared on reopen (L350-352).
- `deleteWord` uses native `confirm()` (L317) and `openFlash` native `alert()` (L390).
- No pagination/virtualisation; `render()` re-renders the whole list on every keystroke (L340-343).
- The `date` field is stored but never displayed or used.
- No sync indicator, no offline/error state — everything is assumed local.

## 6.6 Quizzes / exercises

None. (Flashcards are recall-only, no scoring.)

## 6.7 Navigation

- `← Asosiy` → `app.html` (L96); `← Asosiy sahifaga qaytish` → `app.html` (L169).
- No links to the other five analysed pages.

---

# 7. Cross-page summary

## 7.1 All localStorage keys in scope (3 keys, all in `dars.html` + `lugat.html`)

| Key | File | Type / values | Read | Write |
|---|---|---|---|---|
| `unit1_video_watched` | dars.html | string `'true'` | L640 | L764 |
| `unit1_video_percent` | dars.html | string `'100'` (or absent) | L641 | L765 |
| `unit1_hw_percent` | dars.html | string `'100'` (or `0`) | L642 | L867 |
| `lugat_words` | lugat.html | JSON array of `{id,en,uz,type,ex,status,date}` | L241 | L255, L313, L319, L381 (all via L259) |

`level.html`, `kitoblar.html`, `podcastlar.html`, `oyinlar.html`: **no localStorage**.

## 7.2 Navigation link matrix

| From | To | Reference |
|---|---|---|
| `dars.html` L711 | `app.html#darslar` | back from hub |
| `level.html` L101 | `app.html#resurslar` | back |
| `level.html` L223 | `dars.html` | `Darsga o'tish →` |
| `kitoblar.html` L175 | `app.html#resurslar` | back |
| `podcastlar.html` L100 | `app.html#resurslar` | back |
| `oyinlar.html` L114 | `app.html#resurslar` | back |
| `oyinlar.html` L148 | `jang.html` | `So'zlar jangi` |
| `lugat.html` L96, L169 | `app.html` | back ×2 |

No page links directly to another of the five in this set except `level.html → dars.html`.

## 7.3 Consolidated API surface (grouped by domain entity)

**courses**
- `GET /api/courses`
- `GET /api/courses/{id}`
- `GET /api/courses/{id}/units`

**units**
- `GET /api/units/{id}`
- `GET /api/units/{id}/homework`
- `GET /api/units/{id}/video-lessons`
- `GET /api/me/units/{id}/progress` / `PUT /api/me/units/{id}/progress`

**lessons**
- `GET /api/video-lessons/{id}`
- `POST /api/me/video-lessons/{id}/complete`

**progress**
- `GET /api/me/progress?unitId=`
- `POST /api/me/xp` / `GET /api/me/xp`
- `GET /api/me/dashboard` (aggregate for `dars.html` hub percentages)

**vocabulary**
- `GET|POST /api/me/vocabulary`
- `PATCH|DELETE /api/me/vocabulary/{id}`
- `GET /api/me/vocabulary/stats`
- `GET /api/me/vocabulary/flashcards`
- `POST /api/vocabulary/{id}/review`

**quizzes**
- `GET /api/exercises/{id}/questions`
- `POST /api/me/exercises/{id}/answers`
- `POST /api/me/exercises/{id}/complete`
- `GET /api/placement-test/questions`
- `POST /api/placement-test/submit`

**books**
- `GET /api/books` / `GET /api/books/{id}` / `GET /api/books/genres`
- `GET /api/books/{id}/content`
- `POST /api/books/{id}/view`
- `GET|PUT /api/me/books/{id}/progress`

**podcasts**
- `GET /api/podcasts` / `GET /api/podcasts/{id}`
- `GET /api/podcasts/{id}/transcript`
- `POST /api/me/podcasts/{id}/play` / `POST /api/me/podcasts/{id}/complete`
- `GET /api/me/podcasts`

**games**
- `GET /api/games` / `GET /api/games/{slug}`
- `GET /api/games/speed-match/round`
- `POST /api/games/speed-match/rounds/{id}/submit`
- `POST /api/me/games/{slug}/score` / `GET /api/me/games/score`
- `GET /api/games/leaderboard`

**levels**
- `GET /api/levels` / `GET /api/levels/{code}`
- `GET /api/me/level` / `PUT /api/me/level`

## 7.4 Global seed-data checklist (everything a seeder must insert)

1. Course `A1 Starter` → Unit `1.1` (`Unit 1.1`).
2. 3 video lessons: `Alphabet 1` (YouTube `HQ3APZJj4qY`), `Alphabet 2` (`ccEpTTZXSi8`), `Alphabet 3` (`wpffswm5l9s`), all `autoplay=1&rel=0&modestbranding=1`.
3. 4 compulsory homework items with types/tags/titles/max stars 10,12,10,12 (table in §1.2).
4. 4 fill-in-the-missing-letter alphabet questions (`A_C D`→B, `EF_H`→G, `J_LM`→K, `PQ_S`→R) with examples `Example: A B C D` etc.
5. 4 CEFR levels with titles, Uzbek descriptions, lock thresholds 500/1500/3000, A1 active at 4%.
6. 3 placement-test questions with options and correct indices `[1,2,1]`; threshold `score >= 3 → A2 Elementary`.
7. 7 books in 3 genres with author, level label, view counts, cover gradient/emoji, and the sample-text excerpts (table + texts in §3.2).
8. 5 podcast episodes with title, Uzbek description, level range, duration label, and transcript (table + texts in §4.2).
9. 3 games (`So'zlar jangi`, `Speed Match`, `Sentence Builder`) with descriptions, plus the 8 Speed Match word pairs.
10. 5 starter vocabulary words with statuses per §6.2, plus the 6 vocabulary `type` options.
11. UI copy strings: XP alert (+50), completion alerts, empty/error states, stub alert for Sentence Builder.
