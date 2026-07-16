from abc import ABC, abstractmethod

from app.schemas.official import OfficialCreate


class BaseSpider(ABC):
    source_id: str = ""

    @abstractmethod
    async def fetch(self, url: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def parse(self, html: str, name: str) -> OfficialCreate | None:
        raise NotImplementedError

    @abstractmethod
    def get_official_urls(self, name: str) -> list[str]:
        raise NotImplementedError
