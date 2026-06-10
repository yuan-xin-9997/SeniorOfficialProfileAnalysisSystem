import hashlib
import json

from app.models.official import Official


def compute_content_hash(official: Official) -> str:
    payload = {
        "name": official.name,
        "birth_date": str(official.birth_date),
        "birth_place": official.birth_place,
        "committee_term": official.committee_term,
        "career_entries": [
            {
                "start_year": e.start_year,
                "end_year": e.end_year,
                "entry_type": e.entry_type,
                "description": e.description,
            }
            for e in (official.career_entries or [])
        ],
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()
