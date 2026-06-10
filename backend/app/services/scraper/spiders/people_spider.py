"""Placeholder spider — returns sample data for pipeline testing."""

from datetime import date

from app.schemas.official import CareerEntryIn, OfficialCreate, PoliticalCareerIn


class PeopleSpider:
    source_id = "people"

    async def fetch(self, url: str) -> str:
        return ""

    def get_official_urls(self, name: str) -> list[str]:
        return [f"https://www.people.com.cn/search?keyword={name}"]

    def parse(self, html: str, name: str) -> OfficialCreate | None:
        return OfficialCreate(
            name=name,
            birth_date=date(1960, 1, 1),
            birth_place="示例省示例市",
            gender="M",
            committee_term="第二十届",
            committee_type="member",
            status="active",
            current_position="示例职务",
            current_level="省部级",
            career_entries=[
                CareerEntryIn(
                    start_year=1982,
                    end_year=1986,
                    entry_type="education",
                    description=f"{name} 大学就读",
                ),
                CareerEntryIn(
                    start_year=2000,
                    end_year=2010,
                    entry_type="political",
                    description=f"{name} 某地任职",
                    political_career=PoliticalCareerIn(
                        location="北京市",
                        department="示例部门",
                        position="副市长",
                        level="厅局级",
                    ),
                ),
            ],
        )
