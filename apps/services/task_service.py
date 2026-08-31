"""
Task Service:
- Generates synchronized daily tasks for high school students supporting Dual-Track progression:
  * Track A: Imtihon tayyorgarligi (Exam drills, vocabulary, reading, grammar, mock tests)
  * Track B: Universitet arizasi va Hujjatlar (SOP drafting, extracurricular reflection, LOR request templates, document prep)
- Populates Uzbek titles, instructions, expected outcomes, and points.
- Grades student submissions via Claude API or deterministic heuristic, producing explanatory ai_feedback.
- Records scores, updates progress, and tracks streaks.
"""
import json
import logging
import re
from datetime import date
from typing import Dict, Any, List, Optional, Tuple
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Student
from apps.tasks.models import DailyTask
from apps.study_plans.models import StudyPlan
from apps.services.anthropic_client import call_claude
from apps.services.study_plan_service import get_active_study_plan
from apps.services.score_service import record_task_completion_score

logger = logging.getLogger(__name__)

# ==============================================================================
# CURATED TRACK A TASKS (Imtihon Tayyorgarligi: Grammar, Reading, Vocabulary, Drills)
# ==============================================================================

CURATED_TRACK_A_TASKS: List[Tuple[str, Dict[str, Any]]] = [
    (
        'grammar_drill',
        {
            "title": "Track A (Grammar Drill): Conditional Sentences for Scholarship Applications",
            "skill": "grammar",
            "difficulty": "Intermediate-Advanced",
            "instruction": "Quyidagi gapdagi bo'sh joyni to'g'ri fe'l shakli bilan to'ldiring va tanlovingizni qisqacha izohlang.",
            "question": "If Aziz ________ (apply) for the Global UGRAD exchange program earlier, he would have secured the full sponsorship.",
            "options": [
                {"key": "A", "text": "applied"},
                {"key": "B", "text": "had applied"},
                {"key": "C", "text": "has applied"},
                {"key": "D", "text": "would apply"}
            ],
            "correct_option": "B",
            "explanation": "Third Conditional o'tgan zamondagi amalga oshmagan shartni ifodalaydi: If + Past Perfect (had applied), ... would have + V3.",
            "expected_outcome": "To'g'ri grammatik qolipni aniqlash va xalqaro insholarda to'g'ri qo'llash.",
            "points": 100
        }
    ),
    (
        'grammar_drill',
        {
            "title": "Track A (Grammar Drill): Inversion in Academic Motivation Letters",
            "skill": "grammar",
            "difficulty": "Advanced",
            "instruction": "Inkor so'z bilan boshlangan gapdagi to'g'ri so'z tartibini tanlang.",
            "question": "Seldom ________ such profound dedication to community leadership in high school applicants.",
            "options": [
                {"key": "A", "text": "the admissions committee observes"},
                {"key": "B", "text": "does the admissions committee observe"},
                {"key": "C", "text": "the admissions committee has observed"},
                {"key": "D", "text": "observes the admissions committee"}
            ],
            "correct_option": "B",
            "explanation": "'Seldom', 'Rarely', 'Never' kabi inkor ravishlar gap boshida kelganda inversiya yasaladi (yordamchi fe'l + ega + asosiy fe'l).",
            "expected_outcome": "Akademik matnlarda urg'u berish va inversiya qoidasini qo'llash.",
            "points": 100
        }
    ),
    (
        'grammar_drill',
        {
            "title": "Track A (Grammar Drill): Complex Gerunds and Infinitives in Admissions",
            "skill": "grammar",
            "difficulty": "Intermediate",
            "instruction": "Akademik matn kontekstida to'g'ri fe'l shaklini tanlang.",
            "question": "The DAAD scholarship committee expects all candidates ________ their certified transcripts by December 1st.",
            "options": [
                {"key": "A", "text": "submitting"},
                {"key": "B", "text": "to submit"},
                {"key": "C", "text": "submit"},
                {"key": "D", "text": "submitted"}
            ],
            "correct_option": "B",
            "explanation": "'Expect someone to do something' strukturasi to-infinitive talab qiladi.",
            "expected_outcome": "Rasmiy talablar va qoidalarni ifodalovchi fe'l shakllarini to'g'ri ishlatish.",
            "points": 100
        }
    ),
    (
        'grammar_drill',
        {
            "title": "Track A (Grammar Drill): Subjunctive Mood in Formal Grant Requests",
            "skill": "grammar",
            "difficulty": "Advanced",
            "instruction": "Rasmiy ariza kontekstida to'g'ri Subjunctive shaklini tanlang.",
            "question": "The admissions director recommended that the candidate ________ additional letters of recommendation.",
            "options": [
                {"key": "A", "text": "submits"},
                {"key": "B", "text": "submit"},
                {"key": "C", "text": "submitted"},
                {"key": "D", "text": "would submit"}
            ],
            "correct_option": "B",
            "explanation": "'Recommend/Suggest that someone do something' qolipida subjunctive fe'l asosi (bare infinitive - submit) ishlatiladi.",
            "expected_outcome": "Rasmiy akademik tavsiya va talablarni ifodalashda subjunctive mood qoidasini egallash.",
            "points": 100
        }
    ),
    (
        'reading_comprehension',
        {
            "title": "Track A (Reading): Statement of Purpose Structure & Academic Coherence",
            "skill": "reading",
            "difficulty": "Intermediate",
            "passage": (
                "An effective Statement of Purpose (SOP) for international undergraduate grants must articulate a coherent narrative. "
                "Rather than merely listing academic accolades, strong applicants connect their past leadership projects in Uzbekistan "
                "with their future vision. Admissions committees at European and American institutions look for evidence of self-reflection, "
                "cultural agility, and tangible plans to contribute to the applicant's home country upon graduation."
            ),
            "question": "According to the passage, what distinguishes a compelling Statement of Purpose from a weak one?",
            "options": [
                {"key": "A", "text": "Listing as many awards and certificates as possible without narrative context."},
                {"key": "B", "text": "Connecting past leadership experiences with a clear future vision and community impact."},
                {"key": "C", "text": "Focusing solely on foreign travel aspirations rather than returning to Uzbekistan."},
                {"key": "D", "text": "Writing exclusively about high school examination grades."}
            ],
            "correct_option": "B",
            "explanation": "Matnda kuchli arizachilar o'tmishdagi yetakchilik tajribalarini kelajak rejalari va vataniga hissa qo'shish bilan bog'lashi ta'kidlangan.",
            "expected_outcome": "Akademik insho strukturasini tahlil qilish va asosiy fikrni ajratib olish.",
            "points": 100
        }
    ),
    (
        'reading_comprehension',
        {
            "title": "Track A (Reading): Chevening Leadership Assessment Criteria",
            "skill": "reading",
            "difficulty": "Advanced",
            "passage": (
                "The Chevening scholarship seeks individuals with demonstrable leadership qualities. "
                "Leadership is evaluated not by formal job titles, but by the candidate's ability to influence others, "
                "resolve conflicts, and drive sustainable community initiatives. Applicants must provide concrete STAR-method "
                "(Situation, Task, Action, Result) examples to validate their claims."
            ),
            "question": "How does the Chevening selection committee define and assess true leadership?",
            "options": [
                {"key": "A", "text": "By formal managerial titles and family connections."},
                {"key": "B", "text": "By the applicant's ability to influence, resolve conflict, and demonstrate measurable impact."},
                {"key": "C", "text": "Only through academic test scores and GPA."},
                {"key": "D", "text": "Through letters of recommendation from government officials only."}
            ],
            "correct_option": "B",
            "explanation": "Matnga ko'ra, yetakchilik mansab bilan emas, odamlarga ta'sir o'tkazish va aniq natijalarga erishish orqali baholanadi.",
            "expected_outcome": "Xalqaro stipendiya mezonlarini tushunish va xulosalarni aniqlash.",
            "points": 100
        }
    ),
    (
        'vocabulary_drill',
        {
            "title": "Track A (Vocabulary): Academic Collocations for Scholarships",
            "skill": "vocabulary",
            "difficulty": "Intermediate-Advanced",
            "instruction": "Grant va insholarda ko'p uchraydigan akademik iborani to'ldiring.",
            "question": "The applicant successfully managed to ________ a nationwide environmental awareness campaign.",
            "options": [
                {"key": "A", "text": "spearhead"},
                {"key": "B", "text": "do"},
                {"key": "C", "text": "make up"},
                {"key": "D", "text": "invent"}
            ],
            "correct_option": "A",
            "explanation": "'Spearhead a campaign/initiative' - tashabbus yoki loyihaga yetakchilik qilish ma'nosidagi kuchli akademik birikma.",
            "expected_outcome": "Rezyume va insholarda kuchli akademik so'z birikmalarini qo'llash ko'nikmasi.",
            "points": 100
        }
    ),
    (
        'reading_comprehension',
        {
            "title": "Track A (Reading): DAAD Research Proposal and Study Plan Guidelines",
            "skill": "reading",
            "difficulty": "Advanced",
            "passage": (
                "Securing research grants at German state universities requires a well-delineated study plan. "
                "Committees evaluate feasibility, methodology clarity, and institutional alignment with the host department. "
                "A successful applicant demonstrates that their academic pursuits directly address real-world scientific gaps."
            ),
            "question": "Which factor is critical for German scholarship committee evaluation?",
            "options": [
                {"key": "A", "text": "Vague hypotheses without methodology."},
                {"key": "B", "text": "Methodology clarity, feasibility, and host institution alignment."},
                {"key": "C", "text": "Solely the applicant's age."},
                {"key": "D", "text": "Informal social media recommendations."}
            ],
            "correct_option": "B",
            "explanation": "Germaniya universitetlarida tadqiqot loyihasining aniq metodologiyasi va tanlangan kafedra bilan uyg'unligi hal qiluvchi mezondir.",
            "expected_outcome": "Tadqiqot rejalari bo'yicha akademik matnni tushunish.",
            "points": 100
        }
    )
]

