"""
Views for AI Mentor persistent chat interface.
"""
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages

from apps.accounts.models import Student
from apps.mentor.models import MentorMessage
from apps.services.mentor_service import send_mentor_message, get_conversation_history
from apps.services.score_service import calculate_overall_ready_score
from apps.services.study_plan_service import get_active_study_plan

from apps.services.task_service import get_student_weakest_skill
from apps.programs.models import StudentProgram

logger = logging.getLogger(__name__)


@login_required
def chat_view(request):
    """
    Main persistent AI Mentor chat interface.
    Handles message submissions with full context injection and safety guardrails.
    Includes student grade, tracked program, and weakest skill for context strip.
    """
    student = getattr(request.user, 'student_profile', None)
    if not student or not student.onboarding_completed:
        return redirect('onboarding:step_1')

    if request.method == 'POST':
        user_text = request.POST.get('message', '').strip()
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('format') == 'json'

        if not user_text:
            if is_ajax:
                return JsonResponse({'error': "Xabar matni bo'sh bo'lishi mumkin emas."}, status=400)
            messages.error(request, "Iltimos, xabaringizni yozing.")
            return redirect('mentor:chat')

        try:
            ai_message = send_mentor_message(student, user_text)

            if is_ajax:
                return JsonResponse({
                    'status': 'success',
                    'user_message': user_text,
                    'ai_message': ai_message.content,
                    'created_at': ai_message.created_at.strftime('%H:%M'),
                })
            return redirect('mentor:chat')
        except Exception as e:
            logger.error(f"Chat xabari yuborishda xatolik: {e}")
            if is_ajax:
                return JsonResponse({'error': f"Xatolik: {str(e)}"}, status=500)
            messages.error(request, "Xabarni yuborishda xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.")
            return redirect('mentor:chat')

    # GET request: load conversation history and context
    history = get_conversation_history(student, limit=100)
    ready_score = calculate_overall_ready_score(student)
    active_plan = get_active_study_plan(student)
    weakest_skill = get_student_weakest_skill(student)

    # Calculate context strip elements
    grade_display = f"{student.grade}-sinf" if (student and student.grade) else "9-sinf"
    
    tracked_sp = StudentProgram.objects.filter(student=student).select_related('program').first()
    if tracked_sp:
        program_display = tracked_sp.program.name
    elif student and student.target_countries:
        program_display = student.target_countries[0] if isinstance(student.target_countries, list) and student.target_countries else str(student.target_countries)
    elif active_plan and active_plan.target_program:
        program_display = active_plan.target_program
    elif student and student.target_program_type:
        program_display = student.get_target_program_type_display()
    else:
        program_display = "DAAD"

    skill_labels = {
        'reading': "O'qish",
        'writing': "Yozish (SOP)",
        'listening': "Tinglash",
        'speaking': "Gapirish",
        'grammar': "Grammatika",
    }
    skill_uz = skill_labels.get(weakest_skill, weakest_skill.capitalize() if weakest_skill else "Grammatika")
    weakest_skill_display = f"{skill_uz} — zaif"

    context_strip = {
        'grade_display': grade_display,
        'program_display': program_display,
        'weakest_skill_display': weakest_skill_display,
        'full_display': f"{grade_display} • {program_display} • {weakest_skill_display}",
        'display_text': f"{grade_display} • {program_display} • {weakest_skill_display}",
    }

    # Initial greeting if chat is fresh
    if not history:
        greeting_text = (
            f"Assalomu alaykum, {student.user.first_name or 'o\'quvchi'}! \n\n"
            f"Men sizning raqamli **Maktab va Karyera Maslahatchingiz (AI School Counselor)** man. "
            f"Siz uchun tuzilgan **'Mening Strategiyam'** xaritasidan kelib chiqib, {program_display} maqsadiga yetishimiz uchun kelgusi oylar davomida siz bilan birga ishlaymiz.\n\n"
            f"Quyidagilar bo'yicha menga istalgan vaqtda murojaat qilishingiz mumkin:\n"
            f"- Universitet yoki grantlar ro'yxatini yangilash\n"
            f"- Motivatsion insho (SOP) va rezyumelarni tahlil qilish\n"
            f"- Dedlaynlar va haftalik vazifalar bo'yicha maslahat\n\n"
            f"Bugun qaysi masalani muhokama qilamiz?"
        )
        ai_msg = MentorMessage.objects.create(
            student=student,
            role='ai',
            content=greeting_text
        )
        history = [ai_msg]

    context = {
        'student': student,
        'history': history,
        'ready_score': ready_score,
        'active_plan': active_plan,
        'weakest_skill': weakest_skill,
        'context_strip': context_strip,
    }
    return render(request, 'mentor/chat.html', context)



@login_required
def clear_chat_view(request):
    """
    Clears the student's chat history.
    """
    student = getattr(request.user, 'student_profile', None)
    if student:
        student.mentor_messages.all().delete()
        messages.success(request, "Suhbat tarixi muvaffaqiyatli tozalandi.")
    return redirect('mentor:chat')
