"""Dates in the Ethiopian calendar and Ethiopian phone numbers. Standard library only.

    format_date("2026-12-05", "am")  -> "26 ኅዳር 2019 ዓ.ም."
    format_date("2026-12-05", "en")  -> "5 December 2026"
    normalize_phone("0911 22 33 44") -> "+251911223344"
"""

from __future__ import annotations

import datetime as dt
import re

MONTHS_AM = ["መስከረም", "ጥቅምት", "ኅዳር", "ታኅሣሥ", "ጥር", "የካቲት", "መጋቢት", "ሚያዝያ", "ግንቦት", "ሰኔ", "ሐምሌ", "ነሐሴ", "ጳጉሜ"]
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
             "November", "December"]

# Julian Day Number of the day before 1 Meskerem, year 1 (Amete Mihret era).
_ETHIOPIC_EPOCH = 1723856


def to_ethiopian(day: dt.date) -> tuple[int, int, int]:
    """(year, month 1-13, day) in the Ethiopian calendar. Every month has 30 days; the 13th has 5 or 6."""
    jdn = day.toordinal() + 1721425  # date(1, 1, 1) is JDN 1721426
    r = (jdn - _ETHIOPIC_EPOCH) % 1461
    n = r % 365 + 365 * (r // 1460)
    year = 4 * ((jdn - _ETHIOPIC_EPOCH) // 1461) + r // 365 - r // 1460
    return year, n // 30 + 1, n % 30 + 1


def format_date(value, lang: str = "am", short: bool = False) -> str:
    """An ISO date ("2026-12-05") or date, in the Ethiopian calendar for Amharic, Gregorian otherwise.
    Text that is not a date is returned unchanged."""
    try:
        day = value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return str(value)
    if lang == "am":
        year, month, d = to_ethiopian(day)
        return f"{d} {MONTHS_AM[month - 1]}" if short else f"{d} {MONTHS_AM[month - 1]} {year} ዓ.ም."
    month_name = MONTHS_EN[day.month - 1]
    return f"{day.day} {month_name[:3] if short else month_name}" + ("" if short else f" {day.year}")


def normalize_phone(raw: str) -> str:
    """One format for Ethiopian mobile numbers: 09..., 07..., 9..., 251... and +251... become +2519...
    Anything else (a number from another country, or a test name) is returned trimmed, unchanged."""
    text = str(raw or "").strip()
    digits = re.sub(r"[^\d+]", "", text)
    if digits.startswith("+251"):
        rest = digits[4:]
    elif digits.startswith("00251"):
        rest = digits[5:]
    elif digits.startswith("251") and len(digits) == 12:
        rest = digits[3:]
    elif digits.startswith("0") and len(digits) == 10:
        rest = digits[1:]
    elif len(digits) == 9 and digits[0] in "79":
        rest = digits
    else:
        return text[:32]
    return f"+251{rest}" if len(rest) == 9 and rest[0] in "79" else text[:32]
