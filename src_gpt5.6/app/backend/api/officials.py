"""高级官员履历管理、统计与关系网络 API。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from ..core.database import get_db
from ..core.deps import require_page
from ..models.official import Career, Official, OfficialRelation
from ..models.user import User
from ..schemas.official import (
    DashboardStats, OfficialBrief, OfficialCreate, OfficialDetail, OfficialPage, OfficialUpdate,
    RelationAnalysisRequest, RelationAnalysisResult, RelationCreate, RelationOut,
    TimelineRequest, TimelineResult,
)
from ..services.analysis.llm_client import LLMClient, LLMError

router = APIRouter(prefix="/api/officials", tags=["高级官员履历"])
access = require_page("officials")


def _replace_careers(db: Session, official: Official, careers) -> None:
    official.careers.clear()
    for index, item in enumerate(careers):
        data = item.model_dump(exclude={"id"})
        data["sort_order"] = item.sort_order if item.sort_order else index
        official.careers.append(Career(**data))


@router.get("", response_model=OfficialPage)
def list_officials(
    keyword: str = "", status_filter: str = Query("", alias="status"),
    organization: str = "", page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: User = Depends(access), db: Session = Depends(get_db),
):
    query = db.query(Official)
    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(or_(Official.name.like(pattern), Official.current_position.like(pattern), Official.organization.like(pattern)))
    if status_filter:
        query = query.filter(Official.status == status_filter)
    if organization:
        query = query.filter(Official.organization == organization)
    total = query.count()
    items = query.order_by(Official.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return OfficialPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(_: User = Depends(require_page("dashboard")), db: Session = Depends(get_db)):
    return DashboardStats(
        official_count=db.query(Official).count(),
        active_count=db.query(Official).filter(Official.status == "在任").count(),
        organization_count=db.query(func.count(func.distinct(Official.organization))).filter(Official.organization != "").scalar() or 0,
        career_count=db.query(Career).count(), relation_count=db.query(OfficialRelation).count(),
        recent_officials=db.query(Official).order_by(Official.updated_at.desc()).limit(6).all(),
    )


@router.get("/organizations", response_model=list[str])
def organizations(_: User = Depends(access), db: Session = Depends(get_db)):
    rows = db.query(Official.organization).filter(Official.organization != "").distinct().order_by(Official.organization).all()
    return [row[0] for row in rows]


@router.post("/timeline", response_model=TimelineResult)
def load_timeline(
    payload: TimelineRequest,
    _: User = Depends(require_page("timeline")),
    db: Session = Depends(get_db),
):
    """Load complete career archives for the selected people in selection order."""
    official_ids = list(dict.fromkeys(payload.official_ids))
    rows = (
        db.query(Official)
        .options(selectinload(Official.careers))
        .filter(Official.id.in_(official_ids))
        .all()
    )
    by_id = {row.id: row for row in rows}
    missing = [official_id for official_id in official_ids if official_id not in by_id]
    if missing:
        raise HTTPException(404, f"人物履历不存在：{', '.join(map(str, missing))}")
    return TimelineResult(officials=[by_id[official_id] for official_id in official_ids])


@router.get("/timeline/candidates", response_model=list[OfficialBrief])
def timeline_candidates(
    _: User = Depends(require_page("timeline")), db: Session = Depends(get_db)
):
    """List selectable people without requiring access to the archive editor page."""
    return db.query(Official).order_by(Official.name).all()


@router.get("/relations", response_model=list[RelationOut])
def list_relations(_: User = Depends(require_page("relations")), db: Session = Depends(get_db)):
    rows = db.query(OfficialRelation).options(selectinload(OfficialRelation.source), selectinload(OfficialRelation.target)).all()
    return [RelationOut(id=r.id, source_id=r.source_id, target_id=r.target_id, relation_type=r.relation_type,
        description=r.description, source_name=r.source.name, target_name=r.target.name, created_at=r.created_at) for r in rows]


def _profile_text(official: Official) -> str:
    careers = sorted(official.careers, key=lambda item: (item.sort_order, item.id or 0))
    timeline = "\n".join(
        f"- {item.start_date or '未知'} 至 {item.end_date or '未知'}：{item.organization or '未知机构'}，"
        f"{item.position or '未知职务'}，{item.location or '地点未知'}；{item.description or '无补充说明'}"
        for item in careers
    ) or "- 暂无任职经历"
    return (
        f"姓名：{official.name}\n现任职务：{official.current_position or '未知'}\n"
        f"所属机构：{official.organization or '未知'}\n籍贯：{official.native_place or '未知'}\n"
        f"学历：{official.education or '未知'}\n标签：{'、'.join(official.tags) or '无'}\n"
        f"人物概述：{official.summary or '无'}\n任职时间轴：\n{timeline}"
    )


@router.post("/relations/analyze", response_model=RelationAnalysisResult)
def analyze_relation(payload: RelationAnalysisRequest, _: User = Depends(require_page("relations")), db: Session = Depends(get_db)):
    if payload.source_id == payload.target_id:
        raise HTTPException(400, "请选择两位不同人物")
    rows = db.query(Official).options(selectinload(Official.careers)).filter(Official.id.in_([payload.source_id, payload.target_id])).all()
    by_id = {row.id: row for row in rows}
    source, target = by_id.get(payload.source_id), by_id.get(payload.target_id)
    if not source or not target:
        raise HTTPException(404, "关系人物不存在")
    system_prompt = (
        "你是严谨的公开人物履历关系分析助手。只能依据输入履历判断两人的关系，不得虚构未提供的事实。"
        "重叠任职、同机构、上下级、同乡、校友等均须指出具体履历依据；证据不足时明确写明未发现直接关系。"
        "只返回 JSON 对象，不要使用 Markdown。"
    )
    user_prompt = (
        "分析以下两人的可能关系。返回字段：relation_type（简短关系类型，证据不足写‘未发现直接关系’）、"
        "summary（完整分析结论）、evidence（字符串数组，列出履历中的时间、机构等依据）、confidence（高/中/低）。\n\n"
        f"人物 A：\n{_profile_text(source)}\n\n人物 B：\n{_profile_text(target)}"
    )
    try:
        raw = LLMClient().chat(system_prompt, user_prompt).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(raw)
    except LLMError as exc:
        raise HTTPException(502, f"关系分析失败：{exc}") from exc
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise HTTPException(502, "关系分析失败：模型未返回有效的结构化结果") from exc
    return RelationAnalysisResult(
        source_id=source.id, target_id=target.id, source_name=source.name, target_name=target.name,
        relation_type=str(result.get("relation_type") or "未发现直接关系"),
        summary=str(result.get("summary") or "模型未给出分析结论"),
        evidence=[str(item) for item in result.get("evidence", [])],
        confidence=str(result.get("confidence") or "中"),
    )


@router.post("/relations", response_model=RelationOut, status_code=status.HTTP_201_CREATED)
def create_relation(payload: RelationCreate, _: User = Depends(require_page("relations")), db: Session = Depends(get_db)):
    if payload.source_id == payload.target_id:
        raise HTTPException(400, "不能创建人物自身关系")
    source = db.get(Official, payload.source_id); target = db.get(Official, payload.target_id)
    if not source or not target:
        raise HTTPException(404, "关系人物不存在")
    row = OfficialRelation(**payload.model_dump()); db.add(row); db.commit(); db.refresh(row)
    return RelationOut(**payload.model_dump(), id=row.id, source_name=source.name, target_name=target.name, created_at=row.created_at)


@router.delete("/relations/{relation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_relation(relation_id: int, _: User = Depends(require_page("relations")), db: Session = Depends(get_db)):
    row = db.get(OfficialRelation, relation_id)
    if not row: raise HTTPException(404, "关系不存在")
    db.delete(row); db.commit()


@router.post("", response_model=OfficialDetail, status_code=status.HTTP_201_CREATED)
def create_official(payload: OfficialCreate, _: User = Depends(access), db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"careers"}); row = Official(**data)
    _replace_careers(db, row, payload.careers); db.add(row); db.commit(); db.refresh(row)
    return row


@router.get("/{official_id}", response_model=OfficialDetail)
def get_official(official_id: int, _: User = Depends(access), db: Session = Depends(get_db)):
    row = db.query(Official).options(selectinload(Official.careers)).filter(Official.id == official_id).first()
    if not row: raise HTTPException(404, "官员履历不存在")
    return row


@router.put("/{official_id}", response_model=OfficialDetail)
def update_official(official_id: int, payload: OfficialUpdate, _: User = Depends(access), db: Session = Depends(get_db)):
    row = db.query(Official).options(selectinload(Official.careers)).filter(Official.id == official_id).first()
    if not row: raise HTTPException(404, "官员履历不存在")
    for key, value in payload.model_dump(exclude={"careers"}).items(): setattr(row, key, value)
    _replace_careers(db, row, payload.careers); db.commit(); db.refresh(row)
    return row


@router.delete("/{official_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_official(official_id: int, _: User = Depends(access), db: Session = Depends(get_db)):
    row = db.get(Official, official_id)
    if not row: raise HTTPException(404, "官员履历不存在")
    db.query(OfficialRelation).filter(or_(OfficialRelation.source_id == official_id, OfficialRelation.target_id == official_id)).delete(synchronize_session=False)
    db.delete(row); db.commit()
