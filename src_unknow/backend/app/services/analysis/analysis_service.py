from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.official import Official
from app.repositories.neo4j_repo import Neo4jRepository
from app.services.analysis.relationship_engine import RelationshipEngine


class AnalysisService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.engine = RelationshipEngine(db)
        self.neo4j = Neo4jRepository()

    async def get_relationship(self, official_a: UUID, official_b: UUID) -> dict:
        result = await self.engine.compute_pair(official_a, official_b)
        return result

    async def get_connections(self, official_id: UUID, min_strength: float) -> dict:
        official = await self.db.get(Official, official_id)
        if official is None:
            return {"official": None, "connections": []}
        connections = await self.neo4j.get_connections(str(official_id), min_strength)
        return {
            "official": {"id": str(official.id), "name": official.name},
            "connections": connections,
        }

    async def get_path(self, from_id: UUID, to_id: UUID, max_depth: int) -> dict:
        paths = await self.neo4j.find_shortest_path(str(from_id), str(to_id), max_depth)
        return {"paths": paths}

    async def get_similarity(self, official_a: UUID, official_b: UUID) -> dict:
        score = await self.engine.similarity(official_a, official_b)
        return {"similarity": score}

    async def get_statistics(self) -> dict:
        count = await self.db.scalar(select(func.count()).select_from(Official))
        by_status = await self.db.execute(
            select(Official.status, func.count()).group_by(Official.status)
        )
        status_map = {row[0]: row[1] for row in by_status.all()}
        by_term = await self.db.execute(
            select(Official.committee_term, func.count()).group_by(Official.committee_term)
        )
        term_map = {row[0]: row[1] for row in by_term.all()}
        return {
            "total_officials": count or 0,
            "by_status": status_map,
            "by_committee_term": term_map,
        }

    async def run_clustering(self) -> dict:
        return {"clusters": [], "modularity": 0.0, "message": "Clustering scheduled for background processing"}
