# SkillsGap – staff competency gap analysis

HR defines the competency level each job scope needs. Staff answer a short survey, their supervisor rates them,
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
uvicorn app.main:app --reload      # API on http://localhost:8000  (docs at /docs)
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
3. Supervisor score = average of the supervisor's adjusted answers to the same questions for that competency.
4. Actual = 0.7 × supervisor score + 0.3 × self score.
5. Gap = required − actual, rounded to 2 decimals (so float noise like 1.9999999 cannot change a category).
6. Critical: gap ≥ 2 · Moderate: 1 ≤ gap < 2 · Minor: gap < 1.

## Assumptions
- A gap below zero (staff exceed the requirement) is shown as 0 and counted as Minor.
- The supervisor answers the same survey questions as the staff member (1–5), from their own point of view.
  The brief says "rates each competency", so each competency rating is the average of its questions.
  Negatively worded questions are reversed for the supervisor too. If only some of a competency's questions are
  answered, the average of those is used.
- If the supervisor has not answered any question of a competency yet, Actual uses the self score only, and the report marks the
  supervisor rating as pending. The department report counts how many staff are still provisional.
- Supervisor answers are locked when the cycle closes, the same as staff answers (the brief only says staff).
- Required levels belong to a job scope and competency, not to a question. The brief repeats the level on each
  question row, so it is stored once per job scope and competency.
- The department report includes everyone in the department who has a job scope (supervisors too).
  "Assessed" means they answered at least one question.
- A competency with no survey answers is left out of that person's report.
- Required levels are not versioned per year. HR edits the current level, and reports for older cycles use it.
- Questions that staff or supervisors have already answered cannot be deleted or flipped between positive and negative.

## Access rules
Staff see only their own results. Supervisors see themselves and their direct reports, and only their own
department report. HR sees everything. These are checked on the server for every request, not just hidden in the UI.

## Not done
Deleting job scopes or competencies, password change, and per-year versions of required levels.
