# -*- coding: utf-8 -*-
"""履历刷新（后台增量抓取 + 专用解析器）单元测试。"""
from __future__ import annotations

import pytest

from app.backend.core.database import SessionLocal
from app.backend.models.task import TaskRun
from app.backend.services.info_source.webfetch_client import WebFetchError

WIKI_HTML = """
<html><body><div id="mw-content-text">
  <div class="mw-heading mw-heading2"><h2 id="生平">生平</h2></div>
  <div class="mw-heading mw-heading3"><h3 id="福建任职">福建任职</h3></div>
  <p>1983年，刷新甲任中共福建省委办公厅综合处副处长。</p>
  <p>1994年3月，刷新甲挂职担任中共三明市委副书记。</p>
</div></body></html>
"""

GOV_HTML = """
<html><body><div class="article">
  <p>1973－1975年　福建省永安县西洋公社插队知青</p>
  <p>1975－1978年　福建师范大学政教系政教专业学习</p>
  <p>1983－1987年　福建省委办公厅综合处干部、副处长</p>
</div></body></html>
"""


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
def mock_fetch(monkeypatch):
    """替换履历刷新服务里的 WebFetchClient，返回按 URL 预设的页面。"""
    import app.backend.services.official.refresh as refresh

    state = {
        "pages": {},
        "fail_urls": set(),
        "fetch_calls": [],
        "proxy_calls": [],
    }

    class _MockFetchClient:
        def __init__(self, *args, **kwargs):
            pass

        def fetch_html(self, url, mode="auto", proxy_policy=None):
            state["fetch_calls"].append(url)
            state["proxy_calls"].append((url, proxy_policy))
            if url in state["fail_urls"]:
                raise WebFetchError(f"web_fetch 返回 500: {url}")
            return state["pages"].get(url, GOV_HTML)

    monkeypatch.setattr(refresh, "WebFetchClient", _MockFetchClient)
    return state


def _refresh(client, headers, mode=None):
    body = {"mode": mode} if mode else {}
    return client.post("/api/officials/resume-refresh", json=body, headers=headers)


def _run_detail(client, headers, run_id):
    return client.get(f"/api/task-center/runs/{run_id}", headers=headers).json()


def _careers(client, headers, official_id):
    return client.get(f"/api/officials/{official_id}", headers=headers).json()["careers"]


def test_resume_refresh_updates_careers_and_run(client, admin_headers, sync_worker, mock_fetch):
    mock_fetch["pages"] = {
        "https://zh.wikipedia.org/wiki/%E5%88%B7%E6%96%B0%E7%94%B2": WIKI_HTML,
        "https://example.com/gov": GOV_HTML,
    }
    first = client.post(
        "/api/officials",
        json=_official_payload("刷新甲", "https://zh.wikipedia.org/wiki/%E5%88%B7%E6%96%B0%E7%94%B2"),
        headers=admin_headers,
    ).json()
    second = client.post("/api/officials", json=_official_payload("刷新乙", "https://example.com/gov"), headers=admin_headers).json()

    resp = _refresh(client, admin_headers)
    assert resp.status_code == 200, resp.text
    run = _run_detail(client, admin_headers, resp.json()["run_id"])
    assert run["status"] == "succeeded"
    assert "更新 2" in run["summary"]
    assert run["kind"] == "resume_refresh"
    assert run["mode"] == "incremental"

    wiki_careers = _careers(client, admin_headers, first["id"])
    assert wiki_careers[0]["position"] == "中共福建省委办公厅综合处副处长"
    assert wiki_careers[0]["start_date"] == "1983"
    gov_careers = _careers(client, admin_headers, second["id"])
    assert gov_careers[0]["position"] == "福建省永安县西洋公社插队知青"
    assert (gov_careers[0]["start_date"], gov_careers[0]["end_date"]) == ("1973", "1975")

    # 维基百科链接必须经代理抓取，官媒直连
    proxy_targets = {url for url, policy in mock_fetch["proxy_calls"] if policy == "proxy"}
    assert "https://zh.wikipedia.org/wiki/%E5%88%B7%E6%96%B0%E7%94%B2" in proxy_targets
    assert all(policy is None for url, policy in mock_fetch["proxy_calls"] if url == "https://example.com/gov")

    messages = [log["message"] for log in run["logs"]]
    assert any("刷新甲: 维基百科解析器已更新 2 条任职经历" in msg for msg in messages)
    assert any("刷新乙: 通用解析器已更新 3 条任职经历" in msg for msg in messages)


