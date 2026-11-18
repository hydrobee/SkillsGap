"""One-off schema update: required levels become per year (per assessment cycle).

Run from the backend folder, after stopping uvicorn:

    python -m scripts.migrate_year_levels

What it does, in one transaction (nothing changes if any step fails):
  1. Renames the old job_scope_competencies table.
  2. Creates the new table, which has a cycle_id column and a unique key of
     (job_scope_id, competency_id, cycle_id).
  3. Copies every existing required level into EVERY existing year, so reports for older years
     keep showing exactly what they showed before. Edit the years separately afterwards.
  4. Checks the row count, then drops the old table.
If there is no assessment cycle yet, one is created for the current year first.
Safe to run twice: it does nothing when the cycle_id column already exists.
Job scopes, competencies, questions, answers and ratings are not touched."""
from datetime import date

from sqlalchemy import inspect, text

from app.core.database import engine
from app.models import AssessmentCycle, Base, JobScopeCompetency

OLD = "job_scope_competencies_old"


def migrate() -> str:
    table = JobScopeCompetency.__tablename__
    insp = inspect(engine)
    if not insp.has_table(table):
        Base.metadata.create_all(bind=engine)
        return "No old table found; created the current schema."
    if "cycle_id" in {c["name"] for c in insp.get_columns(table)}:
        return "Already migrated. Nothing to do."

    with engine.begin() as conn:
        cycles = conn.execute(text("SELECT COUNT(*) FROM assessment_cycles")).scalar()
        if not cycles:
            conn.execute(AssessmentCycle.__table__.insert().values(year=date.today().year, is_open=True))
            cycles = 1
        old_rows = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()

        conn.execute(text(f"ALTER TABLE {table} RENAME TO {OLD}"))
        JobScopeCompetency.__table__.create(conn)
        conn.execute(text(
            f"INSERT INTO {table} (job_scope_id, competency_id, cycle_id, required_level) "
            f"SELECT o.job_scope_id, o.competency_id, c.id, o.required_level "
            f"FROM {OLD} o CROSS JOIN assessment_cycles c"))
        new_rows = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        if new_rows != old_rows * cycles:
            raise RuntimeError(f"Row count mismatch ({new_rows} != {old_rows} x {cycles}); rolled back.")
        conn.execute(text(f"DROP TABLE {OLD}"))
    return f"Migrated {old_rows} required level(s) into {cycles} year(s) ({new_rows} rows)."


if __name__ == "__main__":
    print(migrate())
