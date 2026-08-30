# -*- coding: utf-8 -*-
"""Fetch raw wikitext for every roster person from zh.wikipedia API (via NAS proxy)."""
from __future__ import annotations

import io
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from urllib.parse import unquote

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DIR = Path(__file__).parent
OUT = DIR / "articles"
OUT.mkdir(exist_ok=True)

PROXIES = {"http": "http://192.168.0.100:7890", "https": "http://192.168.0.100:7890"}
UA = {
    "User-Agent": "SeniorOfficialProfileAnalysisSystem-seed/1.0 (contact: admin@yuan-xin.top) python-requests"
}
API = "https://zh.wikipedia.org/w/api.php"


def fetch_one(session: requests.Session, person: dict) -> tuple[str, str]:
    title = unquote(person["article"]).replace("_", " ")
    safe = person["article"].replace("/", "_")
    path = OUT / f"{safe}.txt"
    if path.exists() and path.stat().st_size > 200:
        return person["name"], "cached"
    for attempt in range(3):
        try:
            r = session.get(
                API,
                params={
                    "action": "query",
                    "prop": "revisions",
                    "rvprop": "content",
                    "rvslots": "main",
                    "format": "json",
                    "redirects": 1,
                    "titles": title,
                },
                proxies=PROXIES,
                headers=UA,
                timeout=40,
            )
            r.raise_for_status()
            pages = r.json()["query"]["pages"]
            page = list(pages.values())[0]
            if "revisions" not in page:
                path.write_text("MISSING", encoding="utf-8")
                return person["name"], "missing"
            w = page["revisions"][0]["slots"]["main"]["*"]
            path.write_text(w, encoding="utf-8")
            return person["name"], f"ok {len(w)}"
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                return person["name"], f"error {e}"
            time.sleep(1.5 * (attempt + 1))
    return person["name"], "error"


def main() -> None:
    roster = json.loads((DIR / "roster.json").read_text(encoding="utf-8"))
    people = roster["members"] + roster["alternates"]
    print(f"total people: {len(people)}")
    ok = err = missing = cached = 0
    with requests.Session() as session, ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(fetch_one, session, p) for p in people]
        for i, fut in enumerate(as_completed(futures), 1):
            name, status = fut.result()
            if status.startswith("ok"):
                ok += 1
            elif status == "missing":
                missing += 1
                print(f"MISSING: {name}")
            elif status == "cached":
                cached += 1
            else:
                err += 1
                print(f"ERROR: {name} {status}")
            if i % 50 == 0:
                print(f"progress {i}/{len(people)} ok={ok} cached={cached} missing={missing} err={err}")
                time.sleep(1)
    print(f"DONE ok={ok} cached={cached} missing={missing} err={err}")


if __name__ == "__main__":
    main()
