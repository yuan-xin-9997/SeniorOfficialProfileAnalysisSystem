from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.official import Official
from app.models.scraper import ScraperTask
from app.services.official_service import OfficialService
from app.services.scraper.spiders.people_spider import PeopleSpider
from app.services.storage.official_storage import compute_content_hash


class ScraperOrchestrator:
    SPIDERS = {"PeopleSpider": PeopleSpider}

    def __init__(self, db: AsyncSession):
        self.db = db
        self.official_service = OfficialService(db)

    async def run(self, task: ScraperTask) -> dict:
        spider = PeopleSpider()
        target_names = await self._get_target_names()
        total = len(target_names)
        updated = 0
        failed = 0

        for name in target_names:
            try:
                urls = spider.get_official_urls(name)
                html = await spider.fetch(urls[0]) if urls else ""
                dto = spider.parse(html, name)
                if dto is None:
                    failed += 1
                    continue
                existing = await self.db.execute(select(Official).where(Official.name == name))
                official = existing.scalar_one_or_none()
                if official:
                    new_hash = compute_content_hash_from_dto(dto)
                    if official.content_hash == new_hash:
                        continue
                    from app.schemas.official import OfficialUpdate

                    await self.official_service.update(
                        official,
                        OfficialUpdate(
                            current_position=dto.current_position,
                            current_level=dto.current_level,
                            status=dto.status,
                        ),
                    )
                else:
                    await self.official_service.create(dto)
                updated += 1
            except Exception:
                failed += 1

        return {
            "total": total,
            "updated": updated,
            "failed": failed,
            "message": f"processed {total} officials",
        }

    async def _get_target_names(self) -> list[str]:
        result = await self.db.execute(select(Official.name))
        names = [row[0] for row in result.all()]
        if names:
            return names
        return ["示例官员A", "示例官员B"]


def compute_content_hash_from_dto(dto) -> str:
    from app.models.official import Official

    o = Official(
        name=dto.name,
        birth_date=dto.birth_date,
        birth_place=dto.birth_place,
        gender=dto.gender,
        committee_term=dto.committee_term,
        committee_type=dto.committee_type,
        status=dto.status,
    )
    return compute_content_hash(o)
