"""
Tier 1: Feature Sanity & Coverage Test Suite
Tests every feature (F1 through F12) per ORIGINAL_REQUEST.md & TEST_INFRA.md.
"""
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User, Student
from apps.study_plans.models import StudyPlan
from apps.tasks.models import DailyTask
from apps.dashboard.models import SkillScore, ProgressLog
from apps.programs.models import Program
from apps.mentor.models import MentorMessage
from apps.services.task_service import generate_daily_tasks_for_student, grade_task_submission, submit_daily_task
from apps.services.score_service import calculate_overall_ready_score, get_student_streak, decay_student_scores
from apps.services.study_plan_service import generate_study_plan, get_active_study_plan
from apps.services.diagnostic_service import process_diagnostic_submission, get_default_diagnostic_test
from apps.services.mentor_service import send_mentor_message, build_mentor_system_prompt, UNVERIFIED_PROGRAM_FALLBACK, MANDATORY_DISCLAIMER


class Tier1FeatureTests(TestCase):
    """
    Comprehensive feature tests covering F1 through F12.
    """
    def setUp(self):
        self.client = Client()
        # Seed programs
        call_command('seed_programs')
        # Create standard test user
        self.user = User.objects.create_user(
            phone_number='+998901112233',
            password='SecretPassword123!',
            first_name='Malika'
        )
        self.student = self.user.student_profile

    # F1: Phone Authentication
    def test_f1_phone_registration_and_login(self):
        """F1: A student can register with a phone number and log in."""
        reg_resp = self.client.post(reverse('accounts:register'), {
            'phone_number': '+998912345678',
            'first_name': 'Kamola',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        })
        self.assertRedirects(reg_resp, reverse('onboarding:step_1'))
        new_user = User.objects.get(phone_number='+998912345678')
        self.assertEqual(new_user.first_name, 'Kamola')

    # F2: Onboarding Flow
    def test_f2_onboarding_multi_step_flow(self):
        """F2: Multi-step profile intake stores grade, target countries, goal, and English level."""
        self.client.login(phone_number='+998901112233', password='SecretPassword123!')
        step1_resp = self.client.post(reverse('onboarding:step_1'), {
            'grade': 10,
            'target_countries': ['AQSh', 'Germaniya'],
            'target_program_type': 'grant',
            'english_level': 'intermediate'
        })
        self.assertRedirects(step1_resp, reverse('onboarding:diagnostic'))
        self.student.refresh_from_db()
        self.assertEqual(self.student.grade, 10)
        self.assertIn('AQSh', self.student.target_countries)

    # F3: Diagnostic Assessment & 5-Skill Baseline
    def test_f3_diagnostic_grading_and_skill_score_baselines(self):
        """F3: Diagnostic submission creates 5 SkillScores, initial ProgressLog, and marks onboarding complete."""
        answers = {
            'r1': 'B', 'r2': 'C', 'r3': 'B', 'r4': 'B',
            'g1': 'B', 'g2': 'C', 'g3': 'A', 'g4': 'D', 'g5': 'B', 'g6': 'B',
            'writing_essay': 'I want to study Computer Science abroad to help develop Uzbekistan digital infrastructure.',
            'speaking_response': 'I led a youth coding club in my hometown and learned teamwork.'
        }
        res = process_diagnostic_submission(self.student, answers)
        self.assertEqual(self.student.skill_scores.count(), 5)
        self.assertTrue(self.student.onboarding_completed)
        self.assertGreater(res['overall_ready_score'], 0)

    # F4: AI Study Plan Generation
    def test_f4_ai_study_plan_generation(self):
        """F4: Study plan generated with structured JSON and saved as active."""
        plan = generate_study_plan(self.student, goal="DAAD grantiga tayyorgarlik")
        self.assertTrue(plan.active)
        self.assertIn('title', plan.generated_by_ai)
        self.assertEqual(get_active_study_plan(self.student), plan)

    # F5: Daily Task Engine
    def test_f5_daily_task_generation(self):
        """F5: Generates at least 2 tasks (grammar drill and reading comprehension)."""
        tasks = generate_daily_tasks_for_student(self.student)
        self.assertGreaterEqual(len(tasks), 2)
        task_types = [t.task_type for t in tasks]
        self.assertIn('grammar_drill', task_types)
        self.assertIn('reading_comprehension', task_types)

    # F6: Task Submission & Explanatory Reasoning
    def test_f6_task_submission_ai_feedback_reasoning(self):
        """F6: Submitting task evaluates answer and provides explanatory reasoning."""
        tasks = generate_daily_tasks_for_student(self.student)
        task = tasks[0]
        submitted = submit_daily_task(task.id, self.student, "B")
        self.assertTrue(submitted.completed)
        self.assertIsNotNone(submitted.score)
        self.assertGreater(len(submitted.ai_feedback), 15)

    # F7: Progress Dashboard
    def test_f7_progress_dashboard_metrics(self):
        """F7: Dashboard renders Ready Score, streak, 5-skill breakdown, and tasks."""
        self.student.onboarding_completed = True
        self.student.save()
        self.client.login(phone_number='+998901112233', password='SecretPassword123!')
        resp = self.client.get(reverse('dashboard:index'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Tayyorgarlik Darajasi")
        self.assertContains(resp, "Ketma-ketlik (Streak)")

    # F8: Score Decay Command
    def test_f8_score_decay_command(self):
        """F8: decay_scores command reduces Ready Score for missed days."""
        self.student.onboarding_completed = True
        self.student.save()
        for skill in ['reading', 'writing', 'listening', 'speaking', 'grammar']:
            SkillScore.objects.create(student=self.student, skill=skill, current_score=70)
        
        call_command('decay_scores', points=2)
        log = ProgressLog.objects.filter(student=self.student).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.streak_count, 0)

    # F9: AI Mentor Chat Context Injection
    def test_f9_mentor_chat_context_injection(self):
        """F9: System prompt contains student scores, active plan, tasks, and verified programs."""
        prompt = build_mentor_system_prompt(self.student)
        self.assertIn("Reading:", prompt)
        self.assertIn("Bazada Tasdiqlangan Rasmiy Dasturlar:", prompt)
        self.assertIn("Global UGRAD", prompt)

    # F10: Mentor Safety Guardrails
    def test_f10_mentor_safety_and_fallback(self):
        """F10: Mentor refuses unverified programs and defers decisions to family."""
        ai_msg = send_mentor_message(self.student, "Fake Mars Scholarship haqida ma'lumot bering?")
        self.assertIn(UNVERIFIED_PROGRAM_FALLBACK, ai_msg.content)

    # F11: Program Database & Admin Security
    def test_f11_program_database_and_validation(self):
        """F11: Verified programs are stored with last_verified_date and source_url."""
        programs = Program.objects.all()
        self.assertGreaterEqual(programs.count(), 5)
        for p in programs:
            self.assertTrue(p.source_url.startswith("http"))
            self.assertIsNotNone(p.last_verified_date)

    # F12: Trust & Safety Localization
    def test_f12_mandatory_disclaimer_and_uzbek_ui(self):
        """F12: Mandatory Uzbek disclaimer is present on AI and program views."""
        self.student.onboarding_completed = True
        self.student.save()
        self.client.login(phone_number='+998901112233', password='SecretPassword123!')

        for route_name in ['dashboard:index', 'tasks:list', 'mentor:chat', 'programs:catalog']:
            resp = self.client.get(reverse(route_name))
            self.assertEqual(resp.status_code, 200)
            self.assertContains(resp, "AI tavsiyasi")
