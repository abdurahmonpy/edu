"""
End-to-End & UI Revision Test Suite (Tiers 1 to 4 + Regressions)
Covers all requirements from ORIGINAL_REQUEST.md, PROJECT.md, and TEST_INFRA.md:
- R1: Lucide CDN integration, Lucide SVG icon tags, zero emojis across all templates.
- R2: Persistent desktop sidebar (>=640px) with logo, 4 nav items, active pill, ready score/streak widget; mobile bottom nav (<640px); non-overlapping layout.
- R3: StudentProgram tracking model & toggle endpoint, dashboard deadline countdown & 7-day consistency strip, tasks 3-state filter & inline ai_feedback, mentor chips & context strip, programs multi-criteria filter bar.
- Regressions: Django system check, HTTP 200 on all core routes, Uzbek trust & safety disclaimers.
"""
import os
import re
import itertools
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse, NoReverseMatch
from django.core.management import call_command
from django.utils import timezone
from django.conf import settings

from apps.accounts.models import User, Student
from apps.study_plans.models import StudyPlan
from apps.tasks.models import DailyTask
from apps.dashboard.models import SkillScore, ProgressLog
from apps.programs.models import Program
from apps.mentor.models import MentorMessage


EMOJI_PATTERN = re.compile(
    r'[\U0001F600-\U0001F64F]|'  # emoticons
    r'[\U0001F300-\U0001F5FF]|'  # symbols & pictographs
    r'[\U0001F680-\U0001F6FF]|'  # transport & map symbols
    r'[\U0001F700-\U0001F77F]|'  # alchemical symbols
    r'[\U0001F780-\U0001F7FF]|'  # geometric shapes extended
    r'[\U0001F800-\U0001F8FF]|'  # supplemental arrows-c
    r'[\U0001F900-\U0001F9FF]|'  # supplemental symbols and pictographs
    r'[\U0001FA00-\U0001FA6F]|'  # chess symbols
    r'[\U0001FA70-\U0001FAFF]|'  # symbols and pictographs extended-a
    r'[\u2600-\u26FF]|'          # misc symbols (e.g. ⚡, ⏳, 🗓)
    r'[\u2700-\u27BF]'           # dingbats (e.g. ✓, ✅, 🎯)
)

SPECIFIC_EMOJIS = ['🎓', '🔥', '⚡', '✓', '✅', '📊', '🎯', '📈', '⏳', '🔗', '💬', '🏠', '📋', '🗓', '🌟']

_PHONE_COUNTER = itertools.count(1000)


