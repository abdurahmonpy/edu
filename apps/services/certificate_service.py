"""
Certificate Service:
- Standardized test certificate validity checking (3-year / 1095-day threshold).
- Deterministic score normalizers converting IELTS, TOEFL iBT, SAT Digital, Duolingo DET, and CEFR
  into 5 SkillScore dimensions (reading, writing, listening, speaking, grammar) on a 0-100 scale.
- Atomic processing and persistence of TestCertificate records, SkillScores, and ProgressLog entries.
"""

from datetime import date, datetime
import logging
from typing import Dict, Any, Optional, Tuple, Union
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.accounts.models import Student
from apps.onboarding.models import TestCertificate
from apps.dashboard.models import SkillScore, ProgressLog

logger = logging.getLogger(__name__)

SKILL_NAMES = ['reading', 'writing', 'listening', 'speaking', 'grammar']

VALID_CERTIFICATE_MAX_AGE_DAYS = 1095  # Exactly 3 years (3 * 365 days)

IELTS_SCORE_MAP = {
    9.0: 100, 8.5: 95, 8.0: 90, 7.5: 85,
    7.0: 80, 6.5: 72, 6.0: 65, 5.5: 55,
    5.0: 45, 4.5: 35, 4.0: 25, 3.5: 18, 3.0: 10
}

CEFR_SCORE_MAP = {
    'C2': 95,
    'C1': 85,
    'B2': 70,
    'B1': 55,
    'A2': 40,
    'A1': 25
}


class CertificateValidationError(ValidationError, ValueError):
    """
    Validation error raised for invalid certificate scores, dates, or types.
    Inherits from both Django ValidationError and standard ValueError for seamless test/form compatibility.
    """
    def __init__(self, message, code=None, params=None):
        super().__init__(message, code=code, params=params)
        self.message = str(message)


def _parse_date(d: Union[date, str]) -> date:
    """Helper to convert date or string in YYYY-MM-DD format to a datetime.date object."""
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        return datetime.strptime(d.strip(), '%Y-%m-%d').date()
    raise CertificateValidationError(f"Noto'g'ri sana formati: {d}")


def check_certificate_validity(test_date: Union[date, str], reference_date: Optional[Union[date, str]] = None) -> Tuple[bool, int]:
    """
    Checks if a certificate was taken within the 3-year validity window (<= 1095 days).

    Args:
        test_date: The date when the test was taken.
        reference_date: The comparison date (defaults to timezone.localdate()).

    Returns:
        (is_valid, age_in_days):
            - is_valid: True if 0 <= age_in_days <= 1095, False if age_in_days > 1095.
            - age_in_days: Number of days between reference_date and test_date.

    Raises:
        CertificateValidationError: If test_date is in the future (age_in_days < 0).
    """
    t_date = _parse_date(test_date)
    ref_date = _parse_date(reference_date) if reference_date else timezone.localdate()

    if t_date > ref_date:
        raise CertificateValidationError("Sertifikat sanasi kelajakda bo'lishi mumkin emas.")

    age_in_days = (ref_date - t_date).days
    if age_in_days < 0:
        raise CertificateValidationError("Sertifikat sanasi kelajakda bo'lishi mumkin emas.")

    is_valid = age_in_days <= VALID_CERTIFICATE_MAX_AGE_DAYS
    return is_valid, age_in_days


def convert_ielts_to_skill_scores(overall: float, section_scores: Optional[Dict[str, float]] = None) -> Dict[str, int]:
    """
    Converts IELTS score (0.0 - 9.0 in 0.5 steps) to 5 SkillScores (0-100).

    Args:
        overall: Overall band score (0.0 to 9.0, step 0.5).
        section_scores: Optional dict with 'reading', 'listening', 'writing', 'speaking'.

    Returns:
        Dict with 'reading', 'listening', 'writing', 'speaking', 'grammar' integer scores (0-100).
    """
    try:
        overall_float = float(overall)
    except (ValueError, TypeError):
        raise CertificateValidationError("IELTS bali son ko'rinishida bo'lishi shart.")

    if not (0.0 <= overall_float <= 9.0 and (round(overall_float * 2) == overall_float * 2)):
        raise CertificateValidationError("IELTS bali 0.0 dan 9.0 gacha va 0.5 qadamli bo'lishi shart.")

    def _to_100(val: float) -> int:
        return IELTS_SCORE_MAP.get(val, max(10, min(100, round((val / 9.0) * 100))))

    sections = section_scores or {}

    # Validate section scores if provided
    for sec_name in ['reading', 'listening', 'writing', 'speaking']:
        if sec_name in sections:
            try:
                sec_val = float(sections[sec_name])
            except (ValueError, TypeError):
                raise CertificateValidationError(f"IELTS {sec_name} bali son ko'rinishida bo'lishi shart.")
            if not (0.0 <= sec_val <= 9.0 and (round(sec_val * 2) == sec_val * 2)):
                raise CertificateValidationError(f"IELTS {sec_name} bali 0.0 dan 9.0 gacha va 0.5 qadamli bo'lishi shart.")

    r = _to_100(float(sections.get('reading', overall_float)))
    l = _to_100(float(sections.get('listening', overall_float)))
    w = _to_100(float(sections.get('writing', overall_float)))
    s = _to_100(float(sections.get('speaking', overall_float)))
    g = round((r + w) / 2)

    return {
        'reading': r,
        'listening': l,
        'writing': w,
        'speaking': s,
        'grammar': g
    }


