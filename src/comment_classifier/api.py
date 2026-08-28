from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from .runtime import Predictor
from .settings import PROJECT_ROOT


class PredictRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class PredictResponse(BaseModel):
    label: str
    confidence: float
    scores: dict[str, float]
    model_version: str


@lru_cache(maxsize=1)
def get_predictor() -> Predictor:
    model_dir = Path(os.getenv("MODEL_DIR", PROJECT_ROOT / "artifacts" / "model"))
    return Predictor(model_dir)


app = FastAPI(title="Chinese Comment Classifier", version="0.1.0")


@app.get("/health")
def health(predictor: Predictor = Depends(get_predictor)) -> dict:
    return {"status": "ok", "model_version": predictor.metadata["model_version"]}


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest, predictor: Predictor = Depends(get_predictor)) -> dict:
    try:
        return predictor.predict(request.text)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def run() -> None:
    uvicorn.run("comment_classifier.api:app", host="0.0.0.0", port=8000)
