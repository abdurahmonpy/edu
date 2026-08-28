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


@login_required
def exam_prep_view(request):
    """
    Dedicated Exam Prep (IELTS / SAT / CEFR) section:
    - Today's Track A daily drills (grammar, reading, listening, speaking, writing, vocabulary)
    - Per-skill breakdown dashboard (0-100 scores for 5 skills)
    - CTA for full Mock Exam Simulator
    - Scoped IELTS & Language Resource Library (Reading, Writing, Listening, Speaking, Grammar)
    """
    student = getattr(request.user, 'student_profile', None)
    if not student or not student.onboarding_completed:
        return redirect('onboarding:step_1')

    today = timezone.localdate()
    # Ensure today's tasks exist
    generate_daily_tasks_for_student(student, task_date=today, count=2)

    # 1. Track A Tasks
    tab = request.GET.get('tab', 'today').lower().strip()
    if tab == 'completed':
        exam_tasks = DailyTask.objects.filter(student=student, track='track_a', completed=True).order_by('-completed_at', '-date')
    elif tab == 'all':
        exam_tasks = DailyTask.objects.filter(student=student, track='track_a').order_by('-date')
    else:
        exam_tasks = DailyTask.objects.filter(student=student, track='track_a', date=today).order_by('completed', '-id')

    # Counts
    today_count = DailyTask.objects.filter(student=student, track='track_a', date=today).count()
    completed_today_count = DailyTask.objects.filter(student=student, track='track_a', date=today, completed=True).count()
    total_completed_count = DailyTask.objects.filter(student=student, track='track_a', completed=True).count()

    # 2. 5 Skill Scores
    from apps.dashboard.models import SkillScore
    from apps.services.score_service import calculate_overall_ready_score
    skills_map = {s.skill: s.current_score for s in student.skill_scores.all()}
    skill_items = [
        {'key': 'reading', 'label': "Reading (O'qish)", 'score': skills_map.get('reading', 50), 'icon': 'book-open', 'color': 'emerald'},
        {'key': 'listening', 'label': "Listening (Eshitish)", 'score': skills_map.get('listening', 50), 'icon': 'headphones', 'color': 'indigo'},
        {'key': 'writing', 'label': "Writing (Yozish)", 'score': skills_map.get('writing', 50), 'icon': 'pen-tool', 'color': 'amber'},
        {'key': 'speaking', 'label': "Speaking (Gapirish)", 'score': skills_map.get('speaking', 50), 'icon': 'mic', 'color': 'violet'},
        {'key': 'grammar', 'label': "Grammar & Vocab", 'score': skills_map.get('grammar', 50), 'icon': 'spell-check', 'color': 'rose'},
    ]
    ready_score = calculate_overall_ready_score(student)

    # 3. IELTS Specific Resource Library
    from apps.resources.models import Resource
    ielts_categories = ['ielts_reading', 'ielts_writing', 'ielts_listening', 'ielts_speaking', 'grammar_vocab']
    selected_category = request.GET.get('category', '').strip()
    
    resource_qs = Resource.objects.filter(category__in=ielts_categories)
    if selected_category and selected_category in ielts_categories:
        resource_qs = resource_qs.filter(category=selected_category)
    
    ielts_resources = resource_qs.order_by('-created_at')

    context = {
        'student': student,
        'tab': tab,
        'exam_tasks': exam_tasks,
        'today_count': today_count,
        'completed_today_count': completed_today_count,
        'total_completed_count': total_completed_count,
        'skill_items': skill_items,
        'ready_score': ready_score,
        'ielts_resources': ielts_resources,
        'selected_category': selected_category,
        'ielts_category_choices': [
            ('ielts_reading', "Reading"),
            ('ielts_writing', "Writing"),
            ('ielts_listening', "Listening"),
            ('ielts_speaking', "Speaking"),
            ('grammar_vocab', "Grammatika"),
        ],
    }
    return render(request, 'tasks/exam_prep.html', context)


