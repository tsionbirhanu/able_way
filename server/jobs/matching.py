"""Jobs that fit a learner's skills, and the "why it fits" for each.

The learner picks kinds of work (not 33 separate skills): each kind stands for a group of the skills
used in data/jobs.json. A subscription for kinds of work is stored as the keyword "areas:sched,support",
so job alerts (alerts.py) send only the jobs that fit, with the same reason.
"""

# id, icon, label in each language, the job skills it covers (lower case)
AREAS = [
    ("sched", "📅", {"en": "Scheduling and calendars", "am": "ቀጠሮና የቀን መቁጠሪያ", "om": "Beellama fi kaalaandara"},
     {"scheduling", "calendar management", "time zones", "travel booking", "meeting notes"}),
    ("admin", "📧", {"en": "Email and office tools", "am": "ኢሜይልና የቢሮ መሣሪያዎች", "om": "Imeelii fi meeshaalee waajjiraa"},
     {"email", "gmail", "google workspace", "follow-up", "data entry", "excel", "web research", "trello",
      "accuracy", "typing"}),
    ("support", "💬", {"en": "Customer support", "am": "የደንበኞች አገልግሎት", "om": "Tajaajila maamilaa"},
     {"customer support", "live chat", "crm", "lead follow-up", "communication", "order tracking"}),
    ("write", "✍️", {"en": "Writing and social media", "am": "ጽሑፍና ማኅበራዊ ሚዲያ", "om": "Barreeffama fi miidiyaa hawaasaa"},
     {"copywriting", "social media", "canva", "product listings", "shopify"}),
    ("books", "💰", {"en": "Bookkeeping and invoices", "am": "የሂሳብ አያያዝና ደረሰኞች", "om": "Herrega fi nagahee"},
     {"bookkeeping", "invoicing", "quickbooks", "excel"}),
    ("transcribe", "🎧", {"en": "Transcription and captions", "am": "ድምፅን ወደ ጽሑፍ መገልበጥ", "om": "Sagalee gara barreeffamaatti"},
     {"transcription", "captioning", "typing", "meeting notes"}),
]
AREA_IDS = [a[0] for a in AREAS]
PREFIX = "areas:"


def area_label(area_id: str, lang: str) -> str:
    for aid, icon, labels, _ in AREAS:
        if aid == area_id:
            return f"{icon} {labels.get(lang) or labels['en']}"
    return area_id


def keyword_for(areas) -> str:
    """The subscription keyword for these kinds of work, in a fixed order."""
    return PREFIX + ",".join(a for a in AREA_IDS if a in set(areas))


def areas_of(keyword: str) -> list:
    if not (keyword or "").startswith(PREFIX):
        return []
    return [a for a in keyword[len(PREFIX):].split(",") if a in AREA_IDS]


def fitting_skills(job: dict, areas) -> list:
    """The job's own skills that belong to the chosen kinds of work: the reason it fits."""
    wanted = set().union(*[skills for aid, _, _, skills in AREAS if aid in set(areas)]) if areas else set()
    return [s for s in job.get("skills") or [] if s.lower() in wanted]


def best_jobs(jobs: list, areas, limit: int = 3) -> list:
    """[(job, reasons)], the jobs with the most fitting skills first, then the nearest deadline."""
    scored = [(job, fitting_skills(job, areas)) for job in jobs]
    scored = [(job, why) for job, why in scored if why]
    scored.sort(key=lambda pair: (-len(pair[1]), pair[0].get("deadline") or "9999"))
    return scored[:limit]
