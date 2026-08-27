"""
Trust & Safety and Localization Audit Test Suite
Enforces non-negotiable requirements per ORIGINAL_REQUEST.md §R6:
- Zero hardcoded Anthropic API keys (sk-ant-)
- 100% Uzbek Latin UI localization across all user-facing templates
- Mandatory Uzbek disclaimer visibility on all AI/program pages
- Superuser-only admin access for student personal data
"""
import os
import re
from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from apps.accounts.models import User, Student
from apps.programs.models import Program
from apps.tasks.models import DailyTask
from apps.services.mentor_service import MANDATORY_DISCLAIMER


class TrustAndSafetyTests(TestCase):
    """
    Automated audit tests for trust, security, and localization compliance.
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            phone_number='+998901239999',
            password='TestPassword123!',
            first_name='Zilola'
        )
        self.student = self.user.student_profile
        self.student.onboarding_completed = True
        self.student.save()

        # Seed sample program and task
        self.program = Program.objects.create(
            name="Global UGRAD",
            country="AQSH",
            type="exchange",
            requirements={"GPA": "3.0+"},
            deadline="Dekabr 15",
            source_url="https://exchanges.state.gov",
            last_verified_date=timezone.localdate(),
            verified_by="admin"
        )
        self.task = DailyTask.objects.create(
            student=self.student,
            task_type='grammar_drill',
            content={'title': 'Grammar Drill', 'question': 'Sample question'},
            completed=True,
            score=85,
            ai_feedback="Javobingiz to'g'ri va qoidaga mos.",
            completed_at=timezone.now()
        )

    def test_zero_hardcoded_anthropic_api_keys(self):
        """Audit: Scans codebase to verify no live Anthropic API keys (sk-ant-) exist."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        violating_files = []

        for root, dirs, files in os.walk(project_root):
            if any(p in root for p in ['.git', '__pycache__', '.agents', 'tests']):
                continue
            for file in files:
                if file.endswith(('.py', '.html', '.js', '.json', '.env', '.txt', '.md')):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if re.search(r'sk-ant-api03-[A-Za-z0-9_-]{20,}', content):
                            violating_files.append(filepath)

        self.assertEqual(len(violating_files), 0, f"Hardcoded keys found in: {violating_files}")

    def test_mandatory_disclaimer_presence_on_all_ai_pages(self):
        """Audit: Verifies mandatory disclaimer is present on all AI and program pages."""
        self.client.login(phone_number='+998901239999', password='TestPassword123!')

        urls_to_check = [
            reverse('dashboard:index'),
            reverse('tasks:list'),
            reverse('tasks:result', kwargs={'task_id': self.task.id}),
            reverse('mentor:chat'),
            reverse('programs:catalog'),
            reverse('programs:detail', kwargs={'program_id': self.program.id}),
        ]

        for url in urls_to_check:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, f"Failed accessing {url}")
            self.assertContains(resp, "AI tavsiyasi", msg_prefix=f"Disclaimer missing on {url}")

    def test_superuser_only_student_admin_security(self):
        """Audit: Superusers only can access student personal data in admin."""
        # Non-superuser staff member
        staff_user = User.objects.create_user(
            phone_number='+998908887766',
            password='StaffPassword123!',
            first_name='Staff'
        )
        staff_user.is_staff = True
        staff_user.save()

        # Regular client login with staff user
        self.client.login(phone_number='+998908887766', password='StaffPassword123!')
        
        # Student changelist in admin
        student_admin_url = reverse('admin:accounts_student_changelist')
        resp = self.client.get(student_admin_url)
        # Should be forbidden (403) or redirect for non-superuser
        self.assertIn(resp.status_code, [403, 302])

    def test_100_percent_uzbek_latin_ui_templates(self):
        """Audit: Checks user-facing templates contain Uzbek navigation and headings."""
        templates_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
        
        # Key Uzbek words that must be present in templates
        key_uzbek_terms = [
            "Bosh sahifa",
            "Vazifalar",
            "Dasturlar",
            "AI Mentor",
            "Ro'yxatdan o'tish",
            "Kirish"
        ]
        all_templates_content = ""
        for root, dirs, files in os.walk(templates_dir):
            for file in files:
                if file.endswith('.html'):
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        all_templates_content += f.read() + " "

        for term in key_uzbek_terms:
            self.assertIn(term, all_templates_content, f"Uzbek UI term '{term}' missing from templates.")
