"""
Comprehensive Unit & Integration Test Suite for Milestone 2:
- Anthropic Claude client with robust JSON extraction and offline mock mode
- Diagnostic Test Engine, Claude Grading & 5-Skill Baseline Scoring
- AI Study Plan Generation Service
- Verified Programs Seed Management Command
- Multi-step Onboarding Intake, Diagnostic Submission, and Results Views
"""
import os
import re
import json
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Student
from apps.onboarding.models import DiagnosticResult
from apps.dashboard.models import SkillScore, ProgressLog
from apps.study_plans.models import StudyPlan
from apps.programs.models import Program
from apps.services.anthropic_client import (
    extract_json_from_response,
    ClaudeClient,
    MockClaudeClient,
    get_claude_client,
    call_claude,
)
from apps.services.diagnostic_service import (
    get_default_diagnostic_test,
    evaluate_diagnostic_heuristic,
    grade_diagnostic_submission,
    save_diagnostic_results_and_scores,
    process_diagnostic_submission,
    SKILL_NAMES,
)
from apps.services.study_plan_service import (
    calculate_default_target_date,
    get_student_skill_scores,
    get_weakest_skill,
    generate_study_plan,
    get_active_study_plan,
    format_study_plan_summary,
)
from django.core.management import call_command

User = get_user_model()


class AnthropicClientTests(TestCase):
    """Tests for apps/services/anthropic_client.py"""

    def test_extract_json_clean_json(self):
        payload = {"status": "ok", "score": 85}
        result = extract_json_from_response(json.dumps(payload))
        self.assertEqual(result, payload)

    def test_extract_json_markdown_fence(self):
        text = "```json\n{\"reading\": 75, \"grammar\": 80}\n```"
        result = extract_json_from_response(text)
        self.assertEqual(result, {"reading": 75, "grammar": 80})

    def test_extract_json_with_surrounding_conversational_text(self):
        text = (
            "Assalomu alaykum! Mana siz so'ragan baholash natijasi:\n\n"
            "```json\n"
            "{\"scores\": {\"reading\": 70, \"writing\": 65}, \"status\": \"done\"}\n"
            "```\n\n"
            "Umid qilamanki bu sizga yordam beradi."
        )
        result = extract_json_from_response(text)
        self.assertEqual(result.get("status"), "done")
        self.assertEqual(result.get("scores", {}).get("reading"), 70)

    def test_extract_json_trailing_commas(self):
        text = '{"items": ["apple", "banana",], "total": 2,}'
        result = extract_json_from_response(text)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["items"], ["apple", "banana"])

    def test_extract_json_invalid_raises_value_error(self):
        with self.assertRaises(ValueError):
            extract_json_from_response("Bu yerda umuman JSON mavjud emas.")

    def test_mock_claude_client_study_plan_intent(self):
        client = MockClaudeClient()
        response = client.call(
            system_prompt="Sen AI o'quv rejasi tuzuvchisan",
            user_prompt="9-sinf o'quvchisi uchun study_plan tuzib ber",
            response_format='json'
        )
        self.assertIsInstance(response, dict)
        self.assertIn('title', response)
        self.assertIn('total_weeks', response)
        self.assertIn('weekly_schedule', response)
        self.assertIn('milestones', response)
        self.assertIn('weakest_skill', response)

    def test_mock_claude_client_diagnostic_intent(self):
        client = MockClaudeClient()
        response = client.call(
            system_prompt="Diagnostic examiner",
            user_prompt="Evaluate diagnostic answers for 5 skills",
            response_format='json'
        )
        self.assertIsInstance(response, dict)
        self.assertIn('scores', response)
        for skill in SKILL_NAMES:
            self.assertIn(skill, response['scores'])
        self.assertIn('overall_ready_score', response)
        self.assertIn('feedback', response)

    def test_mock_claude_client_task_intent(self):
        client = MockClaudeClient()
        response = client.call(
            system_prompt="Task grader",
            user_prompt="grade_task: Student submitted answer for grammar drill",
            response_format='json'
        )
        self.assertIsInstance(response, dict)
        self.assertIn('score', response)
        self.assertIn('ai_feedback', response)

    def test_mock_claude_client_text_response(self):
        client = MockClaudeClient()
        response = client.call(
            system_prompt="Mentor",
            user_prompt="Salom AI mentor",
            response_format='text'
        )
        self.assertIsInstance(response, str)
        self.assertIn("AI tavsiyasi", response)

    def test_get_claude_client_factory(self):
        mock_client = get_claude_client(api_key="mock")
        self.assertTrue(mock_client.is_mock())

        test_client = get_claude_client(api_key="")
        self.assertTrue(test_client.is_mock())

    def test_zero_hardcoded_anthropic_api_keys(self):
        """Verify no hardcoded sk-ant- keys exist in the repository."""
        pattern = re.compile(r'sk-ant-[a-zA-Z0-9_-]{20,}')
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        matches = []
        for root, dirs, files in os.walk(base_dir):
            if any(p in root for p in ['.git', '__pycache__', '.venv', 'venv']):
                continue
            for file in files:
                if file.endswith(('.py', '.html', '.json', '.txt', '.md')):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern.search(line):
                                matches.append(f"{filepath}:{line_num}")
        self.assertEqual(matches, [], f"Hardcoded Anthropic API key found: {matches}")


