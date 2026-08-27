"""
AI-Driven University & Grant Matching Service for the Kelajak Platform.
Implements multi-factor recommendation engine, tier categorization,
Uzbek Latin rationale and checklist generation, and selection persistence.
"""
import logging
from typing import Dict, Any, List, Optional
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Student
from apps.programs.models import Program, StudentProgram, StudentTargetSelection
from apps.services.score_service import calculate_overall_ready_score

logger = logging.getLogger(__name__)

# Regional & Continental Country Clusters for Partial Region Matching
REGION_CLUSTERS = {
    'north_america': [
        'aqsh', 'aqsh (usa)', 'aqsh davlat departamenti', 'usa', 'united states',
        'kanada', 'canada', 'amerika'
    ],
    'western_europe': [
        'germaniya', 'germany', 'buyuk britaniya', 'uk', 'united kingdom', 'angliya',
        'vengriya', 'hungary', 'shvetsiya', 'sweden', 'fransiya', 'france',
        'italiya', 'italy', 'polsha', 'poland', 'chexiya', 'czech',
        'avstriya', 'austria', 'niderlandiya', 'netherlands', 'shveysariya', 'switzerland',
        'yevropa', 'europe'
    ],
    'east_asia': [
        'janubiy koreya', 'koreya', 'south korea', 'korea',
        'yaponiya', 'japan', 'singapur', 'singapore', 'xitoy', 'china',
        'malayziya', 'malaysia', 'osiyo', 'asia'
    ],
    'middle_east_eurasia': [
        'turkiya', 'turkey', 'turkiye', 'baa', 'uae', 'qatar', 'saudiya arabistoni'
    ],
    'central_asia': [
        "o'zbekiston", 'uzbekistan', "qoraqalpog'iston", 'qozogiston', 'kazakhstan'
    ],
    'global': [
        'xalqaro', 'international', 'global', 'dunyo'
    ]
}

# Academic & Career Field Clusters
FIELD_CLUSTERS = {
    'tech': {
        'codes': ['cs_it', 'ai_ds', 'ai_data', 'engineering'],
        'keywords': ['dasturlash', 'it', 'kompyuter', 'sun\'iy intellekt', 'data science', 'muhandislik', 'robototexnika'],
        'interests': ['coding_web', 'robotics_stem', 'math_olympiad']
    },
    'business_law': {
        'codes': ['business_finance', 'economics', 'international_law', 'law_ir'],
        'keywords': ['biznes', 'moliya', 'iqtisod', 'huquq', 'menejment', 'xalqaro munosabatlar'],
        'interests': ['debate_mun', 'volunteering']
    },
    'medicine_sciences': {
        'codes': ['medicine', 'natural_sciences'],
        'keywords': ['tibbiyot', 'biotexnologiya', 'kimyo', 'fizika', 'biologiya', 'salomatlik'],
        'interests': ['sports_health', 'eco_sustainability', 'reading_research']
    },
    'humanities_arts': {
        'codes': ['humanities_arts', 'education', 'education_humanities', 'architecture_design'],
        'keywords': ['pedagogika', 'san\'at', 'dizayn', 'arxitektura', 'tilshunoslik', 'gumanitar'],
        'interests': ['creative_arts', 'languages', 'reading_research']
    }
}

# Human-readable field names in Uzbek Latin
FIELD_DISPLAY_UZ = {
    'cs_it': "Dasturlash va Axborot Texnologiyalari (CS & IT)",
    'ai_ds': "Sun'iy Intellekt va Data Science",
    'ai_data': "Sun'iy Intellekt va Ma'lumotlar Ilmi",
    'medicine': "Tibbiyot va Sog'liqni Saqlash",
    'business_finance': "Biznes, Moliya va Menejment",
    'engineering': "Muhandislik va Robototexnika",
    'international_law': "Xalqaro Munosabatlar va Huquq",
    'law_ir': "Xalqaro Huquq va Diplomatiya",
    'economics': "Iqtisodiyot va Ekonometrika",
    'natural_sciences': "Aniq va Tabiiy Fanlar (STEM)",
    'humanities_arts': "Gumanitar Fanlar va San'at",
    'education': "Pedagogika va Ta'lim",
    'education_humanities': "Pedagogika va Gumanitar Fanlar",
    'architecture_design': "Arxitektura va Dizayn"
}


