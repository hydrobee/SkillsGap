import pytest
from app.services.gap import (adjust_answer, self_score, actual_level,
                              gap_value, categorise, competency_result)


def test_negative_answer_is_reversed():
    assert adjust_answer(5, True) == 1
    assert adjust_answer(2, True) == 4
    assert adjust_answer(3, True) == 3
    assert adjust_answer(4, False) == 4


def test_self_score_reverses_negative_questions():
    # Programming: "build a feature" = 4, "need help to debug" (negative) = 2 -> 4
    assert self_score([(4, False), (2, True)]) == 4.0


def test_weighting_70_30():
    # supervisor 2, self 2 -> 2.0 ; supervisor 4, self 2 -> 3.4
    assert actual_level(2, 2) == pytest.approx(2.0)
    assert actual_level(2, 4) == pytest.approx(3.4)


def test_supervisor_pending_uses_self_only():
    assert actual_level(3.5, None) == 3.5


def test_brief_example_security_moderate():
    # Required 4, actual 2.1 -> gap 1.9 -> Moderate
    assert gap_value(4, 2.1) == 1.9
    assert categorise(1.9) == "Moderate"


def test_brief_example_database_moderate():
    assert gap_value(3, 1.8) == 1.2
    assert categorise(1.2) == "Moderate"


def test_brief_example_programming_minor():
    assert gap_value(4, 3.6) == 0.4
    assert categorise(0.4) == "Minor"


def test_boundaries():
    assert categorise(2.0) == "Critical"
    assert categorise(1.0) == "Moderate"
    assert categorise(0.99) == "Minor"


def test_float_noise_does_not_break_boundary():
    # 0.7*3 + 0.3*4 = 3.3000000000000003 in floats; required 5 -> gap must be 1.7
    assert gap_value(5, actual_level(4, 3)) == 1.7
    # 0.7*1 + 0.3*1 = 1.0 ; required 3 -> exactly 2.0 -> Critical
    assert categorise(gap_value(3, actual_level(1, 1))) == "Critical"


def test_exceeding_requirement_is_zero_gap_minor():
    r = competency_result(3, [(5, False)], 5)
    assert r["gap"] == 0 and r["category"] == "Minor"


def test_full_competency_result():
    # Security required 4; self answers 2; supervisor 2 -> actual 2.0 -> gap 2.0 Critical
    r = competency_result(4, [(2, False)], 2)
    assert r["actual"] == 2.0 and r["gap"] == 2.0 and r["category"] == "Critical"


def test_invalid_answer_rejected():
    with pytest.raises(ValueError):
        adjust_answer(6, False)


def test_supervisor_rating_is_used_directly():
    # self 2.0 (one answer), supervisor rating 4 -> actual 0.7*4 + 0.3*2 = 3.4 -> gap 0.6
    r = competency_result(4, [(2, False)], 4)
    assert r["supervisor"] == 4 and r["actual"] == 3.4 and r["gap"] == 0.6
    assert r["category"] == "Minor" and r["supervisor_pending"] is False
