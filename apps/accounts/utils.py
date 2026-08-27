"""
Uzbek phone number normalization and formatting utilities.
"""
import re
from django.core.exceptions import ValidationError

UZBEK_PHONE_REGEX = re.compile(
    r'^\+998(33|50|55|70|71|72|73|74|75|76|77|78|79|88|90|91|93|94|95|97|98|99)\d{7}$'
)

def normalize_uzbek_phone(raw_phone: str) -> str:
    """
    Normalizes any Uzbek phone number variation into canonical +998XXXXXXXXX format.

    Supported input variations:
      - "901234567"          -> "+998901234567"
      - "998901234567"        -> "+998901234567"
      - "+998901234567"       -> "+998901234567"
      - "+998 90 123 45 67"   -> "+998901234567"
      - "+998 (90) 123-45-67" -> "+998901234567"
      - "8 90 123 45 67"      -> "+998901234567"
      - "8901234567"          -> "+998901234567"
      - "90-123-45-67"        -> "+998901234567"
      - "(90) 123-45-67"      -> "+998901234567"
    """
    if not raw_phone or not str(raw_phone).strip():
        raise ValidationError("Telefon raqami kiritilishi shart.")

    # Strip all whitespace, parens, hyphens, dots
    cleaned = re.sub(r'[^\d+]', '', str(raw_phone).strip())

    # Strip leading '+' if present to inspect digits
    digits = cleaned.lstrip('+')

    if not digits.isdigit():
        raise ValidationError("Telefon raqami noto'g'ri kiritildi (+998XXXXXXXXX formatida bo'lishi kerak).")

    # Handle digit lengths
    if len(digits) == 9:
        normalized = f"+998{digits}"
    elif len(digits) == 10 and digits.startswith('8'):
        normalized = f"+998{digits[1:]}"
    elif len(digits) == 12 and digits.startswith('998'):
        normalized = f"+{digits}"
    else:
        raise ValidationError("Telefon raqami noto'g'ri kiritildi (+998XXXXXXXXX formatida bo'lishi kerak).")

    # Validate against 13-char +998XXXXXXXXX format
    if not re.match(r'^\+998\d{9}$', normalized):
        raise ValidationError("Telefon raqami noto'g'ri kiritildi (+998XXXXXXXXX formatida bo'lishi kerak).")

    return normalized


def is_valid_uzbek_phone(raw_phone: str) -> bool:
    """
    Returns True if the raw phone string can be normalized to a valid Uzbek phone number.
    """
    try:
        norm = normalize_uzbek_phone(raw_phone)
        return bool(norm)
    except ValidationError:
        return False


def format_uzbek_phone_display(phone_number: str) -> str:
    """
    Formats +998901234567 into '+998 (90) 123-45-67' for human-readable display.
    """
    try:
        norm = normalize_uzbek_phone(phone_number)
        return f"{norm[:4]} ({norm[4:6]}) {norm[6:9]}-{norm[9:11]}-{norm[11:]}"
    except ValidationError:
        return str(phone_number) if phone_number else ""

