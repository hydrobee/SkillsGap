from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
import app.models  # noqa: F401
from app.routers import auth, rating, reports, setup, survey

Base.metadata.create_all(bind=engine)  # fine for a 3-day task; use Alembic later

app = FastAPI(title="SkillsGap API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(setup.router)
app.include_router(survey.router)
app.include_router(rating.router)
app.include_router(reports.router)


@app.get("/health")
def health():
    return {"status": "ok"}
