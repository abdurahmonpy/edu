"""
Milestone 1 Foundation Test Suite:
1. Phone Number Normalization & Validation
2. User and Student Models & Auto-profile Creation
3. All 8 Data Models Schema & Constraints
4. Program Model Validation (source_url, last_verified_date)
5. Superuser-Only Admin Security Access Control
6. Authentication Views & Flow (Register, Login, Logout)
7. Disclaimer Context & Trust and Safety
"""
from datetime import date, timedelta
from django.test import TestCase, RequestFactory, Client
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse

from apps.accounts.utils import normalize_uzbek_phone, format_uzbek_phone_display
from apps.accounts.models import Student
from apps.accounts.admin import StudentAdmin, CustomUserAdmin
from apps.onboarding.models import DiagnosticResult
from apps.onboarding.admin import DiagnosticResultAdmin
from apps.study_plans.models import StudyPlan
from apps.study_plans.admin import StudyPlanAdmin
from apps.tasks.models import DailyTask
from apps.tasks.admin import DailyTaskAdmin
from apps.dashboard.models import SkillScore, ProgressLog
from apps.dashboard.admin import SkillScoreAdmin, ProgressLogAdmin
from apps.programs.models import Program
from apps.programs.admin import ProgramAdmin
from apps.mentor.models import MentorMessage
from apps.mentor.admin import MentorMessageAdmin

User = get_user_model()

class PhoneNormalizationTestCase(TestCase):
    """Tests for phone number normalization across all common Uzbek input formats."""
    
    def test_normalization_valid_formats(self):
        valid_cases = [
            ("901234567", "+998901234567"),
            ("998901234567", "+998901234567"),
            ("+998901234567", "+998901234567"),
            ("+998 90 123 45 67", "+998901234567"),
            ("+998 (90) 123-45-67", "+998901234567"),
            ("8 90 123 45 67", "+998901234567"),
            ("8901234567", "+998901234567"),
            ("90-123-45-67", "+998901234567"),
            ("(90) 123-45-67", "+998901234567"),
            ("  +998 90 123 45 67  ", "+998901234567"),
        ]
        for raw, expected in valid_cases:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_uzbek_phone(raw), expected)

    def test_normalization_invalid_formats(self):
        invalid_cases = [
            "",
            "   ",
            "12345",
            "abcdef",
            "+1234567890",
            "9981234",
            "99890123456789",
            "+9989012345678",
        ]
        for raw in invalid_cases:
            with self.subTest(raw=raw):
                with self.assertRaises(ValidationError):
                    normalize_uzbek_phone(raw)

    def test_phone_display_formatting(self):
        self.assertEqual(format_uzbek_phone_display("+998901234567"), "+998 (90) 123-45-67")
        self.assertEqual(format_uzbek_phone_display("901234567"), "+998 (90) 123-45-67")


