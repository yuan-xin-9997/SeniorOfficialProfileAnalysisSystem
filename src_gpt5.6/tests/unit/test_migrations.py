# -*- coding: utf-8 -*-
"""officials 表 party_role 列的旧库增量迁移与标签回填测试。"""
from __future__ import annotations

import json

from app.backend.core.database import (
    Base,
    SessionLocal,
    _migrate_officials_party_role,
    engine,
)


def _create_legacy_officials_table() -> None:
    """按旧版结构重建 officials 表（缺少 party_role 列），并插入两行历史数据。"""
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE officials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(128) NOT NULL,
                gender VARCHAR(16),
                birth_date DATE,
                ethnicity VARCHAR(64),
                native_place VARCHAR(128),
                education VARCHAR(255),
                current_position VARCHAR(255),
                organization VARCHAR(255),
                administrative_rank VARCHAR(64),
                status VARCHAR(32),
                summary TEXT,
                photo_url VARCHAR(1024),
                source_url VARCHAR(1024),
                tags JSON,
                created_at DATETIME,
                updated_at DATETIME
            )
            """
        )
        conn.exec_driver_sql(
            "INSERT INTO officials (name, status, tags, created_at, updated_at) "
            "VALUES ('张三', '在任', ?, '2024-01-01 00:00:00', '2024-01-01 00:00:00')",
            (json.dumps(["中共二十届中央委员"], ensure_ascii=False),),
        )
        conn.exec_driver_sql(
            "INSERT INTO officials (name, status, tags, created_at, updated_at) "
            "VALUES ('李四', '在任', ?, '2024-01-01 00:00:00', '2024-01-01 00:00:00')",
            (json.dumps([], ensure_ascii=False),),
        )


def _party_roles_by_name() -> dict[str, str]:
    from app.backend.models.official import Official

    db = SessionLocal()
    try:
        return {row.name: row.party_role for row in db.query(Official).all()}
    finally:
        db.close()


def test_party_role_migration_backfills_from_tags(client):
    _create_legacy_officials_table()
    _migrate_officials_party_role()
    assert _party_roles_by_name() == {"张三": "中央委员", "李四": ""}


def test_party_role_migration_is_idempotent(client):
    _create_legacy_officials_table()
    _migrate_officials_party_role()
    _migrate_officials_party_role()
    assert _party_roles_by_name() == {"张三": "中央委员", "李四": ""}
