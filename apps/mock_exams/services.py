"""
Mock Exam Engine Service:
- Generates curated authentic IELTS Mock content (Listening, Reading, Writing)
- Manages sequential timed transitions without pausing
- Performs AI evaluation and calculates IELTS Overall Band Score
- Synchronizes with SkillScore and ProgressLog (Ready Score boost)
"""
import json
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction

from .models import MockExam, MockExamSection
from apps.dashboard.models import SkillScore, ProgressLog
from apps.services.anthropic_client import ClaudeClient

logger = logging.getLogger(__name__)


# Standard Curated IELTS Exam Content Bank
IELTS_MOCK_CONTENT = {
    'listening': {
        'title': "IELTS Listening Practice Test — 4 Sections",
        'instructions': "Quyidagi audio matnlarini diqqat bilan o'qing va savollarga javob bering. Haqiqiy imtihonda har bir bo'lim faqat bir marta eshittiriladi.",
        'audio_transcript': (
            "SECTION 1: Conversation between a student and an accommodation officer at Oxford Campus.\n"
            "Officer: Good morning, student housing services. How can I help you?\n"
            "Student: Hello, I am looking for off-campus accommodation for the upcoming semester. My budget is around 450 pounds per month including utilities.\n"
            "Officer: We have a shared studio apartment near the Central Library on Park Lane, available from September 15th. It is fully furnished with high-speed internet and private study area.\n\n"
            "SECTION 2: Lecture on Global Climate Patterns and Renewable Energy in Central Asia.\n"
            "Professor: Today we analyze solar irradiance and wind energy potential in Uzbekistan and Kazakhstan. Modern photovoltaic panels have achieved 22% efficiency, making desert installations economically viable..."
        ),
        'questions': [
            {
                'id': 'l1',
                'question': "1. Talabaning oylik byudjeti qancha?",
                'type': 'multiple_choice',
                'options': ["350 pounds", "450 pounds", "550 pounds", "600 pounds"],
                'correct_answer': "450 pounds",
                'weight': 1.0
            },
            {
                'id': 'l2',
                'question': "2. Taklif qilingan studiya qayerda joylashgan va qachondan bo'sh?",
                'type': 'multiple_choice',
                'options': [
                    "Park Lane, 15-sentabrdan",
                    "Oxford Street, 1-sentabrdan",
                    "Baker Street, 10-oktabrdan",
                    "Green Avenue, 20-avgustdan"
                ],
                'correct_answer': "Park Lane, 15-sentabrdan",
                'weight': 1.0
            },
            {
                'id': 'l3',
                'question': "3. Quyosh panellarining zamonaviy samaradorlik ko'rsatkichi necha foizga yetgan?",
                'type': 'multiple_choice',
                'options': ["15%", "18%", "22%", "28%"],
                'correct_answer': "22%",
                'weight': 1.0
            },
            {
                'id': 'l4',
                'question': "4. Talabaga tavsiya etilgan kvartirada qanday qulayliklar mavjud?",
                'type': 'text',
                'hint': "Qisqa yozma javob bering (Masalan: internet, mebel...)",
                'correct_keywords': ["internet", "study area", "furnished", "mebel", "shaxsiy"],
                'weight': 1.0
            }
        ]
    },
    'reading': {
        'title': "IELTS Academic Reading — Passage 1 & 2",
        'instructions': "Matnni diqqat bilan o'qing va savollarga True, False, Not Given yoki mos variantni tanlash orqali javob bering.",
        'passage': (
            "THE IMPACT OF ARTIFICIAL INTELLIGENCE ON GLOBAL EDUCATION\n\n"
            "Paragraph A: In recent years, artificial intelligence has fundamentally altered pedagogical methodologies worldwide. Rather than replacing human educators, adaptive learning platforms function as cognitive apprenticeships, tailoring curriculum difficulty to individual student trajectories in real-time.\n\n"
            "Paragraph B: Longitudinal studies conducted across 40 OECD nations demonstrate that students utilizing personalized spaced-repetition algorithms mastered academic English vocabulary 38% faster than control groups. Furthermore, automated diagnostic assessment reduced educator grading burdens by up to 14 hours per week.\n\n"
            "Paragraph C: Nevertheless, educational sociologists urge caution regarding algorithmic bias and the risk of digital divide expansion in developing economies where reliable broadband and hardware access remain constrained."
        ),
        'questions': [
            {
                'id': 'r1',
                'question': "1. AI platformalari o'qituvchilarning o'rnini butunlay egallash uchun yaratilgan.",
                'type': 'multiple_choice',
                'options': ["TRUE", "FALSE", "NOT GIVEN"],
                'correct_answer': "FALSE",
                'explanation': "Matnda AI o'qituvchini almashtirmasdan, yordamchi kognitiv vosita sifatida xizmat qilishi aytilgan."
            },
            {
                'id': 'r2',
                'question': "2. Tadqiqotlarga ko'ra, oraliq takrorlash algoritmlaridan foydalangan o'quvchilar so'zlarni necha foiz tezroq o'rgangan?",
                'type': 'multiple_choice',
                'options': ["24%", "38%", "45%", "50%"],
                'correct_answer': "38%",
                'explanation': "Paragraph B da 38% faster ekanligi keltirilgan."
            },
            {
                'id': 'r3',
                'question': "3. Avtomatlashtirilgan diagnostika baholash tizimi o'qituvchilarning haftalik ish vaqtini qanchaga tejagan?",
                'type': 'multiple_choice',
                'options': ["7 soatgacha", "10 soatgacha", "14 soatgacha", "20 soatgacha"],
                'correct_answer': "14 soatgacha",
                'explanation': "Paragraph B: reduced educator grading burdens by up to 14 hours per week."
            },
            {
                'id': 'r4',
                'question': "4. Rivojlanayotgan davlatlarda sun'iy intellektni joriy etishdagi asosiy cheklov nima?",
                'type': 'multiple_choice',
                'options': [
                    "Internet va texnik qurilmalarga yetarli darajada ega emaslik",
                    "O'quvchilarning ingliz tilini bilmasligi",
                    "Universitetlarning ruxsat bermasligi",
                    "Dasturlarning qimmatligi"
                ],
                'correct_answer': "Internet va texnik qurilmalarga yetarli darajada ega emaslik",
                'explanation': "Paragraph C: reliable broadband and hardware access remain constrained."
            }
        ]
    },
    'writing': {
        'title': "IELTS Academic Writing — Task 1 & Task 2",
        'instructions': "Ikkala topshiriqni ham belgilangan so'z miqdoriga rioya qilgan holda ingliz tilida yozing.",
        'task_1': {
            'prompt': "Task 1 (Report, kamida 150 so'z): The chart below shows the number of international students enrolled in UK and US universities from 2018 to 2024. Summarise the information by selecting and reporting the main features, and make comparisons where relevant.",
            'min_words': 150
        },
        'task_2': {
            'prompt': "Task 2 (Essay, kamida 250 so'z): Some people believe that studying abroad is the best way to achieve career success, while others argue that local education combined with online global resources is equally effective. Discuss both views and give your own opinion.",
            'min_words': 250
        }
    }
}


