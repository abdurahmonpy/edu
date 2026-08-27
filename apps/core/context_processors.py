from django.conf import settings

def trust_safety_context(request):
    """
    Injects global trust and safety metadata and disclaimer text into all templates,
    along with student Ready Score and streak count for sidebar widgets.
    """
    context = {
        'DISCLAIMER_TEXT': getattr(settings, 'DISCLAIMER_TEXT', "AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi."),
    }
    if hasattr(request, 'user') and request.user.is_authenticated:
        student = getattr(request.user, 'student_profile', None)
        if student:
            context['overall_ready_score'] = student.overall_ready_score
            context['streak_count'] = student.streak_days
    return context


