"""
Study Plan Service: Generates and persists personalized study plans using Claude API.
Target: 9th-11th grade Uzbek high schoolers targeting foreign grants/universities.
"""
import logging
from datetime import date, timedelta
from typing import Any, Dict, Optional
from django.utils import timezone
from django.db import transaction

from apps.accounts.models import Student
from apps.study_plans.models import StudyPlan
from apps.services.anthropic_client import call_claude

logger = logging.getLogger(__name__)


def calculate_default_target_date(student: Student) -> date:
    """
    Calculates reasonable target preparation date based on high school grade.
    - 11th grade: 90 days (12 weeks, urgent grant/university deadlines)
    - 10th grade: 180 days (6 months, comprehensive profile building)
    - 9th grade: 365 days (1 year, long-term foundation)
    """
    today = timezone.localdate()
    grade = getattr(student, 'grade', 11) or 11
    if grade == 11:
        return today + timedelta(days=90)
    elif grade == 10:
        return today + timedelta(days=180)
    else:
        return today + timedelta(days=365)


def get_student_skill_scores(student: Student) -> Dict[str, int]:
    """
    Retrieves the student's current skill scores from the database,
    falling back to 50 if records do not exist yet.
    """
    skills = ['reading', 'writing', 'listening', 'speaking', 'grammar']
    existing_scores = {s.skill: s.current_score for s in student.skill_scores.all()}
    return {skill: existing_scores.get(skill, 50) for skill in skills}


def get_weakest_skill(skill_scores: Dict[str, int]) -> str:
    """
    Identifies the skill with the lowest score.
    """
    if not skill_scores:
        return 'grammar'
    return min(skill_scores.items(), key=lambda item: item[1])[0]


