from django.conf import settings

def trust_safety_context(request):
    """
    Injects student Ready Score and streak count for sidebar widgets.
    """
    context = {}
    if hasattr(request, 'user') and request.user.is_authenticated:
        student = getattr(request.user, 'student_profile', None)
        if student:
            context['overall_ready_score'] = student.overall_ready_score
            context['streak_count'] = student.streak_days
    return context


