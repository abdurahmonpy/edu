# Frontend integration contract

Read this fully before touching any HTML. It is the single source of truth for
how the static pages talk to the FastAPI backend.

---

## 1. Load order (exact)

Every page must load the shared scripts in this order, **just before `</body>`**,
after any existing page script:

```html
<script src="assets/js/config.js"></script>
<script src="assets/js/ui.js"></script>
<script src="assets/js/api.js"></script>
<script src="assets/js/auth.js"></script>
<script src="assets/js/pages/<pagename>.js"></script>
```

`config.js`, `ui.js`, `api.js` and `auth.js` already exist — **never edit them**.
Your page logic lives in exactly one new file: `assets/js/pages/<pagename>.js`.

## 2. Page auth mode

Add `data-auth` to the existing `<body>` tag **without removing its `style`**:

| mode | behaviour |
|---|---|
| `required` | redirects to `kirish.html?next=…` when logged out (app pages) |
| `optional` | never redirects (landing page) |
| `public` | never redirects, never loads the profile |
| `guest` | redirects to `app.html` when **already** logged in (login page) |

Example: `<body style="margin:0" data-auth="required">`

`auth.js` boots automatically on `DOMContentLoaded`. To run page code after the
session is ready, either listen for the event or await the helper:

```js
document.addEventListener('englify:user', function (e) { var user = e.detail; });
// or, inside an async IIFE:
var user = await EnglifyAuth.require();   // 'required' pages
var user = await EnglifyAuth.optional();  // 'optional' pages (may be null)
```

## 3. `window.EnglifyApi` — HTTP + session

```js
EnglifyApi.get(path)                    // -> Promise<parsed JSON>
EnglifyApi.post(path, body)
EnglifyApi.patch(path, body)
EnglifyApi.del(path)
EnglifyApi.request(path, { method, body, auth: false, headers })

EnglifyApi.session()      // { access_token, refresh_token, user } | null
EnglifyApi.user()         // cached user object | null
EnglifyApi.isLoggedIn()   // boolean
EnglifyApi.setSession(payload) / .clearSession()
EnglifyApi.wsUrl('/ws/chat/ID')  // ws://…/api/v1/ws/chat/ID?token=…
EnglifyApi.on('login'|'logout'|'session', handler)
EnglifyApi.ApiError       // error.message (Uzbek), error.status, error.body, error.errors
```

* `path` is **relative to `/api/v1`** and must start with `/`, e.g. `EnglifyApi.get('/courses')`.
* The `Authorization` header is added automatically; a 401 triggers one
  transparent refresh + replay, then a redirect-free failure.
* Errors always reject with `EnglifyApi.ApiError`. Show `error.message` to the
  user — it is already human-readable Uzbek.

## 4. `window.EnglifyUI` — rendering helpers

```js
UI.escape(str)                 // ALWAYS use for user-provided text in innerHTML
UI.number(1234)                // "1 234"
UI.initials(name)              // "AV"
UI.avatar(user, size)          // HTML string, handles missing avatar_url
UI.date(v) UI.short(v) UI.datetime(v) UI.relative(v) UI.duration(sec)
UI.eventLabel(startsAt, durationMinutes)   // "Bugun · 18:00 – 19:30"
UI.toast(message, 'success'|'error'|'info'|'warn')
UI.loading(containerEl, rows)  // skeleton loader
UI.empty(message, hint)        // empty-state HTML
UI.errorBox(error)             // error card HTML
UI.on(root, selector, event, handler)
UI.qs('lesson')                // query-string value
UI.debounce(fn, ms)
UI.fill(scopeEl, dataObj)      // fills [data-field="key"] nodes
```

## 5. `window.EnglifyAuth` — session chrome

```js
EnglifyAuth.require() / .optional() / .me(force) / .stats(force)
EnglifyAuth.refreshBadges()    // unread counts -> [data-badge="notifications"|"chat"]
EnglifyAuth.logout({ allDevices: false })
EnglifyAuth.state              // { user, stats, notifications, chats }
EnglifyAuth.bindLogout()       // wires [data-action="logout"]
```

`auth.js` **automatically fills** these attributes wherever you put them:

| attribute | filled with |
|---|---|
| `data-user-name` | full name |
| `data-user-email` | email |
| `data-user-points` | points |
| `data-user-level` | level title ("Starter"…) |
| `data-user-streak` | streak days |
| `data-user-initials` | "AV" |
| `data-user-avatar` | `<img>`/emoji/initials avatar (`data-size="44"` optional) |
| `data-badge="notifications"` | unread count (hidden when 0) |
| `data-badge="chat"` | unread count (hidden when 0) |

Elements with `data-auth="user"` are hidden while logged out, `data-auth="login"`
while logged in. A logout button is just:

