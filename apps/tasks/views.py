"""
Views for daily tasks listing, detailed exercise solving, and AI feedback results.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from apps.accounts.models import Student
from apps.tasks.models import DailyTask
from apps.services.task_service import generate_daily_tasks_for_student, submit_daily_task

logger = logging.getLogger(__name__)


from datetime import timedelta

@login_required
def task_list_view(request):
    """
    Lists tasks based on filter tab (?filter=today|week|completed):
    - today: today's practice exercises (default)
    - week: tasks within the current week (Monday-Sunday)
    - completed: historical completed tasks with inline ai_feedback
    """
    student = getattr(request.user, 'student_profile', None)
    if not student or not student.onboarding_completed:
        return redirect('onboarding:step_1')

    today = timezone.localdate()
    today_tasks = list(generate_daily_tasks_for_student(student, task_date=today, count=2))
    past_tasks = DailyTask.objects.filter(student=student).exclude(date=today).order_by('-date', '-id')[:20]

    completed_today = sum(1 for t in today_tasks if t.completed)

    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    filter_param = request.GET.get('filter', 'today').lower().strip()
    if filter_param not in ('today', 'week', 'completed'):
        filter_param = 'today'

    if filter_param == 'today':
        tasks = today_tasks
    elif filter_param == 'week':
        tasks = list(
            DailyTask.objects.filter(
                student=student,
                date__range=(start_of_week, end_of_week)
            ).order_by('-date', '-id')
        )
    elif filter_param == 'completed':
        tasks = list(
            DailyTask.objects.filter(
                student=student,
                completed=True
            ).order_by('-completed_at', '-date', '-id')
        )
    else:
        tasks = today_tasks

    # Counts for tab badges
    count_today = len(today_tasks)
    count_week = DailyTask.objects.filter(student=student, date__range=(start_of_week, end_of_week)).count()
    count_completed = DailyTask.objects.filter(student=student, completed=True).count()

    context = {
        'student': student,
        'active_filter': filter_param,
        'tasks': tasks,
        'today_tasks': today_tasks,
        'past_tasks': past_tasks,
        'today_date': today,
        'completed_today': completed_today,
        'total_today': len(today_tasks),
        'count_today': count_today,
        'count_week': count_week,
        'count_completed': count_completed,
    }
    return render(request, 'tasks/task_list.html', context)



@login_required
def task_detail_view(request, task_id):
    """
    Presents the interactive task interface (Grammar Drill or Reading Comprehension).
    Accepts student answer and initiates Claude grading.
    """
    student = getattr(request.user, 'student_profile', None)
    if not student or not student.onboarding_completed:
        return redirect('onboarding:step_1')

    task = get_object_or_404(DailyTask, id=task_id, student=student)

    # If task is already completed, redirect directly to result view
    if task.completed:
        return redirect('tasks:result', task_id=task.id)

    if request.method == 'POST':
        student_answer = request.POST.get('student_answer', '').strip()
        selected_option = request.POST.get('selected_option', '').strip()

        # If a multiple-choice option was chosen, use that
        final_answer = selected_option if selected_option else student_answer

        if not final_answer:
            messages.error(request, "Iltimos, topshiriq javobini tanlang yoki yozing.")
            return render(request, 'tasks/task_detail.html', {'task': task, 'student': student})

        try:
            submit_daily_task(task.id, student, final_answer)
            messages.success(request, "Vazifangiz AI tomonidan muvaffaqiyatli tekshirildi!")
            return redirect('tasks:result', task_id=task.id)
        except Exception as e:
            logger.error(f"Vazifani topshirishda xatolik: {e}")
            messages.error(request, f"Vazifani tekshirishda xatolik yuz berdi: {e}")

    return render(request, 'tasks/task_detail.html', {'task': task, 'student': student})


@login_required
def task_result_view(request, task_id):
    """
    Displays the score, student submission, and detailed AI explanatory feedback.
    """
    student = getattr(request.user, 'student_profile', None)
    if not student or not student.onboarding_completed:
        return redirect('onboarding:step_1')

    task = get_object_or_404(DailyTask, id=task_id, student=student)

    if not task.completed:
        return redirect('tasks:detail', task_id=task.id)

    # Check if there is a next pending task today
    today = timezone.localdate()
    next_task = DailyTask.objects.filter(
        student=student,
        date=today,
        completed=False
    ).exclude(id=task.id).first()

    context = {
        'student': student,
        'task': task,
        'content': task.content or {},
        'next_task': next_task,
    }
    return render(request, 'tasks/task_result.html', context)