# Backward compatibility alias
CURATED_GRAMMAR_TASKS = [t[1] for t in CURATED_TRACK_A_TASKS if t[0] == 'grammar_drill']
CURATED_READING_TASKS = [t[1] for t in CURATED_TRACK_A_TASKS if t[0] == 'reading_comprehension']

# ==============================================================================
# CURATED TRACK B TASKS (Universitet Arizasi va Hujjatlar: SOP, LOR, Extracurricular)
# ==============================================================================

CURATED_TRACK_B_TASKS: List[Tuple[str, Dict[str, Any]]] = [
    (
        'essay_milestone',
        {
            "title": "Track B (SOP Drafting): Shaxsiy Bayonot Kirish Qismini Yozish (Hook & Motivation)",
            "skill": "writing",
            "difficulty": "Intermediate-Advanced",
            "instruction": "Shaxsiy bayonotingizning (Statement of Purpose / Personal Statement) 1-xatboshisini (150-200 so'z) yozing. Tanlangan mutaxassislikka qiziqishingiz qanday boshlangani va asosiy maqsadingizni bayon qiling.",
            "question": "Nima uchun aynan shu sohani tanladingiz? Qaysi aniq hayotiy yoki akademik voqea sizni ilhomlantirgan?",
            "guidelines": [
                "1. O'quvchining diqqatini tortuvchi kuchli 'Hook' (kirish jumlasi) bilan boshlang.",
                "2. Umumiy gaplardan qoching; o'zingizning aniq tajribangizni keltiring.",
                "3. 150-200 so'z atrofida ingliz yoki o'zbek tilida bayon qiling."
            ],
            "expected_outcome": "Xalqaro talablarga javob beradigan, shaxsiy va ishonchli insho kirish qoralamasi.",
            "points": 100
        }
    ),
    (
        'essay_milestone',
        {
            "title": "Track B (SOP Drafting): Asosiy Qism — Akademik Loyihalar va STAR Metodi",
            "skill": "writing",
            "difficulty": "Advanced",
            "instruction": "Inshongizning asosiy qismida (Body Paragraph) eng muhim akademik yoki jamoaviy loyihangizni STAR (Situation, Task, Action, Result) usulida yoriting (200-250 so'z).",
            "question": "Qaysi loyiha yoki tadqiqot ustida ishlagansiz? Qanday qiyinchilikka duch keldingiz va qanday aniq natijaga (sonli ko'rsatkichlar bilan) erishdingiz?",
            "guidelines": [
                "Situation: Loyiha qayerda va qanday sharoitda amalga oshirilgan?",
                "Task: Sizning oldingizda qanday aniq vazifa turgan edi?",
                "Action: Muammoni hal qilish uchun shaxsan o'zingiz nima qildingiz?",
                "Result: Qanday o'lchanadigan natijaga erishildi?"
            ],
            "expected_outcome": "STAR metodi asosida tizimlashtirilgan, dalillarga boy asosiy qism matni.",
            "points": 100
        }
    ),
    (
        'extracurricular',
        {
            "title": "Track B (Portfolio): Darsdan Tashqari Faoliyat va Yetakchilik Portfoliosi",
            "skill": "leadership",
            "difficulty": "Intermediate",
            "instruction": "Oxirgi 2 yildagi 3 ta eng muhim darsdan tashqari faoliyatingizni (Volontyorlik, Olimpiada, To'garak, Jamoat ishlari) ro'yxatlang va erishilgan natijalarni yozing.",
            "question": "Har bir faoliyat bo'yicha: 1) Tashkilot/Tadbir nomi, 2) Sizning rolingiz, 3) Qancha soat/hafta vaqt ajratgansiz, 4) Aniq yutug'ingiz.",
            "guidelines": [
                "Misol: 'EcoUzbekistan volontyori — 50 nafar o'quvchiga ekologik darslar o'tdim, 200 ta daraxt ekish aksiyasini boshqardim.'",
                "Sonli ko'rsatkichlar (metrics) keltirishga e'tibor qarating."
            ],
            "expected_outcome": "Xalqaro standartdagi 3 ta kuchli faoliyat tavsifi.",
            "points": 80
        }
    ),
    (
        'lor_request',
        {
            "title": "Track B (LOR): Ustozga Tavsiyanoma (Recommendation Letter) So'rash Xati Shabloni",
            "skill": "communication",
            "difficulty": "Intermediate",
            "instruction": "O'zingizni yaxshi taniydigan fan o'qituvchisiga yoki maktab rahbariga xalqaro grant uchun tavsiyanoma so'rab yoziladigan rasmiy va hurmatli xat loyihasini tayyorlang.",
            "question": "Ustozingizga maqsadingiz, nima uchun aynan undan tavsiyanoma so'rayotganingiz va topshirish muddatlarini aniq bayon qiling.",
            "guidelines": [
                "1. Rasmiy va samimiy salomlashuv bilan boshlang.",
                "2. Ariza topshirilayotgan dastur nomi va deadline'ni ko'rsating.",
                "3. Ustozingiz darsida ko'rsatgan 1-2 ta yutuqli loyihangizni eslatib o'ting (Brag sheet ilova qilinadi)."
            ],
            "expected_outcome": "O'qituvchiga yuborishga tayyor professional LOR so'rov xati.",
            "points": 80
        }
    ),
    (
        'essay_milestone',
        {
            "title": "Track B (SOP Drafting): Xulosa — O'zbekiston Taraqqiyotiga Qo'shiladigan Hissa",
            "skill": "writing",
            "difficulty": "Intermediate",
            "instruction": "Inshoning yakuniy xulosa qismini yozing (150 so'z). O'qishni tugatgach O'zbekistonga qaytib qanday loyihalarni amalga oshirmoqchisiz?",
            "question": "Olingan xalqaro bilim va tajribalaringiz orqali O'zbekistonning qaysi sohasini rivojlantirishga hissa qo'shasiz?",
            "guidelines": [
                "1. O'zingiz tanlagan soha bo'yicha aniq 2-3 ta kelajak tashabbusini ko'rsating.",
                "2. Universitet beradigan imkoniyatlar bu rejalarga qanday yordam berishini bog'lang.",
                "3. Ijobiy va qat'iy yakuniy xulosa jumlasi yozing."
            ],
            "expected_outcome": "Vatanga qaytish va real hissa qo'shish rejasini isbotlovchi xulosa qismi.",
            "points": 100
        }
    ),
    (
        'university_research',
        {
            "title": "Track B (Tadqiqot): Maqsadli Universitetlar va Grant Dasturlari Qabul Mezonlari Tahlili",
            "skill": "research",
            "difficulty": "Intermediate",
            "instruction": "Tanlangan 2 ta maqsadli universitet yoki grantning rasmiy veb-saytini o'rganib, minimal IELTS/SAT, GPA, insho mavzulari va qabul deadline'larini tekshiring.",
            "question": "Har bir universitet bo'yicha talablar jadvalini tuzing va o'zingizning hozirgi ko'rsatkichlaringiz bilan solishtiring.",
            "guidelines": [
                "1. Universitet nomi va davlati",
                "2. Minimal til talabi (IELTS / TOEFL / DET)",
                "3. Grant qamrovi (Full-ride yoki qisman)",
                "4. Arizalar qabulining oxirgi sanasi"
            ],
            "expected_outcome": "Aniq muddatlar va talablar aks etgan qabul jadvali.",
            "points": 70
        }
    ),
    (
        'document_prep',
        {
            "title": "Track B (Hujjatlar): Baholar Tabeli (Transkript) va Sertifikatlar Nazorat Ro'yxati",
            "skill": "organization",
            "difficulty": "Intermediate",
            "instruction": "Ariza topshirish uchun zarur bo'lgan barcha rasmiy hujjatlar ro'yxatini (Checklist) tuzing va ularning tayyorgarlik holatini belgilang.",
            "question": "Passport, 9-11 sinf baholar tabeli tarjimasi, til sertifikati, diplomlar va portfolio fayllari holatini tekshiring.",
            "guidelines": [
                "Barcha hujjatlar ingliz tilida va rasmiy muhrlangan bo'lishi lozimligini tekshiring."
            ],
            "expected_outcome": "100% to'liq akademik hujjatlar nazorat ro'yxati.",
            "points": 70
        }
    )
]


