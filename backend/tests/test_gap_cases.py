"""Gap-calculation test cases for the System Developer job scope (required levels: Programming 4, Database 3, Security 4).
Each case is: required level, staff answers [(answer, is_negative)], supervisor rating (None = not rated yet)."""
import pytest

from app.services.gap import competency_result

CASES = [
    # id,        required, staff answers,                  supervisor, self, actual, gap,  category
    ("TC-GAP-01", 4, [(4, False), (2, True)],  4,    4.0, 4.0,  0.0,  "Minor"),
    ("TC-GAP-02", 3, [(3, False), (3, False)], 5,    3.0, 4.4,  0.0,  "Minor"),
    ("TC-GAP-03", 4, [(3, False)],             3,    3.0, 3.0,  1.0,  "Moderate"),
    ("TC-GAP-04", 4, [(3, False), (4, True)],  2,    2.5, 2.15, 1.85, "Moderate"),
    ("TC-GAP-05", 3, [(1, False), (1, False)], 1,    1.0, 1.0,  2.0,  "Critical"),
    ("TC-GAP-06", 4, [(3, False)],             None, 3.0, 3.0,  1.0,  "Moderate"),
    ("TC-GAP-07", 4, [(3, False)],             2,    3.0, 2.3,  1.7,  "Moderate"),
]


@pytest.mark.parametrize("case_id,required,answers,supervisor,self_,actual,gap,category",
                         CASES, ids=[c[0] for c in CASES])
def test_gap_case(case_id, required, answers, supervisor, self_, actual, gap, category):
    r = competency_result(required, answers, supervisor)
    assert (r["self"], r["actual"], r["gap"], r["category"]) == (self_, actual, gap, category)
    assert r["supervisor_pending"] is (supervisor is None)
