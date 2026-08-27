# Original User Request

## Initial Request — 2026-08-26T18:49:03+05:00

You are the Project Orchestrator for the UI design revision task on the Django + Tailwind CSS study abroad platform.

Working directory: C:\Users\abdur\OneDrive\Desktop\study
Agent metadata working directory: C:\Users\abdur\OneDrive\Desktop\study\.agents\orchestrator\

The authoritative user request is recorded in `ORIGINAL_REQUEST.md`. Here is the full request:

## Requirements
### R1. Replace all emoji icons with Lucide icons (CDN)
Every emoji used as a UI icon across all templates must be replaced with the equivalent Lucide SVG icon loaded via the Lucide CDN (`https://unpkg.com/lucide@latest`). Icons must be colored via `currentColor` so they inherit the surrounding text color. The required mapping is:
- 🎓 → `graduation-cap`
- 🔥 → `flame`
- ⚡ → `zap`
- ✓ / ✅ → `check-circle`
- 📊 → `bar-chart-3`
- 🎯 → `target`
- 📈 → `trending-up`
- ⏳ → `calendar-clock`
- 🔗 → `external-link`
- 💬 → `message-circle`
- 🏠 → `home`
- 📋 → `clipboard-check`
- 🗓️ → `calendar`
- ➔ / → arrows → `arrow-right`
- Any other emoji used decoratively → remove or replace with appropriate Lucide icon

After this change, zero emoji characters should remain anywhere in any user-facing template.

### R2. Persistent left sidebar navigation (desktop), bottom bar fallback (mobile)
Replace the current bottom tab bar with a persistent left sidebar on screens ≥640px. The bottom tab bar must remain intact and functional below 640px — it is the mobile fallback, not to be removed.

Sidebar specification:
- Fixed left column, approximately 240px wide, full viewport height
- Product logo / name "Kelajak" at the top
- Navigation items stacked vertically with icon + label: Bosh sahifa, Vazifalar, AI Mentor, Dasturlar (in that order, using the Lucide icons from R1)
- Active page indicated by a filled background pill or a left accent bar — must be visually unambiguous at a glance, not just a color tint on the icon
- Near the bottom of the sidebar: a small persistent widget showing the student's current Ready Score and streak count, visible from every authenticated page
- The main content area must shift right to account for the sidebar width on desktop (no overlap)

### R3. Per-page content additions (no new models required except one)
Add the following content to each page using data already available from existing models:

**Dashboard (`dashboard/index.html`)**
- Prominent deadline countdown: days remaining to the nearest `Program.deadline` from the programs the student is tracking (if any tracked program exists; otherwise show the nearest deadline among all programs). Display as a large number + label, e.g. "47 kun qoldi — Chevening".
- Weekly consistency strip: 7 day boxes (Mon–Sun of the current week), each filled (completed tasks that day) or empty. Use `ProgressLog` or `DailyTask` records to determine filled days. Replaces or augments the plain streak number.

**Tasks page (`tasks/` templates)**
- Tab or filter strip with three states: Bugungi (today), Bu hafta (this week), Tugallangan (completed). Default view is Bugungi.
- When a completed task is displayed, show its `ai_feedback` text inline below the task — this field exists on `DailyTask` but is not currently surfaced in the UI.

**AI Mentor page (`mentor/` templates)**
- Replace plain-text quick-question links with icon-labeled chips (small pill buttons with a Lucide icon + short label).
- Add a persistent context strip above the chat input showing: student grade, any tracked program name, and the student's weakest skill. Example: "10-sinf • DAAD • Grammatika — zaif". This uses data already injected into the mentor view context.

**Programs page (`programs/` templates)**
- Search/filter bar: filter by country (dropdown), deadline month (dropdown), and program type (grant / exchange / paid — radio or toggle). Filtering can be client-side JS on the rendered list.
- A "Kuzatish" (track/bookmark) toggle per program card. Tracked programs feed the dashboard countdown in the dashboard requirement above. This requires a `StudentProgram` M2M or a simple through-model on the existing `Student` and `Program` models — this is the one backend addition permitted by this task, since the dashboard countdown depends on it. Run migrations.

## Acceptance Criteria
### Icons
- [ ] `grep -r` for common emoji characters in templates/ returns zero matches
- [ ] Lucide CDN script tag is present in `base.html`
- [ ] Icons render as SVG (`<svg>` elements, not text characters)
### Navigation
- [ ] On a viewport ≥640px, a left sidebar is visible with all 4 nav items and the Ready Score widget
- [ ] On a viewport <640px, the bottom tab bar is visible and the sidebar is hidden
- [ ] The active page nav item has a visually distinct filled/accented state (not just a color change)
- [ ] Main content does not overlap the sidebar at desktop widths
### Per-page additions
- [ ] Dashboard shows a deadline countdown with days remaining and program name
- [ ] Dashboard shows a 7-box weekly strip reflecting actual task completion data
- [ ] Tasks page has a working Bugungi / Bu hafta / Tugallangan filter
- [ ] Completed tasks show their `ai_feedback` text inline
- [ ] Mentor page shows the context strip (grade • program • weakest skill) above the chat
- [ ] Mentor quick questions are rendered as chips with icons, not plain links
- [ ] Programs page has a filter bar (country, deadline month, type) that narrows the displayed list
- [ ] Each program card has a Kuzatish toggle; toggling persists to the database
- [ ] Dashboard countdown pulls from tracked programs when at least one is tracked
### No regressions
- [ ] `python manage.py check` reports 0 errors after any model changes
- [ ] All existing pages (onboarding, diagnostic, results, admin) still load without 500 errors
- [ ] Uzbek disclaimer text remains on all pages that previously showed it
