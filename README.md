# SkillsGap – staff competency gap analysis

HR defines the competency level each job scope needs. Staff answer a short survey, their supervisor rates each competency directly,
and the system shows the gap so HR can plan training.

**Stack:** Angular 21 · FastAPI · PostgreSQL (SQLAlchemy). Tests: pytest.

## Run it

**1. Database** (once)
```sql
CREATE USER skillsgap_user WITH PASSWORD 'skillsgap123';
CREATE DATABASE skillsgap OWNER skillsgap_user;
```

**2. Backend**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
Create `backend/.env`:
```
DATABASE_URL=postgresql+psycopg2://skillsgap_user:skillsgap123@localhost:5432/skillsgap
SECRET_KEY=<a long random string>
```
```powershell
python -m app.seed                 # creates the 15 seed questions and demo users
python -m app.seed --demo          # optional: also adds sample answers and supervisor ratings
uvicorn app.main:app --reload      # API on http://localhost:8000  (docs at /docs)
```

**If you already have data from an earlier version** (required levels were not per year), stop uvicorn and run this once
before starting it again. It copies your existing levels into every existing year and is safe to run twice:
```powershell
python -m scripts.migrate_year_levels
```

**3. Frontend**
```powershell
cd frontend
npm install
npx ng serve                       # http://localhost:4200
```

**Demo accounts** (password `password123`): `hr@demo.com`, `aiman@demo.com` (supervisor of Bella and Chris),
`bella@demo.com` (staff). Others: `dayang@demo.com`, `edwin@demo.com`, `farah@demo.com`, `gina@demo.com`.

## Tests
```powershell
cd backend
pytest -v
```
`tests/test_gap.py` covers the gap calculation. `tests/test_reports.py` covers report roll-ups.
`tests/test_api.py` and `tests/test_setup.py` run survey → rating → report and the access rules against a
temporary SQLite file, so they never touch the Postgres data.

## How the gap is calculated
1. Negatively worded answers are reversed first: `6 − answer`.
2. Self score = average of the adjusted answers for the competency.
3. Supervisor score = the supervisor's direct 1–5 rating of that competency (not derived from survey questions).
4. Actual = 0.7 × supervisor score + 0.3 × self score.
5. Gap = required − actual, rounded to 2 decimals (so float noise like 1.9999999 cannot change a category).
6. Critical: gap ≥ 2 · Moderate: 1 ≤ gap < 2 · Minor: gap < 1.

## Assumptions
- A gap below zero (staff exceed the requirement) is shown as 0 and counted as Minor.
- Supervisors rate each competency of the staff member's job scope directly (1–5). Staff still answer the
  individual survey questions. Ratings can be saved partially and changed until the cycle closes.
- If the supervisor has not rated a competency yet, Actual uses the self score only, and the report marks the
  supervisor rating as pending. The department report counts how many staff are still provisional.
- Supervisor ratings are locked when the cycle closes, the same as staff answers (the brief only says staff).
- Required levels belong to a job scope, a competency and a year (assessment cycle), not to a question. The brief repeats
  the level on each question row, so it is stored once per job scope, competency and year.
- A new year can copy the required levels of an earlier year (HR chooses which, or starts empty). Editing one year never
  changes another. Survey questions are the same every year.
- The department report includes everyone in the department who has a job scope (supervisors too).
  "Assessed" means they answered at least one question.
- A competency with no survey answers is left out of that person's report.
- Deleting a year cycle removes that year's required levels, survey answers and supervisor ratings (HR must confirm when
  answers or ratings exist). Job scopes, competencies, questions and other years are kept. The last remaining year cannot be deleted.
- A job scope can be deleted only when no staff are assigned to it and none of its questions have answers. Deleting it
  also deletes its questions and its required levels in every year. A competency can be deleted only when no job scope
  uses it in any year and nobody has been rated on it. Otherwise HR sees a message saying what to remove first.
- Questions that staff have already answered cannot be deleted or flipped between positive and negative.

- `app/services/wording.py` and `tests/test_wording.py` are no longer used by the rating flow.
- The old `supervisor_answers` table is no longer used and can be dropped.

## Access rules
Staff see only their own results. Supervisors see themselves and their direct reports, and only their own
department report. HR sees everything. These are checked on the server for every request, not just hidden in the UI.

## Not done
Password change.
