# -*- coding: utf-8 -*-
"""Fix officials' current_position/organization/summary from a corrected seed file.

Usage:
    python scripts/fix_current_positions.py --base-url http://192.168.0.111:33380 \
        --username admin --password admin123 \
        [--file data/seed/officials_20th_cc.json] [--dry-run] [--include-empty]

Behaviour:
- 只修复 current_position 与派生字段（organization、summary），绝不动服务器上的
  careers（履历刷新已用解析器重算过，种子里的 careers 是旧快照）。
- summary 仅在存储值仍是种子模板（“中共二十届中央X，现任/原任/生前任…”）时才
  同步重建，避免覆盖人工编辑。
- 默认跳过种子中 current_position 为空的记录（用 --include-empty 连空值一起对齐）。
- Prints a summary and changed-name list.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent

SUMMARY_TEMPLATE = re.compile(r"^中共二十届中央(?:委员|候补委员|委员（递补）)，(?:现任|原任|生前任).{0,255}。$")


def login(base_url: str, username: str, password: str) -> str:
    r = requests.post(
        f"{base_url}/api/auth/login",
        json={"username": username, "password": password},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def all_officials(base_url: str, token: str) -> dict[str, int]:
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
    ap.add_argument("--dry-run", action="store_true", help="report what would change without writing")
    ap.add_argument("--include-empty", action="store_true", help="also clear positions that the seed leaves empty")
    args = ap.parse_args()

    records = json.loads(Path(args.file).read_text(encoding="utf-8"))
    print(f"seed records: {len(records)} from {args.file}")

    token = login(args.base_url, args.username, args.password)
    names = all_officials(args.base_url, token)
    print(f"existing officials: {len(names)}")

    headers = {"Authorization": f"Bearer {token}"}
    fixed = unchanged = missing = failed = 0
    failed_names: list[str] = []
    changes: list[tuple[str, str, str]] = []

    for rec in records:
        name = rec["name"]
        official_id = names.get(name)
        if official_id is None:
            missing += 1
            continue
        new_position = rec.get("current_position", "")
        if not new_position and not args.include_empty:
            unchanged += 1
            continue

        r = requests.get(f"{args.base_url}/api/officials/{official_id}", headers=headers, timeout=30)
        r.raise_for_status()
        detail = r.json()

        if detail.get("current_position") == new_position:
            unchanged += 1
            continue

        old_position = detail.get("current_position", "")
        changes.append((name, old_position[:40], new_position[:40]))

        if args.dry_run:
            fixed += 1
            continue

        payload = dict(detail)
        payload["current_position"] = new_position
        payload["organization"] = rec.get("organization", "")
        stored_summary = detail.get("summary") or ""
        if SUMMARY_TEMPLATE.match(stored_summary):
            payload["summary"] = rec.get("summary", stored_summary)

        pr = requests.put(f"{args.base_url}/api/officials/{official_id}", json=payload, headers=headers, timeout=30)
        if pr.ok:
            fixed += 1
        else:
            failed += 1
            failed_names.append(f"{name}: HTTP {pr.status_code} {pr.text[:120]}")

    print(f"\nfixed: {fixed} | unchanged: {unchanged} | missing on server: {missing} | failed: {failed}")
    for name, old, new in changes[:15]:
        print(f"  {name}: {old!r} -> {new!r}")
    if len(changes) > 15:
        print(f"  ... and {len(changes) - 15} more")
    for f in failed_names:
        print("FAILED:", f)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