def convert_toefl_to_skill_scores(overall: int, section_scores: Optional[Dict[str, int]] = None) -> Dict[str, int]:
    """
    Converts TOEFL iBT score (0 - 120) to 5 SkillScores (0-100).

    Args:
        overall: Overall score (0 to 120).
        section_scores: Optional dict with 'reading', 'listening', 'speaking', 'writing' (0 to 30 each).

    Returns:
        Dict with 'reading', 'listening', 'speaking', 'writing', 'grammar' integer scores (0-100).
    """
    try:
        overall_int = int(overall)
    except (ValueError, TypeError):
        raise CertificateValidationError("TOEFL bali butun son bo'lishi shart.")

    if not (0 <= overall_int <= 120):
        raise CertificateValidationError("TOEFL bali 0 dan 120 gacha bo'lishi shart.")

    sections = section_scores or {}
    r_raw = sections.get('reading', round(overall_int / 4.0))
    l_raw = sections.get('listening', round(overall_int / 4.0))
    s_raw = sections.get('speaking', round(overall_int / 4.0))
    w_raw = sections.get('writing', round(overall_int / 4.0))

    for sec_name, val in [('reading', r_raw), ('listening', l_raw), ('speaking', s_raw), ('writing', w_raw)]:
        try:
            val_int = int(val)
        except (ValueError, TypeError):
            raise CertificateValidationError(f"TOEFL {sec_name} bali butun son bo'lishi shart.")
        if not (0 <= val_int <= 30):
            raise CertificateValidationError(f"TOEFL {sec_name} bali 0 dan 30 gacha bo'lishi shart.")

    r = min(100, max(10, round((int(r_raw) / 30.0) * 100)))
    l = min(100, max(10, round((int(l_raw) / 30.0) * 100)))
    s = min(100, max(10, round((int(s_raw) / 30.0) * 100)))
    w = min(100, max(10, round((int(w_raw) / 30.0) * 100)))
    g = round((r + w) / 2)

    return {
        'reading': r,
        'listening': l,
        'speaking': s,
        'writing': w,
        'grammar': g
    }


