"""
Views for verified study abroad programs and scholarships catalog.
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from apps.accounts.models import Student
from .models import Program, StudentProgram

logger = logging.getLogger(__name__)


def program_list_view(request):
    """
    Displays the directory of admin-verified study abroad and scholarship programs.
    Always includes source_url and last_verified_date per R5 requirement.
    Attaches is_tracked boolean for authenticated students.
    """
    country_filter = request.GET.get('country', '').strip()
    type_filter = request.GET.get('type', '').strip()

    programs = Program.objects.all().order_by('name')

    if country_filter:
        programs = programs.filter(country__icontains=country_filter)
    if type_filter:
        programs = programs.filter(type=type_filter)

    # Distinct countries for filter pill badges
    available_countries = Program.objects.values_list('country', flat=True).distinct()

    # Tracked programs for the logged-in student
    tracked_program_ids = set()
    if request.user.is_authenticated:
        student = getattr(request.user, 'student_profile', None)
        if student:
            tracked_program_ids = set(
                StudentProgram.objects.filter(student=student).values_list('program_id', flat=True)
            )

    programs_list = list(programs)
    for p in programs_list:
        p.is_tracked = p.id in tracked_program_ids

    context = {
        'programs': programs_list,
        'total_count': len(programs_list),
        'available_countries': available_countries,
        'selected_country': country_filter,
        'selected_type': type_filter,
        'tracked_program_ids': tracked_program_ids,
    }
    return render(request, 'programs/program_list.html', context)


def program_detail_view(request, program_id):
    """
    Detailed profile for a single verified scholarship/exchange program.
    """
    program = get_object_or_404(Program, id=program_id)
    is_tracked = False
    if request.user.is_authenticated:
        student = getattr(request.user, 'student_profile', None)
        if student:
            is_tracked = StudentProgram.objects.filter(student=student, program=program).exists()

    context = {
        'program': program,
        'is_tracked': is_tracked,
    }
    return render(request, 'programs/program_detail.html', context)


@login_required
def toggle_track_program(request, program_id=None, pk=None):
    """
    Toggle tracking / bookmarking for a study abroad program.
    Supports both AJAX JSON responses and standard POST/GET form redirect fallback.
    """
    actual_id = program_id if program_id is not None else pk
    program = get_object_or_404(Program, id=actual_id)

    student = getattr(request.user, 'student_profile', None)
    if not student:
        try:
            student = request.user.student_profile
        except Exception:
            student, _ = Student.objects.get_or_create(user=request.user)

    tracked_obj = StudentProgram.objects.filter(student=student, program=program).first()
    if tracked_obj:
        tracked_obj.delete()
        is_tracked = False
    else:
        StudentProgram.objects.create(student=student, program=program)
        is_tracked = True

    tracked_count = StudentProgram.objects.filter(student=student).count()

    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or request.content_type == 'application/json'
        or request.headers.get('Accept') == 'application/json'
        or request.GET.get('format') == 'json'
        or request.POST.get('format') == 'json'
    )



    if is_ajax:
        return JsonResponse({
            'status': 'ok',
            'is_tracked': is_tracked,
            'tracked_count': tracked_count,
            'program_id': program.id,
            'program_name': program.name,
        })

    next_url = request.POST.get('next') or request.GET.get('next') or request.META.get('HTTP_REFERER') or 'programs:catalog'
    return redirect(next_url)

