# -*- coding: utf-8 -*-
"""履历刷新（后台增量抓取）单元测试。"""
from __future__ import annotations

import json

import pytest

from app.backend.core.database import SessionLocal
from app.backend.models.task import TaskRun
from app.backend.services.info_source.webfetch_client import WebFetchError

PAGE_A = "<html><body><h1>刷新甲</h1><p>2021.01 至今 任新职务甲</p></body></html>"
PAGE_B = "<html><body><h1>刷新乙</h1><p>2022.02 至今 任新职务乙</p></body></html>"

CAREERS_PAYLOAD = {
    "careers": [
        {
            "start_date": "2021.01",
            "end_date": "至今",
            "organization": "新机构",
            "position": "新职务",
            "location": "北京",
            "administrative_rank": "正部级",
            "description": "刷新后的经历",
        }
    ]
}


def _official_payload(name: str = "刷新甲", source_url: str = "https://example.com/profile") -> dict:
    return {
        "name": name,
        "current_position": "旧职务",
        "organization": "旧机构",
        "status": "在任",
        "source_url": source_url,
        "tags": [],
        "careers": [
            {"start_date": "2010.01", "end_date": "2015.12", "organization": "旧机构", "position": "旧职务", "sort_order": 0}
        ],
    }


@pytest.fixture
def mock_refresh(monkeypatch):
    """替换履历刷新服务里的 WebFetchClient 与 LLMClient，返回可观测的调用状态。"""
    import app.backend.services.official.refresh as refresh

    state = {
        "pages": {},
        "fail_urls": set(),
        "llm_payload": CAREERS_PAYLOAD,
        "llm_error": None,
        "fetch_calls": [],
        "llm_calls": [],
    }

    class _MockFetchClient:
        def __init__(self, *args, **kwargs):
            pass

        def fetch_html(self, url, mode="auto"):
            state["fetch_calls"].append(url)
            if url in state["fail_urls"]:
                raise WebFetchError(f"web_fetch 返回 500: {url}")
            return state["pages"].get(url, PAGE_A)

    class _MockLLM:
        def __init__(self, *args, **kwargs):
            pass

        def chat(self, system, user):
            state["llm_calls"].append(user)
            if state["llm_error"] is not None:
                raise state["llm_error"]
            return json.dumps(state["llm_payload"], ensure_ascii=False)

    monkeypatch.setattr(refresh, "WebFetchClient", _MockFetchClient)
    monkeypatch.setattr(refresh, "LLMClient", _MockLLM)
    return state


def _refresh(client, headers, mode=None):
    body = {"mode": mode} if mode else {}
    return client.post("/api/officials/resume-refresh", json=body, headers=headers)


def _run_detail(client, headers, run_id):
    return client.get(f"/api/task-center/runs/{run_id}", headers=headers).json()


def _careers(client, headers, official_id):
    return client.get(f"/api/officials/{official_id}", headers=headers).json()["careers"]


def test_resume_refresh_updates_careers_and_run(client, admin_headers, sync_worker, mock_refresh):
    mock_refresh["pages"] = {"https://example.com/a": PAGE_A, "https://example.com/b": PAGE_B}
    first = client.post("/api/officials", json=_official_payload("刷新甲", "https://example.com/a"), headers=admin_headers).json()
    second = client.post("/api/officials", json=_official_payload("刷新乙", "https://example.com/b"), headers=admin_headers).json()

    resp = _refresh(client, admin_headers)
    assert resp.status_code == 200, resp.text
    run = _run_detail(client, admin_headers, resp.json()["run_id"])
    assert run["status"] == "succeeded"
    assert "更新 2" in run["summary"]
    assert run["kind"] == "resume_refresh"
    assert run["mode"] == "incremental"

    assert _careers(client, admin_headers, first["id"])[0]["position"] == "新职务"
    assert _careers(client, admin_headers, first["id"])[0]["organization"] == "新机构"
    assert _careers(client, admin_headers, second["id"])[0]["position"] == "新职务"

    messages = [log["message"] for log in run["logs"]]
    assert any("刷新甲: 已更新 1 条任职经历" in msg for msg in messages)
    assert any("共 2 位官员待刷新" in msg for msg in messages)


