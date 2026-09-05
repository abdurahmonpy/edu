"""
Core views: Landing page and public index.
"""
from django.shortcuts import render, redirect
from apps.programs.models import Program


def landing_page_view(request):
    """
    Public landing page for Kelajak study abroad platform.
    If the user is already authenticated and has completed onboarding, redirect to dashboard.
    """
    if request.user.is_authenticated:
        student = getattr(request.user, 'student_profile', None)
        if student and student.onboarding_completed:
            return redirect('dashboard:index')

    # Fetch verified programs to display on landing page
    programs = Program.objects.all()[:6]

    return render(request, 'landing.html', {
        'programs': programs,
        'hide_sidebar': True,
    })