class DiagnosticServiceTests(TestCase):
    """Tests for apps/services/diagnostic_service.py"""

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+998901112233",
            password="testpassword123",
            first_name="Madina"
        )
        self.student = self.user.student_profile
        self.student.grade = 10
        self.student.target_countries = ["AQSh", "Germaniya"]
        self.student.target_program_type = "grant"
        self.student.english_level = "intermediate"
        self.student.save()

    def test_get_default_diagnostic_test_structure(self):
        test_data = get_default_diagnostic_test()
        self.assertIn('reading', test_data)
        self.assertIn('grammar', test_data)
        self.assertIn('writing', test_data)
        self.assertIn('listening_simulation', test_data)
        self.assertIn('speaking_simulation', test_data)
        self.assertEqual(len(test_data['reading']['questions']), 4)
        self.assertEqual(len(test_data['grammar']['questions']), 6)
        self.assertEqual(len(test_data['listening_simulation']['questions']), 2)

    def test_heuristic_grading_all_correct(self):
        answers = {
            'reading_answers': {'r1': 'B', 'r2': 'C', 'r3': 'B', 'r4': 'B'},
            'grammar_answers': {'g1': 'B', 'g2': 'C', 'g3': 'A', 'g4': 'D', 'g5': 'B', 'g6': 'B'},
            'listening_answers': {'l1': 'A', 'l2': 'B'},
            'writing_essay': (
                "I passionately desire to study Computer Science abroad to acquire cutting-edge skills in "
                "artificial intelligence and modern software architecture. Upon graduating, I will return to "
                "Uzbekistan to build innovative technological platforms and empower the next generation of youth."
            ),
            'speaking_response': (
                "Last year, I initiated an English speaking club at my school for 20 students. "
                "Leading this project taught me how to communicate effectively, inspire peers, and solve conflicts calmly."
            )
        }
        result = evaluate_diagnostic_heuristic(self.student, answers)
        for skill in SKILL_NAMES:
            self.assertIn(skill, result['scores'])
            self.assertGreaterEqual(result['scores'][skill], 60)
            self.assertLessEqual(result['scores'][skill], 100)
        self.assertGreaterEqual(result['overall_ready_score'], 60)
        self.assertIn('feedback', result)
        self.assertIn('summary_uz', result)

    def test_save_diagnostic_results_and_scores_atomicity(self):
        answers = {
            'r1': 'B',
            'g1': 'B',
            'writing_essay': 'My personal statement essay...',
            'speaking_response': 'My speaking audio script response...'
        }
        grading_result = {
            'scores': {
                'reading': 80,
                'grammar': 75,
                'writing': 70,
                'listening': 65,
                'speaking': 60
            },
            'overall_ready_score': 70,
            'weakest_skill': 'speaking',
            'feedback': {s: f"Izoh {s}" for s in SKILL_NAMES},
            'summary_uz': "A'lo boshlang'ich natija."
        }

        saved = save_diagnostic_results_and_scores(self.student, answers, grading_result)

        # 1. 5 DiagnosticResult rows created
        self.assertEqual(DiagnosticResult.objects.filter(student=self.student).count(), 5)
        # 2. 5 SkillScore rows created
        self.assertEqual(SkillScore.objects.filter(student=self.student).count(), 5)
        # 3. ProgressLog created with today's date
        today_log = ProgressLog.objects.filter(student=self.student, date=timezone.localdate()).first()
        self.assertIsNotNone(today_log)
        self.assertEqual(today_log.overall_ready_score, 70)
        self.assertEqual(today_log.streak_count, 1)
        # 4. Student marked completed
        self.student.refresh_from_db()
        self.assertTrue(self.student.onboarding_completed)

    def test_idempotent_diagnostic_retake_updates_skill_scores(self):
        answers = {'r1': 'B', 'g1': 'B'}
        
        # 1st run
        process_diagnostic_submission(self.student, answers)
        self.assertEqual(SkillScore.objects.filter(student=self.student).count(), 5)
        self.assertEqual(DiagnosticResult.objects.filter(student=self.student).count(), 5)

        # 2nd run (retake) — unique_together ('student', 'skill') must not throw IntegrityError
        process_diagnostic_submission(self.student, answers)
        self.assertEqual(SkillScore.objects.filter(student=self.student).count(), 5)
        self.assertEqual(DiagnosticResult.objects.filter(student=self.student).count(), 10)


