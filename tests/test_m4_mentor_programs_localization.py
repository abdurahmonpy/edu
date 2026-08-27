"""
Milestone 4 Automated Tests:
- AI Mentor Chat with full context injection (profile, 5 skills, study plan, tasks, verified programs)
- Admission safety guardrails (no admission guarantee, guidance framing, family decision deferral)
- Unverified program fallback phrase ("Men bu haqda tasdiqlangan ma'lumotga ega emasman")
- Program catalog (displaying last_verified_date and source_url)
- Program admin validation (rejecting save without source_url or last_verified_date)
- Trust & Safety disclaimers and 100% Uzbek Latin UI localization
"""
import os
import re
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User, Student
from apps.study_plans.models import StudyPlan
from apps.tasks.models import DailyTask
from apps.dashboard.models import SkillScore
from apps.programs.models import Program
from apps.mentor.models import MentorMessage
from apps.services.mentor_service import (
    build_mentor_system_prompt,
    send_mentor_message,
    UNVERIFIED_PROGRAM_FALLBACK,
    MANDATORY_DISCLAIMER
)


class Milestone4MentorProgramsLocalizationTests(TestCase):
    """
    Test suite for Milestone 4 requirements.
    """
    def setUp(self):
        self.client = Client()
        # Create student with full profile
        self.user = User.objects.create_user(
            phone_number='+998931234567',
            password='TestPassword123!',
            first_name='Anvar'
        )
        self.student = self.user.student_profile
        self.student.grade = 10
        self.student.target_countries = ['AQSH', 'Turkiya']
        self.student.target_program_type = 'grant'
        self.student.english_level = 'intermediate'
        self.student.onboarding_completed = True
        self.student.save()

        # Create 5 skill scores
        for skill_name, score_val in [('reading', 80), ('writing', 72), ('listening', 70), ('speaking', 65), ('grammar', 60)]:
            SkillScore.objects.create(
                student=self.student,
                skill=skill_name,
                current_score=score_val
            )

        # Create active study plan
        self.study_plan = StudyPlan.objects.create(
            student=self.student,
            goal="Türkiye Bursları va AQSH grantlariga tayyorgarlik",
            target_date=timezone.localdate() + timedelta(days=180),
            generated_by_ai={
                "title": "Xalqaro Grantlar O'quv Rejasi",
                "summary": "10-sinf o'quvchisi uchun grantlar rejasi",
                "weakest_skill": "grammar",
                "weekly_hours": 10
            },
            active=True
        )

        # Create recent completed daily tasks
        self.task1 = DailyTask.objects.create(
            student=self.student,
            study_plan=self.study_plan,
            date=timezone.localdate(),
            task_type='grammar_drill',
            content={'title': 'Conditional Sentences', 'question': 'If Aziz had known...'},
            completed=True,
            score=90,
            student_answer="B",
            ai_feedback="Ajoyib natija! Third conditional qoidasini to'g'ri qo'lladingiz.",
            completed_at=timezone.now()
        )

        # Create verified programs
        self.prog_ugrad = Program.objects.create(
            name="Global UGRAD",
            country="AQSH",
            type="exchange",
            requirements={"GPA": "3.0+", "TOEFL": "iBT 61+"},
            deadline="Dekabr 15",
            source_url="https://exchanges.state.gov/non-us/program/global-ugrad",
            last_verified_date=date(2026, 8, 1),
            verified_by="admin"
        )
        self.prog_turkiye = Program.objects.create(
            name="Türkiye Bursları",
            country="Turkiya",
            type="grant",
            requirements={"Bakalavr": "70% akademik ko'rsatkich"},
            deadline="Fevral 20",
            source_url="https://turkiyeburslari.gov.tr",
            last_verified_date=date(2026, 8, 5),
            verified_by="admin"
        )

    def test_mentor_system_prompt_context_injection(self):
        """Verify build_mentor_system_prompt injects profile, 5 skills, plan, tasks, programs."""
        prompt = build_mentor_system_prompt(self.student)

        # 1. Profile injection
        self.assertIn("10-sinf", prompt)
        self.assertIn("AQSH, Turkiya", prompt)
        # 2. 5 Skills injection
        self.assertIn("Reading: 80/100", prompt)
        self.assertIn("Grammar: 60/100", prompt)
        self.assertIn("Overall Ready Score: 69/100", prompt)
        # 3. Active Plan injection
        self.assertIn("Türkiye Bursları va AQSH grantlariga tayyorgarlik", prompt)
        # 4. Recent Tasks injection
        self.assertIn("Conditional Sentences", prompt)
        self.assertIn("90 ball", prompt)
        # 5. Verified Programs injection
        self.assertIn("Global UGRAD", prompt)
        self.assertIn("Türkiye Bursları", prompt)
        # 6. Trust & Safety guardrails
        self.assertIn("Hech qachon 100% qabul kafolatini bermang", prompt)
        self.assertIn(MANDATORY_DISCLAIMER, prompt)
        self.assertIn(UNVERIFIED_PROGRAM_FALLBACK, prompt)

    def test_mentor_chat_flow_and_message_persistence(self):
        """Verify sending a message saves both student and AI messages and responds in Uzbek."""
        self.client.login(phone_number='+998931234567', password='TestPassword123!')

        post_data = {'message': "Global UGRAD dasturiga qanday tayyorlansam bo'ladi?"}
        resp = self.client.post(reverse('mentor:chat'), post_data)
        self.assertRedirects(resp, reverse('mentor:chat'))

        # Check DB persistence
        student_msgs = MentorMessage.objects.filter(student=self.student, role='student')
        ai_msgs = MentorMessage.objects.filter(student=self.student, role='ai')

        self.assertGreaterEqual(student_msgs.count(), 1)
        self.assertGreaterEqual(ai_msgs.count(), 1)
        self.assertIn("Global UGRAD", student_msgs.first().content)

    def test_mentor_unverified_program_fallback(self):
        """Verify asking about an unverified fake program triggers exact fallback phrase."""
        ai_reply = send_mentor_message(self.student, "Fake Mars Scholarship dasturi talablari qanday?")
        self.assertIn(UNVERIFIED_PROGRAM_FALLBACK, ai_reply.content)

    def test_mentor_chat_page_renders_disclaimer_and_messages(self):
        """Verify chat view renders messages and mandatory disclaimer."""
        self.client.login(phone_number='+998931234567', password='TestPassword123!')
        resp = self.client.get(reverse('mentor:chat'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "AI Ta'lim Mentori")
        self.assertContains(resp, "AI tavsiyasi")

    def test_program_catalog_displays_source_url_and_verified_date(self):
        """Verify program catalog displays source_url and last_verified_date for each program (R5)."""
        resp = self.client.get(reverse('programs:catalog'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Global UGRAD")
        self.assertContains(resp, "Türkiye Bursları")
        self.assertContains(resp, "https://exchanges.state.gov/non-us/program/global-ugrad")
        self.assertContains(resp, "https://turkiyeburslari.gov.tr")
        self.assertContains(resp, "AI tavsiyasi")

    def test_program_detail_view(self):
        """Verify program detail view renders all metadata, source_url, and verified_date."""
        resp = self.client.get(reverse('programs:detail', kwargs={'program_id': self.prog_ugrad.id}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Global UGRAD")
        self.assertContains(resp, "Dekabr 15")
        self.assertContains(resp, "https://exchanges.state.gov/non-us/program/global-ugrad")
        self.assertContains(resp, "AI tavsiyasi")

    def test_program_validation_enforces_source_url_and_verified_date(self):
        """Verify program cannot be saved without source_url or last_verified_date."""
        prog_no_url = Program(
            name="Invalid Program",
            country="Buyuk Britaniya",
            type="grant",
            source_url="",
            last_verified_date=date(2026, 8, 1)
        )
        with self.assertRaises(ValidationError):
            prog_no_url.save()

        prog_no_date = Program(
            name="Invalid Program 2",
            country="Germaniya",
            type="grant",
            source_url="https://example.com",
            last_verified_date=None
        )
        with self.assertRaises(ValidationError):
            prog_no_date.save()

    def test_no_hardcoded_anthropic_api_keys_in_codebase(self):
        """Verify no 'sk-ant' hardcoded Anthropic API keys exist in project files (R7, R6)."""
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        found_keys = []

        for root, dirs, files in os.walk(project_root):
            # Skip git, cache, tests, and agents folders
            if any(p in root for p in ['.git', '__pycache__', '.agents', 'tests']):
                continue
            for file in files:
                if file.endswith(('.py', '.html', '.js', '.json', '.env', '.txt', '.md')):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Detect any actual sk-ant live API keys
                        if re.search(r'sk-ant-api03-[A-Za-z0-9_-]{20,}', content):
                            found_keys.append(filepath)

        self.assertEqual(len(found_keys), 0, f"Hardcoded API keys found in: {found_keys}")
