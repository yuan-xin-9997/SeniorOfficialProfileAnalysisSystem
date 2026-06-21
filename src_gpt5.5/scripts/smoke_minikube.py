#!/usr/bin/env python3
import json
import sys
from urllib.parse import quote
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
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(f"{method} {path} failed: {exc.code} {body}") from exc


def main():
    password = open(PASSWORD_FILE, encoding="utf-8").read()
    _, login = request("/api/auth/login", "POST", {"username": "admin", "password": password})
    token = login["access_token"]

    status, health = request("/api/health", token=token)
    print("health", status, health["status"])

    csv_text = "\n".join(
        [
            "name,membership_type,rank_order,profile_summary",
            "测试样例甲,member,9001,用于验证履历和关系生成闭环",
            "测试样例乙,alternate_member,9002,用于验证履历和关系生成闭环",
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

    _, officials = request(f"/api/officials?q={quote('测试样例')}", token=token)
    official_by_name = {item["name"]: item for item in officials}
    left = official_by_name["测试样例甲"]
    right = official_by_name["测试样例乙"]

    for official in (left, right):
        _, timeline = request(f"/api/officials/{official['id']}/timeline", token=token)
        if not any(item["description"] == "测试重叠任职经历" for item in timeline):
            request(
                f"/api/officials/{official['id']}/timeline",
                "POST",
                {
                    "event_type": "appointment",
                    "start_date": "2020-01-01",
                    "end_date": "2021-12-31",
                    "organization_name": "测试机构",
                    "position_name": "测试职位",
                    "location_name": "测试地区",
                    "description": "测试重叠任职经历",
                },
                token,
            )

    _, rebuilt = request("/api/relationships/rebuild", "POST", token=token)
    print("rebuilt", rebuilt)

    _, relationships = request("/api/relationships?min_score=1&limit=20", token=token)
    visible = [
        {
            "type": item["relationship_type"],
            "subject": item.get("subject_name"),
            "object": item.get("object_name"),
            "score": item["strength_score"],
        }
        for item in relationships
        if "测试样例" in (item.get("subject_name") or "") or "测试样例" in (item.get("object_name") or "")
    ]
    print("relationships", visible)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise
