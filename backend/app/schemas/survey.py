from pydantic import BaseModel, Field


class AnswerIn(BaseModel):
    question_id: int
    answer: int = Field(ge=1, le=5)


class SurveySubmit(BaseModel):
    cycle_id: int | None = None
    answers: list[AnswerIn]


class RatingIn(BaseModel):
    competency_id: int
    rating: int = Field(ge=1, le=5)


class RatingSubmit(BaseModel):
    cycle_id: int | None = None
    ratings: list[RatingIn]
