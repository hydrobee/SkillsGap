"""Pure gap calculation. No database, no FastAPI, so it is easy to test."""

SUPERVISOR_WEIGHT = 0.7
SELF_WEIGHT = 0.3


def adjust_answer(answer: int, is_negative: bool) -> int:
    """Reverse a negatively worded answer: 1<->5, 2<->4, 3 stays 3."""
    if not 1 <= answer <= 5:
        raise ValueError("answer must be between 1 and 5")
    return 6 - answer if is_negative else answer


def self_score(answers: list[tuple[int, bool]]) -> float:
    """answers = [(raw_answer, is_negative), ...] for ONE competency."""
    if not answers:
        raise ValueError("no answers for this competency")
    adjusted = [adjust_answer(a, neg) for a, neg in answers]
    return sum(adjusted) / len(adjusted)


def actual_level(self_avg: float, supervisor: float | None) -> float:
    """70% supervisor + 30% self. If the supervisor has not rated yet,
    fall back to the self score only (assumption: report shows 'pending')."""
    if supervisor is None:
        return self_avg
    if not 1 <= supervisor <= 5:
        raise ValueError("supervisor rating must be between 1 and 5")
    return SUPERVISOR_WEIGHT * supervisor + SELF_WEIGHT * self_avg


def gap_value(required: int, actual: float) -> float:
    """Required - actual. Rounded to 2 dp so 1.9999999 does not slip
    under a boundary. Clamped at 0 (exceeding the requirement is no gap)."""
    return max(0.0, round(required - actual, 2))


def categorise(gap: float) -> str:
    if gap >= 2:
        return "Critical"
    if gap >= 1:
        return "Moderate"
    return "Minor"


def competency_result(required: int, answers: list[tuple[int, bool]],
                      supervisor: float | None) -> dict:
    s = self_score(answers)
    a = actual_level(s, supervisor)
    g = gap_value(required, a)
    return {
        "required": required,
        "self": round(s, 2),
        "supervisor": None if supervisor is None else round(supervisor, 2),
        "actual": round(a, 2),
        "gap": g,
        "category": categorise(g),
        "supervisor_pending": supervisor is None,
    }