def get_student_weakest_skill(student: Student) -> str:
    """
    Finds the skill with lowest current_score for this student.
    """
    scores = student.skill_scores.all()
    if not scores.exists():
        return 'grammar'
    weakest = min(scores, key=lambda s: s.current_score)
    return weakest.skill


def get_student_target_scope(student):
    if hasattr(student, 'target_selection') and student.target_selection and student.target_selection.primary_program:
        return student.target_selection.primary_program.scope
    return 'international'

def generate_daily_tasks_for_dual_track(
    student: Student,
    date_for_tasks: Optional[date] = None
) -> List[DailyTask]:
    """
    Alternates / provisions daily tasks tagged with track='track_a' (Exam drills, vocabulary, grammar)
    and track='track_b' (SOP drafting, extracurricular reflection, LOR request templates).
    Populates Uzbek titles, instructions, expected outcomes, and points.
    """
    if date_for_tasks is None:
        date_for_tasks = timezone.localdate()

    existing_tasks = list(DailyTask.objects.filter(student=student, date=date_for_tasks).order_by('id'))
    if existing_tasks:
        return existing_tasks

    active_plan = get_active_study_plan(student)
    weakest_skill = get_student_weakest_skill(student)

    # Offset based on date and student id for deterministic variation
    day_offset = (date_for_tasks - date(2026, 1, 1)).days + (student.id * 3)

    scope = get_student_target_scope(student)
    
    # Pick Track A task (prioritizing weakest skill if applicable)
    track_a_pool = CURATED_TRACK_A_TASKS
    if weakest_skill == 'grammar':
        grammar_pool = [t for t in track_a_pool if t[0] == 'grammar_drill']
        track_a_task = grammar_pool[day_offset % len(grammar_pool)] if grammar_pool else track_a_pool[day_offset % len(track_a_pool)]
    elif weakest_skill == 'reading':
        reading_pool = [t for t in track_a_pool if t[0] == 'reading_comprehension']
        track_a_task = reading_pool[day_offset % len(reading_pool)] if reading_pool else track_a_pool[day_offset % len(track_a_pool)]
    else:
        track_a_task = track_a_pool[day_offset % len(track_a_pool)]

    # If domestic, override Track A task with DTM logic (pseudo-task for now)
    if scope == 'domestic':
        track_a_task = (
            'dtm_drill',
            {
                "title": "Track A (DTM): Ona Tili va Adabiyot (Majburiy Blok)",
                "skill": "reading",
                "difficulty": "Intermediate",
                "instruction": "Quyidagi matnning asosiy g'oyasini toping (DTM standarti).",
                "question": "Milliy qadriyatlar deganda nimani tushunasiz?",
                "options": [
                    {"key": "A", "text": "Faqat tarixiy yodgorliklar."},
                    {"key": "B", "text": "Til, din, urf-odat va milliy o'zlikni anglatuvchi ma'naviy boyliklar."},
                    {"key": "C", "text": "Iqtisodiy resurslar."},
                    {"key": "D", "text": "G'arb madaniyati yutuqlari."}
                ],
                "correct_option": "B",
                "explanation": "Milliy qadriyatlar xalqning ma'naviyati va tarixiy o'zligidir.",
                "expected_outcome": "DTM majburiy blok testiga tayyorgarlik.",
                "points": 100
            }
        )

    # Pick Track B task
    track_b_task = CURATED_TRACK_B_TASKS[(day_offset + 1) % len(CURATED_TRACK_B_TASKS)]

    created_tasks = []
    with transaction.atomic():
        existing_tasks = list(DailyTask.objects.filter(student=student, date=date_for_tasks).order_by('id'))
        if existing_tasks:
            return existing_tasks

        # Create Track A task
        t_type_a, content_a = track_a_task
        task_a = DailyTask.objects.create(
            student=student,
            study_plan=active_plan,
            track='track_a',
            date=date_for_tasks,
            task_type=t_type_a,
            content=content_a,
            completed=False,
            score=None,
            student_answer="",
            ai_feedback=""
        )
        created_tasks.append(task_a)

        # Create Track B task
        t_type_b, content_b = track_b_task
        task_b = DailyTask.objects.create(
            student=student,
            study_plan=active_plan,
            track='track_b',
            date=date_for_tasks,
            task_type=t_type_b,
            content=content_b,
            completed=False,
            score=None,
            student_answer="",
            ai_feedback=""
        )
        created_tasks.append(task_b)

    logger.info(f"Student {student.id} uchun 2 ta Dual-Track vazifa (Track A va Track B) yaratildi ({date_for_tasks}).")
    return created_tasks


