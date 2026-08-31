import logging
from celery import shared_task
from apps.tasks.models import DailyTask
from apps.accounts.models import Student
from apps.services.task_service import grade_task_submission, record_task_completion_score
from django.utils import timezone

logger = logging.getLogger(__name__)

@shared_task
def async_grade_daily_task(task_id, student_id, student_answer):
    try:
        task = DailyTask.objects.get(id=task_id)
        student = Student.objects.get(id=student_id)
        grading = grade_task_submission(task, student_answer)
        task.completed = True
        task.score = grading['score']
        task.student_answer = student_answer
        task.ai_feedback = grading['ai_feedback']
        task.completed_at = timezone.now()
        task.save()
        record_task_completion_score(student, task.task_type, task.score)
        logger.info(f'Async grading completed for task {task_id}')
    except Exception as e:
        logger.error(f'Error grading task {task_id}: {e}')