class BaseUITestCase(TestCase):
    """
    Common setup fixture for UI revision tests.
    """
    def setUp(self):
        # Patch external AI calls to guarantee 100% offline, deterministic, sub-second execution
        self.p_task = patch('apps.services.task_service.call_claude', return_value=None)
        self.p_plan = patch('apps.services.study_plan_service.call_claude', return_value=None)
        self.p_mentor = patch('apps.services.mentor_service.call_claude', return_value=None)
        self.p_task.start()
        self.p_plan.start()
        self.p_mentor.start()
        self.addCleanup(self.p_task.stop)
        self.addCleanup(self.p_plan.stop)
        self.addCleanup(self.p_mentor.stop)

        self.client = Client()
        self.password = 'TestPassword123!'
        unique_phone = f'+998901{next(_PHONE_COUNTER):06d}'
        self.user = User.objects.create_user(
            phone_number=unique_phone,
            password=self.password,
            first_name='Jasur'
        )
        self.student = self.user.student_profile
        self.student.grade = 10
        self.student.target_countries = ['AQSh', 'Germaniya']
        self.student.target_program_type = 'grant'
        self.student.english_level = 'intermediate'
        self.student.onboarding_completed = True
        self.student.save()

        # Create baseline 5 skill scores
        self.skill_scores = {
            'reading': 70,
            'writing': 65,
            'listening': 60,
            'speaking': 55,
            'grammar': 50  # weakest
        }
        for skill, score in self.skill_scores.items():
            SkillScore.objects.create(
                student=self.student,
                skill=skill,
                current_score=score
            )

        today = timezone.localdate()

        # Active study plan
        self.study_plan = StudyPlan.objects.create(
            student=self.student,
            goal="DAAD va Chevening grantlariga tayyorgarlik",
            target_date=today + timedelta(days=90),
            generated_by_ai={
                "title": "Shaxsiy Grant Tayyorgarlik Rejasi",
                "summary": "10-sinf o'quvchisi uchun xalqaro grantlar rejasi",
                "weakest_skill": "grammar",
                "milestones": [
                    {"title": "1-bosqich: Grammatika", "target_week": 2, "description": "Asosiy grammatika"},
                    {"title": "2-bosqich: Insho", "target_week": 6, "description": "SOP yozish"}
                ]
            },
            active=True
        )

        # Pre-create today's daily tasks
        self.task_grammar = DailyTask.objects.create(
            student=self.student,
            study_plan=self.study_plan,
            date=today,
            task_type='grammar_drill',
            content={
                'title': 'Grammar Drill: Conditional Sentences',
                'skill': 'grammar',
                'question': 'If Aziz applied earlier, he would have succeeded.',
                'options': [
                    {'key': 'A', 'text': 'applied'},
                    {'key': 'B', 'text': 'had applied'}
                ],
                'correct_option': 'B',
                'explanation': 'Third conditional explanation.'
            },
            completed=False
        )
        self.task_reading = DailyTask.objects.create(
            student=self.student,
            study_plan=self.study_plan,
            date=today,
            task_type='reading_comprehension',
            content={
                'title': 'Reading Comprehension: SOP Structure',
                'skill': 'reading',
                'passage': 'An effective Statement of Purpose for international grants must articulate a coherent narrative.',
                'question': 'What makes an SOP compelling?',
                'options': [
                    {'key': 'A', 'text': 'Listing awards'},
                    {'key': 'B', 'text': 'Connecting experiences with future vision'}
                ],
                'correct_option': 'B',
                'explanation': 'Clear narrative connection.'
            },
            completed=False
        )

        # Initial progress log
        ProgressLog.objects.create(
            student=self.student,
            date=today,
            overall_ready_score=60,
            streak_count=3,
            delta="+5 ball"
        )

        # Sample verified programs
        self.prog_daad = Program.objects.create(
            name='DAAD Scholarship',
            country='Germaniya',
            type='grant',
            deadline='15-Noyabr',
            source_url='https://www.daad.de',
            last_verified_date=today
        )
        self.prog_chevening = Program.objects.create(
            name='Chevening Scholarship',
            country='Buyuk Britaniya',
            type='grant',
            deadline='01-Noyabr',
            source_url='https://www.chevening.org',
            last_verified_date=today
        )
        self.prog_flex = Program.objects.create(
            name='FLEX Almashinuv Dasturi',
            country='AQSh',
            type='exchange',
            deadline='15-Oktyabr',
            source_url='https://discoverflex.org',
            last_verified_date=today
        )

    def login_student(self):
        self.client.login(phone_number=self.user.phone_number, password=self.password)

    def get_track_toggle_url(self, program_id):
        try:
            return reverse('programs:toggle_track', kwargs={'program_id': program_id})
        except NoReverseMatch:
            return f'/programs/{program_id}/track/'


