from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import (
    CareerEvent,
    Evidence,
    Location,
    Official,
    Organization,
    Position,
    SourceDocument,
)


DATE_RANGE_PATTERN = re.compile(
    r"(?P<sy>19\d{2}|20\d{2})"
    r"(?:[年./\-](?P<sm>\d{1,2})月?)?"
    r"\s*(?:至|到|--|—|－|-|~|～)\s*"
    r"(?:(?P<ey>19\d{2}|20\d{2})(?:[年./\-](?P<em>\d{1,2})月?)?|今|现在|现任)",
)

ORG_KEYWORDS = [
    "大学",
    "学院",
    "学校",
    "中央党校",
    "省委",
    "市委",
    "县委",
    "区委",
    "委员会",
    "政府",
    "国务院",
    "人大",
    "政协",
    "厅",
    "局",
    "部",
    "委",
    "办",
    "公司",
    "集团",
]


@dataclass
class ParsedEvent:
    event_type: str
    start_date: date | None
    end_date: date | None
    start_precision: str
    end_precision: str
    organization_name: str | None
    position_name: str | None
    location_name: str | None
    description: str
    original_text: str
    confidence: float


@dataclass
class ProfileParseResult:
    official_id: str | None
    official_name: str | None
    created_events: int
    skipped_duplicates: int
    parsed_candidates: int
    message: str


def parse_source_document_profile(db: Session, document: SourceDocument) -> ProfileParseResult:
    text = read_document_text(document)
    if not text:
        document.parse_status = "parse_failed"
        db.commit()
        return ProfileParseResult(None, None, 0, 0, 0, "来源文档没有可解析正文")

    official = detect_official(db, text, document.title)
    if not official:
        document.parse_status = "no_official_matched"
        db.commit()
        return ProfileParseResult(None, None, 0, 0, 0, "未能在正文中匹配已入库官员姓名")

    parsed_events = parse_timeline_events(text)
    created_events = 0
    skipped_duplicates = 0

    for parsed in parsed_events:
        if is_duplicate_event(db, official.id, parsed):
            skipped_duplicates += 1
            continue
        event = create_event_from_parsed(db, official.id, parsed)
        db.add(
            Evidence(
                entity_type="career_event",
                entity_id=event.id,
                field_name="description",
                source_document_id=document.id,
                quote_text=parsed.original_text[:1000],
                confidence=parsed.confidence,
            )
        )
        created_events += 1

    document.parse_status = "parsed" if created_events or skipped_duplicates else "no_events_found"
    db.commit()
    return ProfileParseResult(
        official_id=official.id,
        official_name=official.name,
        created_events=created_events,
        skipped_duplicates=skipped_duplicates,
        parsed_candidates=len(parsed_events),
        message="解析完成",
    )


