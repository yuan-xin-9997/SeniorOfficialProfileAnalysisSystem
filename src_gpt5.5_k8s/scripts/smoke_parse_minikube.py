#!/usr/bin/env python3
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import quote


BASE_URL = "http://192.168.0.111:30080"
PASSWORD_FILE = "/home/yuanxin/SeniorOfficialProfileAnalysisSystem/secrets/admin-password.txt"
SMOKE_OFFICIAL_NAME = "解析测试官员"
SMOKE_PAGE = "/usr/share/nginx/html/profile-parse-smoke.html"


def request(path, method="GET", payload=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(f"{method} {path} failed: {exc.code} {body}") from exc


def run(command, input_text=None):
    completed = subprocess.run(
        command,
        input=input_text,
        text=True,
        check=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def write_smoke_page():
    pod = run(["kubectl", "-n", "sopa", "get", "pod", "-l", "app=frontend", "-o", "jsonpath={.items[0].metadata.name}"])
    html = f"""
<!doctype html>
<html lang="zh-CN">
  <head><meta charset="utf-8"><title>{SMOKE_OFFICIAL_NAME}简历</title></head>
  <body>
    <main>
      <h1>{SMOKE_OFFICIAL_NAME}简历</h1>
      <p>1982.09--1986.07 北京大学中文系汉语言文学专业学习</p>
      <p>2020.01--2022.12 测试省委组织部干部一处处长</p>
    </main>
  </body>
</html>
""".strip()
    run(["kubectl", "-n", "sopa", "exec", "-i", pod, "--", "sh", "-c", f"cat > {SMOKE_PAGE}"], html)


def main():
    write_smoke_page()

    password = open(PASSWORD_FILE, encoding="utf-8").read()
    _, login = request("/api/auth/login", "POST", {"username": "admin", "password": password})
    token = login["access_token"]

    csv_text = "\n".join(
        [
            "name,membership_type,rank_order,profile_summary",
            f"{SMOKE_OFFICIAL_NAME},member,9101,用于验证抓取正文自动解析履历",
        ]
    )
    _, imported = request(
        "/api/committee/import-members",
        "POST",
        {
            "term_no": 20,
            "term_name": "中国共产党第二十届中央委员会",
            "start_year": 2022,
            "end_year": 2027,
            "csv_text": csv_text,
        },
        token,
    )
    print("imported", imported)

    source_url = f"http://frontend/profile-parse-smoke.html?ts={int(time.time())}"
    _, source = request(
        "/api/sources/configs",
        "POST",
        {
            "name": "履历解析测试源",
            "base_url": source_url,
            "source_type": "internal_test",
            "trust_level": "A",
            "crawl_strategy": "requests",
            "frequency_cron": "0 3 * * 1",
            "request_interval_seconds": 3,
            "max_retry": 3,
            "is_enabled": True,
        },
        token,
    )
    print("source", source["id"], source["base_url"])

    _, document = request(f"/api/sources/configs/{source['id']}/crawl", "POST", token=token)
    print("document", document["id"], document["parse_status"], document["title"])

    _, parsed = request(f"/api/sources/documents/{document['id']}/parse-profile", "POST", token=token)
    print("parsed", parsed)

    if parsed["official_name"] != SMOKE_OFFICIAL_NAME:
        raise RuntimeError(f"unexpected official match: {parsed['official_name']}")
    if parsed["parsed_candidates"] < 2:
        raise RuntimeError(f"expected at least 2 parsed candidates, got {parsed['parsed_candidates']}")
    if parsed["created_events"] + parsed["skipped_duplicates"] < 2:
        raise RuntimeError("expected parsed events to be created or identified as duplicates")

    _, officials = request(f"/api/officials?q={quote(SMOKE_OFFICIAL_NAME)}", token=token)
    official = next(item for item in officials if item["name"] == SMOKE_OFFICIAL_NAME)
    _, timeline = request(f"/api/officials/{official['id']}/timeline", token=token)
    smoke_events = [
        item
        for item in timeline
        if "北京大学中文系" in item["description"] or "测试省委组织部" in item["description"]
    ]
    print("timeline_events", len(smoke_events), [item["review_status"] for item in smoke_events])
    if len(smoke_events) < 2:
        raise RuntimeError("expected smoke timeline events to be visible")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise
