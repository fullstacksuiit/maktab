from datetime import date
from hijri_converter import Hijri, Gregorian


ISLAMIC_EVENTS = [
    (1, 1, 'Islamic New Year', 'fa-moon'),
    (3, 12, 'Mawlid un-Nabi', 'fa-star'),
    (8, 15, "Shab-e-Barat", 'fa-cloud-moon'),
    (9, 27, 'Laylatul Qadr', 'fa-star-and-crescent'),
    (10, 1, 'Eid ul-Fitr', 'fa-mosque'),
    (12, 10, 'Eid ul-Adha', 'fa-kaaba'),
]


def get_upcoming_islamic_dates(count=4):
    """Return the next `count` upcoming Islamic dates as Gregorian conversions."""
    today = date.today()
    hijri_today = Gregorian(today.year, today.month, today.day).to_hijri()
    hijri_year = hijri_today.year

    candidates = []
    for hijri_month, hijri_day, name, icon in ISLAMIC_EVENTS:
        for year in (hijri_year, hijri_year + 1):
            try:
                h = Hijri(year, hijri_month, hijri_day)
                g = h.to_gregorian()
                if g >= today:
                    candidates.append({
                        'name': name,
                        'hijri_date': f"{hijri_day} {h.month_name()} {year} AH",
                        'gregorian_date': g,
                        'days_until': (g - today).days,
                        'icon': icon,
                    })
                    break
            except (ValueError, OverflowError):
                continue

    candidates.sort(key=lambda x: x['gregorian_date'])
    return candidates[:count]