class StudyPlanServiceTests(TestCase):
    """Tests for apps/services/study_plan_service.py"""

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+998902223344",
            password="testpassword123",
            first_name="Anvar"
        )
        self.student = self.user.student_profile
        self.student.grade = 11
        self.student.target_countries = ["Turkiya", "AQSh"]
        self.student.target_program_type = "grant"
        self.student.english_level = "advanced"
        self.student.save()

    def test_calculate_default_target_date(self):
        self.student.grade = 11
        d11 = calculate_default_target_date(self.student)
        self.assertEqual((d11 - timezone.localdate()).days, 90)

        self.student.grade = 10
        d10 = calculate_default_target_date(self.student)
        self.assertEqual((d10 - timezone.localdate()).days, 180)

        self.student.grade = 9
        d9 = calculate_default_target_date(self.student)
        self.assertEqual((d9 - timezone.localdate()).days, 365)

    def test_get_weakest_skill(self):
        scores = {'reading': 80, 'grammar': 50, 'writing': 65, 'listening': 70, 'speaking': 60}
        self.assertEqual(get_weakest_skill(scores), 'grammar')

    def test_generate_study_plan_creates_active_plan(self):
        plan = generate_study_plan(self.student)
        self.assertTrue(plan.active)
        self.assertEqual(plan.student, self.student)
        self.assertIsInstance(plan.generated_by_ai, dict)
        self.assertIn('title', plan.generated_by_ai)
        self.assertIn('weekly_schedule', plan.generated_by_ai)

    def test_generate_study_plan_deactivates_prior_plans(self):
        plan1 = generate_study_plan(self.student)
        self.assertTrue(plan1.active)

        plan2 = generate_study_plan(self.student)
        plan1.refresh_from_db()
        self.assertFalse(plan1.active)
        self.assertTrue(plan2.active)

        active_plans = StudyPlan.objects.filter(student=self.student, active=True)
        self.assertEqual(active_plans.count(), 1)
        self.assertEqual(active_plans.first(), plan2)

    def test_get_active_study_plan(self):
        self.assertIsNone(get_active_study_plan(self.student))
        plan = generate_study_plan(self.student)
        self.assertEqual(get_active_study_plan(self.student), plan)

    def test_format_study_plan_summary(self):
        plan = generate_study_plan(self.student)
        summary = format_study_plan_summary(plan)
        self.assertIn("Maqsad:", summary)
        self.assertIn("Muddati:", summary)


class SeedProgramsCommandTests(TestCase):
    """Tests for apps/programs/management/commands/seed_programs.py"""

    def test_seed_programs_populates_5_verified_programs(self):
        Program.objects.all().delete()
        call_command('seed_programs')
        self.assertGreaterEqual(Program.objects.count(), 5)

        required_names = ["Global UGRAD", "DAAD", "Chevening", "Türkiye Bursları", "El-Yurt Umidi"]
        for name_frag in required_names:
            self.assertTrue(
                Program.objects.filter(name__icontains=name_frag).exists(),
                f"Missing seeded program: {name_frag}"
            )

    def test_seed_programs_is_idempotent(self):
        call_command('seed_programs')
        count1 = Program.objects.count()
        call_command('seed_programs')
        count2 = Program.objects.count()
        self.assertEqual(count1, count2)

    def test_all_seeded_programs_have_valid_metadata(self):
        call_command('seed_programs')
        for prog in Program.objects.all():
            self.assertTrue(prog.source_url.startswith("http"))
            self.assertIsNotNone(prog.last_verified_date)
            self.assertIsInstance(prog.requirements, dict)
            self.assertTrue(len(prog.requirements) > 0)
            self.assertTrue(len(prog.verified_by) > 0)