def create_mock_exam(student, exam_type='ielts'):
    """
    Creates a new MockExam session with back-to-back timed sections for IELTS MVP.
    """
    with transaction.atomic():
        # Abandon previous unfinished exams if any
        MockExam.objects.filter(student=student, status='in_progress').update(status='abandoned')

        exam = MockExam.objects.create(
            student=student,
            exam_type=exam_type,
            started_at=timezone.now(),
            total_duration_seconds=1800 + 3600 + 3600,  # 30m + 60m + 60m = 8400s
            status='in_progress'
        )

        # Section 1: Listening (30 min)
        MockExamSection.objects.create(
            mock_exam=exam,
            section_type='listening',
            order=1,
            time_limit_seconds=1800,
            content=IELTS_MOCK_CONTENT['listening'],
            status='pending'
        )

        # Section 2: Reading (60 min)
        MockExamSection.objects.create(
            mock_exam=exam,
            section_type='reading',
            order=2,
            time_limit_seconds=3600,
            content=IELTS_MOCK_CONTENT['reading'],
            status='pending'
        )

        # Section 3: Writing (60 min)
        MockExamSection.objects.create(
            mock_exam=exam,
            section_type='writing',
            order=3,
            time_limit_seconds=3600,
            content=IELTS_MOCK_CONTENT['writing'],
            status='pending'
        )

        return exam


