"""
Tier 3: Combinations & State Lifecycle Test Suite
Tests cross-feature interactions, streak progressions, decay recoveries, and study plan transitions.
"""
from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User, Student
from apps.tasks.models import DailyTask
from apps.dashboard.models import SkillScore, ProgressLog
from apps.study_plans.models import StudyPlan
from apps.services.task_service import generate_daily_tasks_for_student, submit_daily_task
from apps.services.score_service import get_student_streak, decay_student_scores, calculate_overall_ready_score
from apps.services.study_plan_service import generate_study_plan, get_active_study_plan
from apps.services.diagnostic_service import process_diagnostic_submission


class Tier3CombinationsTests(TestCase):
    """
    Combinatorial lifecycle and state transition tests.
    """
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='+998905554433',
            password='TestPassword123!',
            first_name='Shahzod'
        )
        self.student = self.user.student_profile
        self.student.grade = 11
        self.student.onboarding_completed = True
        self.student.save()

    def test_multi_day_streak_accumulation_and_decay_recovery(self):
        """
        Lifecycle Test:
        - Day -2: Complete task -> streak 1
        - Day -1: Complete task -> streak 2
        - Day 0 (today): Check streak is 2
        - Simulate missed day decay -> streak resets to 0
        - Complete task today -> streak becomes 1
        """
        today = timezone.localdate()
        day_minus_2 = today - timedelta(days=2)
        day_minus_1 = today - timedelta(days=1)

        # 1. Day -2 task completion
        t_day2 = DailyTask.objects.create(
            student=self.student,
            date=day_minus_2,
            task_type='grammar_drill',
            content={'question': 'Day 2 task', 'correct_option': 'A'},
            completed=True,
            score=85,
            completed_at=timezone.now() - timedelta(days=2)
        )

        # 2. Day -1 task completion
        t_day1 = DailyTask.objects.create(
            student=self.student,
            date=day_minus_1,
            task_type='reading_comprehension',
            content={'question': 'Day 1 task', 'correct_option': 'B'},
            completed=True,
            score=90,
            completed_at=timezone.now() - timedelta(days=1)
        )

        # Check streak before today's task
        streak_before = get_student_streak(self.student)
        self.assertEqual(streak_before, 2)

        # 3. Simulate decay for missed day (e.g. if day_minus_1 was not completed)
        # Delete day_minus_1 completed task to simulate miss
        t_day1.completed = False
        t_day1.save()

        decay_student_scores(target_date=day_minus_1, decay_points=2)
        streak_after_decay = get_student_streak(self.student)
        self.assertEqual(streak_after_decay, 0)

        # 4. Complete task today -> streak recovers to 1
        today_task = DailyTask.objects.create(
            student=self.student,
            date=today,
            task_type='grammar_drill',
            content={'question': 'Today task', 'correct_option': 'B'},
            completed=True,
            score=95,
            completed_at=timezone.now()
        )
        streak_recovered = get_student_streak(self.student)
        self.assertEqual(streak_recovered, 1)

    def test_study_plan_atomic_transition(self):
        """Generating a new study plan automatically deactivates previous active plans."""
        plan1 = generate_study_plan(self.student, goal="1-maqsad: Global UGRAD")
        self.assertTrue(plan1.active)
        self.assertEqual(get_active_study_plan(self.student), plan1)

        # Generate second plan
        plan2 = generate_study_plan(self.student, goal="2-maqsad: DAAD va Chevening")
        self.assertTrue(plan2.active)
        
        plan1.refresh_from_db()
        self.assertFalse(plan1.active)
        self.assertEqual(get_active_study_plan(self.student), plan2)
        self.assertEqual(StudyPlan.objects.filter(student=self.student, active=True).count(), 1)

    def test_diagnostic_retake_updates_existing_skill_scores(self):
        """Retaking diagnostic updates existing 5 SkillScores without integrity error."""
        answers1 = {'r1': 'A', 'g1': 'A'}
        process_diagnostic_submission(self.student, answers1)
        self.assertEqual(self.student.skill_scores.count(), 5)

        # Retake with better answers
        answers2 = {'r1': 'B', 'r2': 'C', 'g1': 'B', 'g2': 'C', 'writing_essay': 'High quality essay'}
        process_diagnostic_submission(self.student, answers2)
        self.assertEqual(self.student.skill_scores.count(), 5)
