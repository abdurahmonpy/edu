"""
Mentor Service:
- Persistent AI Mentor chat for 9th-11th grade Uzbek students.
- Dynamically injects complete student context:
  1. Student profile (grade, target countries, target program type, English level)
  2. All 5 SkillScores (reading, writing, listening, speaking, grammar) and Ready Score
  3. Active StudyPlan summary and milestones
  4. Recent DailyTask history (types, scores, AI feedback)
  5. Admin-verified Program records from database
- Enforces strict Trust & Safety guardrails:
  - Never guarantee or imply guaranteed admission outcome
  - Frame all suggestions as guidance, not promises
  - Defer final decisions to student and family: "AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi."
  - Unverified program fallback phrase: "Men bu haqda tasdiqlangan ma'lumotga ega emasman"
"""
import logging
from typing import List, Dict, Any, Optional
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Student
from apps.mentor.models import MentorMessage
from apps.programs.models import Program
from apps.services.anthropic_client import call_claude
from apps.services.score_service import calculate_overall_ready_score
from apps.services.study_plan_service import get_active_study_plan, format_study_plan_summary

logger = logging.getLogger(__name__)

UNVERIFIED_PROGRAM_FALLBACK = "Men bu haqda tasdiqlangan ma'lumotga ega emasman"
MANDATORY_DISCLAIMER = "AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi."


def get_verified_programs_context() -> str:
    """
    Retrieves all verified Program records and formats them as a clean text reference for the AI Mentor.
    """
    programs = Program.objects.all().order_by('name')
    if not programs.exists():
        return "Hozircha bazada tasdiqlangan dasturlar mavjud emas."

    lines = []
    for p in programs:
        req_str = ", ".join(f"{k}: {v}" for k, v in p.requirements.items()) if isinstance(p.requirements, dict) else str(p.requirements)
        lines.append(
            f"- Dastur: {p.name} ({p.country})\n"
            f"  Turi: {p.get_type_display()}\n"
            f"  Topshirish muddati: {p.deadline or 'Belgilanmagan'}\n"
            f"  Talablar: {req_str}\n"
            f"  Rasmiy manba: {p.source_url}\n"
            f"  Oxirgi tekshirilgan sana: {p.last_verified_date}\n"
        )
    return "\n".join(lines)


def get_recent_tasks_context(student: Student, limit: int = 5) -> str:
    """
    Formats the student's recent daily task history for system prompt injection.
    """
    tasks = student.daily_tasks.filter(completed=True).order_by('-date', '-completed_at')[:limit]
    if not tasks.exists():
        return "Hozircha bajarilgan kunlik vazifalar mavjud emas."

    lines = []
    for t in tasks:
        title = t.content.get('title', t.get_task_type_display()) if isinstance(t.content, dict) else t.get_task_type_display()
        lines.append(
            f"- {t.date} | {title} ({t.get_task_type_display()}): {t.score} ball. "
            f"AI tahlili: {t.ai_feedback[:120]}..."
        )
    return "\n".join(lines)