class OnboardingViewsTests(TestCase):
    """Tests for multi-step onboarding wizard views and URLs"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            phone_number="+998903334455",
            password="securepassword123",
            first_name="Rustam"
        )
        self.client.force_login(self.user)
        self.student = self.user.student_profile

    def test_step_1_view_get(self):
        response = self.client.get(reverse('onboarding:step_1'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/step_1.html')
        self.assertContains(response, "O'quvchi profilingizni sozlang")
        self.assertContains(response, "AI tavsiyasi — yakuniy qarorni oila va o&#x27;quvchi qabul qiladi.")

    def test_step_1_view_post_valid_redirects_to_diagnostic(self):
        data = {
            'grade': 10,
            'target_countries': ['AQSh', 'Germaniya'],
            'target_program_type': 'grant',
            'english_level': 'intermediate',
        }
        response = self.client.post(reverse('onboarding:step_1'), data=data)
        self.assertRedirects(response, reverse('onboarding:diagnostic'))

        self.student.refresh_from_db()
        self.assertEqual(self.student.grade, 10)
        self.assertEqual(self.student.target_countries, ['AQSh', 'Germaniya'])
        self.assertEqual(self.student.target_program_type, 'grant')
        self.assertEqual(self.student.english_level, 'intermediate')

    def test_diagnostic_view_get(self):
        response = self.client.get(reverse('onboarding:diagnostic'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/diagnostic.html')
        self.assertContains(response, "Reading Comprehension")
        self.assertContains(response, "Grammar Drills")
        self.assertContains(response, "Writing Essay")
        self.assertContains(response, "AI tavsiyasi — yakuniy qarorni oila va o&#x27;quvchi qabul qiladi.")

    def test_diagnostic_view_post_creates_records_and_redirects_to_results(self):
        post_data = {
            'r1': 'B', 'r2': 'C', 'r3': 'B', 'r4': 'B',
            'g1': 'B', 'g2': 'C', 'g3': 'A', 'g4': 'D', 'g5': 'B', 'g6': 'B',
            'l1': 'A', 'l2': 'B',
            'writing_essay': "I am applying for Global UGRAD to study Computer Science in the USA...",
            'speaking_response': "I founded a coding club for high school students in Samarkand..."
        }
        response = self.client.post(reverse('onboarding:diagnostic'), data=post_data)
        self.assertRedirects(response, reverse('onboarding:results'))

        # Verify DB states
        self.assertEqual(SkillScore.objects.filter(student=self.student).count(), 5)
        self.assertEqual(DiagnosticResult.objects.filter(student=self.student).count(), 5)
        self.assertTrue(StudyPlan.objects.filter(student=self.student, active=True).exists())

        self.student.refresh_from_db()
        self.assertTrue(self.student.onboarding_completed)

    def test_results_view_displays_scores_and_plan(self):
        # First complete diagnostic
        process_diagnostic_submission(self.student, {'r1': 'B', 'g1': 'B'})
        generate_study_plan(self.student)

        response = self.client.get(reverse('onboarding:results'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'onboarding/results.html')
        self.assertContains(response, "Ready Score")
        self.assertContains(response, "5 ta Asosiy Ko'nikma")
        self.assertContains(response, "Ready Score")
        self.assertContains(response, "AI tavsiyasi — yakuniy qarorni oila va o&#x27;quvchi qabul qiladi.")

    def test_onboarding_completed_allows_dashboard_access(self):
        # Incomplete onboarding -> redirected to onboarding:step_1
        self.student.onboarding_completed = False
        self.student.save()
        response = self.client.get(reverse('dashboard:index'))
        self.assertRedirects(response, reverse('onboarding:step_1'))

        # Complete onboarding -> dashboard accessible
        self.student.onboarding_completed = True
        self.student.save()
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
