# E2E Test Infra: UI Design Revision

## Test Philosophy
- Opaque-box, requirement-driven. Direct validation of templates, rendered DOM/HTML elements, context dictionaries, database state persistence, and HTTP responses.
- Methodology: Category-Partition + Boundary Value Analysis + Pairwise Combinations + Real-World Workflows.

## Feature Inventory & Test Matrix
| # | Feature | Requirement | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|-------------|:------:|:------:|:------:|:------:|
| 1 | Lucide CDN Script in base.html | ORIGINAL_REQUEST §R1 | ✓ (2) | ✓ (1) | ✓ (1) | ✓ (1) |
| 2 | Zero Emojis in all Templates | ORIGINAL_REQUEST §R1 | ✓ (5) | ✓ (2) | ✓ (1) | ✓ (1) |
| 3 | Lucide Icons Rendered in Place of Emojis | ORIGINAL_REQUEST §R1 | ✓ (5) | ✓ (2) | ✓ (1) | ✓ (1) |
| 4 | Desktop Left Sidebar (>=640px) with 4 Nav Items & Logo | ORIGINAL_REQUEST §R2 | ✓ (4) | ✓ (2) | ✓ (1) | ✓ (1) |
| 5 | Mobile Bottom Nav (<640px) Fallback | ORIGINAL_REQUEST §R2 | ✓ (3) | ✓ (1) | ✓ (1) | ✓ (1) |
| 6 | Active Nav Item Visual Distinct State | ORIGINAL_REQUEST §R2 | ✓ (4) | ✓ (2) | ✓ (1) | ✓ (1) |
| 7 | Sidebar Ready Score & Streak Widget | ORIGINAL_REQUEST §R2 | ✓ (3) | ✓ (2) | ✓ (1) | ✓ (1) |
| 8 | Non-overlapping Content Layout (`sm:pl-60`) | ORIGINAL_REQUEST §R2 | ✓ (2) | ✓ (1) | ✓ (1) | ✓ (1) |
| 9 | StudentProgram Tracking Model & Migration | ORIGINAL_REQUEST §R3 | ✓ (3) | ✓ (2) | ✓ (2) | ✓ (1) |
| 10 | Program Tracking Toggle Endpoint & State Persistence | ORIGINAL_REQUEST §R3 | ✓ (4) | ✓ (3) | ✓ (2) | ✓ (1) |
| 11 | Dashboard Deadline Countdown (Tracked / Fallback) | ORIGINAL_REQUEST §R3 | ✓ (4) | ✓ (3) | ✓ (2) | ✓ (1) |
| 12 | Dashboard 7-Box Weekly Consistency Strip | ORIGINAL_REQUEST §R3 | ✓ (4) | ✓ (3) | ✓ (2) | ✓ (1) |
| 13 | Tasks 3-State Filter (Bugungi, Bu hafta, Tugallangan) | ORIGINAL_REQUEST §R3 | ✓ (4) | ✓ (3) | ✓ (2) | ✓ (1) |
| 14 | Tasks Inline AI Feedback Display | ORIGINAL_REQUEST §R3 | ✓ (3) | ✓ (2) | ✓ (1) | ✓ (1) |
| 15 | AI Mentor Quick-Question Icon Chips | ORIGINAL_REQUEST §R3 | ✓ (3) | ✓ (1) | ✓ (1) | ✓ (1) |
| 16 | AI Mentor Context Strip (Grade • Program • Weak Skill) | ORIGINAL_REQUEST §R3 | ✓ (4) | ✓ (2) | ✓ (2) | ✓ (1) |
| 17 | Programs Page Multi-Criteria Filter Bar | ORIGINAL_REQUEST §R3 | ✓ (4) | ✓ (2) | ✓ (1) | ✓ (1) |
| 18 | No Regressions: manage.py check & Uzbek Disclaimers | ORIGINAL_REQUEST §AC | ✓ (5) | ✓ (2) | ✓ (1) | ✓ (1) |

## Coverage Targets
- Total test cases across Tiers: > 60 tests.
- 100% pass rate with `python manage.py test`.
