# -*- coding: utf-8 -*-
"""Parse the 20th CC member/alternate list pages (zh.wikipedia) into a roster JSON.

Usage: python parse_roster.py
Reads wiki_cc.html / wiki_alt.html in the same dir, writes roster.json.
"""
from __future__ import annotations

import io
import json
import re
import sys
from html import unescape
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DIR = Path(__file__).parent

REF_RE = re.compile(r"&#91;[^\]]*&#93;|\[\d+\]|\[註\s*\d+\]")


def clean(text: str) -> str:
    """Strip tags but keep <br> and block boundaries as newlines."""
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"</(p|div|li|tr)>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = REF_RE.sub("", text)
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n")]
    return "\n".join(ln for ln in lines if ln)


def parse_table(table_html: str) -> list[dict]:
    rows = re.findall(r"<tr.*?</tr>", table_html, re.S)
    out = []
    for row in rows:
        cells = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row, re.S)
        if len(cells) < 5:
            continue
        name_cell, birth, level, cat, pos = cells[0], cells[1], cells[2], cells[3], cells[4]
        note = clean(cells[5]) if len(cells) > 5 else ""
        # skip repeated header rows
        if "<a " not in name_cell and ("姓名" in name_cell or "职务" in name_cell):
            continue
        # canonical name from the first link title
        link = re.search(r'<a href="/wiki/([^"?#]+)"[^>]*title="([^"]+)"', row)
        article = unescape(link.group(1)) if link else ""
        name = unescape(link.group(2)) if link else ""
        if not name:
            plain = re.sub(r"<(sub|small|sup)[^>]*>.*?</\1>", "", name_cell, flags=re.S)
            name = clean(plain).split("（")[0].strip()
        gender = "女" if "（女）" in name_cell or "(女)" in name_cell else "男"
        # strike-through marks sanctioned members
        struck = bool(re.search(r"<s[ >]", name_cell))
        birth_year = ""
        m = re.match(r"(\d{4})年(\d{1,2})月", birth)
        if m:
            birth_year = f"{m.group(1)}-{int(m.group(2)):02d}"
        out.append(
            {
                "name": name,
                "gender": gender,
                "birth": birth_year,
                "level": clean(level),
                "category": clean(cat),
                "positions_text": clean(pos),
                "note": note,
                "struck": struck,
                "article": article,
            }
        )
    return out


def main() -> None:
    cc_html = (DIR / "wiki_cc.html").read_text(encoding="utf-8")
    alt_html = (DIR / "wiki_alt.html").read_text(encoding="utf-8")

    def biggest(html: str) -> str:
        return max(re.findall(r"<table.*?</table>", html, re.S), key=len)

    members = parse_table(biggest(cc_html))
    alternates = parse_table(biggest(alt_html))

    coopted = [m for m in members if "递补" in m["note"]]
    coopted_names = {m["name"] for m in coopted}
    promoted_alts = [a for a in alternates if a["name"] in coopted_names]

    roster = {
        "members": members,
        "alternates": alternates,
        "stats": {
            "member_rows": len(members),
            "alternate_rows": len(alternates),
            "coopted": len(coopted),
            "member_struck": sum(1 for m in members if m["struck"]),
            "promoted_alts_matched": len(promoted_alts),
            "current_alternates": len(alternates) - len(promoted_alts),
            "no_article": sum(1 for x in members + alternates if not x["article"]),
        },
    }
    (DIR / "roster.json").write_text(
        json.dumps(roster, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(json.dumps(roster["stats"], ensure_ascii=False, indent=1))
    print("coopted:", [m["name"] for m in coopted])
    print("unmatched coopted:", coopted_names - {a["name"] for a in alternates})
    print("PSC/Politburo check (bold-italic rows present):", "习近平" in {m["name"] for m in members})


if __name__ == "__main__":
    main()
