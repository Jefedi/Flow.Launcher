# -*- coding: utf-8 -*-
"""Date and time-zone calculations for Calculate Anything.

Handles a focused set of natural-language date queries (English + French):

  now / today / maintenant
  time in <city>            now in tokyo          paris time
  in 3 weeks                3 days from now        2 months ago
  days until 2026-12-25     days since 2020-01-01
  days between A and B
  2026-12-25 + 10 days

Uses only the standard library (datetime, zoneinfo). On Windows, ``zoneinfo``
relies on the bundled ``tzdata`` package. Knows nothing about Flow Launcher.
"""

import re
from collections import namedtuple
from datetime import date, datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover
    ZoneInfo = None

    class ZoneInfoNotFoundError(Exception):
        pass

Answer = namedtuple("Answer", ["title", "subtitle", "copy"])


class NotADate(Exception):
    """Raised when the text is not a date/time query (so other handlers can try)."""


WEEKDAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
             "août", "septembre", "octobre", "novembre", "décembre"]

# Month name (en + fr, with common abbreviations) -> month number.
_MONTHS = {}
for i, names in enumerate([
    ("january", "jan", "janvier"), ("february", "feb", "février", "fevrier"),
    ("march", "mar", "mars"), ("april", "apr", "avril"),
    ("may", "mai"), ("june", "jun", "juin"), ("july", "jul", "juillet"),
    ("august", "aug", "août", "aout"), ("september", "sep", "sept", "septembre"),
    ("october", "oct", "octobre"), ("november", "nov", "novembre"),
    ("december", "dec", "décembre", "decembre"),
], start=1):
    for n in names:
        _MONTHS[n] = i

# Common city / alias -> IANA time zone.
CITY_TZ = {
    "utc": "UTC", "gmt": "UTC",
    "paris": "Europe/Paris", "london": "Europe/London", "londres": "Europe/London",
    "berlin": "Europe/Berlin", "madrid": "Europe/Madrid", "rome": "Europe/Rome",
    "amsterdam": "Europe/Amsterdam", "brussels": "Europe/Brussels",
    "bruxelles": "Europe/Brussels", "lisbon": "Europe/Lisbon", "moscow": "Europe/Moscow",
    "moscou": "Europe/Moscow", "istanbul": "Europe/Istanbul", "athens": "Europe/Athens",
    "zurich": "Europe/Zurich", "geneva": "Europe/Zurich", "genève": "Europe/Zurich",
    "dublin": "Europe/Dublin", "stockholm": "Europe/Stockholm",
    "new york": "America/New_York", "newyork": "America/New_York", "nyc": "America/New_York",
    "los angeles": "America/Los_Angeles", "la": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles", "chicago": "America/Chicago",
    "toronto": "America/Toronto", "montreal": "America/Toronto",
    "montréal": "America/Toronto", "mexico": "America/Mexico_City",
    "sao paulo": "America/Sao_Paulo", "são paulo": "America/Sao_Paulo",
    "tokyo": "Asia/Tokyo", "osaka": "Asia/Tokyo", "seoul": "Asia/Seoul",
    "beijing": "Asia/Shanghai", "shanghai": "Asia/Shanghai", "pekin": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong", "singapore": "Asia/Singapore",
    "singapour": "Asia/Singapore", "bangkok": "Asia/Bangkok", "jakarta": "Asia/Jakarta",
    "mumbai": "Asia/Kolkata", "delhi": "Asia/Kolkata", "bangalore": "Asia/Kolkata",
    "dubai": "Asia/Dubai", "dubaï": "Asia/Dubai", "tel aviv": "Asia/Jerusalem",
    "sydney": "Australia/Sydney", "melbourne": "Australia/Melbourne",
    "auckland": "Pacific/Auckland", "honolulu": "Pacific/Honolulu",
    "cairo": "Africa/Cairo", "le caire": "Africa/Cairo",
    "johannesburg": "Africa/Johannesburg", "lagos": "Africa/Lagos",
    "casablanca": "Africa/Casablanca",
}

