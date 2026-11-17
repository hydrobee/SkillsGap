from app.services.reports import (department_rollup, sort_rows, summary_line,
                                  top_priorities)


def row(name, required, actual, gap, category):
    return {"competency": name, "required": required, "actual": actual,
            "gap": gap, "category": category}


# The example in section 4.1 of the brief
BRIEF_ROWS = [row("Programming", 4, 3.6, 0.4, "Minor"),
              row("Security", 4, 2.1, 1.9, "Moderate"),
              row("Database", 3, 1.8, 1.2, "Moderate")]


def test_rows_sorted_by_largest_gap_first():
    names = [r["competency"] for r in sort_rows(BRIEF_ROWS)]
    assert names == ["Security", "Database", "Programming"]


def test_summary_line_matches_brief_example():
    assert summary_line(sort_rows(BRIEF_ROWS)) == (
        "0 Critical · 2 Moderate · 1 Minor. Suggested focus: Security.")


def test_summary_line_no_gap_has_no_focus():
    rows = [row("Programming", 3, 4.0, 0.0, "Minor")]
    assert summary_line(rows).endswith("Suggested focus: none.")


def test_department_rollup_averages_and_counts():
    a = [row("Security", 4, 1.5, 2.5, "Critical"), row("Database", 3, 2.0, 1.0, "Moderate")]
    b = [row("Security", 4, 3.5, 0.5, "Minor"), row("Database", 3, 3.0, 0.0, "Minor")]
    c = [row("Security", 4, 2.0, 2.0, "Critical"), row("Database", 3, 2.5, 0.5, "Minor")]
    roll = {r["competency"]: r for r in department_rollup([a, b, c])}
    sec = roll["Security"]
    assert sec["avg_actual"] == 2.33 and sec["avg_gap"] == 1.67
    assert (sec["critical"], sec["moderate"], sec["minor"]) == (2, 0, 1)
    db_ = roll["Database"]
    assert db_["avg_gap"] == 0.5 and (db_["critical"], db_["moderate"], db_["minor"]) == (0, 1, 2)


def test_department_rollup_lists_staff_by_largest_gap():
    a = [{**row("Security", 4, 1.5, 2.5, "Critical"), "staff_id": 1, "staff_name": "Ann"}]
    b = [{**row("Security", 4, 3.5, 0.5, "Minor"), "staff_id": 2, "staff_name": "Ben"}]
    c = [{**row("Security", 4, 2.6, 1.4, "Moderate"), "staff_id": 3, "staff_name": "Cai"}]
    sec = department_rollup([b, a, c])[0]
    assert [(s["name"], s["category"]) for s in sec["staff"]] == [
        ("Ann", "Critical"), ("Cai", "Moderate"), ("Ben", "Minor")]


def test_top_priorities_ranked_by_avg_gap_and_capped_at_three():
    roll = department_rollup([[row("A", 4, 3, 1.0, "Moderate"), row("B", 4, 2, 2.0, "Critical"),
                               row("C", 4, 3.5, 0.5, "Minor"), row("D", 4, 3.8, 0.2, "Minor"),
                               row("E", 4, 4, 0.0, "Minor")]])
    top = top_priorities(roll)
    assert [t["competency"] for t in top] == ["B", "A", "C"]
    assert [t["rank"] for t in top] == [1, 2, 3]


def test_priorities_skip_competencies_with_no_gap():
    roll = department_rollup([[row("A", 3, 4.0, 0.0, "Minor")]])
    assert top_priorities(roll) == []