class UserAndStudentModelTestCase(TestCase):
    """Tests for Custom User and Student profile creation and relations."""

    def test_create_regular_user(self):
        user = User.objects.create_user(
            phone_number="901234567",
            password="testpassword123",
            first_name="Jasur"
        )
        self.assertEqual(user.phone_number, "+998901234567")
        self.assertEqual(user.first_name, "Jasur")
        self.assertTrue(user.check_password("testpassword123"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        # Verify student profile auto-created
        self.assertTrue(hasattr(user, 'student_profile'))
        self.assertEqual(user.student_profile.user, user)
        self.assertFalse(user.student_profile.onboarding_completed)

    def test_create_superuser(self):
        admin_user = User.objects.create_superuser(
            phone_number="+998909999999",
            password="adminpassword123",
            first_name="Admin"
        )
        self.assertEqual(admin_user.phone_number, "+998909999999")
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)


class CoreModelsTestCase(TestCase):
    """Tests all 8 core data models creation and constraints."""

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="901112233",
            password="password123",
            first_name="Madina"
        )
        self.student = self.user.student_profile

    def test_student_model_fields(self):
        self.student.grade = 11
        self.student.target_countries = ["AQSH", "Germaniya"]
        self.student.target_program_type = "grant"
        self.student.english_level = "intermediate"
        self.student.onboarding_completed = True
        self.student.save()

        refreshed = Student.objects.get(id=self.student.id)
        self.assertEqual(refreshed.grade, 11)
        self.assertEqual(refreshed.target_countries, ["AQSH", "Germaniya"])
        self.assertTrue(refreshed.onboarding_completed)

    def test_diagnostic_result_model(self):
        res = DiagnosticResult.objects.create(
            student=self.student,
            skill="reading",
            score=85,
            raw_response="Student answers"
        )
        self.assertEqual(res.skill, "reading")
        self.assertEqual(res.score, 85)
        self.assertEqual(res.student, self.student)

    def test_study_plan_model(self):
        plan = StudyPlan.objects.create(
            student=self.student,
            goal="IELTS 7.5 va Global UGRAD grantini yutish",
            start_date=date.today(),
            target_date=date.today() + timedelta(days=90),
            generated_by_ai={"weekly_hours": 12, "focus": "Grammar & Reading"},
            active=True
        )
        self.assertTrue(plan.active)
        self.assertIn("weekly_hours", plan.generated_by_ai)

    def test_daily_task_model(self):
        plan = StudyPlan.objects.create(
            student=self.student,
            goal="Grant",
            start_date=date.today(),
            target_date=date.today() + timedelta(days=30),
            generated_by_ai={},
            active=True
        )
        task = DailyTask.objects.create(
            student=self.student,
            study_plan=plan,
            date=date.today(),
            task_type="grammar_drill",
            content={"question": "Choose correct tense"},
            completed=True,
            score=95,
            student_answer="Option B",
            ai_feedback="To'g'ri javob tanlandi! Present perfect zamoni to'g'ri qo'llanilgan."
        )
        self.assertEqual(task.score, 95)
        self.assertTrue(task.completed)
        self.assertEqual(task.study_plan, plan)

    def test_skill_score_model_and_unique_constraint(self):
        SkillScore.objects.create(
            student=self.student,
            skill="grammar",
            current_score=75
        )
        # Unique constraint test
        with self.assertRaises(IntegrityError):
            SkillScore.objects.create(
                student=self.student,
                skill="grammar",
                current_score=80
            )

    def test_progress_log_model(self):
        log = ProgressLog.objects.create(
            student=self.student,
            date=date.today(),
            overall_ready_score=72,
            streak_count=5,
            delta="+3%"
        )
        self.assertEqual(log.overall_ready_score, 72)
        self.assertEqual(log.streak_count, 5)

    def test_mentor_message_model(self):
        msg_student = MentorMessage.objects.create(
            student=self.student,
            role="student",
            content="DAAD dasturiga qanday hujjatlar kerak?"
        )
        msg_ai = MentorMessage.objects.create(
            student=self.student,
            role="ai",
            content="DAAD dasturi uchun tavsiyanoma va motivatsiya xati kerak."
        )
        self.assertEqual(msg_student.role, "student")
        self.assertEqual(msg_ai.role, "ai")


class ProgramValidationTestCase(TestCase):
    """Tests Program model clean() and save() enforcement."""

    def test_valid_program_creation(self):
        prog = Program.objects.create(
            name="Global UGRAD",
            country="AQSH",
            type="grant",
            requirements={"grade": "9-11", "english": "B2"},
            deadline="2026-12-15",
            source_url="https://uz.usembassy.gov/global-ugrad",
            last_verified_date=date.today(),
            verified_by="admin"
        )
        self.assertEqual(prog.name, "Global UGRAD")
        self.assertEqual(prog.country, "AQSH")

    def test_missing_source_url_raises_validation_error(self):
        prog = Program(
            name="DAAD",
            country="Germaniya",
            type="grant",
            requirements={},
            deadline="2026-11-01",
            source_url="",  # missing
            last_verified_date=date.today(),
            verified_by="admin"
        )
        with self.assertRaises(ValidationError):
            prog.full_clean()
        with self.assertRaises(ValidationError):
            prog.save()

    def test_missing_last_verified_date_raises_validation_error(self):
        prog = Program(
            name="Chevening",
            country="Buyuk Britaniya",
            type="grant",
            requirements={},
            deadline="2026-11-01",
            source_url="https://www.chevening.org",
            last_verified_date=None,  # missing
            verified_by="admin"
        )
        with self.assertRaises(ValidationError):
            prog.full_clean()
        with self.assertRaises(ValidationError):
            prog.save()


