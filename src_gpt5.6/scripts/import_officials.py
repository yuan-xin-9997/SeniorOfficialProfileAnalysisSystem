# -*- coding: utf-8 -*-
"""Import seed officials into a running SeniorOfficialProfileAnalysisSystem instance.

Usage:
    python scripts/import_officials.py --base-url http://192.168.0.111:33380 \
        --username admin --password admin123 \
        [--file data/seed/officials_20th_cc.json] [--update] [--dry-run]

Behaviour:
- Reads a seed JSON file whose records match the OfficialCreate API shape.
- Skips records whose name already exists (use --update to overwrite them via PUT).
- Prints a summary and a skipped/failed name list.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent


def login(base_url: str, username: str, password: str) -> str:
    r = requests.post(
        f"{base_url}/api/auth/login",
        json={"username": username, "password": password},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def existing_names(base_url: str, token: str) -> dict[str, int]:
    names: dict[str, int] = {}
    page, page_size = 1, 100
    while True:
        r = requests.get(
            f"{base_url}/api/officials",
            params={"page": page, "page_size": page_size},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        for item in data.get("items", []):
            names[item["name"]] = item["id"]
        if page * page_size >= data.get("total", 0) or not data.get("items"):
            break
        page += 1
    return names


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default="http://127.0.0.1:33380")
    ap.add_argument("--username", default="admin")
    ap.add_argument("--password", default="admin123")
    ap.add_argument("--file", default=str(REPO / "data" / "seed" / "officials_20th_cc.json"))
    ap.add_argument("--update", action="store_true", help="overwrite existing officials with the same name")
    ap.add_argument("--dry-run", action="store_true", help="report what would happen without writing")
    args = ap.parse_args()

    records = json.loads(Path(args.file).read_text(encoding="utf-8"))
    print(f"seed records: {len(records)} from {args.file}")

    token = login(args.base_url, args.username, args.password)
    names = existing_names(args.base_url, token)
    print(f"existing officials: {len(names)}")

    headers = {"Authorization": f"Bearer {token}"}
    created = updated = skipped = failed = 0
    failed_names: list[str] = []

    for rec in records:
        name = rec["name"]
        if name in names:
            if not args.update:
                skipped += 1
                continue
            if args.dry_run:
                updated += 1
                continue
            r = requests.put(
                f"{args.base_url}/api/officials/{names[name]}",
                json=rec,
                headers=headers,
                timeout=30,
            )
            if r.ok:
                updated += 1
            else:
                failed += 1
                failed_names.append(f"{name}: PUT {r.status_code} {r.text[:120]}")
            time.sleep(0.05)
            continue
        if args.dry_run:
            created += 1
            continue
        r = requests.post(
            f"{args.base_url}/api/officials", json=rec, headers=headers, timeout=30
        )
        if r.ok:
            created += 1
        else:
            failed += 1
            failed_names.append(f"{name}: POST {r.status_code} {r.text[:120]}")
        if (created + updated) % 25 == 0 and not args.dry_run:
            print(f"  progress: created={created} updated={updated} failed={failed}")
        time.sleep(0.05)

    print(f"DONE created={created} updated={updated} skipped={skipped} failed={failed}")
    for line in failed_names[:20]:
        print("  FAILED:", line)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
