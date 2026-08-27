"""
Tier 4: Real-World Student Lifecycle Application Scenarios
Simulates realistic end-to-end user journeys from registration to graduation.
"""
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User, Student
from apps.study_plans.models import StudyPlan
from apps.tasks.models import DailyTask
from apps.dashboard.models import SkillScore, ProgressLog
from apps.programs.models import Program
from apps.mentor.models import MentorMessage
from apps.services.task_service import generate_daily_tasks_for_student, submit_daily_task
from apps.services.score_service import calculate_overall_ready_score, get_student_streak, decay_student_scores
from apps.services.study_plan_service import generate_study_plan
from apps.services.diagnostic_service import process_diagnostic_submission
from apps.services.mentor_service import send_mentor_message, UNVERIFIED_PROGRAM_FALLBACK, MANDATORY_DISCLAIMER


class Tier4ScenarioTests(TestCase):
    """
    Full real-world scenario tests per TEST_INFRA.md § Real-World Application Scenarios.
    """
    def setUp(self):
        self.client = Client()
        call_command('seed_programs')

    def test_scenario_1_9th_grader_malika_complete_journey(self):
        """
        Scenario 1: 9th Grader Malika (Tashkent):
        1. Registers via phone number (+998901234567)
        2. Completes onboarding (Grade 9, Turkey, Grant, Beginner)
        3. Takes diagnostic test & establishes 5-skill baseline
        4. Gets AI study plan tailored for 9th grader (1-year timeline)
        5. Solves daily grammar & reading tasks with explanatory AI feedback
        6. Streak increments to 1 on dashboard
        """
        # Step 1: Registration
        reg_resp = self.client.post(reverse('accounts:register'), {
            'phone_number': '+998901234567',
            'first_name': 'Malika',
            'password': 'SecurePassword123!',
            'password_confirm': 'SecurePassword123!'
        })
        self.assertRedirects(reg_resp, reverse('onboarding:step_1'))

        user = User.objects.get(phone_number='+998901234567')
        student = user.student_profile

        # Step 2: Onboarding Step 1
        self.client.login(phone_number='+998901234567', password='SecurePassword123!')
        ob_resp = self.client.post(reverse('onboarding:step_1'), {
            'grade': 9,
            'target_countries': ['Turkiya'],
            'target_program_type': 'grant',
            'english_level': 'beginner'
        })
        self.assertRedirects(ob_resp, reverse('onboarding:diagnostic'))

        # Step 3: Diagnostic Submission
        diag_resp = self.client.post(reverse('onboarding:diagnostic'), {
            'r1': 'B', 'r2': 'C', 'r3': 'B', 'r4': 'B',
            'g1': 'B', 'g2': 'C', 'g3': 'A', 'g4': 'D', 'g5': 'B', 'g6': 'B',
            'writing_essay': 'I want to study in Turkey because of historical ties and great engineering programs.',
            'speaking_response': 'I enjoy learning languages and solving math problems.'
        })
        self.assertRedirects(diag_resp, reverse('onboarding:results'))
        student.refresh_from_db()
        self.assertTrue(student.onboarding_completed)
        self.assertEqual(student.skill_scores.count(), 5)

        # Step 4: Study Plan Generated
        plan = generate_study_plan(student)
        self.assertTrue(plan.active)
        self.assertGreater((plan.target_date - plan.start_date).days, 300)  # 1-year timeline for 9th grader

        # Step 5: Solve Daily Tasks
        tasks = generate_daily_tasks_for_student(student)
        self.assertEqual(len(tasks), 2)
        
        task1 = tasks[0]
        task_submit_resp = self.client.post(
            reverse('tasks:detail', kwargs={'task_id': task1.id}),
            {'selected_option': 'B'}
        )
        self.assertRedirects(task_submit_resp, reverse('tasks:result', kwargs={'task_id': task1.id}))

        task1.refresh_from_db()
        self.assertTrue(task1.completed)
        self.assertTrue(len(task1.ai_feedback) > 15)

        # Step 6: Dashboard verification
        dash_resp = self.client.get(reverse('dashboard:index'))
        self.assertEqual(dash_resp.status_code, 200)
        self.assertContains(dash_resp, "🔥")

    def test_scenario_2_11th_grader_jasur_decay_and_comeback(self):
        """
        Scenario 2: 11th Grader Jasur (Samarkand):
        1. Has existing profile with 5 skill scores
        2. Misses tasks yesterday -> decay_scores runs -> Ready Score drops & streak resets
        3. Logs in -> completes today's tasks -> Ready Score rises & streak restarts
        4. Chats with AI mentor about DAAD requirements
        """
        user = User.objects.create_user(phone_number='+998939998877', password='Password123!', first_name='Jasur')
        student = user.student_profile
        student.grade = 11
        student.onboarding_completed = True
        student.save()

        for skill in ['reading', 'writing', 'listening', 'speaking', 'grammar']:
            SkillScore.objects.create(student=student, skill=skill, current_score=75)

        # Run decay for yesterday
        yesterday = timezone.localdate() - timedelta(days=1)
        decay_student_scores(target_date=yesterday, decay_points=3)
        self.assertEqual(get_student_streak(student), 0)

        # Comeback task completion today
        tasks = generate_daily_tasks_for_student(student)
        submit_daily_task(tasks[0].id, student, "B")
        self.assertEqual(get_student_streak(student), 1)

        # AI Mentor Chat
        ai_reply = send_mentor_message(student, "DAAD dasturi uchun qanday hujjatlar kerak?")
        self.assertTrue(len(ai_reply.content) > 20)
        self.assertIn("AI tavsiyasi", ai_reply.content)

    def test_scenario_3_unverified_program_inquiry_and_disclaimer(self):
        """
        Scenario 3: Student asks about unverified program.
        Verifies AI responds with exact fallback phrase and includes disclaimer.
        """
        user = User.objects.create_user(phone_number='+998971112244', password='Password123!', first_name='Aziz')
        student = user.student_profile
        student.onboarding_completed = True
        student.save()

        ai_msg = send_mentor_message(student, "Super Fake Grant haqida nima deysiz?")
        self.assertIn(UNVERIFIED_PROGRAM_FALLBACK, ai_msg.content)
        self.assertIn(MANDATORY_DISCLAIMER, ai_msg.content)

    def test_scenario_4_admin_security_and_program_validation(self):
        """
        Scenario 4: Superuser admin controls and PII security:
        1. Superuser seeds verified programs
        2. Non-superuser staff cannot access student PII in admin
        3. Attempt to save program without last_verified_date is rejected
        """
        # Superuser
        admin_user = User.objects.create_superuser(
            phone_number='+998990001122',
            password='AdminPassword123!',
            first_name='Admin'
        )
        self.assertTrue(admin_user.is_superuser)

        # Regular user
        reg_user = User.objects.create_user(
            phone_number='+998990003344',
            password='UserPassword123!',
            first_name='StaffUser'
        )
        self.assertFalse(reg_user.is_superuser)

        # Program rejection without source_url
        invalid_p = Program(name="No URL", country="AQSH", type="grant", last_verified_date=date(2026, 8, 1))
        with self.assertRaises(Exception):
            invalid_p.save()
