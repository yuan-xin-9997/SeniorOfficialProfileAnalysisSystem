from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.official import CareerEntry, Education, Official, PoliticalCareer
from app.repositories.neo4j_repo import Neo4jRepository
from app.schemas.official import CareerEntryIn, OfficialCreate, OfficialUpdate
from app.services.analysis.relationship_engine import RelationshipEngine
from app.services.storage.data_quality import DataQualityValidator
from app.services.storage.official_storage import compute_content_hash


class OfficialService:
    def __init__(self, db: AsyncSession, neo4j: Neo4jRepository | None = None):
        self.db = db
        self.neo4j = neo4j or Neo4jRepository()
        self.quality = DataQualityValidator()
        self.relationship_engine = RelationshipEngine(db)

    async def get_by_id(self, official_id: UUID) -> Official | None:
        result = await self.db.execute(
            select(Official)
            .where(Official.id == official_id)
            .options(
                selectinload(Official.career_entries).selectinload(CareerEntry.education),
                selectinload(Official.career_entries).selectinload(CareerEntry.political_career),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, data: OfficialCreate) -> Official:
        official = Official(
            name=data.name,
            birth_date=data.birth_date,
            birth_place=data.birth_place,
            ancestral_home=data.ancestral_home,
            ethnicity=data.ethnicity,
            political_affiliation=data.political_affiliation,
            gender=data.gender,
            photo_url=data.photo_url,
            current_position=data.current_position,
            current_level=data.current_level,
            committee_term=data.committee_term,
            committee_type=data.committee_type,
            status=data.status,
        )
        self._apply_career_entries(official, data.career_entries)
        official.completeness_score = self.quality.score(official)
        official.content_hash = compute_content_hash(official)
        self.db.add(official)
        await self.db.flush()
        await self.neo4j.merge_official(official)
        await self.relationship_engine.recompute_for_official(official.id)
        return official

    async def update(self, official: Official, data: OfficialUpdate) -> Official:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(official, field, value)
        official.completeness_score = self.quality.score(official)
        official.content_hash = compute_content_hash(official)
        await self.db.flush()
        await self.neo4j.merge_official(official)
        await self.relationship_engine.recompute_for_official(official.id)
        return official

    async def delete(self, official: Official) -> None:
        oid = str(official.id)
        await self.db.delete(official)
        await self.db.flush()
        await self.neo4j.delete_official(oid)

    def _apply_career_entries(self, official: Official, entries: list[CareerEntryIn]) -> None:
        for entry_in in entries:
            entry = CareerEntry(
                start_year=entry_in.start_year,
                end_year=entry_in.end_year,
                entry_type=entry_in.entry_type,
                description=entry_in.description,
            )
            if entry_in.education:
                entry.education = Education(**entry_in.education.model_dump())
            if entry_in.political_career:
                entry.political_career = PoliticalCareer(**entry_in.political_career.model_dump())
            official.career_entries.append(entry)