# Relative-unit keywords (en + fr) -> canonical unit.
_UNITS = {
    "day": "days", "days": "days", "jour": "days", "jours": "days",
    "week": "weeks", "weeks": "weeks", "semaine": "weeks", "semaines": "weeks",
    "month": "months", "months": "months", "mois": "months",
    "year": "years", "years": "years", "an": "years", "ans": "years",
    "année": "years", "années": "years", "annee": "years", "annees": "years",
    "hour": "hours", "hours": "hours", "heure": "hours", "heures": "hours",
    "minute": "minutes", "minutes": "minutes", "min": "minutes",
}


def _now():
    return datetime.now()


def _today():
    return date.today()


def _last_day(year, month):
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - timedelta(days=1)).day


def _add_units(base, n, unit):
    """Add ``n`` of ``unit`` to a date/datetime. Returns same type as base."""
    if unit == "days":
        return base + timedelta(days=n)
    if unit == "weeks":
        return base + timedelta(weeks=n)
    if unit == "hours":
        return base + timedelta(hours=n)
    if unit == "minutes":
        return base + timedelta(minutes=n)
    if unit in ("months", "years"):
        months = n * (12 if unit == "years" else 1)
        total = base.month - 1 + months
        year = base.year + total // 12
        month = total % 12 + 1
        day = min(base.day, _last_day(year, month))
        if isinstance(base, datetime):
            return base.replace(year=year, month=month, day=day)
        return date(year, month, day)
    raise NotADate("unit")


def _parse_date(token):
    """Parse a date token into a ``date`` (raises NotADate on failure)."""
    t = (token or "").strip().lower().rstrip(".,!?")
    if t in ("today", "now", "aujourd'hui", "aujourdhui", "ce jour"):
        return _today()
    if t in ("tomorrow", "demain"):
        return _today() + timedelta(days=1)
    if t in ("yesterday", "hier"):
        return _today() - timedelta(days=1)

    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", t)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            raise NotADate("bad date")

    # "25 december 2026" / "25 dec" / "december 25, 2026" / "dec 25"
    m = re.match(r"^(\d{1,2})\s+([a-zà-ÿ]+)\.?(?:\s+(\d{4}))?$", t)
    if m and m.group(2) in _MONTHS:
        day, month = int(m.group(1)), _MONTHS[m.group(2)]
        year = int(m.group(3)) if m.group(3) else _today().year
        try:
            return date(year, month, day)
        except ValueError:
            raise NotADate("bad date")
    m = re.match(r"^([a-zà-ÿ]+)\.?\s+(\d{1,2})(?:\s*,?\s*(\d{4}))?$", t)
    if m and m.group(1) in _MONTHS:
        month, day = _MONTHS[m.group(1)], int(m.group(2))
        year = int(m.group(3)) if m.group(3) else _today().year
        try:
            return date(year, month, day)
        except ValueError:
            raise NotADate("bad date")

    raise NotADate("not a date")


def _resolve_tz(place):
    """Resolve a city/alias/IANA/UTC-offset string into a tzinfo, or None."""
    if ZoneInfo is None:
        return None
    p = (place or "").strip().lower().rstrip(".?!")
    if p in CITY_TZ:
        key = CITY_TZ[p]
    elif "/" in place:
        candidate = place.strip()
        # IANA keys are case-sensitive; try as-is then a title-cased variant.
        for key in (candidate, "/".join(part.title() for part in candidate.split("/"))):
            try:
                return ZoneInfo(key)
            except (ZoneInfoNotFoundError, ValueError):
                continue
        return None
    else:
        m = re.match(r"^(?:utc|gmt)\s*([+-]\d{1,2})(?::?(\d{2}))?$", p)
        if m:
            hours = int(m.group(1))
            mins = int(m.group(2) or 0) * (1 if hours >= 0 else -1)
            return timezone(timedelta(hours=hours, minutes=mins))
        return None
    try:
        return ZoneInfo(key)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def _fmt_date(d):
    return f"{WEEKDAYS_FR[d.weekday()]} {d.day} {MONTHS_FR[d.month - 1]} {d.year}"


def _date_answer(d, prefix=""):
    iso = d.isoformat()
    title = (prefix + " " if prefix else "") + _fmt_date(d)
    return Answer(title.strip().capitalize(), iso, iso)