def test_resume_refresh_incremental_skips_unchanged_pages(client, admin_headers, sync_worker, mock_fetch):
    official = client.post("/api/officials", json=_official_payload(), headers=admin_headers).json()

    first = _run_detail(client, admin_headers, _refresh(client, admin_headers).json()["run_id"])
    assert "更新 1" in first["summary"]

    # 第二次增量刷新：页面相同 -> 哈希命中直接跳过，不再解析。
    second = _run_detail(client, admin_headers, _refresh(client, admin_headers).json()["run_id"])
    assert "跳过 1" in second["summary"] and "更新 0" in second["summary"]

    # full 模式强制重新解析。
    full = _run_detail(client, admin_headers, _refresh(client, admin_headers, "full").json()["run_id"])
    assert "更新 1" in full["summary"]
    assert _careers(client, admin_headers, official["id"])[0]["position"] == "福建省永安县西洋公社插队知青"


def test_resume_refresh_skips_officials_without_source_url(client, admin_headers, sync_worker, mock_fetch):
    client.post("/api/officials", json=_official_payload("有源甲"), headers=admin_headers)
    no_source = _official_payload("无源乙")
    no_source["source_url"] = ""
    client.post("/api/officials", json=no_source, headers=admin_headers)

    run = _run_detail(client, admin_headers, _refresh(client, admin_headers).json()["run_id"])
    assert run["status"] == "succeeded"
    assert "无来源 1" in run["summary"]
    assert len(mock_fetch["fetch_calls"]) == 1
    assert any("无源乙" in msg and "跳过" in msg for msg in [log["message"] for log in run["logs"]])


def test_resume_refresh_survives_single_official_failure(client, admin_headers, sync_worker, mock_fetch):
    mock_fetch["pages"] = {"https://example.com/a": GOV_HTML}
    mock_fetch["fail_urls"] = {"https://example.com/b"}
    ok = client.post("/api/officials", json=_official_payload("成功甲", "https://example.com/a"), headers=admin_headers).json()
    bad = client.post("/api/officials", json=_official_payload("失败乙", "https://example.com/b"), headers=admin_headers).json()

    run = _run_detail(client, admin_headers, _refresh(client, admin_headers).json()["run_id"])
    assert run["status"] == "succeeded"
    assert "失败 1" in run["summary"]

    assert _careers(client, admin_headers, ok["id"])[0]["position"] == "福建省永安县西洋公社插队知青"
    failed_careers = _careers(client, admin_headers, bad["id"])
    assert failed_careers[0]["position"] == "旧职务"
    assert any("失败乙: 刷新失败" in log["message"] for log in run["logs"])


def test_resume_refresh_empty_parse_keeps_existing_careers(client, admin_headers, sync_worker, mock_fetch):
    mock_fetch["pages"] = {"https://example.com/empty": "<html><body><p>没有任何日期的页面</p></body></html>"}
    official = client.post("/api/officials", json=_official_payload("空解析甲", "https://example.com/empty"), headers=admin_headers).json()

    run = _run_detail(client, admin_headers, _refresh(client, admin_headers).json()["run_id"])
    assert run["status"] == "failed"  # 唯一官员失败 => 任务整体失败
    assert "失败 1" in run["summary"]
    assert _careers(client, admin_headers, official["id"])[0]["position"] == "旧职务"

    # 解析结果为空时哈希不落库，配置好来源后下次增量刷新仍会重试。
    mock_fetch["pages"]["https://example.com/empty"] = GOV_HTML
    retry = _run_detail(client, admin_headers, _refresh(client, admin_headers).json()["run_id"])
    assert "更新 1" in retry["summary"]


def test_resume_refresh_rejects_duplicate_running_task(client, admin_headers):
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
