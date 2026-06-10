from app.models.official import Official


class DataQualityValidator:
    REQUIRED_FIELDS = ("name", "birth_date", "birth_place", "committee_term", "gender")

    def score(self, official: Official) -> float:
        filled = 0
        total = 8
        for field in self.REQUIRED_FIELDS:
            if getattr(official, field, None):
                filled += 1
        if official.current_position:
            filled += 1
        if official.ancestral_home:
            filled += 1
        if official.career_entries:
            filled += min(2, len(official.career_entries))
        return round(min(1.0, filled / total), 2)