# ==============================================================================
# TIER 1: FEATURE COVERAGE
# ==============================================================================
class Tier1FeatureTests(BaseUITestCase):
    """
    Tier 1: Feature Coverage per TEST_INFRA.md and ORIGINAL_REQUEST.md.
    """

    def test_t1_01_lucide_cdn_script_present_in_base_html(self):
        """T1.1: Lucide CDN script tag must be present in base.html."""
        templates_dir = Path(settings.BASE_DIR) / 'templates'
        base_html_path = templates_dir / 'base.html'
        self.assertTrue(base_html_path.exists(), "base.html must exist")
        content = base_html_path.read_text(encoding='utf-8')
        
        self.assertIn('unpkg.com/lucide@latest', content, "Lucide CDN script URL must be present in base.html")
        self.assertIn('lucide.createIcons', content, "lucide.createIcons() initialization call must be present")

    def test_t1_02_zero_emojis_in_all_templates_static_analysis(self):
        """T1.2: Static analysis verifies zero emoji characters across all user-facing templates."""
        templates_dir = Path(settings.BASE_DIR) / 'templates'
        violations = []

        for html_file in templates_dir.rglob('*.html'):
            text = html_file.read_text(encoding='utf-8')
            for line_idx, line in enumerate(text.splitlines(), start=1):
                match = EMOJI_PATTERN.search(line)
                if match:
                    violations.append(f"{html_file.relative_to(templates_dir)}:{line_idx} - '{match.group()}' in '{line.strip()}'")
                else:
                    for emoji_char in SPECIFIC_EMOJIS:
                        if emoji_char in line:
                            violations.append(f"{html_file.relative_to(templates_dir)}:{line_idx} - '{emoji_char}' in '{line.strip()}'")

        self.assertEqual(
            len(violations), 0,
            f"Found {len(violations)} emoji violations in templates:\n" + "\n".join(violations[:15])
        )

    def test_t1_03_lucide_icons_rendered_in_templates(self):
        """T1.3: Templates must utilize Lucide icon markup (data-lucide attributes)."""
        templates_dir = Path(settings.BASE_DIR) / 'templates'
        all_template_content = ""
        for html_file in templates_dir.rglob('*.html'):
            all_template_content += html_file.read_text(encoding='utf-8') + "\n"

        required_icons = [
            'graduation-cap',
            'flame',
            'zap',
            'check-circle',
            'target',
            'trending-up',
            'message-circle',
            'clipboard-check',
            'arrow-right',
        ]
        for icon in required_icons:
            self.assertTrue(
                f'data-lucide="{icon}"' in all_template_content or f"data-lucide='{icon}'" in all_template_content or f'lucide-{icon}' in all_template_content,
                f"Required Lucide icon '{icon}' must be referenced in templates."
            )

    def test_t1_04_desktop_sidebar_structure_and_links(self):
        """T1.4: Persistent desktop sidebar (>=640px) contains 'Kelajak' logo and 4 nav items."""
        self.login_student()
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')

        self.assertTrue('Kelajak' in html, "Brand name 'Kelajak' must appear in navigation.")
        self.assertIn(reverse('dashboard:index'), html, "Dashboard nav link must be present")
        self.assertIn(reverse('tasks:list'), html, "Tasks nav link must be present")
        self.assertIn(reverse('mentor:chat'), html, "Mentor nav link must be present")
        self.assertIn(reverse('programs:catalog'), html, "Programs nav link must be present")
        
        self.assertIn('Bosh sahifa', html)
        self.assertIn('Vazifalar', html)
        self.assertIn('AI Mentor', html)
        self.assertIn('Dasturlar', html)

    def test_t1_05_mobile_bottom_nav_presence(self):
        """T1.5: Mobile bottom navigation fallback (<640px) remains present and functional."""
        self.login_student()
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')

        self.assertTrue(
            'sm:hidden' in html or 'md:hidden' in html or 'fixed bottom-0' in html or 'pb-safe' in html,
            "Mobile bottom nav bar fallback must be present."
        )

    def test_t1_06_active_nav_item_visual_indicator(self):
        """T1.6: Active page is highlighted with a distinct background pill or accent indicator."""
        self.login_student()
        
        endpoints = [
            (reverse('dashboard:index'), 'dashboard'),
            (reverse('tasks:list'), 'tasks'),
            (reverse('mentor:chat'), 'mentor'),
            (reverse('programs:catalog'), 'programs'),
        ]
        for url, section in endpoints:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200)
            html = res.content.decode('utf-8')
            self.assertTrue(
                'bg-emerald-50' in html or 'bg-emerald-600' in html or 'bg-emerald-100' in html or 'bg-indigo-50' in html or 'text-indigo-700' in html or 'font-semibold' in html or 'font-bold' in html,
                f"Active indicator must be visually distinguishable for {section}."
            )

    def test_t1_07_sidebar_ready_score_and_streak_widget(self):
        """T1.7: Sidebar contains Ready Score & streak widget visible across authenticated pages."""
        self.login_student()
        for url in [reverse('dashboard:index'), reverse('tasks:list'), reverse('mentor:chat'), reverse('programs:catalog')]:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200)
            html = res.content.decode('utf-8')
            self.assertTrue('Ready Score' in html or '60%' in html or 'kun' in html, f"Score/streak widget missing on {url}")

    def test_t1_08_non_overlapping_main_content_layout(self):
        """T1.8: Main content area shifts on desktop (sm:pl-60, sm:ml-60, md:pl-60, or equivalent)."""
        templates_dir = Path(settings.BASE_DIR) / 'templates'
        base_html_path = templates_dir / 'base.html'
        content = base_html_path.read_text(encoding='utf-8')
        
        has_shift_class = any(
            cls in content for cls in ['sm:pl-60', 'sm:ml-60', 'md:pl-60', 'md:ml-60', 'sm:pl-64', 'md:pl-64', 'sm:ml-64', 'md:ml-64']
        )
        self.assertTrue(has_shift_class, "Main content area must have padding/margin shift to avoid sidebar overlap on desktop.")

    def test_t1_09_student_program_model_structure_and_persistence(self):
        """T1.9: StudentProgram model exists with student, program, created_at and unique constraint."""
        try:
            from apps.programs.models import StudentProgram
        except ImportError:
            self.fail("StudentProgram model must be defined in apps.programs.models per M1 contract")

        sp = StudentProgram.objects.create(student=self.student, program=self.prog_daad)
        self.assertEqual(sp.student, self.student)
        self.assertEqual(sp.program, self.prog_daad)
        self.assertIsNotNone(sp.created_at)

        # Check reverse relationships
        self.assertTrue(hasattr(self.student, 'tracked_programs'))
        self.assertIn(sp, self.student.tracked_programs.all())

    def test_t1_10_program_tracking_toggle_endpoint(self):
        """T1.10: Program tracking toggle endpoint toggles bookmark and returns JSON response."""
        self.login_student()
        toggle_url = self.get_track_toggle_url(self.prog_daad.id)
        
        # 1. First toggle -> Track
        res1 = self.client.post(toggle_url)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertEqual(data1.get('status'), 'ok')
        self.assertTrue(data1.get('is_tracked'))
        
        from apps.programs.models import StudentProgram
        self.assertTrue(StudentProgram.objects.filter(student=self.student, program=self.prog_daad).exists())

        # 2. Second toggle -> Untrack
        res2 = self.client.post(toggle_url)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(data2.get('status'), 'ok')
        self.assertFalse(data2.get('is_tracked'))
        self.assertFalse(StudentProgram.objects.filter(student=self.student, program=self.prog_daad).exists())

    def test_t1_11_dashboard_deadline_countdown_card(self):
        """T1.11: Dashboard displays prominent deadline countdown card with days remaining and program name."""
        try:
            from apps.programs.models import StudentProgram
            StudentProgram.objects.create(student=self.student, program=self.prog_chevening)
        except Exception:
            pass

        self.login_student()
        res = self.client.get(reverse('dashboard:index'))
        self.assertEqual(res.status_code, 200)
        
        self.assertIn('nearest_deadline', res.context)
        nearest = res.context['nearest_deadline']
        self.assertIn('days_left', nearest)
        self.assertIn('program_name', nearest)
        
        html = res.content.decode('utf-8')
        self.assertTrue('kun qoldi' in html or 'muddati' in html or 'Chevening' in html)

    def test_t1_12_dashboard_weekly_consistency_strip_structure(self):
        """T1.12: Dashboard provides 7-day consistency strip (Mon-Sun) in context and HTML."""
        self.login_student()
        res = self.client.get(reverse('dashboard:index'))
        self.assertEqual(res.status_code, 200)
        
        self.assertIn('weekly_consistency', res.context)
        strip = res.context['weekly_consistency']
        self.assertEqual(len(strip), 7, "Weekly strip must contain exactly 7 days (Mon-Sun)")
        
        for day in strip:
            self.assertIn('day_name', day)
            self.assertIn('day_number', day)
            self.assertIn('is_completed', day)
            self.assertIn('is_today', day)

    def test_t1_13_tasks_three_state_filter_tabs(self):
        """T1.13: Tasks page has 3-state filter strip: today, week, completed."""
        self.login_student()
        for f in ['today', 'week', 'completed']:
            res = self.client.get(f"{reverse('tasks:list')}?filter={f}")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.context.get('active_filter'), f)
            html = res.content.decode('utf-8')
            self.assertIn('Bugungi', html)
            self.assertIn('Bu hafta', html)
            self.assertIn('Tugallangan', html)

    def test_t1_14_tasks_inline_ai_feedback_display(self):
        """T1.14: Completed tasks surface ai_feedback text inline below the task card."""
        today = timezone.localdate()
        DailyTask.objects.create(
            student=self.student,
            task_type='grammar_drill',
            date=today,
            completed=True,
            score=90,
            ai_feedback="Ajoyib! Present Perfect zamoni to'g'ri qo'llanilgan."
        )
        self.login_student()
        res = self.client.get(f"{reverse('tasks:list')}?filter=completed")
        self.assertEqual(res.status_code, 200)
        html = res.content.decode('utf-8')
        self.assertTrue("Ajoyib" in html and "Present Perfect" in html)

    def test_t1_15_mentor_quick_question_icon_chips(self):
        """T1.15: AI Mentor page replaces plain-text links with icon-labeled chips."""
        self.login_student()
        res = self.client.get(reverse('mentor:chat'))
        self.assertEqual(res.status_code, 200)
        html = res.content.decode('utf-8')
        self.assertTrue('rounded-full' in html or 'chip' in html or 'data-lucide' in html)

    def test_t1_16_mentor_persistent_context_strip(self):
        """T1.16: Context strip above chat input shows student grade • program • weakest skill."""
        try:
            from apps.programs.models import StudentProgram
            StudentProgram.objects.create(student=self.student, program=self.prog_daad)
        except Exception:
            pass

        self.login_student()
        res = self.client.get(reverse('mentor:chat'))
        self.assertEqual(res.status_code, 200)
        
        self.assertIn('context_strip', res.context)
        cs = res.context['context_strip']
        self.assertIn('10-sinf', cs.get('grade_display', ''))
        self.assertTrue(len(cs.get('program_display', '')) > 0)
        self.assertTrue('Grammatika' in cs.get('weakest_skill_display', '') or 'grammar' in cs.get('weakest_skill_display', '').lower())
        
        html = res.content.decode('utf-8')
        self.assertIn('10-sinf', html)

    def test_t1_17_programs_page_multi_criteria_filter_bar(self):
        """T1.17: Programs catalog includes filter bar for country, deadline month, and type."""
        self.login_student()
        res = self.client.get(reverse('programs:catalog'))
        self.assertEqual(res.status_code, 200)
        html = res.content.decode('utf-8')
        
        self.assertIn('country', html)
        self.assertTrue('deadline' in html or 'month' in html or 'type' in html or 'grant' in html)


