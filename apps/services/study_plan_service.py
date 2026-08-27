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


def generate_dual_track_study_plan(
    student: Student,
    timeline_months: int = 6,
    planned_test_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Generates structured Dual-Track Study Plan for 1 to 8 months:
    - Track A (Imtihon tayyorgarligi - IELTS/SAT/DET):
      * Phase 1 (Diagnostic review & grammar drills)
      * Phase 2 (Section mastery & speed practice)
      * Phase 3 (Full timed mock exams & error analysis)
      * Target milestones with countdowns
    - Track B (Universitet arizasi va Hujjatlar):
      * Phase 1 (Target university shortlist & criteria review)
      * Phase 2 (Extracurricular portfolio & CV/Resume writing)
      * Phase 3 (Personal Statement / SOP drafting & mentor review)
      * Phase 4 (Recommendation letters / LORs collection & translation)
      * Phase 5 (Final application submission & visa prep)
      * Target milestones with countdowns
    - Weekly synchronized schedule mapping Track A days and Track B days.
    """
    if not isinstance(timeline_months, int) or timeline_months < 1 or timeline_months > 8:
        raise ValueError("Tayyorgarlik muddati 1 oydan 8 oygacha bo'lishi shart.")

    start_date = timezone.localdate()
    target_date = planned_test_date or (start_date + timedelta(days=timeline_months * 30))
    total_weeks = timeline_months * 4

    skill_scores = get_student_skill_scores(student)
    weakest = get_weakest_skill(skill_scores)

    target_countries = getattr(student, 'target_countries', None) or ["AQSh", "Germaniya"]
    target_str = ", ".join(target_countries) if target_countries else "Xalqaro Universitetlar"
    grade = getattr(student, 'grade', 11) or 11

    # Track A Phase descriptions
    track_a_phases = [
        {"phase": 1, "name": "Diagnostic review & grammar drills (Zaif ko'nikma va grammatik poydevor)"},
        {"phase": 2, "name": "Section mastery & speed practice (Bo'limlar bo'yicha chuqur mashqlar va tezlik)"},
        {"phase": 3, "name": "Full timed mock exams & error analysis (To'liq vaqtli sinov imtihonlari va xatolar tahlili)"},
    ]

    # Track B Phase descriptions
    track_b_phases = [
        {"phase": 1, "name": "Target university shortlist & criteria review (Maqsadli universitetlar ro'yxati va mezonlar tahlili)"},
        {"phase": 2, "name": "Extracurricular portfolio & CV/Resume writing (Darsdan tashqari faoliyat portfoliosi va Rezyume)"},
        {"phase": 3, "name": "Personal Statement / SOP drafting & mentor review (Shaxsiy bayonot / Motivatsiya inshosi va mentor ko'rigi)"},
        {"phase": 4, "name": "Recommendation letters / LORs collection & translation (Tavsiyanomalar yig'ish va hujjatlar tarjimasi)"},
        {"phase": 5, "name": "Final application submission & visa prep (Arizani yakuniy topshirish va viza tayyorgarligi)"},
    ]

    # Comprehensive monthly milestones templates for Track A
    track_a_catalog = [
        {
            "month": 1,
            "focus": f"Diagnostika natijalari tahlili, {weakest.capitalize()} ko'nikmasi poydevori va 300 ta yangi akademik so'z",
            "goal": "Grammatika va zaif ko'nikma bo'yicha asosiy xatolarni to'g'rilash",
            "phase": 1,
        },
        {
            "month": 2,
            "focus": "Reading & Listening strategiyalari, vaqtni to'g'ri taqsimlash va test formatiga moslashish",
            "goal": "Akademik matnlar va audio dialoglarni 75%+ aniqlikda bajarish",
            "phase": 2 if timeline_months > 2 else 1,
        },
        {
            "month": 3,
            "focus": "1-To'liq Mock Imtihon, xatolar tahlili va Writing Task 1/Task 2 akademik qoliplari",
            "goal": "1-Mock testda 6.5+ (SAT 1300+) natijaga erishish va xatolarni tahlil qilish",
            "phase": 2,
        },
        {
            "month": 4,
            "focus": "Speaking mock intervyulari, intensiv grammatik tahrir va tezkor yozish mashqlari",
            "goal": "Speaking va Writing bo'yicha mustaqil ravonlikka erishish",
            "phase": 2,
        },
        {
            "month": 5,
            "focus": "2-To'liq Mock Imtihon, murakkab savollar ustida ishlash va imtihon psixologiyasi",
            "goal": "Mock testda 7.0+ (SAT 1380+) ko'rsatkichini mustahkamlash",
            "phase": 3,
        },
        {
            "month": 6,
            "focus": "Yakuniy Mock Imtihonlar, vaqt nazorati va rasmiy test topshirishga tayyorgarlik",
            "goal": "Maqsadli ballga (IELTS 7.5+ / SAT 1400+) erishish va rasmiy testga kirish",
            "phase": 3,
        },
        {
            "month": 7,
            "focus": "Yuqori darajadagi akademik tahlil, takroriy testlar va natijalarni mustahkamlash",
            "goal": "Maksimal aniqlik va mukammal ball darajasiga chiqish",
            "phase": 3,
        },
        {
            "month": 8,
            "focus": "Rasmiy sertifikat natijalarini qabul qilish va yakuniy ballni tasdiqlash",
            "goal": "Xalqaro sertifikatni rasmiy qabul qilish va ballarni portalga yuklash",
            "phase": 3,
        },
    ]

    # Comprehensive monthly milestones templates for Track B
    track_b_catalog = [
        {
            "month": 1,
            "focus": "Maqsadli xorijiy universitetlar va grantlar ro'yxatini (Shortlist) tuzish, mezonlarni o'rganish",
            "goal": "3-5 ta asosiy va zaxira dasturlar mezonlarini to'liq aniqlash",
            "phase": 1,
        },
        {
            "month": 2,
            "focus": "Darsdan tashqari faoliyat (Extracurricular) portfoliosini shakllantirish va Rezyume (CV) yozish",
            "goal": "Xalqaro formatdagi 1 sahifalik akademik CV va loyihalar portfoliosini tayyorlash",
            "phase": 2,
        },
        {
            "month": 3,
            "focus": "Shaxsiy bayonot / Motivatsiya inshosi (Statement of Purpose) 1-qoralamasini yozish",
            "goal": "Insho xomaki variantini (Draft 1) yozish va asosiy hikoyani shakllantirish",
            "phase": 3,
        },
        {
            "month": 4,
            "focus": "O'qituvchilardan 2 ta tavsiyanoma (LOR) so'rash va inshoni mentorlar bilan tahrirlash",
            "goal": "2 ta rasmiy tavsiyanomani qo'lga kiritish va inshoni 2-qoralamagacha yaxshilash",
            "phase": 4,
        },
        {
            "month": 5,
            "focus": "Baholar tabeli (Transkript) va sertifikatlarni tarjima qilib notarial tasdiqlash",
            "goal": "Barcha akademik hujjatlarni to'liq qabul talablariga moslashtirish",
            "phase": 4,
        },
        {
            "month": 6,
            "focus": "Arizalar portalini (Common App / Universitet portali) to'ldirish va arizani jo'natish (Submit)",
            "goal": "Hujjatlar to'plamini to'liq jo'natish va qabul tasdig'ini olish",
            "phase": 5,
        },
        {
            "month": 7,
            "focus": "Moliyaviy yordam, grant arizalari va qo'shimcha intervyularga tayyorgarlik",
            "goal": "Grant intervyusidan muvaffaqiyatli o'tish va to'liq moliyalashtirishni kafolatlash",
            "phase": 5,
        },
        {
            "month": 8,
            "focus": "Talabalik vizasi (F-1 / D-viza) hujjatlarini tayyorlash va safar oldi tayyorgarlik",
            "goal": "Viza suhbatidan o'tish va o'qishga jo'nab ketish rejalarini yakunlash",
            "phase": 5,
        },
    ]

    track_a_milestones = []
    track_b_milestones = []

    for m in range(1, timeline_months + 1):
        # Calculate countdown days to target date from start of month m
        month_start_date = start_date + timedelta(days=(m - 1) * 30)
        countdown_days = max(0, (target_date - month_start_date).days)

        # Scale index to catalog
        cat_idx = m - 1 if m <= len(track_a_catalog) else len(track_a_catalog) - 1
        t_a_item = track_a_catalog[cat_idx]
        t_b_item = track_b_catalog[cat_idx]

        track_a_milestones.append({
            "month": m,
            "target_week": m * 4,
            "phase": t_a_item["phase"],
            "focus": t_a_item["focus"],
            "goal": t_a_item["goal"],
            "drills_target": m * 20,
            "countdown_days": countdown_days
        })

        track_b_milestones.append({
            "month": m,
            "target_week": m * 4,
            "phase": t_b_item["phase"],
            "focus": t_b_item["focus"],
            "goal": t_b_item["goal"],
            "deadline_check": True,
            "countdown_days": countdown_days
        })

    # Weekly synchronized dual-track schedule
    weekly_schedule = []
    for w in range(1, total_weeks + 1):
        month_num = (w - 1) // 4 + 1
        week_in_month = (w - 1) % 4 + 1

        if week_in_month == 1:
            a_focus = f"{month_num}-oy {weakest.capitalize()} bo'yicha yangi mavzular va lug'at boyligi"
            b_focus = f"{month_num}-oy Universitet talablari tahlili va reja tuzish"
        elif week_in_month == 2:
            a_focus = "Akademik matnlar tahlili va listening amaliyoti"
            b_focus = "Insho va rezyume qoralamasi ustida ishlash"
        elif week_in_month == 3:
            a_focus = "Intensiv grammatik mashqlar va yozish ko'nikmalari"
            b_focus = "Tavsiyanoma va transkript hujjatlarini tayyorlash"
        else:
            a_focus = f"{month_num}-oylik Mock test sinovi va xatolar tahlili"
            b_focus = "Oylik portfolio nazorati va mentor tekshiruvi"

        weekly_schedule.append({
            "week": w,
            "month": month_num,
            "track_a_days": ["Dushanba", "Chorshanba", "Juma"],
            "track_a_focus": a_focus,
            "track_b_days": ["Seshanba", "Payshanba", "Shanba"],
            "track_b_focus": b_focus,
            "daily_hours": 1.5,
            "milestone": f"{w}-haftalik sinov ko'rsatkichi"
        })

    payload = {
        "title": f"{target_str} Grantlari Uchun Dual-Track O'quv Rejasi",
        "summary": (
            f"{grade}-sinf o'quvchisi uchun {target_str} grant va universitetlariga "
            f"tayyorgarlikning {total_weeks} haftalik ({timeline_months} oylik) sinxronlashtirilgan Dual-Track rejasi."
        ),
        "timeline_months": timeline_months,
        "start_date": str(start_date),
        "target_date": str(target_date),
        "total_weeks": total_weeks,
        "weekly_hours": 12,
        "weakest_skill": weakest,
        "weakest_skill_strategy": f"{weakest.capitalize()} ko'nikmasi bo'yicha har kuni 20 daqiqa maxsus amaliy mashqlar va testlar bajarish.",
        "track_a": {
            "name": "Imtihon Tayyorgarligi (Standardized Test Prep)",
            "title": "Track A: Imtihon tayyorgarligi (IELTS/SAT/DET)",
            "target_score": "IELTS 7.5+ / SAT 1400+",
            "weakest_skill": weakest,
            "weekly_hours": 8,
            "phases": track_a_phases,
            "milestones": track_a_milestones
        },
        "track_b": {
            "name": "Universitet Arizasi va Hujjatlar (Admissions & Documents)",
            "title": "Track B: Universitet arizasi va Hujjatlar",
            "target_programs": target_countries,
            "weekly_hours": 4,
            "phases": track_b_phases,
            "milestones": track_b_milestones
        },
        "weekly_schedule": weekly_schedule,
        "daily_routine_tips": [
            "Kunlik 20 daqiqa Track A grammatika va o'qish mashqini bajaring.",
            "Haftada 2 soat Track B insho va portfolio ustida ishlang.",
            "AI bergan xatolik tushuntirishlarini diqqat bilan o'rganing.",
            "Har kuni 15 daqiqa ingliz tilida maqolalar o'qing."
        ],
        "motivational_advice": "Har kungi doimiy intizom orzudagi grantga yetaklaydi. AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi."
    }

    return payload


@transaction.atomic
def activate_dual_track_study_plan(student: Student, plan_payload: Dict[str, Any]) -> StudyPlan:
    """
    Deactivates previous study plans for student and saves new active StudyPlan with
    timeline_months, goal, start_date, target_date, generated_by_ai=plan_payload.
    """
    timeline_months = int(plan_payload.get('timeline_months', 6))

    start_date_val = plan_payload.get('start_date')
    if isinstance(start_date_val, str):
        try:
            start_date = date.fromisoformat(start_date_val)
        except ValueError:
            start_date = timezone.localdate()
    elif isinstance(start_date_val, date):
        start_date = start_date_val
    else:
        start_date = timezone.localdate()

    target_date_val = plan_payload.get('target_date')
    if isinstance(target_date_val, str):
        try:
            target_date = date.fromisoformat(target_date_val)
        except ValueError:
            target_date = start_date + timedelta(days=timeline_months * 30)
    elif isinstance(target_date_val, date):
        target_date = target_date_val
    else:
        target_date = start_date + timedelta(days=timeline_months * 30)

    goal = plan_payload.get('title') or (
        f"{student.grade or 11}-sinf o'quvchisi uchun {timeline_months} oylik Dual-Track o'quv rejasi"
    )

    # Deactivate existing active plans for this student
    StudyPlan.objects.filter(student=student, active=True).update(active=False)

    # Save new active study plan
    study_plan = StudyPlan.objects.create(
        student=student,
        goal=goal,
        start_date=start_date,
        target_date=target_date,
        timeline_months=timeline_months,
        generated_by_ai=plan_payload,
        active=True
    )

    # Synchronize student model fields if present
    updated_fields = []
    if hasattr(student, 'plan_timeline_months') and student.plan_timeline_months != timeline_months:
        student.plan_timeline_months = timeline_months
        updated_fields.append('plan_timeline_months')
    if hasattr(student, 'planned_test_date') and student.planned_test_date != target_date:
        student.planned_test_date = target_date
        updated_fields.append('planned_test_date')
    if updated_fields:
        student.save(update_fields=updated_fields)

    logger.info(f"O'quvchi {student.id} uchun yangi faol Dual-Track reja ({study_plan.id}) muvaffaqiyatli saqlandi.")
    return study_plan


@transaction.atomic
def generate_study_plan(
    student: Student,
    goal: Optional[str] = None,
    target_date: Optional[date] = None,
    skill_scores: Optional[Dict[str, int]] = None
) -> StudyPlan:
    """
    Generates a new AI study plan, deactivates previous plans, and stores the new plan.
    Delegates to generate_dual_track_study_plan and activate_dual_track_study_plan.
    """
    start_date = timezone.localdate()
    target_date = target_date or calculate_default_target_date(student)
    days_diff = (target_date - start_date).days
    timeline_months = max(1, min(8, round(days_diff / 30)))

    plan_payload = generate_dual_track_study_plan(
        student=student,
        timeline_months=timeline_months,
        planned_test_date=target_date
    )

    if goal:
        plan_payload['title'] = goal

    return activate_dual_track_study_plan(student, plan_payload)


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

