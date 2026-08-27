"""
Tier 2: Boundary & Corner Cases Test Suite
Tests input boundaries, score clamping, validation limits, and error handling.
"""
from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts.models import User, Student
from apps.accounts.utils import normalize_uzbek_phone, is_valid_uzbek_phone
from apps.tasks.models import DailyTask
from apps.dashboard.models import SkillScore, ProgressLog
from apps.programs.models import Program
from apps.services.diagnostic_service import evaluate_diagnostic_heuristic
from apps.services.score_service import calculate_overall_ready_score, decay_student_scores
from apps.services.task_service import grade_task_submission


class Tier2BoundaryTests(TestCase):
    """
    Boundary and edge condition tests.
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            phone_number='+998909998877',
            password='TestPassword123!',
            first_name='Bobur'
        )
        self.student = self.user.student_profile

    def test_phone_normalization_and_validation_boundaries(self):
        """Test varied phone format inputs and rejection of invalid formats."""
        # Valid variants that must normalize to +998901234567
        valid_variants = [
            '+998901234567',
            '998901234567',
            '901234567',
            '+998 90 123 45 67',
            '+998-90-123-45-67',
            ' (90) 123-45-67 ',
        ]
        for phone in valid_variants:
            normalized = normalize_uzbek_phone(phone)
            self.assertEqual(normalized, '+998901234567', f"Failed for {phone}")
            self.assertTrue(is_valid_uzbek_phone(normalized))

        # Invalid phone numbers
        invalid_variants = [
            '',
            '12345',
            '+12345678901',
            '+79161234567',
            'not-a-phone',
            '+9989012345678',  # 10 digits
            '+99890123456',    # 8 digits
        ]
        for phone in invalid_variants:
            with self.assertRaises((ValidationError, ValueError)):
                normalize_uzbek_phone(phone)

    def test_score_clamping_boundaries(self):
        """Verify scores never exceed 100 or fall below 0."""
        # Lower bound
        score_low = SkillScore(student=self.student, skill='reading', current_score=-10)
        with self.assertRaises(ValidationError):
            score_low.full_clean()

        # Upper bound
        score_high = SkillScore(student=self.student, skill='reading', current_score=150)
        with self.assertRaises(ValidationError):
            score_high.full_clean()

        # Clamping in calculate_overall_ready_score
        SkillScore.objects.create(student=self.student, skill='reading', current_score=0)
        SkillScore.objects.create(student=self.student, skill='grammar', current_score=100)
        ready = calculate_overall_ready_score(self.student)
        self.assertEqual(ready, 50)
        self.assertTrue(0 <= ready <= 100)

    def test_diagnostic_empty_and_extreme_inputs(self):
        """Diagnostic heuristic evaluator safely handles empty or extreme responses."""
        # Empty answers
        empty_res = evaluate_diagnostic_heuristic(self.student, {})
        self.assertIn('scores', empty_res)
        for s, score in empty_res['scores'].items():
            self.assertTrue(0 <= score <= 100)

        # Huge text submission
        huge_text = "I want to study abroad. " * 500
        huge_res = evaluate_diagnostic_heuristic(self.student, {'writing_essay': huge_text})
        self.assertTrue(0 <= huge_res['scores']['writing'] <= 100)

    def test_task_grading_unexpected_inputs(self):
        """Task grading handles unexpected or empty answers safely."""
        task = DailyTask.objects.create(
            student=self.student,
            task_type='grammar_drill',
            content={'question': 'Choose option', 'correct_option': 'B', 'explanation': 'Rule explanation'}
        )
        # Empty string answer
        res_empty = grade_task_submission(task, "")
        self.assertTrue(res_empty['completed'])
        self.assertTrue(0 <= res_empty['score'] <= 100)
        self.assertGreater(len(res_empty['ai_feedback']), 10)

        # Non-matching gibberish
        res_gibberish = grade_task_submission(task, "zzzzzz random words 12345")
        self.assertTrue(0 <= res_gibberish['score'] <= 100)
        self.assertGreater(len(res_gibberish['ai_feedback']), 10)

    def test_decay_bounds_at_minimum_score(self):
        """Score decay never decays below minimum floor (10)."""
        self.student.onboarding_completed = True
        self.student.save()
        for skill in ['reading', 'writing', 'listening', 'speaking', 'grammar']:
            SkillScore.objects.create(student=self.student, skill=skill, current_score=10)

        yesterday = timezone.localdate() - timedelta(days=1)
        decay_student_scores(target_date=yesterday, decay_points=5)

        for s in self.student.skill_scores.all():
            self.assertGreaterEqual(s.current_score, 10)