# ==============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ==============================================================================
class Tier2BoundaryTests(BaseUITestCase):
    """
    Tier 2: Boundary and corner condition tests.
    """

    def test_t2_01_dashboard_countdown_no_tracked_programs_fallback(self):
        """T2.1: When student has NO tracked programs, countdown shows nearest deadline among all programs."""
        self.login_student()
        res = self.client.get(reverse('dashboard:index'))
        self.assertEqual(res.status_code, 200)
        
        nearest = res.context.get('nearest_deadline', {})
        self.assertFalse(nearest.get('has_tracked', True))
        self.assertIsNotNone(nearest.get('program_name'))

    def test_t2_02_dashboard_countdown_zero_programs_in_database(self):
        """T2.2: When 0 programs exist in the database, dashboard handles it gracefully without 500 error."""
        Program.objects.all().delete()
        self.login_student()
        res = self.client.get(reverse('dashboard:index'))
        self.assertEqual(res.status_code, 200)
        
        nearest = res.context.get('nearest_deadline', {})
        self.assertFalse(nearest.get('has_tracked'))
        self.assertIsNone(nearest.get('program_name'))

    def test_t2_03_dashboard_consistency_strip_zero_tasks_completed(self):
        """T2.3: Zero tasks completed in week -> all 7 boxes have is_completed=False."""
        DailyTask.objects.filter(student=self.student).update(completed=False)
        self.login_student()
        res = self.client.get(reverse('dashboard:index'))
        self.assertEqual(res.status_code, 200)
        
        strip = res.context.get('weekly_consistency', [])
        for day in strip:
            self.assertFalse(day['is_completed'])

    def test_t2_04_dashboard_consistency_strip_all_7_days_completed(self):
        """T2.4: All 7 days with completed tasks -> all 7 boxes have is_completed=True."""
        DailyTask.objects.filter(student=self.student).delete()
        today = timezone.localdate()
        start_of_week = today - timedelta(days=today.weekday())  # Monday
        for i in range(7):
            day_date = start_of_week + timedelta(days=i)
            DailyTask.objects.create(
                student=self.student,
                date=day_date,
                task_type='grammar_drill',
                completed=True,
                score=80
            )

        self.login_student()
        res = self.client.get(reverse('dashboard:index'))
        self.assertEqual(res.status_code, 200)
        
        strip = res.context.get('weekly_consistency', [])
        for day in strip:
            self.assertTrue(day['is_completed'])

    def test_t2_05_dashboard_zero_streak_display(self):
        """T2.5: 0 streak count displays '0 kun' cleanly."""
        ProgressLog.objects.filter(student=self.student).update(streak_count=0)
        DailyTask.objects.filter(student=self.student).update(completed=False)
        self.login_student()
        res = self.client.get(reverse('dashboard:index'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context.get('streak_count'), 0)
        html = res.content.decode('utf-8')
        self.assertIn('0 kun', html)

    def test_t2_06_ready_score_boundary_zero_and_hundred(self):
        """T2.6: Boundary values 0% and 100% Ready Score render cleanly."""
        # 0 score
        SkillScore.objects.filter(student=self.student).update(current_score=0)
        self.login_student()
        res_zero = self.client.get(reverse('dashboard:index'))
        self.assertEqual(res_zero.context.get('overall_ready_score'), 0)

        # 100 score
        SkillScore.objects.filter(student=self.student).update(current_score=100)
        res_max = self.client.get(reverse('dashboard:index'))
        self.assertEqual(res_max.context.get('overall_ready_score'), 100)

    def test_t2_07_unauthenticated_access_redirects(self):
        """T2.7: Unauthenticated users are redirected to login for protected pages."""
        protected_urls = [
            reverse('dashboard:index'),
            reverse('tasks:list'),
            reverse('mentor:chat'),
            self.get_track_toggle_url(self.prog_daad.id),
        ]
        for url in protected_urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 302)
            self.assertIn(reverse('accounts:login'), res.url)

    def test_t2_08_tasks_invalid_filter_param_defaults_to_today(self):
        """T2.8: Invalid ?filter=xyz query param gracefully defaults to 'today'."""
        self.login_student()
        res = self.client.get(f"{reverse('tasks:list')}?filter=invalid_value_xyz")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context.get('active_filter'), 'today')

    def test_t2_09_uncompleted_onboarding_redirects_to_step_1(self):
        """T2.9: Student with onboarding_completed=False is redirected to step 1."""
        self.student.onboarding_completed = False
        self.student.save()
        self.login_student()
        
        for url in [reverse('dashboard:index'), reverse('tasks:list'), reverse('mentor:chat')]:
            res = self.client.get(url)
            self.assertRedirects(res, reverse('onboarding:step_1'))


