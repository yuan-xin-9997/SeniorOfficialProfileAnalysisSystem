from datetime import date

from app.modules.relationships.scoring import (
    RelationshipWeight,
    calculate_overlap_days,
    combine_edge_scores,
    score_path,
    score_relationship_edge,
)


def test_calculate_overlap_days() -> None:
    assert (
        calculate_overlap_days(
            date(2020, 1, 1),
            date(2020, 12, 31),
            date(2020, 6, 1),
            date(2021, 1, 1),
        )
        == 213
    )


def test_score_relationship_edge_caps_at_max_score() -> None:
    score = score_relationship_edge(
        RelationshipWeight("secretary_to", base_weight=120, max_score=90),
        overlap_days=1500,
        source_trust_level="A",
        confidence=1.0,
    )
    assert score == 90


def test_combine_edge_scores() -> None:
    assert combine_edge_scores([50, 50]) == 75


def test_score_path_applies_hop_decay() -> None:
    assert score_path([80, 60]) == 39

