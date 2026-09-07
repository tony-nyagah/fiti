import os

from fastapi import FastAPI
from pydantic import BaseModel

APP_NAME = os.getenv("APP_NAME", "fiti")
APP_ENV = os.getenv("APP_ENV", "dev")
API_KEY_SET = bool(os.getenv("API_KEY"))

app = FastAPI(title=APP_NAME, version="0.1.0")


class Exercise(BaseModel):
    name: str
    sets: int = 3
    reps: int = 10
    weight_kg: float | None = None


class Workout(BaseModel):
    name: str
    exercises: list[Exercise]


# In-memory store — fine for the scaffold; swap for SQLite/Postgres in a later week.
workouts: dict[int, Workout] = {}
_counter = 0


@app.get("/")
def root():
    return {"service": APP_NAME, "env": APP_ENV, "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME}


@app.get("/config")
def config():
    # Confirms ConfigMap + Secret are wired in WITHOUT leaking the secret value.
    return {"app_name": APP_NAME, "env": APP_ENV, "api_key_loaded": API_KEY_SET}


@app.get("/workouts")
def list_workouts():
    return list(workouts.values())


@app.post("/workouts")
def create_workout(w: Workout):
    global _counter
    _counter += 1
    workouts[_counter] = w
    return {"id": _counter, **w.model_dump()}
