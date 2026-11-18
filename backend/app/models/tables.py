from sqlalchemy import (Boolean, CheckConstraint, ForeignKey, Integer, String,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class JobScope(Base):
    __tablename__ = "job_scopes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class Competency(Base):
    __tablename__ = "competencies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class JobScopeCompetency(Base):
    """Required level of a competency for a job scope, in one assessment cycle (year)."""
    __tablename__ = "job_scope_competencies"
    __table_args__ = (
        UniqueConstraint("job_scope_id", "competency_id", "cycle_id"),
        CheckConstraint("required_level BETWEEN 1 AND 5"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    job_scope_id: Mapped[int] = mapped_column(ForeignKey("job_scopes.id"))
    competency_id: Mapped[int] = mapped_column(ForeignKey("competencies.id"))
    cycle_id: Mapped[int] = mapped_column(ForeignKey("assessment_cycles.id"))
    required_level: Mapped[int] = mapped_column(Integer)
    competency: Mapped[Competency] = relationship()


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_scope_id: Mapped[int] = mapped_column(ForeignKey("job_scopes.id"))
    competency_id: Mapped[int] = mapped_column(ForeignKey("competencies.id"))
    text: Mapped[str] = mapped_column(String(500))
    is_negative: Mapped[bool] = mapped_column(Boolean, default=False)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))  # staff | supervisor | hr
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    job_scope_id: Mapped[int | None] = mapped_column(ForeignKey("job_scopes.id"))
    supervisor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class AssessmentCycle(Base):
    __tablename__ = "assessment_cycles"
    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer, unique=True)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)


class SurveyAnswer(Base):
    __tablename__ = "survey_answers"
    __table_args__ = (
        UniqueConstraint("user_id", "cycle_id", "question_id"),
        CheckConstraint("answer BETWEEN 1 AND 5"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    cycle_id: Mapped[int] = mapped_column(ForeignKey("assessment_cycles.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    answer: Mapped[int] = mapped_column(Integer)  # raw answer, reverse in gap.py


class SupervisorRating(Base):
    """The supervisor's rating (1-5) of one competency of one staff member in one cycle."""
    __tablename__ = "supervisor_ratings"
    __table_args__ = (
        UniqueConstraint("staff_id", "cycle_id", "competency_id"),
        CheckConstraint("rating BETWEEN 1 AND 5"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    supervisor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    staff_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    cycle_id: Mapped[int] = mapped_column(ForeignKey("assessment_cycles.id"))
    competency_id: Mapped[int] = mapped_column(ForeignKey("competencies.id"))
    rating: Mapped[int] = mapped_column(Integer)
