# Project: UI Design Revision (Django + Tailwind CSS)

## Architecture
This project refactors and upgrades the UI design of the study abroad platform (`study_abroad_mvp`), replacing all emoji UI icons with Lucide SVG icons loaded via CDN, introducing a persistent desktop left sidebar (>=640px) with mobile bottom navigation fallback (<640px), and adding rich per-page widgets and features including program tracking (`StudentProgram`), dashboard deadline countdowns, weekly consistency strips, task filtering with inline AI feedback, AI mentor chips and context strip, and client-side program filtering.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Lucide CDN Integration | Load Lucide via CDN (`https://unpkg.com/lucide@latest`) and render SVG icons with `currentColor` | M2 | ORIGINAL_REQUEST §R1 |
| 2 | Emoji Purge & Icon Mapping | Replace 100% of emojis in user-facing templates with Lucide icons (zero emoji characters remaining) | M2, M3 | ORIGINAL_REQUEST §R1 |
| 3 | Desktop Left Sidebar (>=640px) | Fixed ~240px wide left sidebar with "Kelajak" logo, vertical nav, active filled pill, Ready Score & streak widget | M2 | ORIGINAL_REQUEST §R2 |
| 4 | Mobile Bottom Navigation (<640px) | Persistent bottom tab bar fallback on small screens with Lucide icons and 4 main nav items | M2 | ORIGINAL_REQUEST §R2 |
| 5 | Non-overlapping Main Content | Desktop main content area shifted (`sm:pl-60`) to prevent sidebar overlap | M2 | ORIGINAL_REQUEST §R2 |
| 6 | StudentProgram Tracking Model | Backend through/M2M model `StudentProgram` with `student`, `program`, `tracked_at` and migrations | M1 | ORIGINAL_REQUEST §R3 |
| 7 | Program Tracking Endpoint / Action | Toggle tracking API endpoint `/programs/<id>/track/` and bookmark button UI | M1, M3 | ORIGINAL_REQUEST §R3 |
| 8 | Dashboard Deadline Countdown | Large countdown displaying days remaining to nearest deadline (tracked program priority, all programs fallback) | M1, M3 | ORIGINAL_REQUEST §R3 |
| 9 | Dashboard 7-Day Consistency Strip | Mon–Sun 7-box weekly consistency strip showing filled/empty task completion states | M1, M3 | ORIGINAL_REQUEST §R3 |
| 10 | Tasks 3-State Filter Tabs | Filter strip with Bugungi (today), Bu hafta (this week), Tugallangan (completed) states | M1, M3 | ORIGINAL_REQUEST §R3 |
| 11 | Tasks Inline AI Feedback | Surface `ai_feedback` text inline under completed tasks in the UI | M1, M3 | ORIGINAL_REQUEST §R3 |
| 12 | Mentor Quick-Question Chips | Replace plain-text quick-questions with icon-labeled pill chips | M3 | ORIGINAL_REQUEST §R3 |
| 13 | Mentor Persistent Context Strip | Context strip above chat input: student grade • tracked program • weakest skill | M1, M3 | ORIGINAL_REQUEST §R3 |
| 14 | Programs Multi-Criteria Filter Bar | Filter bar by country dropdown, deadline month dropdown, and program type toggle/radio | M3 | ORIGINAL_REQUEST §R3 |
| 15 | E2E Testing Suite (Tiers 1–4) | Requirement-driven test suite validating R1, R2, R3, models, and zero regressions | E2E Track | ORIGINAL_REQUEST §AC |
| 16 | Adversarial Hardening & Forensic Audit | White-box stress tests, edge cases, and integrity audit | M5 | ORIGINAL_REQUEST §AC |

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Test Suite Creation | Design and build comprehensive opaque-box test suite across Tiers 1-4 for all UI revision requirements | none | DONE |
| M1 | Backend Data Models, Migrations & View Contexts | `StudentProgram` model, migrations, toggle tracking view/route, dashboard deadline & 7-day strip calculation, tasks tab filtering & feedback passing, mentor context strip data | none | DONE |
| M2 | Global Navigation, Sidebar Layout & Lucide CDN Integration | `base.html` Lucide CDN & `lucide.createIcons()`, desktop persistent sidebar (>=640px) with logo, active pill, ready score/streak widget, mobile bottom bar (<640px), content padding, global emoji replacement | none | DONE |
| M3 | Page-Specific UI Additions & Per-Page Emoji Purge | Dashboard countdown card & 7-day strip, Tasks 3-state filter & inline `ai_feedback`, Mentor chips & context strip, Programs filter bar & Kuzatish toggle button, 100% emoji purge across all templates | M1, M2 | DONE |
| M4 | Full E2E Test Suite Verification (Tiers 1–4) | Execute 100% of test suite to verify all acceptance criteria and zero regressions | E2E, M1, M2, M3 | DONE |
| M5 | Adversarial Hardening (Tier 5) & Forensic Integrity Audit | Reviewer verification (APPROVE) and Forensic Auditor integrity verification (CLEAN) | M4 | DONE |

---

## Interface Contracts

### `apps.programs.models.StudentProgram`
- `student`: `ForeignKey('accounts.Student', on_delete=CASCADE, related_name='tracked_programs')`
- `program`: `ForeignKey('programs.Program', on_delete=CASCADE, related_name='student_tracking')`
- `tracked_at`: `DateTimeField(auto_now_add=True)`
- `Meta`: `unique_together = ('student', 'program')`

### Program Tracking URL & View
- URL: `path('<int:program_id>/track/', views.toggle_track_program, name='toggle_track')`
- View: `toggle_track_program(request, program_id)` returns JSON `{'status': 'ok', 'is_tracked': bool, 'tracked_count': int}` or redirects back.

### Dashboard View Context Additions
- `nearest_deadline`: `{'days_left': int, 'program_name': str, 'has_tracked': bool, 'deadline_text': str}`
- `weekly_consistency`: `list[dict]` containing 7 items for Monday through Sunday of the current week: `[{'day_name': 'Du', 'day_number': int, 'is_completed': bool, 'is_today': bool}, ...]`

### Tasks View Context Additions
- Query parameter: `?filter=today|week|completed` (default: `today`)
- Context `active_filter`: `'today' | 'week' | 'completed'`
- `tasks`: list of `DailyTask` matching the filter, with `ai_feedback` populated for completed tasks.

### Mentor View Context Additions
- `context_strip`: `{'grade_display': str, 'program_display': str, 'weakest_skill_display': str, 'full_display': str}` (e.g. "10-sinf • DAAD • Grammatika — zaif")

---

## Code Layout
```
study/
├── apps/
│   ├── accounts/
│   ├── dashboard/
│   │   └── views.py
│   ├── mentor/
│   │   └── views.py
│   ├── onboarding/
│   ├── programs/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── migrations/
│   │       └── 0002_studentprogram.py
│   └── tasks/
│       └── views.py
├── templates/
│   ├── base.html
│   ├── accounts/
│   ├── dashboard/
│   │   └── index.html
│   ├── includes/
│   │   ├── disclaimer.html
│   │   ├── messages.html
│   │   ├── nav_bottom.html
│   │   ├── nav_top.html
│   │   └── sidebar.html
│   ├── mentor/
│   │   └── chat.html
│   ├── onboarding/
│   ├── programs/
│   │   ├── program_detail.html
│   │   └── program_list.html
│   └── tasks/
│       ├── task_detail.html
│       ├── task_list.html
│       └── task_result.html
└── tests/
```
