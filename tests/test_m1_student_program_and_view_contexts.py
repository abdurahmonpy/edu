"""
Unit and integration tests for Milestone 1:
- StudentProgram model & constraints
- Program tracking toggle API (AJAX & form fallback)
- Program catalog is_tracked context annotation
- Dashboard nearest_deadline & 7-day weekly_consistency calculation
- Tasks 3-tab filtering (?filter=today|week|completed) & inline ai_feedback
- AI Mentor context strip (grade, program, weakest skill)
"""
from datetime import date, timedelta
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.db import IntegrityError
from django.utils import timezone


from apps.accounts.models import User, Student
from apps.programs.models import Program, StudentProgram
from apps.tasks.models import DailyTask
from apps.dashboard.models import SkillScore, ProgressLog


@override_settings(ANTHROPIC_API_KEY='mock')
class StudentProgramModelTests(TestCase):
    """Tests for StudentProgram model schema, relations, and unique constraint."""

    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='+998901234501',
            password='Password123!',
            first_name='Aziz'
        )
        self.student = self.user.student_profile
        self.program1 = Program.objects.create(
            name="Global UGRAD",
            country="AQSH",
            type="exchange",
            deadline="Har yili dekabr oyi oxiri",
            source_url="https://uz.usembassy.gov/global-ugrad/",
            last_verified_date=date(2026, 1, 15),
            verified_by="admin"
        )
        self.program2 = Program.objects.create(
            name="DAAD Scholarship",
            country="Germaniya",
            type="grant",
            deadline="Har yili oktyabr — noyabr oylari",
            source_url="https://www.daad.de/en/",
            last_verified_date=date(2026, 1, 20),
            verified_by="admin"
        )

    def test_student_program_creation_and_relations(self):
        """StudentProgram links student and program, populating timestamps and reverse relations."""
        sp = StudentProgram.objects.create(student=self.student, program=self.program1)
        self.assertEqual(sp.student, self.student)
        self.assertEqual(sp.program, self.program1)
        self.assertIsNotNone(sp.tracked_at)
        self.assertIsNotNone(sp.created_at)

        # Reverse relation on student
        self.assertEqual(self.student.tracked_programs.count(), 1)
        self.assertEqual(self.student.tracked_programs.first().program, self.program1)

        # Reverse relation on program
        self.assertEqual(self.program1.student_tracking.count(), 1)
        self.assertEqual(self.program1.student_tracking.first().student, self.student)

    def test_student_program_unique_constraint(self):
        """A student cannot track the same program multiple times."""
        StudentProgram.objects.create(student=self.student, program=self.program1)
        with self.assertRaises(IntegrityError):
            StudentProgram.objects.create(student=self.student, program=self.program1)

    def test_student_program_cascade_deletion(self):
        """Deleting a student or program cascades and removes the StudentProgram record."""
        sp = StudentProgram.objects.create(student=self.student, program=self.program1)
        sp_id = sp.id
        self.program1.delete()
        self.assertFalse(StudentProgram.objects.filter(id=sp_id).exists())


