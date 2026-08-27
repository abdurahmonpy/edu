from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone

from .models import MockExam, MockExamSection
from .services import create_mock_exam, evaluate_ielts_mock_exam


@login_required
def mock_exam_intro_view(request, exam_type='ielts'):
    """
    Pre-exam instructions screen showing exam rules, sections, and strict no-pause timer conditions.
    """
    student = getattr(request.user, 'student_profile', None)
    if not student:
        messages.warning(request, "Iltimos, avval profilingizni to'liq sozlang.")
        return redirect('onboarding:step_1')

    active_exam = MockExam.objects.filter(student=student, status='in_progress').first()
    past_exams = MockExam.objects.filter(student=student, status='completed').order_by('-completed_at')[:5]

    return render(request, 'mock_exams/intro.html', {
        'exam_type': exam_type,
        'active_exam': active_exam,
        'past_exams': past_exams,
    })


@login_required
@require_POST
def start_mock_exam_view(request, exam_type='ielts'):
    """
    Initializes a new Mock Exam session and redirects directly to Section 1 (Listening).
    """
    student = getattr(request.user, 'student_profile', None)
    if not student:
        return redirect('onboarding:step_1')

    exam = create_mock_exam(student, exam_type)
    first_section = exam.sections.order_by('order').first()

    if first_section:
        first_section.started_at = timezone.now()
        first_section.status = 'in_progress'
        first_section.save()
        return redirect('mock_exams:section', exam_id=exam.id, section_id=first_section.id)

    return redirect('mock_exams:intro')


@login_required
def mock_exam_section_view(request, exam_id, section_id):
    """
    Active section testing environment with live countdown timer and questions/passages.
    """
    student = getattr(request.user, 'student_profile', None)
    exam = get_object_or_404(MockExam, id=exam_id, student=student, status='in_progress')
    section = get_object_or_404(MockExamSection, id=section_id, mock_exam=exam)

    if not section.started_at:
        section.started_at = timezone.now()
        section.status = 'in_progress'
        section.save()

    # Calculate remaining time in seconds
    elapsed = (timezone.now() - section.started_at).total_seconds()
    remaining_seconds = max(0, int(section.time_limit_seconds - elapsed))

    all_sections = list(exam.sections.order_by('order'))
    current_index = all_sections.index(section) + 1

    return render(request, 'mock_exams/section.html', {
        'exam': exam,
        'section': section,
        'remaining_seconds': remaining_seconds,
        'current_index': current_index,
        'total_sections': len(all_sections),
        'hide_sidebar': True,
        'hide_header': True,
    })


@login_required
@require_POST
def submit_mock_section_view(request, exam_id, section_id):
    """
    Handles section submission and routes to next section or triggers final AI grading.
    """
    student = getattr(request.user, 'student_profile', None)
    exam = get_object_or_404(MockExam, id=exam_id, student=student, status='in_progress')
    section = get_object_or_404(MockExamSection, id=section_id, mock_exam=exam)

    # Collect answers from POST data
    responses = {}
    for key, val in request.POST.items():
        if key not in ['csrfmiddlewaretoken', 'auto_submitted']:
            responses[key] = val

    section.student_response = responses
    section.status = 'completed'
    section.ended_at = timezone.now()
    section.save()

    # Find next section in sequence
    next_section = exam.sections.filter(order__gt=section.order).order_by('order').first()

    if next_section:
        next_section.started_at = timezone.now()
        next_section.status = 'in_progress'
        next_section.save()
        messages.success(request, f"{section.get_section_type_display()} yakunlandi. Navbatdagi bo'lim boshlandi!")
        return redirect('mock_exams:section', exam_id=exam.id, section_id=next_section.id)
    else:
        # All sections completed! Trigger AI evaluation
        evaluate_ielts_mock_exam(exam)
        messages.success(request, "Tabriklaymiz! IELTS Mock imtihoni yakunlandi va AI tomonidan baholandi.")
        return redirect('mock_exams:results', exam_id=exam.id)


@login_required
def mock_exam_result_view(request, exam_id):
    """
    Displays full breakdown of Band Score, section analytics, and feedback.
    """
    student = getattr(request.user, 'student_profile', None)
    exam = get_object_or_404(MockExam, id=exam_id, student=student)

    sections = exam.sections.all().order_by('order')

    return render(request, 'mock_exams/results.html', {
        'exam': exam,
        'sections': sections,
    })
