# TEST READY: UI Design Revision End-to-End Suite

## Overview
Comprehensive, opaque-box, requirement-driven test suite for the UI revision milestone covering Lucide CDN migration, emoji purge, persistent desktop sidebar (>=640px), mobile bottom navigation fallback (<640px), `StudentProgram` model and toggle bookmarking, dashboard countdown & 7-day consistency strip, task 3-state filtering with inline AI feedback, mentor quick question chips and context strip, and program multi-criteria filtering.

## Test Runner Command
```bash
python manage.py test tests.test_ui_revision
```

To run specific test tiers:
```bash
python manage.py test tests.test_ui_revision.Tier1FeatureTests
python manage.py test tests.test_ui_revision.Tier2BoundaryTests
python manage.py test tests.test_ui_revision.Tier3CombinationTests
python manage.py test tests.test_ui_revision.Tier4WorkflowTests
python manage.py test tests.test_ui_revision.RegressionTests
```

---

## Test Inventory & Tier Breakdown

### 1. Tier 1: Feature Coverage (`Tier1FeatureTests` — 17 tests)
- `test_t1_01_lucide_cdn_script_present_in_base_html`: Lucide CDN script tag and `lucide.createIcons()` presence in `base.html`.
- `test_t1_02_zero_emojis_in_all_templates_static_analysis`: Static analysis scan across all HTML templates ensuring 0 emoji characters remain.
- `test_t1_03_lucide_icons_rendered_in_templates`: Verifies required Lucide icon attributes (`data-lucide`) are present in user templates.
- `test_t1_04_desktop_sidebar_structure_and_links`: Desktop sidebar (>=640px) structure with logo "Kelajak" and 4 primary links in order (Bosh sahifa, Vazifalar, AI Mentor, Dasturlar).
- `test_t1_05_mobile_bottom_nav_presence`: Mobile bottom navigation fallback (<640px) remains intact.
- `test_t1_06_active_nav_item_visual_indicator`: Active page visual indicator (filled pill / accent state).
- `test_t1_07_sidebar_ready_score_and_streak_widget`: Sidebar persistent Ready Score & streak widget across authenticated pages.
- `test_t1_08_non_overlapping_main_content_layout`: Main content desktop offset (`sm:pl-60` / `sm:ml-60`) to avoid sidebar overlap.
- `test_t1_09_student_program_model_structure_and_persistence`: `StudentProgram` through-model creation and database persistence.
- `test_t1_10_program_tracking_toggle_endpoint`: Program bookmark toggle endpoint (`/programs/<id>/track/`) and JSON responses.
- `test_t1_11_dashboard_deadline_countdown_card`: Dashboard countdown card showing days remaining and program name.
- `test_t1_12_dashboard_weekly_consistency_strip_structure`: Dashboard 7-day Monday–Sunday consistency strip structure.
- `test_t1_13_tasks_three_state_filter_tabs`: Tasks 3-state filter strip (`?filter=today|week|completed`).
- `test_t1_14_tasks_inline_ai_feedback_display`: Completed tasks surface `ai_feedback` text inline under task card.
- `test_t1_15_mentor_quick_question_icon_chips`: AI Mentor quick questions rendered as icon-labeled chips.
- `test_t1_16_mentor_persistent_context_strip`: AI Mentor persistent context strip (grade • program • weakest skill).
- `test_t1_17_programs_page_multi_criteria_filter_bar`: Programs catalog multi-criteria filter controls (country, month, type).

### 2. Tier 2: Boundary & Corner Cases (`Tier2BoundaryTests` — 9 tests)
- `test_t2_01_dashboard_countdown_no_tracked_programs_fallback`: No tracked programs defaults to nearest deadline among all programs.
- `test_t2_02_dashboard_countdown_zero_programs_in_database`: 0 programs in database handled gracefully without 500 error.
- `test_t2_03_dashboard_consistency_strip_zero_tasks_completed`: 0 completed tasks yields 7 uncompleted day boxes.
- `test_t2_04_dashboard_consistency_strip_all_7_days_completed`: All 7 days completed yields 7 filled day boxes.
- `test_t2_05_dashboard_zero_streak_display`: 0 streak displays "0 kun" without crashing.
- `test_t2_06_ready_score_boundary_zero_and_hundred`: Ready Score boundary values 0% and 100% render cleanly.
- `test_t2_07_unauthenticated_access_redirects`: Unauthenticated requests to protected endpoints redirect to login.
- `test_t2_08_tasks_invalid_filter_param_defaults_to_today`: Invalid `?filter=xyz` query param falls back to `today`.
- `test_t2_09_uncompleted_onboarding_redirects_to_step_1`: Incomplete onboarding redirects to step 1.

### 3. Tier 3: Cross-Feature Combinations (`Tier3CombinationTests` — 5 tests)
- `test_t3_01_toggle_tracking_immediately_switches_dashboard_deadline`: Toggling tracking immediately prioritizes tracked program on dashboard.
- `test_t3_02_task_completion_updates_weekly_consistency_strip`: Completing a task immediately sets today's strip box to filled.
- `test_t3_03_tracking_program_updates_mentor_context_strip`: Tracking a program updates AI Mentor context strip.
- `test_t3_04_completed_task_filtering_and_feedback_display`: Submitting a task moves it to completed filter and displays inline feedback.
- `test_t3_05_multiple_tracked_programs_selects_nearest_among_tracked`: Multiple tracked programs picks the nearest deadline among tracked.

### 4. Tier 4: Real-World Workflows (`Tier4WorkflowTests` — 1 test)
- `test_t4_01_complete_student_workflow`: Complete end-to-end lifecycle traversing Onboarding -> Dashboard -> Tasks -> AI Feedback -> Programs Tracking -> Dashboard Countdown & Consistency Strip -> AI Mentor Context.

### 5. Regressions (`RegressionTests` — 3 tests)
- `test_reg_01_django_system_check`: Django `manage.py check` reports 0 issues.
- `test_reg_02_all_core_routes_return_http_200`: Authenticated student can access all core views without 500 error.
- `test_reg_03_uzbek_disclaimer_text_present`: Mandatory Uzbek disclaimer ("AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi") present on pages.

**Total Test Count: 35 tests**

---

## Discovered Implementation Defects (Escalation to Implementing Agent)
1. **Template Syntax Error in Sidebar & Mobile Header**:
   - Files: `templates/includes/sidebar.html` (line 55, line 64) and `templates/includes/nav_top.html` (line 19, line 25).
   - Issue: The template expressions use invalid chained filter arguments:
     `{{ request.user.student_profile.overall_ready_score|default:request.user.student_profile.progress_logs.first.overall_ready_score|default:0 }}`
   - Cause: Django template filter `|default:` cannot accept chained dotted variable paths as argument without quotes or context resolution.
   - Recommended Fix: Simplify to `{{ request.user.student_profile.progress_logs.first.overall_ready_score|default:0 }}` and `{{ request.user.student_profile.progress_logs.first.streak_count|default:0 }}` (or provide property getters on `Student` model / context processor).
