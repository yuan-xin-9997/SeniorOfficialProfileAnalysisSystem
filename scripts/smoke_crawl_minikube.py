#!/usr/bin/env python3
import json
import sys
import urllib.error
import urllib.request


BASE_URL = "http://192.168.0.111:30080"
PASSWORD_FILE = "/home/yuanxin/SeniorOfficialProfileAnalysisSystem/secrets/admin-password.txt"


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


def main():
    password = open(PASSWORD_FILE, encoding="utf-8").read()
    _, login = request("/api/auth/login", "POST", {"username": "admin", "password": password})
    token = login["access_token"]

    _, source = request(
        "/api/sources/configs",
        "POST",
        {
            "name": "系统健康检查测试源",
            "base_url": "http://frontend/api/health",
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
    print(
        "document",
        {
            "status": document["parse_status"],
            "http": document["http_status"],
            "title": document["title"],
            "has_excerpt": bool(document["plain_text_excerpt"]),
        },
    )

    _, documents = request(f"/api/sources/documents?source_config_id={source['id']}", token=token)
    print("documents", len(documents), documents[0]["parse_status"])


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise

