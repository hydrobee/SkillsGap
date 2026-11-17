from pydantic import BaseModel, Field


class NameIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class RequiredLevelIn(BaseModel):
    required_level: int = Field(ge=1, le=5)


class QuestionCreate(BaseModel):
    job_scope_id: int
    competency_id: int
    text: str = Field(min_length=3, max_length=500)
    is_negative: bool = False


class QuestionUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=3, max_length=500)
    is_negative: bool | None = None


class CycleCreate(BaseModel):
    year: int = Field(ge=2000, le=2100)
