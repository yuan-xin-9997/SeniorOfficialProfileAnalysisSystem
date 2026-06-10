from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.official import CareerEntry, Education, Official, PoliticalCareer, Relationship
from app.repositories.neo4j_repo import Neo4jRepository

DIMENSIONS = [
    ("department", 0.30),
    ("region", 0.25),
    ("superior", 0.20),
    ("schoolmate", 0.10),
    ("hometown", 0.10),
    ("time_overlap", 0.05),
]

STRENGTH_LEVELS = [
    (0.8, "密切同盟"),
    (0.5, "一般同盟"),
    (0.3, "弱关联"),
    (0.0, "无明显关联"),
]


def strength_level(strength: float) -> str:
    for threshold, label in STRENGTH_LEVELS:
        if strength >= threshold:
            return label
    return "无明显关联"


def _years_overlap(a_start: int, a_end: int | None, b_start: int, b_end: int | None) -> int:
    a_end_val = a_end or 9999
    b_end_val = b_end or 9999
    start = max(a_start, b_start)
    end = min(a_end_val, b_end_val)
    return max(0, end - start + 1)


def _normalize_province(location: str | None) -> str:
    if not location:
        return ""
    for suffix in ("省", "市", "自治区"):
        if suffix in location:
            return location.split(suffix)[0] + suffix
    return location[:2]


class RelationshipEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.neo4j = Neo4jRepository()

    async def _load_official(self, official_id: UUID) -> Official | None:
        result = await self.db.execute(
            select(Official)
            .where(Official.id == official_id)
            .options(
                selectinload(Official.career_entries).selectinload(CareerEntry.political_career),
                selectinload(Official.career_entries).selectinload(CareerEntry.education),
            )
        )
        return result.scalar_one_or_none()

    async def compute_pair(self, id_a: UUID, id_b: UUID) -> dict:
        a = await self._load_official(id_a)
        b = await self._load_official(id_b)
        if a is None or b is None:
            return {"error": "official not found"}
        dims = []
        score_sum = 0.0
        max_overlap = 0

        pol_a = [e.political_career for e in a.career_entries if e.political_career]
        pol_b = [e.political_career for e in b.career_entries if e.political_career]

        dept_match = False
        region_match = False
        for pa, ea in [(p, e) for e in a.career_entries for p in ([e.political_career] if e.political_career else [])]:
            for pb, eb in [
                (p, e) for e in b.career_entries for p in ([e.political_career] if e.political_career else [])
            ]:
                overlap = _years_overlap(ea.start_year, ea.end_year, eb.start_year, eb.end_year)
                max_overlap = max(max_overlap, overlap)
                if pa.department and pb.department and pa.department == pb.department and overlap >= 1:
                    dept_match = True
                if _normalize_province(pa.location) == _normalize_province(pb.location) and overlap >= 1:
                    region_match = True

        superior_match = any(
            (p.superior_id == b.id) or (q.superior_id == a.id)
            for p in pol_a
            for q in pol_b
            if p and q
        ) or any(p.superior_id == b.id for p in pol_a if p) or any(p.superior_id == a.id for p in pol_b if p)

        edu_a = {e.education.institution for e in a.career_entries if e.education}
        edu_b = {e.education.institution for e in b.career_entries if e.education}
        school_match = bool(edu_a & edu_b)

        home_a = {_normalize_province(a.birth_place), _normalize_province(a.ancestral_home or "")}
        home_b = {_normalize_province(b.birth_place), _normalize_province(b.ancestral_home or "")}
        hometown_match = bool((home_a - {""}) & (home_b - {""}))

        flags = [
            ("同一部门共事", 0.30, dept_match),
            ("同一地区任职", 0.25, region_match),
            ("上下级关系", 0.20, superior_match),
            ("校友关系", 0.10, school_match),
            ("同乡关系", 0.10, hometown_match),
            ("时间重叠度", 0.05, max_overlap > 0),
        ]
        time_factor = min(1.0, max_overlap / (max(max_overlap, 1) + 2))
        for name, weight, matched in flags:
            si = 1.0 if matched else 0.0
            score_sum += weight * si
            dims.append({"name": name, "weight": weight, "matched": matched})

        strength = min(1.0, round(score_sum * time_factor, 4))
        return {
            "official_a": {"id": str(a.id), "name": a.name},
            "official_b": {"id": str(b.id), "name": b.name},
            "strength": strength,
            "level": strength_level(strength),
            "dimensions": dims,
            "time_overlap_years": max_overlap,
        }

    async def similarity(self, id_a: UUID, id_b: UUID) -> float:
        a = await self._load_official(id_a)
        b = await self._load_official(id_b)
        if a is None or b is None:
            return 0.0
        regions_a = {
            _normalize_province(e.political_career.location)
            for e in a.career_entries
            if e.political_career
        }
        regions_b = {
            _normalize_province(e.political_career.location)
            for e in b.career_entries
            if e.political_career
        }
        schools_a = {e.education.institution for e in a.career_entries if e.education}
        schools_b = {e.education.institution for e in b.career_entries if e.education}
        union = regions_a | regions_b | schools_a | schools_b
        if not union:
            return 0.0
        inter = (regions_a & regions_b) | (schools_a & schools_b)
        return round(len(inter) / len(union), 4)

    async def recompute_for_official(self, official_id: UUID) -> None:
        result = await self.db.execute(select(Official.id).where(Official.id != official_id))
        other_ids = [row[0] for row in result.all()]
        for other_id in other_ids:
            pair = await self.compute_pair(official_id, other_id)
            strength = pair.get("strength", 0)
            if strength < 0.3:
                continue
            rel_type = "COLLEAGUE"
            for d in pair.get("dimensions", []):
                if d["name"] == "上下级关系" and d["matched"]:
                    rel_type = "SUPERIOR_SUBORDINATE"
                    break
            await self._upsert_relationship(official_id, other_id, rel_type, strength)
            await self.neo4j.merge_relationship(
                str(official_id), str(other_id), rel_type, strength
            )

    async def _upsert_relationship(
        self, source_id: UUID, target_id: UUID, rel_type: str, strength: float
    ) -> None:
        result = await self.db.execute(
            select(Relationship).where(
                Relationship.source_official_id == source_id,
                Relationship.target_official_id == target_id,
                Relationship.relationship_type == rel_type,
            )
        )
        rel = result.scalar_one_or_none()
        if rel:
            rel.strength = strength
        else:
            self.db.add(
                Relationship(
                    source_official_id=source_id,
                    target_official_id=target_id,
                    relationship_type=rel_type,
                    strength=strength,
                )
            )