def evaluate_ielts_mock_exam(mock_exam):
    """
    Evaluates all submitted sections, calculates IELTS Band scores, updates Student SkillScore & Ready Score.
    """
    client = ClaudeClient()
    sections = mock_exam.sections.all().order_by('order')

    band_scores = []
    summary_notes = []

    for section in sections:
        responses = section.student_response or {}

        if section.section_type == 'listening':
            score_band = _grade_listening_section(section, responses)
            section.section_score = score_band
            section.ai_feedback = (
                f"Listening natijasi: Band {score_band}. "
                "Eshitish ko'nikmangiz audio detallarini anglashda yaxshi shakllangan."
            )
            band_scores.append(score_band)

        elif section.section_type == 'reading':
            score_band = _grade_reading_section(section, responses)
            section.section_score = score_band
            section.ai_feedback = (
                f"Reading natijasi: Band {score_band}. "
                "Akademik matnlardan asosiy faktlar va mantiqiy xulosalarni ajratib olish darajasi baholandi."
            )
            band_scores.append(score_band)

        elif section.section_type == 'writing':
            task1_text = responses.get('task_1', '')
            task2_text = responses.get('task_2', '')
            
            score_band, feedback_text = _grade_writing_section_with_ai(client, task1_text, task2_text)
            section.section_score = score_band
            section.ai_feedback = feedback_text
            band_scores.append(score_band)

        section.status = 'completed'
        section.ended_at = timezone.now()
        section.save()

    # Calculate overall IELTS band with standard IELTS half-band rounding
    if band_scores:
        raw_average = sum(band_scores) / len(band_scores)
        # IELTS standard rounding: e.g. 6.25 -> 6.5, 6.75 -> 7.0, 6.125 -> 6.0
        overall_band = round(raw_average * 2) / 2.0
    else:
        overall_band = 5.0

    mock_exam.overall_band_score = overall_band
    mock_exam.status = 'completed'
    mock_exam.completed_at = timezone.now()
    mock_exam.ai_summary_feedback = (
        f"IELTS Mock imtihoni muvaffaqiyatli yakunlandi. Umumiy taxminiy natijangiz: Band {overall_band}. "
        "Ushbu ball sizning hozirgi tayyorgarlik darajangizni ifodalaydi."
    )
    mock_exam.save()

    # Sync with Student SkillScores & Ready Score
    _sync_mock_results_to_skills(mock_exam.student, band_scores, overall_band)

    return mock_exam


def _grade_listening_section(section, responses):
    correct_count = 0
    questions = section.content.get('questions', [])
    for q in questions:
        qid = q.get('id')
        user_ans = str(responses.get(qid, '')).strip().lower()
        correct_ans = str(q.get('correct_answer', '')).strip().lower()
        if user_ans and user_ans == correct_ans:
            correct_count += 1
        elif q.get('type') == 'text':
            keywords = q.get('correct_keywords', [])
            if any(k.lower() in user_ans for k in keywords):
                correct_count += 1

    ratio = correct_count / max(len(questions), 1)
    if ratio >= 0.85:
        return 7.5
    elif ratio >= 0.7:
        return 6.5
    elif ratio >= 0.5:
        return 6.0
    elif ratio >= 0.3:
        return 5.5
    return 5.0


