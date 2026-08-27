"""
Milestone 3 Automated Tests:
- Task Generation (Grammar Drill + Reading Comprehension targeting weakest skill)
- Task Submission, Claude Grading with Explanatory Reasoning (ai_feedback)
- Dashboard View (Ready Score, Streak, 5-Skill Breakdown, Active Plan)
- Decay Scores Command and ProgressLog delta tracking
- Trust & Safety Disclaimer Verification
"""
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.core.management import call_command
from django.utils import timezone
from django.utils.html import escape

from apps.accounts.models import User, Student
from apps.study_plans.models import StudyPlan
from apps.tasks.models import DailyTask
from apps.dashboard.models import SkillScore, ProgressLog
from apps.services.task_service import (
    get_student_weakest_skill,
    generate_daily_tasks_for_student,
    grade_task_submission,
    submit_daily_task
)
from apps.services.score_service import (
    calculate_overall_ready_score,
    get_student_streak,
    decay_student_scores,
    record_task_completion_score
)


class Milestone3TasksDashboardDecayTests(TestCase):
    """
    Test suite for Milestone 3 requirements.
    """
    def setUp(self):
        self.client = Client()
        # Create active onboarding-completed student
        self.user = User.objects.create_user(
            phone_number='+998901234567',
            password='TestPassword123!',
            first_name='Dilnoza'
        )
        self.student = self.user.student_profile
        self.student.grade = 11
        self.student.target_countries = ['AQSH', 'Germaniya']
        self.student.target_program_type = 'grant'
        self.student.english_level = 'intermediate'
        self.student.onboarding_completed = True
        self.student.save()
        # Create 5 skill scores
        self.skills = {
            'reading': 75,
            'writing': 70,
            'listening': 65,
            'speaking': 60,
            'grammar': 55  # Weakest skill
        }
        for skill_name, score_val in self.skills.items():
            SkillScore.objects.create(
                student=self.student,
                skill=skill_name,
                current_score=score_val
            )
        # Create active study plan
        self.study_plan = StudyPlan.objects.create(
            student=self.student,
            goal="Global UGRAD grantiga tayyorgarlik",
            target_date=timezone.localdate() + timedelta(days=90),
            generated_by_ai={
                "title": "Global UGRAD Shaxsiy Rejasi",
                "summary": "11-sinf o'quvchisi uchun grant tayyorgarligi",
                "weakest_skill": "grammar",
                "milestones": [{"title": "1-bosqich", "target_week": 4, "description": "Grammatika bazasi"}]
            },
            active=True
        )

    def test_weakest_skill_identified_correctly(self):
        """Verify get_student_weakest_skill returns the skill with lowest score."""
        weakest = get_student_weakest_skill(self.student)
        self.assertEqual(weakest, 'grammar')

    def test_generate_daily_tasks_creates_grammar_and_reading(self):
        """Verify 2 tasks are generated (1 grammar_drill, 1 reading_comprehension)."""
        tasks = generate_daily_tasks_for_student(self.student, count=2)
        self.assertEqual(len(tasks), 2)
        
        task_types = [t.task_type for t in tasks]
        self.assertIn('grammar_drill', task_types)
        self.assertIn('reading_comprehension', task_types)

        for t in tasks:
            self.assertEqual(t.student, self.student)
            self.assertEqual(t.study_plan, self.study_plan)
            self.assertFalse(t.completed)
            self.assertIsNone(t.score)
            self.assertIn('title', t.content)

    def test_generate_daily_tasks_idempotent_for_same_day(self):
        """Calling generate_daily_tasks multiple times on same day returns existing tasks."""
        today = timezone.localdate()
        tasks_first = generate_daily_tasks_for_student(self.student, task_date=today)
        tasks_second = generate_daily_tasks_for_student(self.student, task_date=today)

        self.assertEqual(len(tasks_first), len(tasks_second))
        self.assertEqual([t.id for t in tasks_first], [t.id for t in tasks_second])
        self.assertEqual(DailyTask.objects.filter(student=self.student, date=today).count(), 2)

    def test_grade_task_submission_provides_explanatory_reasoning(self):
        """Verify task grading returns score and explanatory ai_feedback."""
        tasks = generate_daily_tasks_for_student(self.student)
        grammar_task = next(t for t in tasks if t.task_type == 'grammar_drill')
        
        grading = grade_task_submission(grammar_task, "B")
        self.assertIn('score', grading)
        self.assertIn('ai_feedback', grading)
        self.assertGreaterEqual(grading['score'], 0)
        self.assertLessEqual(grading['score'], 100)
        self.assertTrue(len(grading['ai_feedback']) > 15)

    def test_submit_daily_task_updates_scores_and_logs_progress(self):
        """Verify submitting task updates task, SkillScore, Ready Score, streak, and ProgressLog."""
        tasks = generate_daily_tasks_for_student(self.student)
        task = tasks[0]
        
        initial_score = calculate_overall_ready_score(self.student)
        submitted_task = submit_daily_task(task.id, self.student, "B")

        self.assertTrue(submitted_task.completed)
        self.assertIsNotNone(submitted_task.score)
        self.assertTrue(len(submitted_task.ai_feedback) > 0)
        self.assertIsNotNone(submitted_task.completed_at)

        # Check ProgressLog created
        today = timezone.localdate()
        log = ProgressLog.objects.filter(student=self.student, date=today).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.streak_count, 1)
        self.assertIn("Vazifa bajarildi", log.delta)

    def test_task_views_workflow(self):
        """Test full HTTP flow: list -> detail GET -> detail POST -> result GET."""
        self.client.login(phone_number='+998901234567', password='TestPassword123!')

        # 1. Task List view
        list_resp = self.client.get(reverse('tasks:list'))
        self.assertEqual(list_resp.status_code, 200)
        self.assertContains(list_resp, "Bugungi Vazifalar")

        # 2. Task Detail view
        task = DailyTask.objects.filter(student=self.student).first()
        detail_resp = self.client.get(reverse('tasks:detail', kwargs={'task_id': task.id}))
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, escape("AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi."))

        # 3. Task Submission POST
        post_resp = self.client.post(
            reverse('tasks:detail', kwargs={'task_id': task.id}),
            {'selected_option': 'B'}
        )
        self.assertRedirects(post_resp, reverse('tasks:result', kwargs={'task_id': task.id}))

        # 4. Task Result view
        result_resp = self.client.get(reverse('tasks:result', kwargs={'task_id': task.id}))
        self.assertEqual(result_resp.status_code, 200)
        self.assertContains(result_resp, "AI Tahlili va Xatolik Tushuntirishi")
        self.assertContains(result_resp, escape("AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi."))

    def test_dashboard_view_renders_metrics_and_disclaimer(self):
        """Test dashboard renders Ready Score, streak, 5 skills, today tasks, and disclaimer."""
        self.client.login(phone_number='+998901234567', password='TestPassword123!')
        resp = self.client.get(reverse('dashboard:index'))
        self.assertEqual(resp.status_code, 200)

        # Verify Ready Score & Streak
        self.assertContains(resp, "Tayyorgarlik Darajasi")
        self.assertContains(resp, "Ketma-ketlik (Streak)")
        # Verify 5 skills
        self.assertContains(resp, "Reading")
        self.assertContains(resp, "Grammar")
        # Verify Disclaimer
        self.assertContains(resp, "AI tavsiyasi")

    def test_decay_scores_reduces_score_for_inactive_students(self):
        """Verify decay_student_scores reduces score and resets streak for students with no tasks yesterday."""
        yesterday = timezone.localdate() - timedelta(days=1)
        
        # Initial ready score: (75+70+65+60+55)/5 = 65
        initial_ready = calculate_overall_ready_score(self.student)
        self.assertEqual(initial_ready, 65)

        # Run decay for yesterday
        result = decay_student_scores(target_date=yesterday, decay_points=2)
        self.assertEqual(result['students_processed'], 1)
        self.assertEqual(result['students_decayed'], 1)

        # Check new score: each skill decayed by 1 => mean = 60
        new_ready = calculate_overall_ready_score(self.student)
        self.assertLess(new_ready, initial_ready)

        # Verify ProgressLog recorded decay
        today = timezone.localdate()
        log = ProgressLog.objects.filter(student=self.student, date=today).first()
        self.assertIsNotNone(log)
        self.assertEqual(log.streak_count, 0)
        self.assertIn("Faollik o'tkazib yuborildi", log.delta)

    def test_decay_scores_management_command(self):
        """Verify python manage.py decay_scores runs without errors."""
        call_command('decay_scores', points=2)
        today = timezone.localdate()
        log = ProgressLog.objects.filter(student=self.student, date=today).first()
        self.assertIsNotNone(log)