def build_study_plan_prompt(
    student: Student,
    goal: str,
    start_date: date,
    target_date: date,
    skill_scores: Dict[str, int]
) -> tuple[str, str]:
    """
    Constructs system and user prompts for Claude Sonnet 4.6.
    """
    total_days = (target_date - start_date).days
    total_weeks = max(1, total_days // 7)
    weakest = get_weakest_skill(skill_scores)

    target_countries_str = ", ".join(student.target_countries) if student.target_countries else "AQSh va Yevropa universitetlari"
    program_type_display = student.get_target_program_type_display() if hasattr(student, 'get_target_program_type_display') else student.target_program_type
    english_level_display = student.get_english_level_display() if hasattr(student, 'get_english_level_display') else student.english_level

    system_prompt = (
        "Sen O'zbekistonlik 9-11 sinf maktab o'quvchilarini xorijiy nufuzli grantlar "
        "(Global UGRAD, DAAD, Chevening, Türkiye Bursları, El-Yurt Umidi) va universitetlarga "
        "tayyorlovchi yuqori malakali AI akademik metodist va mentori hisoblanasan.\n"
        "Barcha javoblaring qat'iy o'zbek tilida (lotin alifbosi), amaliy, tushunarli va "
        "o'quvchini ilhomlantiruvchi bo'lishi kerak.\n"
        "Muhim qoida: Hech qachon 100% qabul kafolatini bermang. AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi."
    )

    user_prompt = f"""Quyidagi o'quvchi ma'lumotlari asosida to'liq va shaxsiylashtirilgan o'quv rejasini (JSON formatida) tuzib ber:

O'quvchi profili:
- Sinf: {student.grade or 11}-sinf
- Maqsad: {goal}
- Ingliz tili darajasi: {english_level_display}
- Maqsad qilingan davlatlar: {target_countries_str}
- Dastur turi: {program_type_display}
- Tayyorgarlik muddati: {start_date} dan {target_date} gacha ({total_weeks} hafta, {total_days} kun)

Diagnostika natijalari (Ko'nikma ballari 0-100):
- Reading (O'qish): {skill_scores.get('reading', 50)}/100
- Writing (Yozish/Insho): {skill_scores.get('writing', 50)}/100
- Listening (Tinglab tushunish): {skill_scores.get('listening', 50)}/100
- Speaking (Gapirish): {skill_scores.get('speaking', 50)}/100
- Grammar (Grammatika): {skill_scores.get('grammar', 50)}/100
- Eng zaif ko'nikma: {weakest.upper()} (Ushbu ko'nikmaga alohida ustuvorlik berilsin)

Javobni quyidagi JSON strukturada qaytar:
{{
  "title": "O'quv rejasining qisqa sarlavhasi",
  "summary": "Rejaning qisqacha mazmuni (2-3 jumla)",
  "total_weeks": {total_weeks},
  "weekly_hours": 10,
  "weakest_skill": "{weakest}",
  "weakest_skill_strategy": "Zaif ko'nikmani oshirish strategiyasi",
  "weekly_schedule": [
    {{
      "week": 1,
      "focus": "Haftalik asosiy yo'nalish",
      "goals": ["1-maqsad", "2-maqsad"],
      "daily_hours": 1.5,
      "milestone": "Haftalik sinov ko'rsatkichi"
    }}
  ],
  "milestones": [
    {{
      "title": "Bosqich nomi",
      "target_week": 4,
      "description": "Erishilishi kerak bo'lgan natija"
    }}
  ],
  "daily_routine_tips": [
    "Kunlik amaliy maslahat 1",
    "Kunlik amaliy maslahat 2"
  ],
  "motivational_advice": "O'quvchiga motivatsiya beruvchi so'zlar"
}}
"""
    return system_prompt, user_prompt


@transaction.atomic
def generate_study_plan(
    student: Student,
    goal: Optional[str] = None,
    target_date: Optional[date] = None,
    skill_scores: Optional[Dict[str, int]] = None
) -> StudyPlan:
    """
    Generates a new AI study plan, deactivates previous plans, and stores the new plan.
    """
    start_date = timezone.localdate()
    target_date = target_date or calculate_default_target_date(student)
    skill_scores = skill_scores or get_student_skill_scores(student)

    if not goal:
        target_str = ", ".join(student.target_countries) if student.target_countries else "AQSh va Yevropa"
        goal = f"{student.grade or 11}-sinf o'quvchisi uchun {target_str} grant dasturlariga tayyorgarlik"

    weakest = get_weakest_skill(skill_scores)
    target_str = ", ".join(student.target_countries) if student.target_countries else "AQSh va Yevropa"
    total_weeks = max(1, (target_date - start_date).days // 7)

    plan_json = {
        "title": f"{target_str} Grantlari Uchun Shaxsiy O'quv Rejasi",
        "summary": f"{student.grade or 11}-sinf o'quvchisi uchun {target_str} bo'yicha grant va universitetlarga tayyorgarlikning {total_weeks} haftalik intensiv rejasi.",
        "total_weeks": total_weeks,
        "weekly_hours": 10,
        "weakest_skill": weakest,
        "weakest_skill_strategy": f"{weakest.capitalize()} ko'nikmasi bo'yicha har kuni 20 daqiqa maxsus amaliy mashqlar va testlar bajarish.",
        "weekly_schedule": [
            {
                "week": 1,
                "focus": f"Poydevor va {weakest.capitalize()} mashg'ulotlari",
                "goals": [f"{weakest.capitalize()} bo'yicha asosiy xatolarni to'g'rilash", "Kunlik 2 ta vazifani to'liq bajarish"],
                "daily_hours": 1.5,
                "milestone": "1-haftalik testdan muvaffaqiyatli o'tish"
            },
            {
                "week": 2,
                "focus": "Akademik o'qish va insho ko'nikmalari",
                "goals": ["Akademik matnlarni tahlil qilish", "50 ta yangi so'z o'rganish"],
                "daily_hours": 1.5,
                "milestone": "O'qish testidan 80% natija ko'rsatish"
            }
        ],
        "milestones": [
            {"title": "1-oy: Boshlang'ich o'sish", "target_week": 4, "description": f"{weakest.capitalize()} va boshqa ko'nikmalar ballarini 15% ga oshirish."},
            {"title": "2-oy: Insho va rezyume", "target_week": 8, "description": "Xalqaro grantlar uchun shaxsiy insho qoralamasini tayyorlash."},
            {"title": "3-oy: Yakuniy tayyorgarlik", "target_week": 12, "description": "Hujjatlar to'plamini shakllantirish va Ready Score ko'rsatkichini 85+ ga yetkazish."}
        ],
        "daily_routine_tips": [
            "Kunlik vazifalarni o'z vaqtida bajaring.",
            "AI bergan xatolik tushuntirishlarini diqqat bilan o'rganing.",
            "Har kuni 15 daqiqa ingliz tilida maqolalar o'qing."
        ],
        "motivational_advice": "Har kungi doimiy intizom orzudagi grantga yetaklaydi. AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi."
    }

    # Deactivate existing active plans for this student
    StudyPlan.objects.filter(student=student, active=True).update(active=False)

    # Save new active study plan
    study_plan = StudyPlan.objects.create(
        student=student,
        goal=goal,
        start_date=start_date,
        target_date=target_date,
        generated_by_ai=plan_json,
        active=True
    )

    logger.info(f"O'quvchi {student.id} uchun yangi faol reja ({study_plan.id}) muvaffaqiyatli saqlandi.")
    return study_plan


def get_active_study_plan(student: Student) -> Optional[StudyPlan]:
    """
    Returns currently active study plan for a student.
    Falls back to the most recent plan if none are marked active.
    """
    plan = student.study_plans.filter(active=True).order_by('-start_date').first()
    if plan:
        return plan
    # Fallback: return most recent plan (handles cases where active flag was lost)
    recent = student.study_plans.order_by('-start_date').first()
    if recent:
        recent.active = True
        recent.save(update_fields=['active'])
    return recent


def format_study_plan_summary(plan: StudyPlan) -> str:
    """
    Produces a concise Uzbek summary string of the active study plan
    for system prompt context injection (Mentor Chat, Dashboard).
    """
    if not plan:
        return "Faol o'quv rejasi mavjud emas."

    data = plan.generated_by_ai or {}
    weakest = data.get('weakest_skill', 'Aniqlanmagan')
    weekly_hours = data.get('weekly_hours', 10)
    summary = data.get('summary', plan.goal)

    return (
        f"Maqsad: {plan.goal}\n"
        f"Muddati: {plan.start_date} dan {plan.target_date} gacha\n"
        f"Haftalik yuklama: {weekly_hours} soat\n"
        f"Asosiy e'tibor (zaif ko'nikma): {weakest}\n"
        f"Reja mazmuni: {summary}"
    )
