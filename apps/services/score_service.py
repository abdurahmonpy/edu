"""
Score Service:
- Calculates overall Ready Score (0-100) from 5 SkillScores.
- Computes streak count based on consecutive days with completed tasks.
- Updates scores and creates ProgressLog entries upon task completion.
- Implements motivating score decay for students who missed tasks on the previous day.
"""
import logging
from datetime import date, timedelta
from typing import Dict, Any, Optional, List
from django.db import transaction
from django.utils import timezone
from apps.accounts.models import Student
from apps.dashboard.models import SkillScore, ProgressLog

logger = logging.getLogger(__name__)

ALL_SKILLS = ['reading', 'writing', 'listening', 'speaking', 'grammar']


def calculate_overall_ready_score(student: Student) -> int:
    """
    Calculates overall Ready Score (0-100) as the arithmetic mean of all 5 skill scores.
    """
    scores = student.skill_scores.all()
    if not scores.exists():
        return 0
    total = sum(s.current_score for s in scores)
    return max(0, min(100, round(total / len(scores))))


def get_student_streak(student: Student) -> int:
    """
    Calculates consecutive active days streak ending either today or yesterday.
    A day counts if the student completed at least 1 DailyTask on that date.
    """
    from apps.tasks.models import DailyTask
    today = timezone.localdate()
    
    # Get distinct dates of completed tasks in descending order
    completed_dates = set(
        DailyTask.objects.filter(student=student, completed=True)
        .values_list('date', flat=True)
        .distinct()
    )
    
    if not completed_dates:
        return 0

    streak = 0
    check_date = today

    # If nothing completed today, check if yesterday was completed
    if check_date not in completed_dates:
        check_date = today - timedelta(days=1)
        if check_date not in completed_dates:
            return 0

    while check_date in completed_dates:
        streak += 1
        check_date -= timedelta(days=1)

    return streak


@transaction.atomic
def record_task_completion_score(student: Student, task_type: str, task_score: int) -> Dict[str, Any]:
    """
    Updates relevant SkillScore adaptively, recalculates overall Ready Score,
    computes streak, and creates a ProgressLog entry.
    """
    # Map task type to skill
    skill_mapping = {
        'grammar_drill': 'grammar',
        'reading_comprehension': 'reading',
        'essay_writing': 'writing',
        'listening_exercise': 'listening',
        'speaking_exercise': 'speaking',
    }
    skill_name = skill_mapping.get(task_type, 'grammar')
    
    # 1. Update or create SkillScore for this skill
    skill_obj, _ = SkillScore.objects.get_or_create(
        student=student,
        skill=skill_name,
        defaults={'current_score': task_score}
    )
    
    # Adaptive score update: 80% weight on existing, 20% on new performance
    old_score = skill_obj.current_score
    updated_score = max(0, min(100, round(old_score * 0.8 + task_score * 0.2)))
    # If task score is higher than current, ensure positive progress
    if task_score > old_score and updated_score <= old_score:
        updated_score = min(100, old_score + 1)
    skill_obj.current_score = updated_score
    skill_obj.save(update_fields=['current_score', 'last_updated'])

    # 2. Recalculate overall Ready Score
    new_ready_score = calculate_overall_ready_score(student)
    
    # 3. Calculate current streak
    streak = get_student_streak(student)
    
    # 4. Create or update today's ProgressLog
    today = timezone.localdate()
    delta_msg = f"Vazifa bajarildi ({skill_name.capitalize()}: {task_score} ball)"
    
    progress_log, created = ProgressLog.objects.get_or_create(
        student=student,
        date=today,
        defaults={
            'overall_ready_score': new_ready_score,
            'streak_count': streak,
            'delta': delta_msg
        }
    )
    if not created:
        progress_log.overall_ready_score = new_ready_score
        progress_log.streak_count = streak
        progress_log.delta = delta_msg
        progress_log.save(update_fields=['overall_ready_score', 'streak_count', 'delta'])

    return {
        'skill': skill_name,
        'old_skill_score': old_score,
        'new_skill_score': updated_score,
        'overall_ready_score': new_ready_score,
        'streak_count': streak,
        'progress_log_id': progress_log.id
    }


@transaction.atomic
def decay_student_scores(target_date: Optional[date] = None, decay_points: int = 2) -> Dict[str, Any]:
    """
    Decays the Ready Score slightly for students who missed tasks on target_date (default: yesterday).
    Motivating decay: reduces score by 1-2 points (bounded at min 10), resets streak if inactive.
    """
    from apps.tasks.models import DailyTask
    today = timezone.localdate()
    if target_date is None:
        target_date = today - timedelta(days=1)

    students = Student.objects.filter(onboarding_completed=True).select_related('user')
    processed_count = 0
    decayed_count = 0
    decay_details = []

    for student in students:
        processed_count += 1
        
        # Check if student had any completed tasks on target_date
        completed_count = DailyTask.objects.filter(
            student=student,
            date=target_date,
            completed=True
        ).count()

        if completed_count == 0:
            # Student missed all tasks on target_date
            decayed_count += 1
            
            # 1. Decay each skill score slightly (e.g. -1 point, min 10)
            for skill_obj in student.skill_scores.all():
                if skill_obj.current_score > 10:
                    skill_obj.current_score = max(10, skill_obj.current_score - 1)
                    skill_obj.save(update_fields=['current_score', 'last_updated'])

            # 2. Recalculate overall Ready Score
            current_ready = calculate_overall_ready_score(student)
            
            # 3. Create or update ProgressLog for decay record
            delta_text = f"Faollik o'tkazib yuborildi (-{decay_points} ball)"
            progress_log, created = ProgressLog.objects.get_or_create(
                student=student,
                date=today,
                defaults={
                    'overall_ready_score': current_ready,
                    'streak_count': 0,
                    'delta': delta_text
                }
            )
            if not created:
                progress_log.overall_ready_score = current_ready
                progress_log.streak_count = 0
                progress_log.delta = delta_text
                progress_log.save(update_fields=['overall_ready_score', 'streak_count', 'delta'])

            decay_details.append({
                'student_id': student.id,
                'phone_number': student.user.phone_number,
                'new_ready_score': current_ready,
                'decayed': True
            })

    logger.info(
        f"Score decay completed for {target_date}: {processed_count} students checked, "
        f"{decayed_count} students decayed."
    )

    return {
        'target_date': str(target_date),
        'students_processed': processed_count,
        'students_decayed': decayed_count,
        'decay_points': decay_points,
        'details': decay_details
    }