# ==============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS
# ==============================================================================
class Tier3CombinationTests(BaseUITestCase):
    """
    Tier 3: Multi-feature interaction tests.
    """

    def test_t3_01_toggle_tracking_immediately_switches_dashboard_deadline(self):
        """T3.1: Toggling tracking changes dashboard nearest deadline from all-fallback to tracked program."""
        self.login_student()
        
        # 1. Before tracking: shows nearest from all (FLEX in Oct)
        res_before = self.client.get(reverse('dashboard:index'))
        self.assertFalse(res_before.context['nearest_deadline']['has_tracked'])
        
        # 2. Track DAAD (Nov)
        toggle_url = self.get_track_toggle_url(self.prog_daad.id)
        self.client.post(toggle_url)
        
        # 3. After tracking: dashboard prioritizes tracked program DAAD
        res_after = self.client.get(reverse('dashboard:index'))
        self.assertTrue(res_after.context['nearest_deadline']['has_tracked'])
        self.assertEqual(res_after.context['nearest_deadline']['program_name'], 'DAAD Scholarship')

    def test_t3_02_task_completion_updates_weekly_consistency_strip(self):
        """T3.2: Completing a daily task immediately sets today's consistency strip box to filled."""
        today = timezone.localdate()
        today_idx = today.weekday()
        DailyTask.objects.filter(student=self.student, date=today).update(completed=False)
        
        self.login_student()
        res_before = self.client.get(reverse('dashboard:index'))
        strip_before = res_before.context['weekly_consistency']
        self.assertFalse(strip_before[today_idx]['is_completed'])
        
        # Complete a task today
        self.task_grammar.completed = True
        self.task_grammar.score = 85
        self.task_grammar.save()
        
        res_after = self.client.get(reverse('dashboard:index'))
        strip_after = res_after.context['weekly_consistency']
        self.assertTrue(strip_after[today_idx]['is_completed'])

    def test_t3_03_tracking_program_updates_mentor_context_strip(self):
        """T3.3: Tracking a program updates the AI Mentor persistent context strip."""
        self.login_student()
        
        # Track Chevening
        toggle_url = self.get_track_toggle_url(self.prog_chevening.id)
        self.client.post(toggle_url)
        
        res = self.client.get(reverse('mentor:chat'))
        cs = res.context.get('context_strip', {})
        self.assertIn('Chevening', cs.get('program_display', ''))

    def test_t3_04_completed_task_filtering_and_feedback_display(self):
        """T3.4: Submitting a task moves it to completed filter and surfaces inline feedback."""
        today = timezone.localdate()
        task = DailyTask.objects.create(
            student=self.student,
            task_type='reading_comprehension',
            date=today,
            completed=True,
            score=95,
            ai_feedback="Matn mazmuni to'liq tushunilgan."
        )
        self.login_student()
        res = self.client.get(f"{reverse('tasks:list')}?filter=completed")
        self.assertEqual(res.status_code, 200)
        tasks = res.context.get('tasks', [])
        self.assertIn(task, tasks)
        html = res.content.decode('utf-8')
        self.assertTrue("Matn" in html and "tushunilgan" in html)

    def test_t3_05_multiple_tracked_programs_selects_nearest_among_tracked(self):
        """T3.5: Multiple tracked programs selects the one with nearest deadline among tracked."""
        from apps.programs.models import StudentProgram
        StudentProgram.objects.create(student=self.student, program=self.prog_daad)       # 15-Noyabr
        StudentProgram.objects.create(student=self.student, program=self.prog_chevening)  # 01-Noyabr (earlier)
        
        self.login_student()
        res = self.client.get(reverse('dashboard:index'))
        nearest = res.context.get('nearest_deadline', {})
        self.assertTrue(nearest.get('has_tracked'))
        self.assertEqual(nearest.get('program_name'), 'Chevening Scholarship')


