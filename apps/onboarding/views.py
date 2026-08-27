"""
Views for onboarding wizard, diagnostic test administration, and results.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import OnboardingStep1Form
from apps.accounts.models import Student
from apps.services.diagnostic_service import (
    get_default_diagnostic_test,
    process_diagnostic_submission,
    SKILL_NAMES
)
from apps.services.study_plan_service import (
    generate_study_plan,
    get_active_study_plan
)


@login_required
def step_1_view(request):
    """
    Step 1: Student academic intake profile form.
    """
    student, _ = Student.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = OnboardingStep1Form(request.POST)
        if form.is_valid():
            form.save(student)
            messages.success(request, "Profil ma'lumotlaringiz saqlandi. Endi diagnostika testini topshiring.")
            return redirect('onboarding:diagnostic')
    else:
        initial_data = {}
        if student.grade:
            initial_data['grade'] = student.grade
        if student.target_countries:
            initial_data['target_countries'] = student.target_countries
        if student.target_program_type:
            initial_data['target_program_type'] = student.target_program_type
        if student.english_level:
            initial_data['english_level'] = student.english_level
        form = OnboardingStep1Form(initial=initial_data)

    return render(request, 'onboarding/step_1.html', {
        'form': form,
        'student': student
    })


@login_required
def diagnostic_view(request):
    """
    Step 2: Diagnostic test page and submission handler.
    """
    student, _ = Student.objects.get_or_create(user=request.user)
    test_data = get_default_diagnostic_test()

    if request.method == 'POST':
        # Extract reading answers
        reading_answers = {
            q['id']: request.POST.get(q['id'], '').strip()
            for q in test_data['reading']['questions']
            if request.POST.get(q['id'])
        }

        # Extract grammar answers
        grammar_answers = {
            q['id']: request.POST.get(q['id'], '').strip()
            for q in test_data['grammar']['questions']
            if request.POST.get(q['id'])
        }

        # Extract listening answers
        listening_answers = {
            q['id']: request.POST.get(q['id'], '').strip()
            for q in test_data['listening_simulation']['questions']
            if request.POST.get(q['id'])
        }

        # Extract writing and speaking responses
        writing_essay = request.POST.get('writing_essay', request.POST.get('writing_response', '')).strip()
        speaking_response = request.POST.get('speaking_response', '').strip()

        answers_payload = {
            'reading_answers': reading_answers,
            'grammar_answers': grammar_answers,
            'listening_answers': listening_answers,
            'writing_essay': writing_essay,
            'speaking_response': speaking_response,
        }
        # Also copy flat keys in case direct access is needed
        for k, v in request.POST.items():
            if k not in answers_payload:
                answers_payload[k] = v

        # Process diagnostic grading and save 5 SkillScores & 5 DiagnosticResults
        result_data = process_diagnostic_submission(student, answers_payload)

        # Generate personalized active AI study plan
        generate_study_plan(student, skill_scores=result_data.get('scores'))

        messages.success(request, "Diagnostika testi yakunlandi! Natijalaringiz va shaxsiy o'quv rejangiz bilan tanishing.")
        return redirect('onboarding:results')

    return render(request, 'onboarding/diagnostic.html', {
        'student': student,
        'test_data': test_data,
        'reading': test_data['reading'],
        'grammar': test_data['grammar'],
        'writing': test_data['writing'],
        'listening': test_data['listening_simulation'],
        'speaking': test_data['speaking_simulation'],
    })


@login_required
def results_view(request):
    """
    Step 3: Baseline 5-skill breakdown, active StudyPlan and dashboard unlock.
    """
    student, _ = Student.objects.get_or_create(user=request.user)

    skill_scores = list(student.skill_scores.all())
    active_plan = get_active_study_plan(student)
    latest_log = student.progress_logs.order_by('-date', '-created_at').first()
    diagnostic_results = list(student.diagnostic_results.all()[:5])

    ready_score = latest_log.overall_ready_score if latest_log else 0
    if not ready_score and skill_scores:
        ready_score = round(sum(s.current_score for s in skill_scores) / len(skill_scores))

    # Identify weakest skill
    weakest_skill = None
    if skill_scores:
        weakest_skill = min(skill_scores, key=lambda s: s.current_score)

    return render(request, 'onboarding/results.html', {
        'student': student,
        'skill_scores': skill_scores,
        'active_plan': active_plan,
        'ready_score': ready_score,
        'weakest_skill': weakest_skill,
        'diagnostic_results': diagnostic_results,
    })