def generate_daily_tasks_for_student(
    student: Student,
    task_date: Optional[date] = None,
    count: int = 2
) -> List[DailyTask]:
    """
    Generates or retrieves DailyTask records for a student for the given date.
    Standardized to delegate to generate_daily_tasks_for_dual_track.
    """
    return generate_daily_tasks_for_dual_track(student, date_for_tasks=task_date)


def grade_task_submission(task: DailyTask, student_answer: str) -> Dict[str, Any]:
    """
    Evaluates a student's answer using Claude API, returning numeric score (0-100)
    and detailed explanatory ai_feedback in Uzbek Latin script.
    """
    content = task.content or {}
    correct_option = content.get('correct_option', '').strip().upper()
    explanation = content.get('explanation', '')
    question_text = content.get('question', '')
    passage_text = content.get('passage', '')
    is_multiple_choice = bool(correct_option and 'options' in content)

    system_prompt = (
        "Sen xalqaro grant va universitetlarga (shuningdek, O'zbekiston ichidagi DTM va Ijodiy imtihonlarga) tayyorlovchi AI o'qituvchisan. "
        "O'quvchining vazifaga bergan javobini xolisona bahola va ENG MUHIMI unga xatosining "
        "sababini, qoidani va to'g'ri yondashuvni tushuntirib beruvchi 'ai_feedback' (Uzbek Latin) yoz.\n"
        "Muhim: ai_feedback faqat 'to'g'ri' yoki 'noto'g'ri' deb qolmasdan, nima uchun bundayligini tushuntirsin.\n"
        "Hech qachon 100% qabul kafolatini bermang. AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi."
    )

    user_prompt = f"""Vazifa turi: {task.get_task_type_display()} (Track: {task.get_track_display()})
Sarlavha: {content.get('title', '')}
Ko'rsatma: {content.get('instruction', '')}
Savol / Topshiriq: {question_text}
{f'Matn: {passage_text}' if passage_text else ''}
{f'To\'g\'ri javob kaliti: {correct_option}' if correct_option else ''}
{f'Standart izoh: {explanation}' if explanation else ''}

O'quvchi bergan javob: "{student_answer}"

Javobni quyidagi JSON formatda qaytar:
{{
  "score": <0 dan 100 gacha butun son>,
  "completed": true,
  "ai_feedback": "<O'quvchiga yo'naltirilgan, xato va to'g'ri jihatlarini tushuntiruvchi o'zbekcha batafsil tahlil>"
}}
"""

    try:
        response = call_claude(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format='json',
            max_tokens=1000
        )
        if isinstance(response, dict) and 'score' in response and 'ai_feedback' in response:
            score = max(0, min(100, int(response['score'])))
            feedback = str(response['ai_feedback']).strip()
            if feedback:
                return {
                    'score': score,
                    'completed': True,
                    'ai_feedback': feedback
                }
    except Exception as e:
        logger.warning(f"Claude grading failed: {e}. Using deterministic heuristic.")

    # Heuristic fallback grading
    cleaned_ans = student_answer.strip().upper()

    if is_multiple_choice:
        is_correct = False
        if correct_option and (cleaned_ans == correct_option or cleaned_ans.startswith(f"{correct_option})") or cleaned_ans.startswith(f"{correct_option}.")):
            is_correct = True
        elif correct_option and 'options' in content:
            for opt in content.get('options', []):
                if opt.get('key') == correct_option and opt.get('text', '').lower() in student_answer.lower():
                    is_correct = True
                    break

        if is_correct:
            score = 100
            ai_feedback = (
                f"Ajoyib! Siz to'g'ri javobni tanladingiz ({correct_option}). "
                f"{explanation} Ushbu qoidani amaliyotda to'g'ri qo'llay olishingiz grant insholarida akademik aniqlikni ta'minlaydi."
            )
        else:
            if len(student_answer.split()) >= 10:
                score = 50
                ai_feedback = (
                    f"Sizning javobingizda yaxshi fikrlar bor, biroq to'g'ri javob {correct_option} edi. "
                    f"Tushuntirish: {explanation}. Keyingi safar kalit so'zlarga va grammatik qolipga e'tibor qarating."
                )
            else:
                score = 30
                ai_feedback = (
                    f"Afsuski javobingiz noto'g'ri. To'g'ri javob: {correct_option}. "
                    f"Tushuntirish: {explanation}. Ushbu mavzuni mustahkamlash uchun yana mashq qiling."
                )
    else:
        # Open-ended essay / Track B task heuristic grading
        words = student_answer.strip().split()
        word_count = len(words)
        if word_count >= 25:
            score = 95
            ai_feedback = (
                "Ajoyib va mazmunli topshiriq ijrosi! Siz o'z fikringizni aniq dalillar va reja bilan ifodalagansiz. "
                "Ushbu yondashuv xalqaro grant va universitet komissiyasida yuqori baholanadi."
            )
        elif word_count >= 12:
            score = 80
            ai_feedback = (
                "Yaxshi urinish. Javobingizda asosiy g'oya aks etgan. "
                "Keyingi safar fikringizni yanada boyitish uchun aniqroq misollar va sonli ko'rsatkichlar qo'shish tavsiya etiladi."
            )
        elif word_count >= 5:
            score = 60
            ai_feedback = (
                "Qisqa javob berildi. Topshiriq bo'yicha to'liqroq yoritish va batafsilroq bayon qilish orqali "
                "ko'proq ball to'plashingiz mumkin."
            )
        else:
            score = 35
            ai_feedback = (
                "Javob juda qisqa. Iltimos, topshiriq ko'rsatmalariga muvofiq to'liqroq va batafsilroq yozing."
            )

    return {
        'score': score,
        'completed': True,
        'ai_feedback': ai_feedback
    }


@transaction.atomic
def submit_daily_task(task_id: int, student: Student, student_answer: str) -> DailyTask:
    """
    Processes task submission: grades via Claude/heuristic, updates DailyTask,
    and updates student SkillScore & ProgressLog.
    """
    task = DailyTask.objects.select_for_update().get(id=task_id, student=student)
    
    # Grade submission
    grading = grade_task_submission(task, student_answer)
    
    task.completed = True
    task.score = grading['score']
    task.student_answer = student_answer
    task.ai_feedback = grading['ai_feedback']
    task.completed_at = timezone.now()
    task.save()

    # Record score update, calculate streak, and log progress
    record_task_completion_score(student, task.task_type, task.score)

    logger.info(
        f"Task {task.id} ({task.task_type}, track={task.track}) submitted by student {student.id}. "
        f"Score: {task.score}."
    )
    return task