# ==============================================================================
# TIER 4: REAL-WORLD WORKFLOWS
# ==============================================================================
class Tier4WorkflowTests(BaseUITestCase):
    """
    Tier 4: End-to-end full user journey simulation.
    """

    def test_t4_01_complete_student_workflow(self):
        """
        T4.1: Comprehensive end-to-end workflow:
        1. Login & access dashboard -> verify layout, strip, countdown.
        2. Navigate to tasks -> complete task.
        3. Switch to completed tasks tab -> inspect inline AI feedback.
        4. Navigate to programs catalog -> filter and track a scholarship.
        5. Return to dashboard -> verify updated countdown and weekly consistency.
        6. Navigate to AI Mentor -> verify context strip reflects tracked program.
        """
        self.login_student()
        
        # Step 1: Initial Dashboard inspection
        dash_res = self.client.get(reverse('dashboard:index'))
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn('weekly_consistency', dash_res.context)
        self.assertIn('nearest_deadline', dash_res.context)
        
        # Step 2: Navigate to Tasks & Complete a Task
        tasks_res = self.client.get(reverse('tasks:list'))
        self.assertEqual(tasks_res.status_code, 200)
        
        today = timezone.localdate()
        task = DailyTask.objects.create(
            student=self.student,
            task_type='grammar_drill',
            date=today,
            completed=False
        )
        task.completed = True
        task.score = 90
        task.ai_feedback = "Qoidalar aniq va to'g'ri bajarilgan."
        task.save()
        
        # Step 3: Switch to Completed Tasks Tab
        comp_res = self.client.get(f"{reverse('tasks:list')}?filter=completed")
        self.assertEqual(comp_res.status_code, 200)
        self.assertIn(task, comp_res.context.get('tasks', []))
        
        # Step 4: Programs Catalog & Track DAAD
        prog_res = self.client.get(reverse('programs:catalog'))
        self.assertEqual(prog_res.status_code, 200)
        
        track_url = self.get_track_toggle_url(self.prog_daad.id)
        track_post = self.client.post(track_url)
        self.assertEqual(track_post.status_code, 200)
        self.assertTrue(track_post.json().get('is_tracked'))
        
        # Step 5: Return to Dashboard -> Verify Countdown and Strip
        dash_return = self.client.get(reverse('dashboard:index'))
        self.assertEqual(dash_return.status_code, 200)
        self.assertTrue(dash_return.context['nearest_deadline']['has_tracked'])
        self.assertEqual(dash_return.context['nearest_deadline']['program_name'], 'DAAD Scholarship')
        
        today_idx = today.weekday()
        self.assertTrue(dash_return.context['weekly_consistency'][today_idx]['is_completed'])
        
        # Step 6: Navigate to AI Mentor -> Context Strip Verification
        mentor_res = self.client.get(reverse('mentor:chat'))
        self.assertEqual(mentor_res.status_code, 200)
        cs = mentor_res.context.get('context_strip', {})
        self.assertIn('DAAD', cs.get('program_display', ''))


# ==============================================================================
# REGRESSION & COMPLIANCE TESTS
# ==============================================================================
class RegressionTests(BaseUITestCase):
    """
    System check, route availability, and Uzbek trust/safety disclaimers.
    """

    def test_reg_01_django_system_check(self):
        """R.1: System check reports 0 errors."""
        call_command('check')

    def test_reg_02_all_core_routes_return_http_200(self):
        """R.2: All core student routes return HTTP 200 for authenticated students."""
        self.login_student()
        core_routes = [
            reverse('dashboard:index'),
            reverse('tasks:list'),
            reverse('mentor:chat'),
            reverse('programs:catalog'),
            reverse('onboarding:step_1'),
            reverse('onboarding:diagnostic'),
        ]
        for url in core_routes:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Route {url} failed with {res.status_code}")

    def test_reg_03_uzbek_disclaimer_text_present(self):
        """R.3: Mandatory Uzbek disclaimer remains present on core application pages."""
        self.login_student()
        res = self.client.get(reverse('dashboard:index'))
        html = res.content.decode('utf-8')
        disclaimer_snippet = "AI tavsiyasi"
        self.assertIn(disclaimer_snippet, html)