```html
<button data-action="logout" type="button">Chiqish</button>
```

Document events: `englify:user`, `englify:stats`, `englify:realtime`, `englify:guest`.

---

## 6. Backend endpoints (all prefixed with `/api/v1`)

Fetch the live, authoritative schema with:

```
curl http://127.0.0.1:8126/openapi.json
```

A dev server with seeded demo data is normally running at
`http://127.0.0.1:8126` (check `GET /health` first). Demo login:
`abdurahmon@englify.uz` / `englify1234`.

### Auth
| Method + path | Notes |
|---|---|
| `POST /auth/register` | `{email, password, full_name, phone?}` → tokens+user |
| `POST /auth/login` | `{email, password}` → `{access_token, refresh_token, expires_in, user}` |
| `POST /auth/refresh` | `{refresh_token}` |
| `POST /auth/logout` | `{refresh_token?, all_devices?}` |
| `GET /auth/me` · `PATCH /auth/me` | profile; PATCH accepts `full_name, phone, avatar_url, avatar_emoji, bio, level, daily_goal_minutes` |
| `POST /auth/change-password` · `/auth/forgot-password` · `/auth/reset-password` | |

### Users / stats
| Endpoint | Returns |
|---|---|
| `GET /users/me/stats` | `{points, xp, level, level_title, streak_days, longest_streak, rank, lessons_completed, words_learned, minutes_this_week, skills:[{skill,percent}×5], battles_played, battles_won, battles_lost, coins}` |
| `GET /users/me/activity?days=7` | `[{day, minutes, points, lessons_completed, words_reviewed}]` |
| `GET /users/me/achievements` | `[{slug,title,description,icon,points,threshold,earned,earned_at}]` |
| `GET /users/me/streak` | `{streak_days, longest_streak, active_today, daily_goal_minutes}` |

### Courses & lessons
| Endpoint | Notes |
|---|---|
| `GET /courses` | `[{id,slug,title,level,unit_count,lesson_count,enrolled,progress_percent,…}]` |
| `GET /courses/{slug}` | adds `units:[{…,lessons:[…]}]` |
| `POST /courses/{slug}/enroll` | |
| `GET /lessons/{id}` | `{…, content, homework, question_count, progress}` |
| `GET /lessons/{id}/quiz` | questions **without** `correct_index` |
| `POST /lessons/{id}/progress` | `{video_percent?, homework_percent?, watch_seconds?, status?, score?}` |
| `POST /lessons/{id}/quiz` | `{answers:[int]}` → `{correct_count,total,score,points_earned,total_points,results:[{question_id,given_index,correct_index,is_correct,explanation}]}` |
| `GET /progress` · `GET /progress/continue` | last one → `{lesson_id,title,url,progress}` |

### Vocabulary
| Endpoint | Notes |
|---|---|
| `GET /vocabulary?q=&status=&favorite=&due_only=&limit=&offset=` | `{items,total,limit,offset}` |
| `GET /vocabulary/stats` | `{total,new,learning,mastered,due_today,favorites}` |
| `GET /vocabulary/due?limit=` | review queue |
| `POST /vocabulary` | `{word,translation,example?,part_of_speech?,level_tag?,is_favorite?}` |
| `POST /vocabulary/bulk` | `{items:[…]}` |
| `PATCH /vocabulary/{id}` · `DELETE /vocabulary/{id}` | |
| `POST /vocabulary/{id}/favorite` | toggles |
| `POST /vocabulary/{id}/review` | `{quality:0..5}` → updated item (SM-2) |

### Notifications
`GET /notifications?unread_only=&kind=&limit=&offset=` → `{items,total,…}` where an
item is `{id,kind,title,body,banner,link,cta_label,icon,is_read,created_at}` and
`banner` is an object like `{gradient,badge,headline,subline,emoji,chips:[…]}` or null.
`GET /notifications/unread-count` → `{unread,total}`.
`POST /notifications/{id}/read`, `POST /notifications/read-all`, `DELETE /notifications/{id}`.

### Chat
| Endpoint | Notes |
|---|---|
| `GET /chat/conversations` | `[{id,kind,title,emoji,color,is_system,unread_count,last_message,last_message_at,members:[{id,name,avatar_url,emoji,is_bot}]}]` |
| `POST /chat/conversations` | `{kind:"direct"\|"group", title?, member_ids:[…]}` |
| `GET /chat/conversations/{id}/messages?limit=&before=` | `[{id,sender_id,sender_name,body,kind,created_at,is_mine}]` |
| `POST /chat/conversations/{id}/messages` | `{body, kind?, attachment_url?}` |
| `POST /chat/conversations/{id}/read` | |
| `GET /chat/unread-count` | |
| `WS /ws/chat/{id}` | frames: send `{type:"typing",data}`/`{type:"ping"}`; receive `{type:"connected"\|"message.created"\|"typing"\|"conversation.read"}` |

