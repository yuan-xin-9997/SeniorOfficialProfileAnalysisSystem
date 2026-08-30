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


def _migrate_officials_party_role() -> None:
    """旧库增量升级：officials 表缺少 party_role 列时补列，并按标签回填历史数据。"""
    from ..models.official import Official, derive_party_role

    with engine.connect() as conn:
        columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(officials)")}
        if not columns or "party_role" in columns:
            return
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


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
