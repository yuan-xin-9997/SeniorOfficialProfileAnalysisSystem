"""Database engine, declarative base, session factory."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


settings.database_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{settings.database_path}",
    connect_args={"check_same_thread": False},  # required for FastAPI threadpool
    echo=False,
)


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    """SQLite 默认关闭外键约束，导致 ondelete=CASCADE 不生效。每个连接开启它。"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Create all tables. Imports models so they register on ``Base``."""
    from .. import models  # noqa: F401  (registers ORM models)

    Base.metadata.create_all(bind=engine)
    _migrate_officials_party_role()
    _migrate_page_key_aliases()


def _table_columns(conn, table: str) -> set[str]:
    return {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}


def _migrate_officials_party_role() -> None:
    """旧库增量升级：补 party_role 列（如缺失），并把空值行按标签回填党内职务。"""
    from ..models.official import Official, derive_party_role

    with engine.connect() as conn:
        columns = _table_columns(conn, "officials")
        if not columns or "party_role" in columns:
            pass
        else:
            conn.exec_driver_sql(
                "ALTER TABLE officials ADD COLUMN party_role VARCHAR(32) NOT NULL DEFAULT ''"
            )
            conn.commit()

    db = SessionLocal()
    try:
        rows = db.query(Official).filter(Official.party_role == "").all()
        changed = 0
        for row in rows:
            derived = derive_party_role(row.tags)
            if derived:
                row.party_role = derived
                changed += 1
        if changed:
            db.commit()
    finally:
        db.close()


def _migrate_page_key_aliases() -> None:
    """页面合并/改名后，把 page_permissions 中的旧权限键改写为新键并去重。"""
    from .pages import PAGE_KEY_ALIASES

    with engine.connect() as conn:
        if "page_key" not in _table_columns(conn, "page_permissions"):
            return
        for old_key, new_key in PAGE_KEY_ALIASES.items():
            if old_key == new_key:
                continue
            # 目标新键已存在的用户直接删掉旧行，避免触发 (user_id, page_key) 唯一约束。
            conn.exec_driver_sql(
                "DELETE FROM page_permissions WHERE page_key = ? AND EXISTS ("
                "SELECT 1 FROM page_permissions p2 "
                "WHERE p2.user_id = page_permissions.user_id AND p2.page_key = ?)",
                (old_key, new_key),
            )
            conn.exec_driver_sql(
                "UPDATE page_permissions SET page_key = ? WHERE page_key = ?",
                (new_key, old_key),
            )
            # 同一用户的多个旧键合并到同一新键后按行去重。
            conn.exec_driver_sql(
                "DELETE FROM page_permissions WHERE page_key = ? AND id NOT IN ("
                "SELECT MIN(id) FROM page_permissions WHERE page_key = ? GROUP BY user_id)",
                (new_key, new_key),
            )
        conn.commit()


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