@override_settings(ANTHROPIC_API_KEY='mock')
class ToggleTrackProgramViewTests(TestCase):
    """Tests for toggle_track_program endpoint supporting AJAX and standard form requests."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            phone_number='+998901234502',
            password='Password123!',
            first_name='Shahnoza'
        )
        self.student = self.user.student_profile
        self.student.onboarding_completed = True
        self.student.save()

        self.program = Program.objects.create(
            name="Chevening Scholarship",
            country="Buyuk Britaniya",
            type="grant",
            deadline="Har yili noyabr oyi boshi",
            source_url="https://www.chevening.org/",
            last_verified_date=date(2026, 1, 10),
            verified_by="admin"
        )

    def test_toggle_track_login_required(self):
        """Unauthenticated requests are redirected to login."""
        url = reverse('programs:toggle_track', kwargs={'program_id': self.program.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_toggle_track_ajax_flow(self):
        """AJAX request toggles tracking on and off returning JSON."""
        self.client.login(phone_number='+998901234502', password='Password123!')
        url = reverse('programs:toggle_track', kwargs={'program_id': self.program.id})

        # 1. Track program via AJAX
        resp1 = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.json()
        self.assertEqual(data1['status'], 'ok')
        self.assertTrue(data1['is_tracked'])
        self.assertEqual(data1['tracked_count'], 1)
        self.assertTrue(StudentProgram.objects.filter(student=self.student, program=self.program).exists())

        # 2. Untrack program via AJAX
        resp2 = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp2.status_code, 200)
        data2 = resp2.json()
        self.assertEqual(data2['status'], 'ok')
        self.assertFalse(data2['is_tracked'])
        self.assertEqual(data2['tracked_count'], 0)
        self.assertFalse(StudentProgram.objects.filter(student=self.student, program=self.program).exists())

    def test_toggle_track_post_redirect_fallback(self):
        """Standard form POST redirects back to catalog or next url."""
        self.client.login(phone_number='+998901234502', password='Password123!')
        url = reverse('programs:toggle_track', kwargs={'program_id': self.program.id})

        resp = self.client.post(url, {'next': '/programs/'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/programs/')
        self.assertTrue(StudentProgram.objects.filter(student=self.student, program=self.program).exists())


@override_settings(ANTHROPIC_API_KEY='mock')
class ProgramListViewContextTests(TestCase):
    """Tests for is_tracked context annotation in program list view."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            phone_number='+998901234503',
            password='Password123!',
            first_name='Dilnoza'
        )
        self.student = self.user.student_profile
        self.program_tracked = Program.objects.create(
            name="Türkiye Bursları",
            country="Turkiya",
            type="grant",
            deadline="Har yili 10-yanvardan 20-fevralgacha",
            source_url="https://www.turkiyeburslari.gov.tr",
            last_verified_date=date(2026, 2, 1),
            verified_by="admin"
        )
        self.program_untracked = Program.objects.create(
            name="El-Yurt Umidi Jamg'armasi",
            country="Xalqaro",
            type="grant",
            deadline="Har yili may — iyun oylari",
            source_url="https://eyuf.uz",
            last_verified_date=date(2026, 2, 10),
            verified_by="admin"
        )
        StudentProgram.objects.create(student=self.student, program=self.program_tracked)

    def test_program_list_annotates_is_tracked_for_student(self):
        """Authenticated student sees is_tracked=True on tracked programs."""
        self.client.login(phone_number='+998901234503', password='Password123!')
        response = self.client.get(reverse('programs:catalog'))
        self.assertEqual(response.status_code, 200)

        programs_in_ctx = {p.id: p for p in response.context['programs']}
        self.assertTrue(programs_in_ctx[self.program_tracked.id].is_tracked)
        self.assertFalse(programs_in_ctx[self.program_untracked.id].is_tracked)

    def test_program_list_unauthenticated(self):
        """Unauthenticated visitors see is_tracked=False for all programs."""
        response = self.client.get(reverse('programs:catalog'))
        self.assertEqual(response.status_code, 200)
        for p in response.context['programs']:
            self.assertFalse(p.is_tracked)


