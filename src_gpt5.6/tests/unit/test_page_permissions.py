# -*- coding: utf-8 -*-
"""智能分析合并页面：权限键迁移与接口访问控制测试。"""
from __future__ import annotations

from app.backend.core.database import SessionLocal, _migrate_page_key_aliases, engine
from app.backend.core.pages import GRANTABLE_PAGE_KEYS, PAGE_KEY_ALIASES
from app.backend.models.user import PagePermission, User


def _user_id_by_name(username: str) -> int:
    db = SessionLocal()
    try:
        return db.query(User).filter_by(username=username).one().id
    finally:
        db.close()


def _grant(user_id: int, keys: list[str]) -> None:
    db = SessionLocal()
    try:
        db.query(PagePermission).filter_by(user_id=user_id).delete()
        for key in keys:
            db.add(PagePermission(user_id=user_id, page_key=key))
        db.commit()
    finally:
        db.close()


def test_merged_page_key_replaces_old_keys(client, admin_headers):
    pages = client.get("/api/users/pages", headers=admin_headers).json()
    keys = {p["key"] for p in pages}
    assert "analysis" in keys
    assert "analysis_tasks" not in keys and "analysis_result" not in keys


def test_page_key_alias_migration_dedupes(client):
    """旧键 analysis_tasks / analysis_result 迁移为 analysis，并按用户去重。"""
    assert set(PAGE_KEY_ALIASES.values()) == {"analysis"}
    uid = _user_id_by_name("tester")
    _grant(uid, ["info_sources", "analysis_tasks", "analysis_result"])

    _migrate_page_key_aliases()

    db = SessionLocal()
    try:
        keys = sorted(p.page_key for p in db.query(PagePermission).filter_by(user_id=uid).all())
    finally:
        db.close()
    assert keys == ["analysis", "info_sources"]


def test_analysis_permission_gates_tasks_and_results(client, admin_headers):
    task = client.post(
        "/api/analysis-tasks",
        headers=admin_headers,
        json={"name": "权限任务", "source_ids": []},
    )
    assert task.status_code == 201, task.text
    tid = task.json()["id"]

    tester_token = client.post(
        "/api/auth/login", json={"username": "tester", "password": "tester123"}
    ).json()["access_token"]
    th = {"Authorization": f"Bearer {tester_token}"}
    uid = _user_id_by_name("tester")

    # 未授权：任务与结果接口都不可访问
    assert client.get("/api/analysis-tasks", headers=th).status_code == 403
    assert client.get("/api/analysis-results", headers=th).status_code == 403

    # 授予合并后的 analysis 键：两个接口都可访问
    _grant(uid, ["analysis"])
    assert client.get("/api/analysis-tasks", headers=th).status_code == 200
    assert client.get(f"/api/analysis-tasks/{tid}/results", headers=th).status_code == 200
    assert client.get("/api/analysis-results", headers=th).status_code == 200

    # 权限读取接口只返回有效键
    client.put(f"/api/users/{uid}/permissions", headers=admin_headers, json={"page_keys": ["analysis"]})
    perms = client.get(f"/api/users/{uid}/permissions", headers=admin_headers).json()
    assert perms == ["analysis"]


def test_grantable_keys_do_not_contain_legacy_aliases(client):
    assert "analysis_tasks" not in GRANTABLE_PAGE_KEYS
    assert "analysis_result" not in GRANTABLE_PAGE_KEYS
    assert "analysis" in GRANTABLE_PAGE_KEYS