def convert_sat_to_skill_scores(overall: int, section_scores: Optional[Dict[str, int]] = None) -> Dict[str, int]:
    """
    Converts SAT Digital score (400 - 1600 in increments of 10) to 5 SkillScores (0-100).

    Args:
        overall: Overall score (400 to 1600, multiple of 10).
        section_scores: Optional dict with 'ebrw' (200-800, multiple of 10) and 'math'.

    Returns:
        Dict with 'reading', 'writing', 'grammar', 'listening', 'speaking' integer scores (0-100).
    """
    try:
        overall_int = int(overall)
    except (ValueError, TypeError):
        raise CertificateValidationError("SAT bali butun son bo'lishi shart.")

    if not (400 <= overall_int <= 1600 and overall_int % 10 == 0):
        raise CertificateValidationError("SAT bali 400 dan 1600 gacha va 10 ga karrali bo'lishi shart.")

    sections = section_scores or {}
    ebrw = sections.get('ebrw', sections.get('reading_writing', overall_int // 2))
    math = sections.get('math', overall_int // 2)

    try:
        ebrw_int = int(ebrw)
        math_int = int(math)
    except (ValueError, TypeError):
        raise CertificateValidationError("SAT bo'lim ballari butun son bo'lishi shart.")

    if not (200 <= ebrw_int <= 800 and ebrw_int % 10 == 0):
        raise CertificateValidationError("SAT EBRW bali 200 dan 800 gacha bo'lishi shart.")
    if not (200 <= math_int <= 800 and math_int % 10 == 0):
        raise CertificateValidationError("SAT Math bali 200 dan 800 gacha bo'lishi shart.")

    reading = max(10, min(100, round(((ebrw_int - 200) / 600.0) * 100)))
    writing = reading
    grammar = reading
    listening = max(30, min(95, reading - 5))
    speaking = max(30, min(95, reading - 5))

    return {
        'reading': reading,
        'writing': writing,
        'grammar': grammar,
        'listening': listening,
        'speaking': speaking
    }


def convert_det_to_skill_scores(overall: int, section_scores: Optional[Dict[str, int]] = None) -> Dict[str, int]:
    """
    Converts Duolingo English Test (DET) score (10 - 160 in increments of 5) to 5 SkillScores (0-100).

    Args:
        overall: Overall score (10 to 160, multiple of 5).
        section_scores: Optional dict with 'comprehension', 'production', 'conversation', 'literacy'.

    Returns:
        Dict with 'reading', 'writing', 'listening', 'speaking', 'grammar' integer scores (0-100).
    """
    try:
        overall_int = int(overall)
    except (ValueError, TypeError):
        raise CertificateValidationError("Duolingo DET bali butun son bo'lishi shart.")

    if not (10 <= overall_int <= 160 and overall_int % 5 == 0):
        raise CertificateValidationError("Duolingo DET bali 10 dan 160 gacha va 5 ga karrali bo'lishi shart.")

    sections = section_scores or {}
    comp = sections.get('comprehension', overall_int)
    prod = sections.get('production', overall_int)
    conv = sections.get('conversation', overall_int)
    lit = sections.get('literacy', overall_int)

    for sec_name, val in [('comprehension', comp), ('production', prod), ('conversation', conv), ('literacy', lit)]:
        try:
            val_int = int(val)
        except (ValueError, TypeError):
            raise CertificateValidationError(f"Duolingo DET {sec_name} bali butun son bo'lishi shart.")
        if not (10 <= val_int <= 160 and val_int % 5 == 0):
            raise CertificateValidationError(f"Duolingo DET bo'lim bali 10 dan 160 gacha va 5 ga karrali bo'lishi shart.")

    r = max(10, min(100, round(((int(comp) - 10) / 150.0) * 100)))
    w = max(10, min(100, round(((int(prod) - 10) / 150.0) * 100)))
    l = max(10, min(100, round(((int(conv) - 10) / 150.0) * 100)))
    s = l
    g = max(10, min(100, round(((int(lit) - 10) / 150.0) * 100)))

    return {
        'reading': r,
        'writing': w,
        'listening': l,
        'speaking': s,
        'grammar': g
    }


def convert_cefr_to_skill_scores(level: Union[str, float, int]) -> Dict[str, int]:
    """
    Converts CEFR level (A1-C2) to 5 SkillScores (0-100).

    Args:
        level: CEFR level string ('A1', 'A2', 'B1', 'B2', 'C1', 'C2') or numeric score.

    Returns:
        Dict with 'reading', 'writing', 'listening', 'speaking', 'grammar' integer scores (0-100).
    """
    if isinstance(level, str):
        lvl_key = level.strip().upper()
        if lvl_key not in CEFR_SCORE_MAP:
            raise CertificateValidationError(f"Noto'g'ri CEFR darajasi: {level}")
        base = CEFR_SCORE_MAP[lvl_key]
    elif isinstance(level, (int, float)):
        val = float(level)
        if val >= 95:
            base = 95
        elif val >= 85:
            base = 85
        elif val >= 70:
            base = 70
        elif val >= 55:
            base = 55
        elif val >= 40:
            base = 40
        else:
            base = 25
    else:
        raise CertificateValidationError(f"Noto'g'ri CEFR qiymati: {level}")

    return {
        'reading': base,
        'writing': base,
        'listening': base,
        'speaking': base,
        'grammar': base
    }


def convert_certificate_to_skill_scores(
    cert_type: str,
    overall_score: Union[float, int, str],
    section_scores: Optional[Dict[str, Any]] = None
) -> Dict[str, int]:
    """
    Generic dispatcher normalizing any supported certificate type to 5 SkillScores (0-100).

    Args:
        cert_type: 'ielts', 'toefl', 'sat', 'duolingo', 'cefr' (case-insensitive).
        overall_score: Test overall score (float, int, or CEFR level string).
        section_scores: Optional breakdown dict.

    Returns:
        Dict with 5 SkillScores (reading, writing, listening, speaking, grammar).
    """
    if not cert_type:
        raise CertificateValidationError("Sertifikat turi ko'rsatilishi shart.")

    norm_type = str(cert_type).strip().lower()

    if norm_type in ['ielts']:
        return convert_ielts_to_skill_scores(float(overall_score), section_scores)

    if norm_type in ['toefl', 'toefl_ibt', 'toefl ibt']:
        return convert_toefl_to_skill_scores(int(overall_score), section_scores)

    if norm_type in ['sat', 'sat_digital', 'sat digital']:
        return convert_sat_to_skill_scores(int(overall_score), section_scores)

    if norm_type in ['duolingo', 'det', 'duolingo english test', 'duolingo english test (det)']:
        return convert_det_to_skill_scores(int(overall_score), section_scores)

    if norm_type in ['cefr', 'cefr_milliy', 'milliy', 'cefr / milliy sertifikat']:
        return convert_cefr_to_skill_scores(overall_score)

    raise CertificateValidationError(f"Qo'llab-quvvatlanmaydigan sertifikat turi: {cert_type}")


def _normalize_certificate_type_for_model(cert_type: str) -> str:
    """Normalizes raw cert_type string to match TestCertificate.CERTIFICATE_TYPE_CHOICES."""
    norm = str(cert_type).strip().lower()
    if norm in ['ielts']:
        return 'ielts'
    if norm in ['toefl', 'toefl_ibt', 'toefl ibt']:
        return 'toefl'
    if norm in ['sat', 'sat_digital', 'sat digital']:
        return 'sat'
    if norm in ['duolingo', 'det', 'duolingo english test', 'duolingo english test (det)']:
        return 'duolingo'
    if norm in ['cefr', 'cefr_milliy', 'milliy', 'cefr / milliy sertifikat']:
        return 'cefr'
    return 'ielts'


@transaction.atomic
def process_and_save_certificate(
    student: Student,
    cert_type: str,
    test_date: Union[date, str],
    overall_score: Union[float, int, str],
    section_scores: Optional[Dict[str, Any]] = None
) -> Tuple[TestCertificate, bool]:
    """
    Validates, normalizes, and persists a TestCertificate.
    If valid (<= 1095 days old), updates/creates 5 SkillScore records and a ProgressLog entry.

    Args:
        student: Student model instance.
        cert_type: Certificate type ('ielts', 'toefl', 'sat', 'duolingo', 'cefr').
        test_date: Date when the exam was taken.
        overall_score: Overall test score.
        section_scores: Optional breakdown dictionary.

    Returns:
        (certificate, is_valid):
            - certificate: TestCertificate instance saved to DB.
            - is_valid: Boolean indicating whether certificate is valid (<= 3 years).
    """
    t_date = _parse_date(test_date)
    is_valid, age_in_days = check_certificate_validity(t_date)

    normalized_model_type = _normalize_certificate_type_for_model(cert_type)
    skill_scores = convert_certificate_to_skill_scores(cert_type, overall_score, section_scores)

    # Determine numeric score to store in TestCertificate.overall_score
    if isinstance(overall_score, (int, float)):
        stored_overall = float(overall_score)
    elif str(overall_score).strip().upper() in CEFR_SCORE_MAP:
        stored_overall = float(CEFR_SCORE_MAP[str(overall_score).strip().upper()])
    else:
        try:
            stored_overall = float(overall_score)
        except (ValueError, TypeError):
            stored_overall = float(skill_scores.get('reading', 70))

    stored_section_scores = dict(section_scores) if section_scores else {}
    if isinstance(overall_score, str) and str(overall_score).strip().upper() in CEFR_SCORE_MAP:
        stored_section_scores['cefr_level'] = str(overall_score).strip().upper()

    # 1. Create or update TestCertificate
    certificate, _ = TestCertificate.objects.update_or_create(
        student=student,
        certificate_type=normalized_model_type,
        test_date=t_date,
        defaults={
            'overall_score': stored_overall,
            'section_scores': stored_section_scores,
            'is_valid': is_valid,
            'verified_at': timezone.now() if is_valid else None
        }
    )

    # 2. If valid, populate SkillScores and ProgressLog
    if is_valid:
        for skill_name in SKILL_NAMES:
            score_val = skill_scores.get(skill_name, 70)
            SkillScore.objects.update_or_create(
                student=student,
                skill=skill_name,
                defaults={'current_score': score_val}
            )

        ready_score = round(sum(skill_scores[s] for s in SKILL_NAMES) / len(SKILL_NAMES))
        today = timezone.localdate()
        cert_display = certificate.get_certificate_type_display()

        ProgressLog.objects.update_or_create(
            student=student,
            date=today,
            defaults={
                'overall_ready_score': ready_score,
                'streak_count': 1,
                'delta': f"Sertifikat tasdiqlandi ({cert_display}: {overall_score})"
            }
        )

    logger.info(
        f"Processed certificate for student {student.id}: type={normalized_model_type}, "
        f"valid={is_valid}, age_days={age_in_days}"
    )

    return certificate, is_valid
