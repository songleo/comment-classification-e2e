from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LABELS = ("positive", "negative", "neutral", "complaint")
LABEL_TO_ID = {label: index for index, label in enumerate(LABELS)}
ID_TO_LABEL = {index: label for label, index in LABEL_TO_ID.items()}


@dataclass(frozen=True)
class TrainConfig:
    base_model: str
    model_revision: str
    max_length: int
    batch_size: int
    epochs: int
    learning_rate: float
    weight_decay: float
    seed: int
    early_stopping_patience: int
    min_complaint_recall: float


def load_config(path: Path | None = None) -> TrainConfig:
    config_path = path or PROJECT_ROOT / "configs" / "train.json"
    with config_path.open(encoding="utf-8") as handle:
        return TrainConfig(**json.load(handle))
