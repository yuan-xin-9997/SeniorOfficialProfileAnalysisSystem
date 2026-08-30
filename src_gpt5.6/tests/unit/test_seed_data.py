# -*- coding: utf-8 -*-
"""Validate the bundled 20th CC seed file against the OfficialCreate schema."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.backend.schemas.official import OfficialCreate

SEED = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "seed"
    / "officials_20th_cc.json"
)


@pytest.mark.skipif(not SEED.exists(), reason="seed file not present")
def test_seed_file_loads_and_matches_schema():
    records = json.loads(SEED.read_text(encoding="utf-8"))
    assert len(records) >= 370, f"expected ~376 records, got {len(records)}"

    for rec in records:
        parsed = OfficialCreate.model_validate(rec)  # raises on any schema violation
        assert parsed.name
        assert parsed.careers is not None
        for i, career in enumerate(parsed.careers):
            assert career.sort_order == i
            assert career.position

    names = [r["name"] for r in records]
    assert len(names) == len(set(names)), "duplicate names in seed file"

    tags = {t for r in records for t in r["tags"]}
    assert "中共二十届中央委员" in tags
    assert "中共二十届中央候补委员" in tags

    members = sum(1 for r in records if "中共二十届中央委员" in r["tags"])
    alternates = sum(1 for r in records if "中共二十届中央候补委员" in r["tags"])
    assert members == 219, members
    assert alternates == 157, alternates


@pytest.mark.skipif(not SEED.exists(), reason="seed file not present")
def test_seed_career_dates_are_wellformed():
    import re

    records = json.loads(SEED.read_text(encoding="utf-8"))
    date_re = re.compile(r"^\d{4}(\.\d{1,2})?$|^至今$")
    for rec in records:
        for career in rec["careers"]:
            assert date_re.match(career["start_date"]), (rec["name"], career["start_date"])
            assert date_re.match(career["end_date"]), (rec["name"], career["end_date"])