@login_required
def application_prep_view(request):
    """
    Dedicated University & Scholarship Application Prep (Track B) section:
    - Today's Track B daily tasks (essay milestones, LOR, document prep, extracurricular)
    - Active application statuses (StudentProgram)
    - Linked documents
    """
    student = getattr(request.user, 'student_profile', None)
    if not student or not student.onboarding_completed:
        return redirect('onboarding:step_1')

    today = timezone.localdate()
    # Ensure today's tasks exist
    generate_daily_tasks_for_student(student, task_date=today, count=2)

    tab = request.GET.get('tab', 'today').lower().strip()
    if tab == 'completed':
        app_tasks = DailyTask.objects.filter(student=student, track='track_b', completed=True).order_by('-completed_at', '-date')
    elif tab == 'all':
        app_tasks = DailyTask.objects.filter(student=student, track='track_b').order_by('-date')
    else:
        app_tasks = DailyTask.objects.filter(student=student, track='track_b', date=today).order_by('completed', '-id')

    # Applications summary
    from apps.programs.models import StudentProgram
    tracked_programs = StudentProgram.objects.filter(student=student).select_related('program')

    # Documents summary
    from apps.documents.models import Document
    documents = Document.objects.filter(student=student).order_by('-updated_at')[:4]

    # Application Guides
    from apps.resources.models import Resource
    app_guides = Resource.objects.filter(category__in=['essay_writing', 'interview_prep', 'visa_process', 'general_tips'])[:4]

    context = {
        'student': student,
        'tab': tab,
        'app_tasks': app_tasks,
        'tracked_programs': tracked_programs,
        'documents': documents,
        'app_guides': app_guides,
    }
    return render(request, 'tasks/application_prep.html', context)
from django.http import JsonResponse
from apps.tasks.models import SpeakingSession
from apps.services.speaking_service import get_random_part2_prompt, transcribe_audio, evaluate_speaking

@login_required
def speaking_start_view(request):
    "View to start a new speaking practice session (Part 2)."
    student = getattr(request.user, 'student_profile', None)
    if not student:
        return redirect('onboarding:step_1')
        
    if request.method == 'POST':
        prompt = get_random_part2_prompt()
        session = SpeakingSession.objects.create(
            student=student,
            part='part2_cue_card',
            prompt_text=prompt,
            prep_time_seconds=60,
            speak_time_seconds=120
        )
        return redirect('tasks:speaking_record', session_id=session.id)
        
    return render(request, 'tasks/speaking_start.html')

@login_required
def speaking_record_view(request, session_id):
    "View to record audio for the speaking session."
    session = get_object_or_404(SpeakingSession, id=session_id, student__user=request.user)
    
    if session.transcript or session.ai_feedback:
        return redirect('tasks:speaking_result', session_id=session.id)
        
    return render(request, 'tasks/speaking_record.html', {'session': session})

@login_required
def speaking_submit_view(request, session_id):
    """AJAX endpoint to receive audio, transcribe, evaluate, and save."""
    if request.method != 'POST':
        return JsonResponse({'error': "Faqat POST so'rovlar qabul qilinadi."}, status=405)
        
    try:
        session = get_object_or_404(SpeakingSession, id=session_id, student__user=request.user)
        audio_file = request.FILES.get('audio')
        
        if not audio_file:
            return JsonResponse({'error': 'Audio fayl topilmadi.'}, status=400)
            
        session.audio_file = audio_file
        session.save()
        
        # Process audio
        transcript = transcribe_audio(session.audio_file)
        session.transcript = transcript
        session.save()
        
        band_score, ai_feedback = evaluate_speaking(transcript, session.prompt_text, session.speak_time_seconds)
        
        session.band_score = band_score
        session.ai_feedback = ai_feedback
        session.save()
        
        return JsonResponse({'success': True, 'redirect_url': f"/tasks/speaking/result/{session.id}/"})
    except Exception as e:
        logger.error(f"Error processing speaking submission: {e}")
        return JsonResponse({'error': f"Xatolik yuz berdi: {str(e)}"}, status=500)

@login_required
def speaking_result_view(request, session_id):
    "View to display the speaking evaluation results."
    session = get_object_or_404(SpeakingSession, id=session_id, student__user=request.user)
    return render(request, 'tasks/speaking_result.html', {'session': session})