def read_document_text(document: SourceDocument) -> str:
    if not document.plain_text_path:
        return ""
    path = Path(document.plain_text_path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def detect_official(db: Session, text: str, title: str | None) -> Official | None:
    haystack = f"{title or ''}\n{text[:5000]}"
    officials = db.query(Official).filter(Official.deleted_at.is_(None)).all()
    officials.sort(key=lambda item: len(item.name), reverse=True)
    for official in officials:
        if official.name and official.name in haystack:
            return official
    return None


def parse_timeline_events(text: str) -> list[ParsedEvent]:
    events: list[ParsedEvent] = []
    for line in normalize_lines(text):
        match = DATE_RANGE_PATTERN.search(line)
        if not match:
            continue
        description = line[match.end() :].strip(" ，,；;。")
        if len(description) < 4:
            continue
        start_date, start_precision = build_date(match.group("sy"), match.group("sm"), is_end=False)
        end_date, end_precision = build_date(match.group("ey"), match.group("em"), is_end=True)
        event_type = infer_event_type(description)
        organization_name = infer_organization_name(description)
        position_name = infer_position_name(description, event_type)
        location_name = infer_location_name(description)
        confidence = infer_confidence(description, organization_name, start_date, end_date)
        events.append(
            ParsedEvent(
                event_type=event_type,
                start_date=start_date,
                end_date=end_date,
                start_precision=start_precision,
                end_precision=end_precision,
                organization_name=organization_name,
                position_name=position_name,
                location_name=location_name,
                description=description,
                original_text=line,
                confidence=confidence,
            )
        )
    return events


def normalize_lines(text: str) -> list[str]:
    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        line = line.strip("●·•\t ")
        if line:
            lines.append(line)
    return lines


def build_date(year: str | None, month: str | None, is_end: bool) -> tuple[date | None, str]:
    if not year:
        return None, "unknown"
    month_int = int(month) if month else (12 if is_end else 1)
    month_int = min(max(month_int, 1), 12)
    day = 28 if is_end else 1
    return date(int(year), month_int, day), "month" if month else "year"


def infer_event_type(description: str) -> str:
    if any(keyword in description for keyword in ["大学", "学院", "学校", "专业", "学习", "研究生", "博士", "硕士"]):
        return "education"
    if "挂职" in description:
        return "temporary_post"
    if "任" in description or any(keyword in description for keyword in ["书记", "主任", "部长", "省长", "市长", "主席", "委员", "干部"]):
        return "appointment"
    return "career"


def infer_organization_name(description: str) -> str | None:
    segments = re.split(r"[，,；;。]", description)
    for segment in segments:
        segment = segment.strip()
        if any(keyword in segment for keyword in ORG_KEYWORDS):
            return trim_org_segment(segment)
    return None


def trim_org_segment(segment: str) -> str:
    segment = re.sub(r"(任|为|兼|学习|工作).*$", "", segment).strip()
    if len(segment) > 40:
        segment = segment[:40]
    return segment or "未知机构"


def infer_position_name(description: str, event_type: str) -> str | None:
    if event_type == "education":
        match = re.search(r"([\u4e00-\u9fa5A-Za-z0-9（）()]+专业)", description)
        return match.group(1) if match else "学生"
    match = re.search(r"(书记|副书记|主任|副主任|部长|副部长|省长|副省长|市长|副市长|主席|副主席|委员|干部)", description)
    return match.group(1) if match else None


def infer_location_name(description: str) -> str | None:
    match = re.search(r"([\u4e00-\u9fa5]{2,8}(省|市|县|区|自治区))", description)
    return match.group(1) if match else None


def infer_confidence(
    description: str,
    organization_name: str | None,
    start_date: date | None,
    end_date: date | None,
) -> float:
    confidence = 0.55
    if organization_name:
        confidence += 0.15
    if start_date:
        confidence += 0.1
    if end_date:
        confidence += 0.1
    if len(description) >= 8:
        confidence += 0.05
    return min(confidence, 0.9)


def is_duplicate_event(db: Session, official_id: str, parsed: ParsedEvent) -> bool:
    return (
        db.query(CareerEvent)
        .filter(
            CareerEvent.official_id == official_id,
            CareerEvent.start_date == parsed.start_date,
            CareerEvent.end_date == parsed.end_date,
            CareerEvent.description == parsed.description,
            CareerEvent.deleted_at.is_(None),
        )
        .first()
        is not None
    )


def create_event_from_parsed(db: Session, official_id: str, parsed: ParsedEvent) -> CareerEvent:
    organization = ensure_organization(db, parsed.organization_name)
    location = ensure_location(db, parsed.location_name)
    position = ensure_position(db, parsed.position_name, organization.id if organization else None)
    event = CareerEvent(
        official_id=official_id,
        event_type=parsed.event_type,
        start_date=parsed.start_date,
        end_date=parsed.end_date,
        start_precision=parsed.start_precision,
        end_precision=parsed.end_precision,
        organization_id=organization.id if organization else None,
        position_id=position.id if position else None,
        location_id=location.id if location else None,
        description=parsed.description,
        original_text=parsed.original_text,
        confidence=parsed.confidence,
        review_status="pending_review",
    )
    db.add(event)
    db.flush()
    return event


def ensure_organization(db: Session, name: str | None) -> Organization | None:
    if not name:
        return None
    organization = db.query(Organization).filter(Organization.name == name).first()
    if organization:
        return organization
    organization = Organization(name=name, full_name=name, org_type="unknown")
    db.add(organization)
    db.flush()
    return organization


def ensure_location(db: Session, name: str | None) -> Location | None:
    if not name:
        return None
    location = db.query(Location).filter(Location.name == name).first()
    if location:
        return location
    location = Location(name=name, full_name=name, country="中国", level="unknown")
    db.add(location)
    db.flush()
    return location


def ensure_position(db: Session, name: str | None, organization_id: str | None) -> Position | None:
    if not name:
        return None
    query = db.query(Position).filter(Position.name == name)
    if organization_id:
        query = query.filter(Position.organization_id == organization_id)
    position = query.first()
    if position:
        return position
    position = Position(
        name=name,
        normalized_name=name,
        organization_id=organization_id,
        position_type="unknown",
    )
    db.add(position)
    db.flush()
    return position