def test_resume_refresh_incremental_skips_unchanged_pages(client, admin_headers, sync_worker, mock_refresh):
    official = client.post("/api/officials", json=_official_payload(), headers=admin_headers).json()

    first = _run_detail(client, admin_headers, _refresh(client, admin_headers).json()["run_id"])
    assert "更新 1" in first["summary"]

    # 第二次增量刷新：页面文本相同 -> 哈希命中直接跳过，不再调用 LLM。
    second = _run_detail(client, admin_headers, _refresh(client, admin_headers).json()["run_id"])
    assert "跳过 1" in second["summary"] and "更新 0" in second["summary"]
    assert len(mock_refresh["llm_calls"]) == 1

    # full 模式强制重新解析。
    full = _run_detail(client, admin_headers, _refresh(client, admin_headers, "full").json()["run_id"])
    assert "更新 1" in full["summary"]
    assert len(mock_refresh["llm_calls"]) == 2
    assert _careers(client, admin_headers, official["id"])[0]["position"] == "新职务"


def test_resume_refresh_skips_officials_without_source_url(client, admin_headers, sync_worker, mock_refresh):
    client.post("/api/officials", json=_official_payload("有源甲"), headers=admin_headers)
    no_source = _official_payload("无源乙")
    no_source["source_url"] = ""
    client.post("/api/officials", json=no_source, headers=admin_headers)

    run = _run_detail(client, admin_headers, _refresh(client, admin_headers).json()["run_id"])
    assert run["status"] == "succeeded"
    assert "无来源 1" in run["summary"]
    assert len(mock_refresh["fetch_calls"]) == 1
    assert any("无源乙" in msg and "跳过" in msg for msg in [log["message"] for log in run["logs"]])


def test_resume_refresh_survives_single_official_failure(client, admin_headers, sync_worker, mock_refresh):
    mock_refresh["pages"] = {"https://example.com/a": PAGE_A, "https://example.com/b": PAGE_B}
    mock_refresh["fail_urls"] = {"https://example.com/b"}
    ok = client.post("/api/officials", json=_official_payload("成功甲", "https://example.com/a"), headers=admin_headers).json()
    bad = client.post("/api/officials", json=_official_payload("失败乙", "https://example.com/b"), headers=admin_headers).json()

    run = _run_detail(client, admin_headers, _refresh(client, admin_headers).json()["run_id"])
    assert run["status"] == "succeeded"
    assert "失败 1" in run["summary"]

    assert _careers(client, admin_headers, ok["id"])[0]["position"] == "新职务"
    failed_careers = _careers(client, admin_headers, bad["id"])
    assert failed_careers[0]["position"] == "旧职务"
    assert any("失败乙: 刷新失败" in log["message"] for log in run["logs"])


def test_resume_refresh_empty_parse_keeps_existing_careers(client, admin_headers, sync_worker, mock_refresh):
    mock_refresh["llm_payload"] = {"careers": []}
    official = client.post("/api/officials", json=_official_payload(), headers=admin_headers).json()

    run = _run_detail(client, admin_headers, _refresh(client, admin_headers).json()["run_id"])
    assert run["status"] == "failed"  # 唯一官员失败 => 任务整体失败
    assert "失败 1" in run["summary"]
    assert _careers(client, admin_headers, official["id"])[0]["position"] == "旧职务"

    # 解析结果为空时哈希不落库，下次增量刷新仍会重试。
    mock_refresh["llm_payload"] = CAREERS_PAYLOAD
    retry = _run_detail(client, admin_headers, _refresh(client, admin_headers).json()["run_id"])
    assert "更新 1" in retry["summary"]


def test_resume_refresh_rejects_duplicate_running_task(client, admin_headers, monkeypatch):
    db = SessionLocal()
    try:
        db.add(TaskRun(kind="resume_refresh", ref_name="全体官员履历刷新", mode="incremental", status="running"))
        db.commit()
    finally:
        db.close()

    resp = _refresh(client, admin_headers)
    assert resp.status_code == 409
    assert "正在运行" in resp.json()["detail"]


def test_resume_refresh_rejects_invalid_mode(client, admin_headers):
    resp = _refresh(client, admin_headers, "once")
    assert resp.status_code == 400


def test_resume_refresh_requires_auth(client):
    resp = client.post("/api/officials/resume-refresh", json={})
    assert resp.status_code in (401, 403)