def _normalize_string(text: Optional[str]) -> str:
    """Normalizes string for comparison: lowercase, stripped, ASCII-approximated."""
    if not text:
        return ""
    return str(text).strip().lower().replace("'", "").replace("`", "").replace("ʻ", "").replace("’", "")


def _get_country_cluster(country_name: str) -> Optional[str]:
    """Finds which regional cluster a given country belongs to."""
    norm_c = _normalize_string(country_name)
    for cluster_name, countries in REGION_CLUSTERS.items():
        for c in countries:
            if c in norm_c or norm_c in c:
                return cluster_name
    return None


def _calculate_country_score(student: Student, program: Program) -> int:
    r"""
    Factor 1: Country Match ($S_{country} \in [0, 100]$)
    - 100 if program.country in student.target_countries or program is Global/International.
    - 70 if region/continent overlaps.
    - 50 if popular destination hub.
    - 30 otherwise.
    """
    target_countries = student.target_countries or []
    norm_prog_country = _normalize_string(program.country)

    if not target_countries:
        # If no preference set, give neutral baseline
        return 70

    # Check for Global / International programs
    if norm_prog_country in ['xalqaro', 'international', 'global', 'dunyo']:
        return 100

    # Check for exact or substring match in student's target countries
    norm_targets = [_normalize_string(c) for c in target_countries]
    for target in norm_targets:
        if target and (target == norm_prog_country or target in norm_prog_country or norm_prog_country in target):
            return 100

    # Check regional cluster overlap
    prog_cluster = _get_country_cluster(program.country)
    if prog_cluster:
        for target in target_countries:
            target_cluster = _get_country_cluster(target)
            if target_cluster and target_cluster == prog_cluster:
                return 70

    # Popular global destination hubs
    popular_hubs = ['aqsh', 'germaniya', 'turkiya', 'buyuk britaniya', 'janubiy koreya', 'kanada', 'yaponiya', 'singapur']
    if any(hub in norm_prog_country for hub in popular_hubs):
        return 50

    return 30


def _calculate_field_score(student: Student, program: Program) -> int:
    r"""
    Factor 2: Field of Study Match ($S_{field} \in [0, 100]$)
    - 100 if exact match or keyword overlap with target_field_of_study / interests.
    - 70 if related academic cluster overlap.
    - 50 otherwise.
    """
    student_field = getattr(student, 'target_field_of_study', '') or getattr(student, 'target_field', '')
    student_interests = student.interests or []
    reqs = program.requirements or {}
    prog_fields = reqs.get('fields', [])
    prog_field_direct = program.field_of_study or ''

    # If program is open to all fields
    if not prog_field_direct and not prog_fields:
        return 100
    if prog_field_direct in ['all', 'any', 'general', 'barcha']:
        return 100

    # Exact field code match
    if student_field:
        if student_field == prog_field_direct or student_field in prog_fields:
            return 100
        if _normalize_string(student_field) == _normalize_string(prog_field_direct):
            return 100

    # Keyword / cluster overlap
    student_clusters = set()
    for c_name, c_data in FIELD_CLUSTERS.items():
        if student_field in c_data['codes']:
            student_clusters.add(c_name)
        for interest in student_interests:
            if interest in c_data['interests'] or interest in c_data['codes']:
                student_clusters.add(c_name)

    prog_clusters = set()
    for c_name, c_data in FIELD_CLUSTERS.items():
        if prog_field_direct in c_data['codes']:
            prog_clusters.add(c_name)
        for pf in prog_fields:
            if pf in c_data['codes']:
                prog_clusters.add(c_name)
        for kw in c_data['keywords']:
            if kw in _normalize_string(program.name) or kw in _normalize_string(program.description):
                prog_clusters.add(c_name)

    if student_clusters.intersection(prog_clusters):
        return 70

    return 50


def _derive_student_readiness_score(student: Student, ready_score_override: Optional[int] = None) -> int:
    """Computes effective readiness score (0-100) from SkillScores, certificates, or English level."""
    if ready_score_override is not None:
        return max(0, min(100, ready_score_override))

    # 1. Overall Ready Score from active SkillScores
    ready_score = student.overall_ready_score
    if ready_score > 0:
        return ready_score

    # 2. Derive from valid TestCertificate if available
    try:
        from apps.onboarding.models import TestCertificate
        valid_certs = TestCertificate.objects.filter(student=student, is_valid=True).order_by('-created_at')
        if valid_certs.exists():
            cert = valid_certs.first()
            if cert.certificate_type == 'ielts':
                ielts_val = cert.overall_score
                return min(100, max(10, round((ielts_val / 9.0) * 100)))
            elif cert.certificate_type == 'toefl':
                return min(100, max(10, round((cert.overall_score / 120.0) * 100)))
            elif cert.certificate_type == 'sat':
                return min(100, max(10, round(((cert.overall_score - 400) / 1200.0) * 100)))
            elif cert.certificate_type == 'duolingo':
                return min(100, max(10, round(((cert.overall_score - 10) / 150.0) * 100)))
    except Exception:
        pass

    # 3. Derive from English level choice
    level_defaults = {
        'advanced': 85,
        'intermediate': 70,
        'beginner': 50
    }
    return level_defaults.get(getattr(student, 'english_level', 'beginner'), 50)


def _calculate_readiness_score(student: Student, program: Program, ready_score_override: Optional[int] = None) -> int:
    r"""
    Factor 3: Academic & Language Readiness ($S_{readiness} \in [0, 100]$)
    - Compares student's readiness with program requirements (min_ielts, min_sat, min_ready_score).
    - 100 if student_score >= min_required
    - 75 if deficit <= 10 points
    - 50 if deficit <= 20 points
    - 30 if deficit > 20 points
    """
    student_score = _derive_student_readiness_score(student, ready_score_override)
    reqs = program.requirements or {}

    # Determine required benchmark (0-100)
    if 'min_ready_score' in reqs:
        min_required = int(reqs['min_ready_score'])
    elif program.min_ielts:
        ielts = program.min_ielts
        if ielts >= 7.5:
            min_required = 85
        elif ielts >= 7.0:
            min_required = 80
        elif ielts >= 6.5:
            min_required = 75
        elif ielts >= 6.0:
            min_required = 70
        elif ielts >= 5.5:
            min_required = 60
        else:
            min_required = 50
    elif program.min_sat:
        sat = program.min_sat
        if sat >= 1450:
            min_required = 85
        elif sat >= 1350:
            min_required = 80
        elif sat >= 1200:
            min_required = 70
        else:
            min_required = 65
    elif program.min_toefl:
        toefl = program.min_toefl
        if toefl >= 100:
            min_required = 80
        elif toefl >= 80:
            min_required = 75
        elif toefl >= 60:
            min_required = 65
        else:
            min_required = 50
    else:
        min_required = 65

    deficit = min_required - student_score
    if deficit <= 0:
        return 100
    elif deficit <= 10:
        return 75
    elif deficit <= 20:
        return 50
    else:
        return 30


def _calculate_type_score(student: Student, program: Program) -> int:
    r"""
    Factor 4: Program / Budget Fit ($S_{type} \in [0, 100]$)
    - 100 if student.target_program_type matches program.type or budget_preference.
    - 60 otherwise.
    """
    target_type = getattr(student, 'target_program_type', 'grant')
    budget_pref = getattr(student, 'budget_preference', 'toliq_grant')
    prog_type = program.type
    grant_coverage = program.grant_coverage or 'toliq_grant'

    # Direct match on program type
    if target_type == prog_type:
        return 100

    # Full grant alignment
    if budget_pref == 'toliq_grant' and prog_type in ['grant', 'exchange'] and grant_coverage == 'toliq_grant':
        return 100

    # Partial grant alignment
    if budget_pref == 'qisman_grant' and prog_type in ['grant', 'partial_grant', 'exchange']:
        return 100

    # Self-funded covers all programs
    if budget_pref == 'ozi_moliyalashtirish':
        return 100

    return 60


def _generate_match_rationale(
    student: Student,
    program: Program,
    match_score: int,
    tier: str,
    s_country: int,
    s_field: int,
    s_readiness: int,
    s_type: int
) -> str:
    """Generates personalized match rationale in 100% Uzbek Latin script."""
    country_name = program.country
    prog_name = program.name
    field_name = FIELD_DISPLAY_UZ.get(
        student.target_field_of_study or getattr(student, 'target_field', ''),
        "tanlangan mutaxassislik"
    )

    if tier == 'safety':
        rationale = (
            f"Ushbu dastur sizning profilingizga eng yuqori darajada mos keladi ({match_score}%). "
            f"{country_name} davlatida {field_name} bo'yicha ta'lim olish maqsadlaringiz va "
            f"akademik tayyorgarlik darajangiz dasturning barcha saralash mezonlariga to'liq javob beradi. "
            f"Sizda mazkur grantni yutish va qabul qilinish imkoniyati juda yuqori (Safety / Kafolatlangan daraja)."
        )
    elif tier == 'target':
        rationale = (
            f"Ushbu dastur sizning maqsadlaringizga juda yaxshi mos keladi ({match_score}%). "
            f"{country_name} davlati va {field_name} yo'nalishi rejalaringizga to'g'ri keladi. "
            f"Tayyorgarlik ko'rsatkichlaringiz dastur talablariga mos. Tavsiya etilgan o'quv rejasidagi "
            f"mashqlarni muntazam bajarib borsangiz, ushbu dasturga muvaffaqiyatli qabul qilinish imkoniyatingiz yuqori (Target)."
        )
    else:  # reach
        rationale = (
            f"Ushbu dastur siz uchun nufuzli va yuqori marrali tanlov hisoblanadi ({match_score}%). "
            f"{country_name} oliygohlarida raqobat yuqori bo'lganligi sababli, til va akademik ko'rsatkichlarni "
            f"yanada mustahkamlash talab etiladi. Dual-track o'quv rejasi orqali tayyorgarlikni kuchaytirib, "
            f"ushbu yuqori marrani (Reach) zabt etishingiz mumkin."
        )

    return rationale