def handle(text):
    """Interpret ``text`` as a date/time query. Raises NotADate otherwise."""
    raw = (text or "").strip()
    low = raw.lower()
    if not low:
        raise NotADate("empty")

    # now / today
    if low in ("now", "today", "maintenant", "aujourd'hui", "aujourdhui", "date", "time", "heure"):
        n = _now()
        return Answer(
            n.strftime("%H:%M:%S"),
            _fmt_date(n.date()).capitalize(),
            n.strftime("%Y-%m-%d %H:%M:%S"),
        )

    # bare relative day
    if low in ("tomorrow", "demain", "yesterday", "hier"):
        return _date_answer(_parse_date(low))

    # time/now in <place>   |   <place> time   (match on raw to keep IANA casing)
    m = (re.match(r"^(?:now|time|heure|date)\s+(?:in|at|à|a|au|aux)\s+(?P<place>.+)$", raw, re.IGNORECASE)
         or re.match(r"^(?P<place>.+?)\s+(?:time|heure)$", raw, re.IGNORECASE))
    if m:
        tz = _resolve_tz(m.group("place"))
        if tz is not None:  # otherwise fall through to other handlers
            n = datetime.now(tz)
            label = m.group("place").strip().title()
            return Answer(
                f"{n.strftime('%H:%M')} — {label}",
                f"{_fmt_date(n.date()).capitalize()} · UTC{n.strftime('%z')[:3]}",
                n.strftime("%Y-%m-%d %H:%M %Z"),
            )

    # days between A and B
    m = re.match(r"^(?:days?\s+|jours?\s+)?between\s+(?P<a>.+?)\s+and\s+(?P<b>.+)$", low)
    if m:
        a, b = _parse_date(m.group("a")), _parse_date(m.group("b"))
        days = abs((b - a).days)
        return Answer(f"{days} jours", f"{a.isoformat()} → {b.isoformat()}", str(days))

    # days until / till <date>
    m = re.match(r"^(?:how\s+many\s+)?(?:days?\s+)?(?:until|till|til|jusqu'?au?|jusqua)\s+(?P<d>.+)$", low)
    if m:
        target = _parse_date(m.group("d"))
        days = (target - _today()).days
        return Answer(f"{days} jours", f"jusqu'au {_fmt_date(target)}", str(days))

    # days since <date>
    m = re.match(r"^(?:days?\s+)?(?:since|depuis)\s+(?P<d>.+)$", low)
    if m:
        past = _parse_date(m.group("d"))
        days = (_today() - past).days
        return Answer(f"{days} jours", f"depuis le {_fmt_date(past)}", str(days))

    # N units ago / il y a N units
    m = re.match(r"^(?:il\s+y\s+a\s+)?(?P<n>\d+)\s+(?P<u>[a-zà-ÿ]+)\s+(?:ago)$", low) \
        or re.match(r"^il\s+y\s+a\s+(?P<n>\d+)\s+(?P<u>[a-zà-ÿ]+)$", low)
    if m and m.group("u") in _UNITS:
        unit = _UNITS[m.group("u")]
        res = _add_units(_now(), -int(m.group("n")), unit)
        return _relative_answer(res, unit)

    # in N units / N units from now / later / dans N units
    m = (re.match(r"^(?:in|dans)\s+(?P<n>\d+)\s+(?P<u>[a-zà-ÿ]+)$", low)
         or re.match(r"^(?P<n>\d+)\s+(?P<u>[a-zà-ÿ]+)\s+(?:from\s+now|from\s+today|later)$", low))
    if m and m.group("u") in _UNITS:
        unit = _UNITS[m.group("u")]
        res = _add_units(_now(), int(m.group("n")), unit)
        return _relative_answer(res, unit)

    # <date> +/- N units
    m = re.match(r"^(?P<date>.+?)\s*(?P<op>[+\-])\s*(?P<n>\d+)\s*(?P<u>[a-zà-ÿ]+)$", low)
    if m and m.group("u") in _UNITS:
        base = _parse_date(m.group("date"))
        n = int(m.group("n")) * (1 if m.group("op") == "+" else -1)
        res = _add_units(base, n, _UNITS[m.group("u")])
        return _date_answer(res)

    raise NotADate("no date pattern")


def _relative_answer(res, unit):
    if unit in ("hours", "minutes"):
        return Answer(
            res.strftime("%H:%M — ") + _fmt_date(res.date()),
            res.strftime("%Y-%m-%d %H:%M"),
            res.strftime("%Y-%m-%d %H:%M"),
        )
    d = res.date() if isinstance(res, datetime) else res
    return _date_answer(d)