### Leaderboard / battles / events / library
| Endpoint | Notes |
|---|---|
| `GET /leaderboard?period=all\|week&level=&limit=` | `{scope,period,level,entries:[{rank,user_id,name,avatar_url,avatar_emoji,points,level,level_title,is_me,streak_days}],me}` |
| `GET /battles/stats` | `{played,won,lost,drawn,total_points}` |
| `GET /battles/history` | `[BattleOut]` |
| `POST /battles` | `{mode:"ai"\|"duel"\|"group", topic:"grammar"\|"vocabulary"\|"mixed", level?}` → BattleOut (duel/group may return `status:"waiting"`) |
| `GET /battles/{id}` · `POST /battles/{id}/join` | |
| `POST /battles/{id}/answer` | `{round_index, correct, answer_index}` |
| `POST /battles/{id}/finish` · `/{id}/cancel` · `GET /{id}/result` | |
| `WS /ws/battles/{id}` | `{type:"battle.started"\|"battle.score"\|"battle.finished"}` |
| `GET /events?when=upcoming\|past\|all&level=` | `[{id,slug,title,host_name,starts_at,duration_minutes,level,meeting_id,join_url,recording_url,is_past,is_registered,registered_count,…}]` (`join_url` is **null** until registered) |
| `GET /events/week` | `{week_start,today,counts:{date:count},registered_today}` |
| `GET /events/registrations` · `POST /events/{slug}/register` · `DELETE /events/{slug}/register` | |
| `GET /books` · `GET /books/{slug}` | `[{slug,title,author,level,description,pages,category,tags,file_url}]` |
| `GET /podcasts` · `GET /podcasts/{slug}` | `[{slug,title,host,level,episode_number,duration_sec,audio_url,transcript,tags}]` |
| `GET /games` · `GET /games/{slug}` | `[{slug,title,kind,description,emoji,color,play_url,config}]` |
| `POST /games/{slug}/score` | `{score,correct_count,total}` → `{game_id,score,points_earned,best_score}` |
| `GET /games/{slug}/leaderboard` | `[{rank,user_id,name,avatar_url,score,is_me}]` |
| `GET /levels` | `[{slug,title,order,points_required,unlocked,progress_percent,lessons,description}]` |
| `GET /library/summary` | `{books,podcasts,games,upcoming_events,lessons_completed,points,level,level_title}` |
| `POST /leads` | **public** `{name,phone,email?,source?,message?}` → 201 |

---

## 7. Rules for editing the existing HTML

1. **Preserve the visual design exactly.** These pages are hand-built with inline
   styles and were matched to a designer's screenshots. Do not restyle, do not
   move sections, do not "clean up" inline CSS.
2. **Only** add: `data-auth` on `<body>`, `data-*` hooks on existing elements,
   `id` attributes where you need a container, `<script>` tags, and — where a
   list is currently hardcoded — a container element you fill from JS (you may
   replace the hardcoded rows with a template, but the resulting DOM must look
   the same).
3. Replace existing placeholder text (`[%]`, `Talaba`, `0 ball`, `Hali so'zlar
   yo'q`, fake names/scores) with **live** values, and keep a sane fallback so
   the page still looks right before the fetch resolves.
4. Keep every existing link, anchor and navigation intact.
5. Do not remove "dead" buttons (Marketplace, Tarjimon, FAQ, …) — wire the ones
   that have a real endpoint, leave the rest visually unchanged.
6. **Remove `localStorage` persistence where a real endpoint exists**
   (`dars.html`: `unit1_*`, `lugat.html`: `lugat_words`) and use the API instead.
   Do not delete the keys from other pages' code unless you replace the feature.
7. User-supplied text going into `innerHTML` **must** pass through `UI.escape`.
8. Every page must still render sensibly when the API is unreachable: catch the
   error, show `UI.toast(error.message, 'error')` or an error box, and leave a
   usable (empty) state.

## 8. Verification you must run before reporting back

1. `node --check assets/js/pages/<pagename>.js` → no syntax errors.
2. Confirm every `id`/selector your script queries actually exists in the page
   (`Select-String -Path <page>.html -Pattern '<id>'`), and that the script tag
   order is correct.
3. If the dev server is up (`Invoke-RestMethod http://127.0.0.1:8126/health`),
   exercise the exact endpoints your page calls with the demo account's token and
   confirm the response fields you rely on exist. Report any mismatch instead of
   guessing.
4. Report: files changed, endpoints used, and anything you could not verify.
