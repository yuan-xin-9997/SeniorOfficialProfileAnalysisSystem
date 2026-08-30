# -*- coding: utf-8 -*-
"""Batch extraction: roster + wikitext articles -> profiles.json + quality report."""
from __future__ import annotations

import io
import json
import re
import sys
import urllib.parse
from pathlib import Path

import extract_proto as ep

ep._setup_stdout()

DIR = Path(__file__).parent
ART = DIR / "articles"


def seg_year(s: str):
    m = re.match(r"(\d{4})(?:\.(\d{1,2}))?", str(s))
    return (int(m.group(1)), int(m.group(2) or 0)) if m else None


def main() -> None:
    roster = json.loads((DIR / "roster.json").read_text(encoding="utf-8"))
    people = roster["members"] + roster["alternates"]
    seen_ids = set()
    profiles = []
    report = {"no_segments": [], "few_segments": [], "weird_positions": [], "no_native": []}
    for p in people:
        key = p["article"]
        art_file = ART / f"{key}.txt"
        if not art_file.exists():
            report["no_segments"].append((p["name"], "NO FILE"))
            continue
        raw = art_file.read_text(encoding="utf-8")
        if raw == "MISSING":
            report["no_segments"].append((p["name"], "MISSING"))
            continue
        cleaned = ep.clean_wikitext(raw)
        prof = ep.profile_from_text(cleaned)
        segs = ep.parse_careers(cleaned)
        # merge roster data (birth/positions/note) with article data
        rec = {
            "name": p["name"],
            "gender": p["gender"],
            "birth": p["birth"] or "",
            "level": p["level"],
            "category": p["category"],
            "roster_positions": [ln for ln in p["positions_text"].split("\n") if ln.strip()],
            "note": p["note"],
            "struck": p["struck"],
            "article": p["article"],
            "ethnicity": prof["ethnicity"],
            "native_place": prof["native_place"],
            "education": prof["education"],
            "careers": segs,
        }
        if key not in seen_ids:
            seen_ids.add(key)
            profiles.append(rec)
        if len(segs) == 0:
            report["no_segments"].append((p["name"], key))
        elif len(segs) < 3:
            report["few_segments"].append((p["name"], len(segs)))
        for s in segs:
            if re.match(r"^[）、(（，,。]|^\d+日|^\s*$", s["position"]):
                report["weird_positions"].append((p["name"], s["position"][:40]))
                break
        if not prof["native_place"]:
            report["no_native"].append(p["name"])

    (DIR / "profiles.json").write_text(
        json.dumps(profiles, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"profiles: {len(profiles)}")
    for k, v in report.items():
        print(f"\n== {k} ({len(v)}):")
        for item in v[:25]:
            print("  ", item)


if __name__ == "__main__":
    main()