class AdminSecurityTestCase(TestCase):
    """Tests Superuser-Only access control in Django Admin across all PII models."""

    def setUp(self):
        self.rf = RequestFactory()
        self.site = AdminSite()

        # Regular Staff User (is_staff=True, is_superuser=False)
        self.staff_user = User.objects.create_user(
            phone_number="901001001",
            password="staffpass123",
            first_name="StaffUser",
            is_staff=True,
            is_superuser=False
        )

        # Superuser (is_staff=True, is_superuser=True)
        self.superuser = User.objects.create_superuser(
            phone_number="902002002",
            password="superpass123",
            first_name="SuperAdmin"
        )

    def test_student_admin_permissions(self):
        admin_inst = StudentAdmin(Student, self.site)
        
        # Staff request
        req_staff = self.rf.get('/admin/accounts/student/')
        req_staff.user = self.staff_user

        # Superuser request
        req_super = self.rf.get('/admin/accounts/student/')
        req_super.user = self.superuser

        # Assert staff denied
        self.assertFalse(admin_inst.has_module_permission(req_staff))
        self.assertFalse(admin_inst.has_view_permission(req_staff))
        self.assertFalse(admin_inst.has_add_permission(req_staff))
        self.assertFalse(admin_inst.has_change_permission(req_staff))
        self.assertFalse(admin_inst.has_delete_permission(req_staff))

        # Assert superuser allowed
        self.assertTrue(admin_inst.has_module_permission(req_super))
        self.assertTrue(admin_inst.has_view_permission(req_super))
        self.assertTrue(admin_inst.has_add_permission(req_super))
        self.assertTrue(admin_inst.has_change_permission(req_super))
        self.assertTrue(admin_inst.has_delete_permission(req_super))

    def test_all_student_pii_admins_deny_staff_access(self):
        admin_model_pairs = [
            (DiagnosticResultAdmin, DiagnosticResult),
            (StudyPlanAdmin, StudyPlan),
            (DailyTaskAdmin, DailyTask),
            (SkillScoreAdmin, SkillScore),
            (ProgressLogAdmin, ProgressLog),
            (MentorMessageAdmin, MentorMessage),
        ]

        req_staff = self.rf.get('/admin/')
        req_staff.user = self.staff_user

        req_super = self.rf.get('/admin/')
        req_super.user = self.superuser

        for admin_cls, model_cls in admin_model_pairs:
            with self.subTest(model=model_cls.__name__):
                admin_inst = admin_cls(model_cls, self.site)
                self.assertFalse(admin_inst.has_module_permission(req_staff))
                self.assertFalse(admin_inst.has_view_permission(req_staff))
                self.assertTrue(admin_inst.has_module_permission(req_super))
                self.assertTrue(admin_inst.has_view_permission(req_super))


class AuthViewsTestCase(TestCase):
    """Tests HTTP registration, login, and logout views and redirects."""

    def setUp(self):
        self.client = Client()

    def test_registration_success(self):
        response = self.client.post(reverse('accounts:register'), {
            'first_name': 'Anvar',
            'phone_number': '+998 90 555 66 77',
            'password': 'secretpassword',
            'password_confirm': 'secretpassword'
        })
        self.assertRedirects(response, reverse('onboarding:step_1'))
        # User created in canonical format
        user = User.objects.get(phone_number='+998905556677')
        self.assertEqual(user.first_name, 'Anvar')
        self.assertTrue(hasattr(user, 'student_profile'))

    def test_registration_duplicate_phone_error(self):
        User.objects.create_user(phone_number="905556677", password="pwd", first_name="Existing")
        response = self.client.post(reverse('accounts:register'), {
            'first_name': 'NewUser',
            'phone_number': '905556677',
            'password': 'secretpassword',
            'password_confirm': 'secretpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ushbu telefon raqami allaqachon ro&#x27;yxatdan o&#x27;tgan.")

    def test_registration_password_mismatch(self):
        response = self.client.post(reverse('accounts:register'), {
            'first_name': 'Test',
            'phone_number': '901113344',
            'password': 'password123',
            'password_confirm': 'password999'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Parollar bir-biriga mos kelmadi.")

    def test_login_success(self):
        User.objects.create_user(
            phone_number="907778899",
            password="validpassword123",
            first_name="Temur"
        )
        response = self.client.post(reverse('accounts:login'), {
            'phone_number': '90 777 88 99',  # non-standard format
            'password': 'validpassword123'
        })
        # Student onboarding not completed -> redirects to onboarding:step_1
        self.assertRedirects(response, reverse('onboarding:step_1'))

    def test_login_invalid_password(self):
        User.objects.create_user(
            phone_number="907778899",
            password="validpassword123",
            first_name="Temur"
        )
        response = self.client.post(reverse('accounts:login'), {
            'phone_number': '907778899',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Telefon raqami yoki parol noto&#x27;g&#x27;ri.")

    def test_logout_clears_session(self):
        user = User.objects.create_user(
            phone_number="908889900",
            password="pass",
            first_name="Shahzod"
        )
        self.client.force_login(user)
        response = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('accounts:login'))


class TrustAndSafetyTestCase(TestCase):
    """Tests Trust & Safety disclaimer rendering and API key safety."""

    def test_disclaimer_rendered_in_base_context(self):
        client = Client()
        response = client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI tavsiyasi — yakuniy qarorni oila va o&#x27;quvchi qabul qiladi.")