@override_settings(ANTHROPIC_API_KEY='mock')
class DashboardViewContextTests(TestCase):
    """Tests for nearest_deadline and 7-day weekly_consistency calculation on dashboard."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            phone_number='+998901234504',
            password='Password123!',
            first_name='Rustam'
        )
        self.student = self.user.student_profile
        self.student.onboarding_completed = True
        self.student.save()

        for skill in ['reading', 'writing', 'listening', 'speaking', 'grammar']:
            SkillScore.objects.create(student=self.student, skill=skill, current_score=70)

        today = timezone.localdate()
        from apps.study_plans.models import StudyPlan
        StudyPlan.objects.create(
            student=self.student,
            goal="Grant tayyorgarligi",
            start_date=today,
            target_date=today + timedelta(days=90),
            generated_by_ai={"title": "Test Plan", "target_program": "DAAD"},
            active=True
        )
        DailyTask.objects.create(
            student=self.student,
            date=today,
            task_type="grammar_drill",
            content={"q": "init"},
            completed=False
        )

        self.p_general = Program.objects.create(
            name="General Program",
            country="AQSH",
            type="grant",
            deadline="Har yili dekabr oyi oxiri",
            source_url="https://example.com/p1",
            last_verified_date=date(2026, 1, 1),
            verified_by="admin"
        )
        self.p_tracked = Program.objects.create(
            name="Tracked Elite Grant",
            country="Germaniya",
            type="grant",
            deadline="Har yili oktyabr — noyabr oylari",
            source_url="https://example.com/p2",
            last_verified_date=date(2026, 1, 1),
            verified_by="admin"
        )


    def test_nearest_deadline_fallback_to_all_programs(self):
        """When no programs are tracked, nearest_deadline selects from all programs."""
        self.client.login(phone_number='+998901234504', password='Password123!')
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)

        nd = response.context['nearest_deadline']
        self.assertFalse(nd['has_tracked'])
        self.assertGreaterEqual(nd['days_left'], 0)
        self.assertIn('program_name', nd)

    def test_nearest_deadline_prioritizes_tracked_programs(self):
        """When student tracks a program, nearest_deadline uses tracked program."""
        StudentProgram.objects.create(student=self.student, program=self.p_tracked)

        self.client.login(phone_number='+998901234504', password='Password123!')
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)

        nd = response.context['nearest_deadline']
        self.assertTrue(nd['has_tracked'])
        self.assertEqual(nd['program_name'], self.p_tracked.name)
        self.assertGreaterEqual(nd['days_left'], 0)

    def test_weekly_consistency_7_day_strip(self):
        """Weekly consistency contains 7 days (Mon-Sun) and reflects task completion."""
        today = timezone.localdate()
        # Mark task completed today
        DailyTask.objects.create(
            student=self.student,
            date=today,
            task_type="grammar_drill",
            content={"q": "test"},
            completed=True,
            score=90
        )

        self.client.login(phone_number='+998901234504', password='Password123!')
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)

        strip = response.context['weekly_consistency']
        self.assertEqual(len(strip), 7)
        day_names = [d['day_name'] for d in strip]
        self.assertEqual(day_names, ['Du', 'Se', 'Chor', 'Pay', 'Ju', 'Sha', 'Yak'])

        # Today's box is marked as today and completed
        today_box = next(d for d in strip if d['is_today'])
        self.assertTrue(today_box['is_completed'])


@override_settings(ANTHROPIC_API_KEY='mock')
class TaskListViewContextTests(TestCase):
    """Tests for 3-tab filtering (?filter=today|week|completed) and inline ai_feedback."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            phone_number='+998901234505',
            password='Password123!',
            first_name='Anora'
        )
        self.student = self.user.student_profile
        self.student.onboarding_completed = True
        self.student.save()

        today = timezone.localdate()
        start_of_week = today - timedelta(days=today.weekday())

        # Today pending task
        self.t_today = DailyTask.objects.create(
            student=self.student,
            date=today,
            task_type="grammar_drill",
            content={"q": "today test"},
            completed=False
        )

        # Completed past task with ai_feedback
        self.t_completed = DailyTask.objects.create(
            student=self.student,
            date=start_of_week,
            task_type="reading_comprehension",
            content={"q": "completed test"},
            completed=True,
            score=85,
            student_answer="Option A",
            ai_feedback="Ajoyib natija! Asosiy mavzu to'g'ri tushunilgan."
        )

    def test_task_list_today_filter_default(self):
        """Default view shows today's tasks and active_filter='today'."""
        self.client.login(phone_number='+998901234505', password='Password123!')
        resp = self.client.get(reverse('tasks:list'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['active_filter'], 'today')
        task_ids = [t.id for t in resp.context['tasks']]
        self.assertIn(self.t_today.id, task_ids)

    def test_task_list_week_filter(self):
        """?filter=week returns tasks for current week."""
        self.client.login(phone_number='+998901234505', password='Password123!')
        resp = self.client.get(reverse('tasks:list') + '?filter=week')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['active_filter'], 'week')
        task_ids = [t.id for t in resp.context['tasks']]
        self.assertIn(self.t_today.id, task_ids)
        self.assertIn(self.t_completed.id, task_ids)

    def test_task_list_completed_filter_with_ai_feedback(self):
        """?filter=completed returns completed tasks with accessible ai_feedback."""
        self.client.login(phone_number='+998901234505', password='Password123!')
        resp = self.client.get(reverse('tasks:list') + '?filter=completed')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['active_filter'], 'completed')
        task_ids = [t.id for t in resp.context['tasks']]
        self.assertIn(self.t_completed.id, task_ids)
        self.assertNotIn(self.t_today.id, task_ids)

        completed_task = next(t for t in resp.context['tasks'] if t.id == self.t_completed.id)
        self.assertEqual(completed_task.ai_feedback, "Ajoyib natija! Asosiy mavzu to'g'ri tushunilgan.")


@override_settings(ANTHROPIC_API_KEY='mock')
class MentorChatViewContextTests(TestCase):

    """Tests for mentor view context strip (grade, program, weakest skill)."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            phone_number='+998901234506',
            password='Password123!',
            first_name='Bobur'
        )
        self.student = self.user.student_profile
        self.student.grade = 10
        self.student.onboarding_completed = True
        self.student.save()

        # Create skill scores where grammar is weakest
        SkillScore.objects.create(student=self.student, skill='reading', current_score=80)
        SkillScore.objects.create(student=self.student, skill='writing', current_score=75)
        SkillScore.objects.create(student=self.student, skill='listening', current_score=70)
        SkillScore.objects.create(student=self.student, skill='speaking', current_score=65)
        SkillScore.objects.create(student=self.student, skill='grammar', current_score=40)

        self.program = Program.objects.create(
            name="DAAD — Germaniya Akademik Almashinuv Xizmati",
            country="Germaniya",
            type="grant",
            deadline="Har yili oktyabr oyi",
            source_url="https://www.daad.de/",
            last_verified_date=date(2026, 1, 1),
            verified_by="admin"
        )
        StudentProgram.objects.create(student=self.student, program=self.program)

    def test_mentor_context_strip_populated(self):
        """Mentor chat view includes context_strip with grade, tracked program, and weakest skill."""
        self.client.login(phone_number='+998901234506', password='Password123!')
        resp = self.client.get(reverse('mentor:chat'))
        self.assertEqual(resp.status_code, 200)

        cs = resp.context['context_strip']
        self.assertIn('10-sinf', cs['grade_display'])
        self.assertIn('DAAD', cs['program_display'])
        self.assertIn('Grammatika', cs['weakest_skill_display'])
        self.assertIn('zaif', cs['weakest_skill_display'])
        self.assertIn('•', cs['full_display'])
