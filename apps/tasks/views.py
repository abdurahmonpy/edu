"""
Views for daily tasks listing, detailed exercise solving, and AI feedback results.
Supports Dual-Track filtering (Track A: Exam Prep, Track B: Admissions & Documents).
"""
import logging
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from apps.accounts.models import Student
from apps.tasks.models import DailyTask
from apps.services.task_service import generate_daily_tasks_for_student, submit_daily_task

logger = logging.getLogger(__name__)


@login_required
def task_list_view(request):
    """
    Lists tasks based on time filter (?filter=today|week|completed|all)
    and Dual-Track filter (?track=all|track_a|track_b):
    - today: today's practice exercises (default)
    - week: tasks within the current week (Monday-Sunday)
    - completed: historical completed tasks with inline ai_feedback
    - all: all recorded tasks
    - track: all / track_a (Imtihon tayyorgarligi) / track_b (Universitet arizasi va Hujjatlar)
    """
    student = getattr(request.user, 'student_profile', None)
    if not student or not student.onboarding_completed:
        return redirect('onboarding:step_1')

    today = timezone.localdate()
    # Ensure today's dual-track tasks are generated
    today_tasks = list(generate_daily_tasks_for_student(student, task_date=today, count=2))

    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    # 1. Parse time filter parameter
    filter_param = request.GET.get('filter', 'today').lower().strip()
    if filter_param not in ('today', 'week', 'completed', 'all'):
        filter_param = 'today'

    # 2. Parse track filter parameter
    track_param = request.GET.get('track', 'all').lower().strip()
    if track_param not in ('all', 'track_a', 'track_b'):
        track_param = 'all'

    # 3. Base queryset for time filter
    if filter_param == 'today':
        base_qs = DailyTask.objects.filter(student=student, date=today)
    elif filter_param == 'week':
        base_qs = DailyTask.objects.filter(student=student, date__range=(start_of_week, end_of_week))
    elif filter_param == 'completed':
        base_qs = DailyTask.objects.filter(student=student, completed=True)
    elif filter_param == 'all':
        base_qs = DailyTask.objects.filter(student=student)
    else:
        base_qs = DailyTask.objects.filter(student=student, date=today)

    # Track counts within the active time filter
    count_all = base_qs.count()
    count_track_a = base_qs.filter(track='track_a').count()
    count_track_b = base_qs.filter(track='track_b').count()

    # 4. Apply track filtering
    if track_param == 'track_a':
        filtered_qs = base_qs.filter(track='track_a')
    elif track_param == 'track_b':
        filtered_qs = base_qs.filter(track='track_b')
    else:
        filtered_qs = base_qs

    # Order tasks appropriately
    if filter_param == 'completed':
        tasks = list(filtered_qs.order_by('-completed_at', '-date', '-id'))
    else:
        tasks = list(filtered_qs.order_by('-date', '-id'))

    # Global time counts for tabs
    count_today = DailyTask.objects.filter(student=student, date=today).count()
    count_week = DailyTask.objects.filter(student=student, date__range=(start_of_week, end_of_week)).count()
    count_completed = DailyTask.objects.filter(student=student, completed=True).count()
    completed_today = DailyTask.objects.filter(student=student, date=today, completed=True).count()

    context = {
        'student': student,
        'active_filter': filter_param,
        'active_track': track_param,
        'tasks': tasks,
        'today_tasks': today_tasks,
        'today_date': today,
        'completed_today': completed_today,
        'total_today': count_today,
        'count_today': count_today,
        'count_week': count_week,
        'count_completed': count_completed,
        'count_all': count_all,
        'count_track_a': count_track_a,
        'count_track_b': count_track_b,
    }
    return render(request, 'tasks/task_list.html', context)


@login_required
def task_detail_view(request, task_id):
    """
    Presents the interactive task interface for Track A (Grammar/Reading drills)
    or Track B (SOP/Essay milestones, Extracurricular reflection, LOR requests).
    Accepts student answer and initiates Claude/heuristic grading.
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

        # If a multiple-choice option was chosen, use that; otherwise use written answer
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

    return render(request, 'tasks/task_detail.html', {
        'task': task,
        'student': student,
        'content': task.content or {},
    })


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