def _generate_admission_checklist(program: Program) -> List[str]:
    """Generates structured admission checklist in 100% Uzbek Latin script."""
    checklist = []

    # 1. Standardized Language / Academic Test
    if program.min_ielts or program.min_toefl:
        ielts_str = f"IELTS {program.min_ielts}+" if program.min_ielts else ""
        toefl_str = f"TOEFL {program.min_toefl}+" if program.min_toefl else ""
        combined = f"{ielts_str} yoki {toefl_str}".strip(" yoki ")
        checklist.append(f"Xalqaro til sertifikati: kamida {combined} ballini qo'lga kiritish.")
    elif program.min_sat:
        checklist.append(f"SAT Digital imtihonidan kamida {program.min_sat}+ ball to'plash.")
    else:
        checklist.append("Ingliz tili (IELTS / TOEFL) yoki mezbon davlat tili bo'yicha sertifikat tayyorlash.")

    # 2. Academic Transcripts
    if program.min_gpa:
        checklist.append(f"Akademik baholar tabeli (Transkript): GPA kamida {program.min_gpa}+ (ingliz tiliga tarjima va tasdiq).")
    else:
        checklist.append("Akademik baholar tabeli (Transkript) va maktab shahodatnomasini tarjima qilib notarial tasdiqlash.")

    # 3. Statement of Purpose / Motivation Letter
    checklist.append("Motivatsiya inshosi (Statement of Purpose / Personal Statement): kelajak maqsadlari va liderlik salohiyatini yoritish.")

    # 4. Letters of Recommendation
    checklist.append("Tavsiyanomalar: fan o'qituvchilari yoki maktab ma'muriyatidan 2 ta rasmiy tavsiyanoma olish.")

    # 5. Extracurriculars & Specific Requirements
    reqs = program.requirements or {}
    if 'hujjatlar' in reqs and isinstance(reqs['hujjatlar'], list):
        for doc in reqs['hujjatlar']:
            if doc not in checklist and len(doc) > 5:
                checklist.append(f"Qo'shimcha talab: {doc}")

    # 6. Final Submission & Deadline
    deadline_str = program.deadline or "belgilangan muddat"
    source_url_str = program.source_url or "rasmiy portal"
    checklist.append(f"Rasmiy ariza topshirish: {source_url_str} orqali {deadline_str} sanasigacha arizani jo'natish.")

    return checklist