def build_mentor_system_prompt(student: Student) -> str:
    """
    Constructs the comprehensive system prompt with complete context injection.
    """
    # 1. Profile & Scores
    ready_score = calculate_overall_ready_score(student)
    skills = {s.skill: s.current_score for s in student.skill_scores.all()}
    skills_summary = (
        f"Reading: {skills.get('reading', 50)}/100, "
        f"Writing: {skills.get('writing', 50)}/100, "
        f"Listening: {skills.get('listening', 50)}/100, "
        f"Speaking: {skills.get('speaking', 50)}/100, "
        f"Grammar: {skills.get('grammar', 50)}/100 | "
        f"Overall Ready Score: {ready_score}/100"
    )

    target_countries = ", ".join(student.target_countries) if student.target_countries else "Belgilanmagan"
    program_type = student.get_target_program_type_display() if hasattr(student, 'get_target_program_type_display') else student.target_program_type
    english_level = student.get_english_level_display() if hasattr(student, 'get_english_level_display') else student.english_level

    # 2. Active Plan
    active_plan = get_active_study_plan(student)
    plan_summary = format_study_plan_summary(active_plan)

    # 3. Tasks History
    tasks_history = get_recent_tasks_context(student)

    # 4. Verified Programs
    verified_programs = get_verified_programs_context()

    # 5. Tracked Programs and Application Statuses
    from apps.programs.models import StudentProgram
    tracked_apps = StudentProgram.objects.filter(student=student).select_related('program')
    if tracked_apps.exists():
        app_status_lines = []
        for app in tracked_apps:
            sub_date = f", Topshirilgan sana: {app.submitted_at}" if app.submitted_at else ""
            dec_date = f", Qaror sanasi: {app.decision_at}" if app.decision_at else ""
            notes_str = f" (Izoh: {app.notes})" if app.notes else ""
            app_status_lines.append(f"- {app.program.name}: Holati = «{app.get_status_display()}»{sub_date}{dec_date}{notes_str}")
        tracked_apps_context = "\n".join(app_status_lines)
    else:
        tracked_apps_context = "O'quvchi hali aniq dasturlar bo'yicha ariza holatini kiritmagan."

    # 6. Verified Resource Guides (Grouped by Track)
    from apps.resources.models import Resource
    ielts_res = Resource.objects.filter(category__in=['ielts_reading', 'ielts_writing', 'ielts_listening', 'ielts_speaking', 'grammar_vocab'])
    ielts_titles = ", ".join([f"«{r.title}»" for r in ielts_res[:4]]) or "IELTS Reading, Writing, Listening va Grammatika qo'llanmalari"

    app_res = Resource.objects.filter(category__in=['essay_writing', 'interview_prep', 'visa_process', 'general_tips'])
    app_titles = ", ".join([f"«{r.title}»" for r in app_res[:4]]) or "Insho yozish, intervyu, viza va extracurricular bo'yicha qo'llanmalar"

    system_prompt = f"""Sen O'zbekistondagi 9-11 sinf maktab o'quvchilari uchun xalqaro universitetlar va grant dasturlariga (Global UGRAD, DAAD, Chevening, Türkiye Bursları, El-Yurt Umidi va boshqalar) tayyorlovchi **AI School Counselor (Maktab va Karyera Maslahatchisi)** san.
Sening maqsading o'quvchining qobiliyatlari va baholaridan kelib chiqib unga to'g'ri strategiya tuzib berish, motivatsiya berish va xatolarini to'g'irlashdir.

O'quvchining joriy profili va to'liq konteksti:
- Sinf: {student.grade or 10}-sinf
- Maqsad qilingan davlatlar: {target_countries}
- Dastur turi: {program_type}
- Ingliz tili darajasi: {english_level}
- Ko'nikma ballari: {skills_summary}

O'quvchining Kuzatayotgan Dasturlari va Ariza Topshirish Holatlari:
{tracked_apps_context}

Faol O'quv Rejasi (Mening Strategiyam):
{plan_summary}

So'nggi Bajarilgan Vazifalar:
{tasks_history}

Bazada Tasdiqlangan Rasmiy Dasturlar:
{verified_programs}

Platformadagi Tasdiqlangan Qo'llanmalar (Resurslar):
- Imtihon Tayyorgarligi (IELTS / Til): {ielts_titles} (IELTS yoki til o'rganish bo'yicha savollarda ushbu qo'llanmalarni tavsiya qiling).
- Universitet Arizasi va Hujjatlar: {app_titles} (Insho, intervyu, tavsiyanoma yoki viza haqida so'raganda ushbu resurslarni tavsiya qiling).

MUHIM QOIDALAR (AI Counselor sifatida):
1. **Universitet va Grantlarga yo'naltirish:** Agar o'quvchi "qayerga topshirsam bo'ladi?" desa, uning reytingi (Overall Ready Score) va qiziqishlariga mos keluvchi bazadagi dasturlarni taklif qil.
2. **Motivatsion insho va Rezyumelar:** O'quvchiga inshosining mavzusini topishga yordam ber, uni o'qib xatolarini to'g'irla. 
3. **Realistik kutishlar:** Hech qachon 100% qabul kafolatini bermang. Faqatgina imkoniyatni oshirish usullarini o'rgating. "Reach", "Match", "Safety" konseptlarini tushuntiring.
4. **Tasdiqlanmagan dasturlar:** Agar o'quvchi bazamizda (Tasdiqlangan Dasturlar) bo'lmagan dastur haqida so'rasa, to'qib chiqarmang va: "{UNVERIFIED_PROGRAM_FALLBACK}" deng.
5. Barcha javoblaringizni o'zbek tilida (lotin alifbosi), o'ta muloyim, rag'batlantiruvchi va amaliy maslahatlar bilan yozing.
"""
    return system_prompt


def send_mentor_message(student: Student, user_text: str) -> MentorMessage:
    """
    Saves student message, calls Claude API with injected context, and saves/returns AI message.
    """
    # 1. Save student message
    student_msg = MentorMessage.objects.create(
        student=student,
        role='student',
        content=user_text.strip()
    )

    # 2. Build system prompt with complete context injection
    system_prompt = build_mentor_system_prompt(student)

    # 3. Retrieve recent message history (last 8 messages)
    recent_msgs = list(
        MentorMessage.objects.filter(student=student)
        .order_by('-created_at')[:8]
    )
    recent_msgs.reverse()

    history_text = "\n".join([f"{'Oquvchi' if m.role == 'student' else 'AI Mentor'}: {m.content}" for m in recent_msgs])
    combined_user_prompt = f"Suhbat tarixi:\n{history_text}\n\nO'quvchining oxirgi savoli:\n{user_text}"

    # 4. Call Claude API
    try:
        ai_reply_text = call_claude(
            system_prompt=system_prompt,
            user_prompt=combined_user_prompt,
            response_format='text',
            max_tokens=1500
        )
    except Exception as e:
        logger.error(f"AI Mentor chat Claude API error: {e}")
        ai_reply_text = (
            f"Assalomu alaykum! Savolingiz uchun rahmat. "
            f"Hozirda tizimimiz profilingizni tahlil qilmoqda. "
            f"{MANDATORY_DISCLAIMER}"
        )

    # 5. Save AI response
    ai_msg = MentorMessage.objects.create(
        student=student,
        role='ai',
        content=ai_reply_text.strip()
    )

    return ai_msg


def get_conversation_history(student: Student, limit: int = 50) -> List[MentorMessage]:
    """
    Returns the chat history for a student.
    """
    return list(
        MentorMessage.objects.filter(student=student)
        .order_by('created_at')[:limit]
    )
