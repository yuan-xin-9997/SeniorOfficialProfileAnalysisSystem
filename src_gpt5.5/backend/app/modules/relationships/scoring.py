from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import reduce
from operator import mul


SOURCE_FACTORS = {
    "A": 1.0,
    "B": 0.85,
    "C": 0.6,
    "D": 0.3,
}


@dataclass(frozen=True)
class RelationshipWeight:
    relationship_type: str
    base_weight: float
    max_score: float
    time_decay_enabled: bool = True


def calculate_overlap_days(
    start_a: date | None,
    end_a: date | None,
    start_b: date | None,
    end_b: date | None,
) -> int:
    if not start_a or not end_a or not start_b or not end_b:
        return 0
    start = max(start_a, start_b)
    end = min(end_a, end_b)
    return max(0, (end - start).days)


def duration_factor(overlap_days: int) -> float:
    if overlap_days < 90:
        return 0.2
    if overlap_days < 365:
        return 0.5
    if overlap_days < 1095:
        return 0.8
    return 1.0


def score_relationship_edge(
    weight: RelationshipWeight,
    overlap_days: int,
    source_trust_level: str,
    confidence: float,
) -> float:
    source_factor = SOURCE_FACTORS.get(source_trust_level.upper(), SOURCE_FACTORS["D"])
    confidence_factor = max(0.0, min(confidence, 1.0))
    time_factor = duration_factor(overlap_days) if weight.time_decay_enabled else 1.0
    score = weight.base_weight * time_factor * source_factor * confidence_factor
    return round(min(weight.max_score, score), 3)


def combine_edge_scores(scores: list[float]) -> float:
    if not scores:
        return 0.0
    normalized = [max(0.0, min(score / 100.0, 1.0)) for score in scores]
    combined = 1.0 - reduce(mul, (1.0 - value for value in normalized), 1.0)
    return round(combined * 100.0, 3)


def score_path(edge_scores: list[float]) -> float:
    if not edge_scores:
        return 0.0
    hop_count = len(edge_scores)
    decay = {1: 1.0, 2: 0.65, 3: 0.4}.get(hop_count, 0.25)
    return round(min(edge_scores) * decay, 3)