def calculate_program_match(
    student: Student,
    program: Program,
    ready_score: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calculates 4-factor matching percentage and tier for a given student and program.
    
    Formula:
      MatchScore = round(0.25 * S_country + 0.30 * S_field + 0.30 * S_readiness + 0.15 * S_type)
      Tiers: >= 85% Safety, 70-84% Target, < 70% Reach.
    
    Returns comprehensive dictionary with Uzbek Latin rationale, checklist, and breakdown.
    """
    # 1. 4-factor subscores
    s_country = _calculate_country_score(student, program)
    s_field = _calculate_field_score(student, program)
    s_readiness = _calculate_readiness_score(student, program, ready_score_override=ready_score)
    s_type = _calculate_type_score(student, program)

    # 2. Weighted MatchScore
    raw_match = 0.25 * s_country + 0.30 * s_field + 0.30 * s_readiness + 0.15 * s_type
    match_percentage = max(10, min(100, round(raw_match)))

    # 3. Match Tier Classification
    if match_percentage >= 85:
        tier = 'safety'
        tier_display = "Kafolatlangan (Safety)"
        tier_badge = "bg-emerald-50 text-emerald-700 border-emerald-200"
    elif match_percentage >= 70:
        tier = 'target'
        tier_display = "Maqsadli (Target)"
        tier_badge = "bg-blue-50 text-blue-700 border-blue-200"
    else:
        tier = 'reach'
        tier_display = "Yuqori marra (Reach)"
        tier_badge = "bg-amber-50 text-amber-700 border-amber-200"

    # 4. Uzbek Latin Rationale and Checklist
    rationale = _generate_match_rationale(
        student, program, match_percentage, tier,
        s_country, s_field, s_readiness, s_type
    )
    checklist = _generate_admission_checklist(program)

    uni_name = program.university.name if program.university else program.name
    uni_ranking = program.university.world_ranking if program.university else None

    return {
        'program_id': program.id,
        'program': program,
        'program_name': program.name,
        'university_name': uni_name,
        'world_ranking': uni_ranking,
        'country': program.country,
        'type': program.type,
        'type_display': program.get_type_display(),
        'grant_coverage': program.grant_coverage,
        'deadline': program.deadline,
        'source_url': program.source_url,
        'last_verified_date': str(program.last_verified_date),
        'min_ielts': program.min_ielts,
        'min_toefl': program.min_toefl,
        'min_sat': program.min_sat,
        'min_gpa': program.min_gpa,
        'match_percentage': match_percentage,
        'match_score': match_percentage,  # Alias
        'match_tier': tier,
        'match_tier_display': tier_display,
        'tier_badge': tier_badge,
        'match_rationale': rationale,
        'rationale': rationale,            # Alias
        'admission_checklist': checklist,
        'checklist': checklist,            # Alias
        'breakdown': {
            'country_fit': s_country,
            'field_fit': s_field,
            'readiness_fit': s_readiness,
            'type_fit': s_type,
        },
        'criteria_breakdown': {            # Alias
            'country_fit': s_country,
            'field_fit': s_field,
            'readiness_fit': s_readiness,
            'type_fit': s_type,
        },
        'requirements': program.requirements,
        'disclaimer': "AI tavsiyasi — yakuniy qarorni oila va o'quvchi qabul qiladi."
    }


def get_curated_recommendations(
    student: Student,
    limit: int = 5,
    ready_score: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Scores all verified programs in the catalog and returns top 3-5 curated options
    sorted descending by match percentage.
    """
    programs = list(Program.objects.select_related('university').all())

    # If database is empty, seed programs idempotently
    if not programs:
        try:
            from django.core.management import call_command
            call_command('seed_programs')
            programs = list(Program.objects.select_related('university').all())
        except Exception as e:
            logger.warning(f"Could not auto-seed programs: {e}")

    recommendations = []
    for prog in programs:
        match_info = calculate_program_match(student, prog, ready_score=ready_score)
        recommendations.append(match_info)

    # Sort primarily by match_percentage DESC, secondarily by university ranking ASC (better rank first)
    recommendations.sort(
        key=lambda item: (
            item['match_percentage'],
            -(item['world_ranking'] or 9999) if item['world_ranking'] else -9999
        ),
        reverse=True
    )

    return recommendations[:limit]


@transaction.atomic
def save_student_target_selection(
    student: Student,
    primary_program_id: int,
    backup_program_ids: Optional[List[int]] = None,
    notes: str = ''
) -> StudentTargetSelection:
    """
    Persists student's primary and backup university/grant selections into StudentTargetSelection,
    and registers all selected programs into StudentProgram tracker.
    """
    primary_program = Program.objects.get(id=primary_program_id)
    match_result = calculate_program_match(student, primary_program)

    backup_ids = backup_program_ids or []
    backup_programs = list(Program.objects.filter(id__in=backup_ids))

    backup_data = [
        {
            'id': bp.id,
            'name': bp.name,
            'country': bp.country,
            'type': bp.type,
            'grant_coverage': bp.grant_coverage,
            'deadline': bp.deadline,
            'source_url': bp.source_url
        }
        for bp in backup_programs
    ]

    target_sel, created = StudentTargetSelection.objects.update_or_create(
        student=student,
        defaults={
            'primary_program': primary_program,
            'match_score': match_result['match_percentage'],
            'notes': notes,
            'backup_programs_data': backup_data,
        }
    )

    if backup_programs:
        target_sel.backup_programs.set(backup_programs)
    else:
        target_sel.backup_programs.clear()

    # Update StudentProgram tracker
    StudentProgram.objects.get_or_create(student=student, program=primary_program)
    for bp in backup_programs:
        StudentProgram.objects.get_or_create(student=student, program=bp)

    # Update student.target_universities_data if the field is present on Student
    if hasattr(student, 'target_universities_data'):
        data_list = [{'id': primary_program.id, 'name': primary_program.name, 'is_primary': True}]
        for bp in backup_programs:
            data_list.append({'id': bp.id, 'name': bp.name, 'is_primary': False})
        student.target_universities_data = data_list
        student.save(update_fields=['target_universities_data'])

    logger.info(
        f"Target selection saved for student {student.id}: Primary={primary_program.name}, "
        f"Backups={len(backup_programs)}, Match={match_result['match_percentage']}%"
    )

    return target_sel