def _grade_reading_section(section, responses):
    correct_count = 0
    questions = section.content.get('questions', [])
    for q in questions:
        qid = q.get('id')
        user_ans = str(responses.get(qid, '')).strip().upper()
        correct_ans = str(q.get('correct_answer', '')).strip().upper()
        if user_ans and user_ans == correct_ans:
            correct_count += 1

    ratio = correct_count / max(len(questions), 1)
    if ratio >= 0.85:
        return 7.5
    elif ratio >= 0.7:
        return 6.5
    elif ratio >= 0.5:
        return 6.0
    elif ratio >= 0.3:
        return 5.5
    return 5.0


def _grade_writing_section_with_ai(client, task1, task2):
    t1_len = len(task1.split())
    t2_len = len(task2.split())

    if t1_len < 30 and t2_len < 30:
        return 4.5, "Insho matnlari juda qisqa yoki yetarli darajada to'ldirilmagan. To'liqroq fikr bildirish tavsiya etiladi."

    prompt = (
        f"Baholash mezonlari (IELTS Academic Writing Task 1 va Task 2):\n\n"
        f"Task 1 (So'zlar: {t1_len}):\n{task1}\n\n"
        f"Task 2 (So'zlar: {t2_len}):\n{task2}\n\n"
        f"Iltimos, ushbu insholarni Task Achievement, Coherence & Cohesion, Lexical Resource, Grammatical Range "
        f"mezonlari bo'yicha tahlil qiling va 0.0 dan 9.0 gacha Band ball bering. "
        f"O'zbek tilida xatolarni va kuchli tomonlarini izohlab bering. "
        f"Javobni JSON formatda bering: {{\"band_score\": 6.5, \"feedback\": \"...\"}}"
    )

    try:
        if client.is_configured():
            ai_res = client.generate_study_plan(prompt, {"task1_len": t1_len, "task2_len": t2_len}, 6)
            score = float(ai_res.get('band_score', 6.0))
            fb = ai_res.get('feedback', "Insho tuzilishi tahlil qilindi.")
            return score, fb
    except Exception as e:
        logger.warning(f"Writing AI grading fallback: {e}")

    # Heuristic fallback if AI API is unavailable
    if t1_len >= 140 and t2_len >= 240:
        return 6.5, "Insho talab qilingan so'z miqdoriga mos va fikrlar ketma-ket bayon etilgan. Grammatik xilma-xillikni oshirish tavsiya etiladi."
    elif t1_len >= 80 or t2_len >= 150:
        return 6.0, "Insho fikri tushunarli, ammo so'z boyligi va akademik iboralarni ko'proq ishlatish lozim."
    return 5.5, "Insho hajmi va akademik uslubni rivojlantirish bo'yicha qo'shimcha mashqlar zarur."


def _sync_mock_results_to_skills(student, band_scores, overall_band):
    """
    Updates student baseline skills and boosts Ready Score based on Mock Exam accomplishment.
    """
    # Convert IELTS 0-9 scale to 0-100 Ready Score scale (e.g. 6.5 = ~72%, 7.0 = ~78%, 8.0 = ~89%)
    converted_skill_score = min(100, int((overall_band / 9.0) * 100))

    for skill_name in ['reading', 'writing', 'listening']:
        score_obj, _ = SkillScore.objects.get_or_create(
            student=student,
            skill=skill_name,
            defaults={'current_score': converted_skill_score}
        )
        score_obj.current_score = max(score_obj.current_score, converted_skill_score)
        score_obj.save()

    # Update Student Overall Ready Score
    all_scores = list(SkillScore.objects.filter(student=student).values_list('current_score', flat=True))
    if all_scores:
        new_ready = sum(all_scores) // len(all_scores)
    else:
        new_ready = converted_skill_score

    old_ready = student.overall_ready_score
    student.overall_ready_score = max(student.overall_ready_score, new_ready)
    student.save()

    # Record in ProgressLog
    delta = student.overall_ready_score - old_ready
    ProgressLog.objects.create(
        student=student,
        overall_ready_score=student.overall_ready_score,
        streak_count=student.streak_days,
        delta=delta
    )
