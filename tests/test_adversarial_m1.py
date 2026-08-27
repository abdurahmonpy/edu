"""
Milestone 1 Adversarial Stress Testing Suite:
1. Malformed, Boundary, and Extreme Phone Number Inputs
2. Admin Security Bypass Attempts (Privilege escalation & data privacy)
3. Program Model Validation Bypass Attempts (Whitespace, None, Admin Forms)
4. Foreign Key Integrity and Cascade Deletion Behavior Across All 8 Models
"""
import datetime
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
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


class AdversarialPhoneStressTestCase(TestCase):
    """
    Adversarially tests phone number normalization, model validation,
    and authentication views against malformed, boundary, and hostile inputs.
    """

    def test_extreme_and_hostile_phone_strings_rejected(self):
        """Tests that clearly invalid phone strings are rejected with ValidationError."""
        strictly_invalid_inputs = [
            "",
            " ",
            "\n\t\r\n ",
            "9",
            "99",
            "998",
            "9012345",        # 7 digits
            "90123456",       # 8 digits
            "9012345678",      # 10 digits not starting with 8
            "99890123456",     # 11 digits
            "9989012345678",   # 13 digits
            "123456789012345", # 15 digits
            "+",
            "++",
            "+998+90+1234567",
            "+998 90 123 45 67 89",
            "+99890123456a",    # trailing letter causing 8 digits
            "+99890123456\u0430", # Cyrillic letter causing 8 digits
            "+998 (90) 123-45-6a",
            "<script>alert(1)</script>",
            "'+OR+'1'='1",
            "901234567.0",
            "1e9",
            "None",
            "null",
            "undefined",
            "+14155552671",   # US E.164 number
            "+79991234567",    # Russian number
            "+998" + "0" * 30, # 34 chars
            "9" * 1000,        # 1000 chars overflow attempt
        ]

        for raw in strictly_invalid_inputs:
            with self.subTest(raw=raw):
                with self.assertRaises(ValidationError, msg=f'Expected ValidationError for input: {raw!r}'):
                    normalize_uzbek_phone(raw)

    def test_permissive_sanitization_surfaced_vulnerability(self):
        """
        Adversarially surfaces the finding where re.sub(r'[^\\d+]', '', raw) silently
        strips non-digit characters (SQL injection, null bytes, alphabetical characters,
        leading hyphens, multiple pluses) rather than strictly rejecting them.
        """
        # These hostile inputs contain malicious/invalid characters with embedded 9-digit Uzbek sequences.
        # Under current implementation, they are silently sanitized into canonical phone numbers.
        vulnerable_cases = [
            ("+++998901234567", "+998901234567"),
            ("-998901234567", "+998901234567"),
            ("--901234567", "+998901234567"),
            ("+998901234567\x00", "+998901234567"),
            ("901234567; DROP TABLE accounts_user;--", "+998901234567"),
            ("abcdef901234567", "+998901234567"),
        ]
        for raw, expected in vulnerable_cases:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_uzbek_phone(raw), expected)

    def test_canonical_equivalencies(self):
        """Different formatting variants of the same physical number must produce identical canonical string."""
        variants = [
            "901234567",
            "998901234567",
            "+998901234567",
            "+998 90 123 45 67",
            "+998 (90) 123-45-67",
            "8 90 123 45 67",
            "8901234567",
            "8(90)1234567",
            "90-123-45-67",
            "(90) 123-45-67",
            "   +998 (90) 123-45-67  ",
            "+998.90.123.45.67",
            "+998/90/123/45/67",
        ]
        canonical = "+998901234567"
        for var in variants:
            with self.subTest(variant=var):
                self.assertEqual(normalize_uzbek_phone(var), canonical)

    def test_user_manager_rejects_invalid_phone(self):
        with self.assertRaises(ValidationError):
            User.objects.create_user(phone_number="invalid_phone", password="pass12345")

        with self.assertRaises(ValueError):
            User.objects.create_user(phone_number="", password="pass12345")

    def test_user_model_full_clean_rejects_malformed_phone(self):
        user = User(phone_number="12345", first_name="Bad")
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_duplicate_registration_under_different_formats_blocked(self):
        User.objects.create_user(phone_number="901234567", password="password123", first_name="User1")
        
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(phone_number="+998 (90) 123-45-67", password="password456", first_name="User2")

    def test_registration_view_rejects_malformed_phone(self):
        client = Client()
        response = client.post(reverse('accounts:register'), {
            'first_name': 'BadPhone',
            'phone_number': '123456',
            'password': 'password123',
            'password_confirm': 'password123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Telefon raqami")

    def test_login_view_rejects_malformed_phone(self):
        client = Client()
        response = client.post(reverse('accounts:login'), {
            'phone_number': 'not_a_phone',
            'password': 'password123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Telefon raqami")


class AdversarialAdminSecurityTestCase(TestCase):
    """
    Adversarially tests that non-superuser staff members cannot bypass admin permissions,
    access student PII querysets, view changeforms, or perform POST operations.
    """

    def setUp(self):
        self.rf = RequestFactory()
        self.site = AdminSite()
        self.client = Client()

        self.staff_user = User.objects.create_user(
            phone_number="901111111",
            password="staffpass123",
            first_name="StaffMember",
            is_staff=True,
            is_superuser=False
        )

        self.superuser = User.objects.create_superuser(
            phone_number="909999999",
            password="superpass123",
            first_name="SuperAdmin"
        )

        self.target_user = User.objects.create_user(
            phone_number="902222222",
            password="studentpass123",
            first_name="TargetStudent"
        )
        self.student = self.target_user.student_profile
        self.student.grade = 10
        self.student.save()

        self.diagnostic = DiagnosticResult.objects.create(
            student=self.student,
            skill="reading",
            score=88
        )
        self.study_plan = StudyPlan.objects.create(
            student=self.student,
            goal="Global UGRAD",
            target_date=datetime.date.today() + datetime.timedelta(days=60)
        )
        self.daily_task = DailyTask.objects.create(
            student=self.student,
            study_plan=self.study_plan,
            task_type="grammar_drill",
            date=datetime.date.today(),
            content={"q": "test"}
        )
        self.skill_score = SkillScore.objects.create(
            student=self.student,
            skill="reading",
            current_score=88
        )
        self.progress_log = ProgressLog.objects.create(
            student=self.student,
            date=datetime.date.today(),
            overall_ready_score=80,
            streak_count=3
        )
        self.mentor_message = MentorMessage.objects.create(
            student=self.student,
            role="student",
            content="Sensitive student inquiry"
        )

    def test_staff_with_explicit_model_permissions_still_blocked_by_mixin(self):
        """Evgen if standard django permissions are granted to staff, SuperuserOnlyAdminMixin MUST deny access."""
        all_student_perms = Permission.objects.filter(content_type__app_label__in=[
            'accounts', 'onboarding', 'study_plans', 'tasks', 'dashboard', 'mentor'
        ])
        self.staff_user.user_permissions.set(all_student_perms)
        self.staff_user.save()

        req = self.rf.get('/admin/accounts/student/')
        req.user = self.staff_user

        admins_and_objs = [
            (StudentAdmin(Student, self.site), self.student),
            (DiagnosticResultAdmin(DiagnosticResult, self.site), self.diagnostic),
            (StudyPlanAdmin(StudyPlan, self.site), self.study_plan),
            (DailyTaskAdmin(DailyTask, self.site), self.daily_task),
            (SkillScoreAdmin(SkillScore, self.site), self.skill_score),
            (ProgressLogAdmin(ProgressLog, self.site), self.progress_log),
            (MentorMessageAdmin(MentorMessage, self.site), self.mentor_message),
        ]

        for admin_inst, obj in admins_and_objs:
            model_name = admin_inst.model.__name__
            with self.subTest(model=model_name):
                self.assertFalse(admin_inst.has_module_permission(req), f'{model_name}: staff has module perm')
                self.assertFalse(admin_inst.has_view_permission(req, obj), f'{model_name}: staff has view perm')
                self.assertFalse(admin_inst.has_add_permission(req), f'{model_name}: staff has add perm')
                self.assertFalse(admin_inst.has_change_permission(req, obj), f'{model_name}: staff has change perm')
                self.assertFalse(admin_inst.has_delete_permission(req, obj), f'{model_name}: staff has delete perm')

    def test_staff_in_privileged_group_still_blocked_by_mixin(self):
        """Even if assigned to a group with all model permissions, staff is blocked."""
        group = Group.objects.create(name="Advisors")
        all_student_perms = Permission.objects.filter(content_type__app_label__in=[
            'accounts', 'onboarding', 'study_plans', 'tasks', 'dashboard', 'mentor'
        ])
        group.permissions.set(all_student_perms)
        self.staff_user.groups.add(group)

        req = self.rf.get('/admin/accounts/student/')
        req.user = self.staff_user
        admin_inst = StudentAdmin(Student, self.site)
        self.assertFalse(admin_inst.has_module_permission(req))
        self.assertFalse(admin_inst.has_view_permission(req, self.student))

    def test_http_admin_endpoints_strictly_deny_staff(self):
        """HTTP GET/POST to admin changelist, change, add, delete, history views for student models must return 403 or redirect."""
        self.client.force_login(self.staff_user)

        restricted_urls = [
            '/admin/accounts/student/',
            f'/admin/accounts/student/{self.student.id}/change/',
            f'/admin/accounts/student/{self.student.id}/delete/',
            f'/admin/accounts/student/{self.student.id}/history/',
            '/admin/accounts/student/add/',

            '/admin/onboarding/diagnosticresult/',
            f'/admin/onboarding/diagnosticresult/{self.diagnostic.id}/change/',
            
            '/admin/study_plans/studyplan/',
            f'/admin/study_plans/studyplan/{self.study_plan.id}/change/',

            '/admin/tasks/dailytask/',
            f'/admin/tasks/dailytask/{self.daily_task.id}/change/',

            '/admin/dashboard/skillscore/',
            f'/admin/dashboard/skillscore/{self.skill_score.id}/change/',

            '/admin/dashboard/progresslog/',
            f'/admin/dashboard/progresslog/{self.progress_log.id}/change/',

            '/admin/mentor/mentormessage/',
            f'/admin/mentor/mentormessage/{self.mentor_message.id}/change/',
        ]

        for url in restricted_urls:
            with self.subTest(url=url):
                res_get = self.client.get(url)
                self.assertIn(res_get.status_code, [302, 403], f'Staff was able to GET {url} with code {res_get.status_code}')

                res_post = self.client.post(url, {'action': 'delete_selected'})
                self.assertIn(res_post.status_code, [302, 403], f'Staff was able to POST {url} with code {res_post.status_code}')

    def test_superuser_can_access_all_admin_endpoints(self):
        self.client.force_login(self.superuser)
        res = self.client.get('/admin/accounts/student/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "O&#x27;quvchilar profillari")

    def test_anonymous_user_redirected_to_admin_login(self):
        client = Client()
        res = client.get('/admin/accounts/student/')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/admin/login/', res.url)


class AdversarialProgramValidationTestCase(TestCase):
    """
    Adversarially tests Program model validation against bypass attempts:
    empty/whitespace strings, None values, invalid formats.
    """

    def test_whitespace_source_url_bypass_attempt(self):
        whitespace_variations = [
            " ",
            "   ",
            "\t",
            "\n\r",
            "  \t  \n  ",
        ]
        for ws in whitespace_variations:
            with self.subTest(ws=repr(ws)):
                p = Program(
                    name="Test Program",
                    country="AQSH",
                    type="grant",
                    source_url=ws,
                    last_verified_date=datetime.date.today(),
                    verified_by="admin"
                )
                with self.assertRaises(ValidationError):
                    p.full_clean()
                with self.assertRaises(ValidationError):
                    p.save()

    def test_none_source_url_and_date_bypass_attempt(self):
        p1 = Program(
            name="P1", country="USA", type="grant",
            source_url=None, last_verified_date=datetime.date.today()
        )
        with self.assertRaises(ValidationError):
            p1.save()

        p2 = Program(
            name="P2", country="USA", type="grant",
            source_url="https://example.com", last_verified_date=None
        )
        with self.assertRaises(ValidationError):
            p2.save()

    def test_program_objects_create_enforces_validation(self):
        with self.assertRaises(ValidationError):
            Program.objects.create(
                name="Invalid",
                country="USA",
                type="grant",
                source_url="",
                last_verified_date=datetime.date.today()
            )

    def test_program_admin_form_validation(self):
        superuser = User.objects.create_superuser(
            phone_number="908888888",
            password="superpass123",
            first_name="Admin"
        )
        client = Client()
        client.force_login(superuser)

        # POST without source_url
        response = client.post('/admin/programs/program/add/', {
            'name': 'Test Admin Program',
            'country': 'USA',
            'type': 'grant',
            'requirements': '{}',
            'source_url': '',
            'last_verified_date': '2026-08-26',
            'verified_by': 'admin'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'errorlist')
        self.assertFalse(Program.objects.filter(name='Test Admin Program').exists())

        # POST without last_verified_date
        response2 = client.post('/admin/programs/program/add/', {
            'name': 'Test Admin Program 2',
            'country': 'USA',
            'type': 'grant',
            'requirements': '{}',
            'source_url': 'https://example.com',
            'last_verified_date': '',
            'verified_by': 'admin'
        })
        self.assertEqual(response2.status_code, 200)
        self.assertContains(response2, 'errorlist')
        self.assertFalse(Program.objects.filter(name='Test Admin Program 2').exists())


class AdversarialForeignKeyCascadeTestCase(TestCase):
    """
    Adversarially tests foreign key cascade, set_null, and database referential integrity
    across all 8 data models under stress and deletions.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="903334455",
            password="password123",
            first_name="Ali"
        )
        self.student = self.user.student_profile
        self.plan = StudyPlan.objects.create(
            student=self.student,
            goal="Chevening",
            target_date=datetime.date.today() + datetime.timedelta(days=90)
        )
        self.diag = DiagnosticResult.objects.create(
            student=self.student,
            skill="grammar",
            score=90
        )
        self.task = DailyTask.objects.create(
            student=self.student,
            study_plan=self.plan,
            task_type="grammar_drill",
            date=datetime.date.today()
        )
        self.score = SkillScore.objects.create(
            student=self.student,
            skill="grammar",
            current_score=90
        )
        self.log = ProgressLog.objects.create(
            student=self.student,
            date=datetime.date.today(),
            overall_ready_score=85,
            streak_count=1
        )
        self.msg = MentorMessage.objects.create(
            student=self.student,
            role="student",
            content="Hello AI mentor"
        )
        self.program = Program.objects.create(
            name="DAAD Masters",
            country="Germaniya",
            type="grant",
            source_url="https://daad.de",
            last_verified_date=datetime.date.today(),
            verified_by="admin"
        )

    def test_deleting_user_cascades_to_all_student_child_records(self):
        """Deleting User must delete Student profile and all 6 related student entities."""
        user_id = self.user.id
        student_id = self.student.id
        diag_id = self.diag.id
        plan_id = self.plan.id
        task_id = self.task.id
        score_id = self.score.id
        log_id = self.log.id
        msg_id = self.msg.id
        program_id = self.program.id

        self.user.delete()

        self.assertFalse(User.objects.filter(id=user_id).exists())
        self.assertFalse(Student.objects.filter(id=student_id).exists())
        self.assertFalse(DiagnosticResult.objects.filter(id=diag_id).exists())
        self.assertFalse(StudyPlan.objects.filter(id=plan_id).exists())
        self.assertFalse(DailyTask.objects.filter(id=task_id).exists())
        self.assertFalse(SkillScore.objects.filter(id=score_id).exists())
        self.assertFalse(ProgressLog.objects.filter(id=log_id).exists())
        self.assertFalse(MentorMessage.objects.filter(id=msg_id).exists())

        # Unrelated Program must survive
        self.assertTrue(Program.objects.filter(id=program_id).exists())

    def test_deleting_study_plan_sets_null_on_daily_task_without_deleting_task(self):
        """StudyPlan deletion must NOT delete DailyTask (on_delete=SET_NULL)."""
        plan_id = self.plan.id
        task_id = self.task.id

        self.plan.delete()

        self.assertFalse(StudyPlan.objects.filter(id=plan_id).exists())
        task_refreshed = DailyTask.objects.get(id=task_id)
        self.assertIsNone(task_refreshed.study_plan)
        self.assertEqual(task_refreshed.student, self.student)


    def test_deleting_child_record_does_not_delete_student_or_user(self):
        """Reverse deletion protection: deleting a task/message/score must never delete parent student/user."""
        self.task.delete()
        self.msg.delete()
        self.diag.delete()
        self.score.delete()
        self.log.delete()

        self.assertTrue(Student.objects.filter(id=self.student.id).exists())
        self.assertTrue(User.objects.filter(id=self.user.id).exists())


    def test_student_one_to_one_enforcement(self):
        """Cannot assign multiple Student profiles to a single User."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Student.objects.create(user=self.user, grade=9)


    def test_skill_score_unique_together_enforcement(self):
        """Cannot create duplicate (student, skill) records."""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SkillScore.objects.create(student=self.student, skill="grammar", current_score=50)


    def test_score_and_grade_boundary_validators(self):
        """Values outside 0-100 for score fields must fail validation."""
        invalid_scores = [-1, -50, 101, 999]
        for bad_score in invalid_scores:
            with self.subTest(bad_score=bad_score):
                d = DiagnosticResult(student=self.student, skill="reading", score=bad_score)
                with self.assertRaises(ValidationError):
                    d.full_clean()

                s = SkillScore(student=self.student, skill="writing", current_score=bad_score)
                with self.assertRaises(ValidationError):
                    s.full_clean()

                t = DailyTask(student=self.student, task_type="grammar_drill", score=bad_score)
                with self.assertRaises(ValidationError):
                    t.full_clean()

                p = ProgressLog(student=self.student, overall_ready_score=bad_score)
                with self.assertRaises(ValidationError):
                    p.full_clean()
