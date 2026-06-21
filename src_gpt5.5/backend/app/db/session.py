from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import (
    Base,
    CommitteeTerm,
    RelationshipWeightItem,
    RelationshipWeightProfile,
    User,
)


engine_kwargs = {}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


DEFAULT_RELATIONSHIP_WEIGHTS = {
    "secretary_to": (90, 100, "公开来源明确描述的秘书/服务对象关系。"),
    "superior_subordinate": (80, 100, "同机构或公开资料显示的上下级关系。"),
    "same_organization_overlap": (60, 90, "同机构任职且时间重叠。"),
    "same_location_overlap": (45, 70, "同地区任职且时间重叠。"),
    "same_major_same_period": (45, 70, "同专业且学习时间重叠。"),
    "predecessor_successor": (35, 60, "同一职位前后任。"),
    "same_school": (25, 50, "曾在同一学校学习。"),
    "same_native_place": (20, 40, "籍贯相同。"),
    "same_birth_place": (20, 40, "出生地相同。"),
    "same_committee_term": (10, 25, "同一届中央委员会。"),
}


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ensure_initial_admin(db)
        ensure_current_committee_term(db)
        ensure_default_weight_profile(db)


def ensure_initial_admin(db: Session) -> None:
    existing = db.query(User).filter(User.username == settings.INITIAL_ADMIN_USERNAME).first()
    if existing:
        return
    db.add(
        User(
            username=settings.INITIAL_ADMIN_USERNAME,
            password_hash=hash_password(settings.INITIAL_ADMIN_PASSWORD),
            role="ADMIN",
            display_name="系统管理员",
            is_active=True,
        )
    )
    db.commit()


def ensure_current_committee_term(db: Session) -> None:
    existing = db.query(CommitteeTerm).filter(CommitteeTerm.term_no == 20).first()
    if existing:
        if not existing.is_current:
            existing.is_current = True
            db.commit()
        return
    db.add(
        CommitteeTerm(
            term_no=20,
            name="中国共产党第二十届中央委员会",
            start_year=2022,
            end_year=2027,
            is_current=True,
        )
    )
    db.commit()


def ensure_default_weight_profile(db: Session) -> None:
    existing = (
        db.query(RelationshipWeightProfile)
        .filter(RelationshipWeightProfile.name == "default")
        .first()
    )
    if existing:
        return

    profile = RelationshipWeightProfile(name="default", is_default=True)
    db.add(profile)
    db.flush()
    for relationship_type, (base_weight, max_score, description) in (
        DEFAULT_RELATIONSHIP_WEIGHTS.items()
    ):
        db.add(
            RelationshipWeightItem(
                profile_id=profile.id,
                relationship_type=relationship_type,
                base_weight=base_weight,
                max_score=max_score,
                description=description,
            )
        )
    db.commit()
