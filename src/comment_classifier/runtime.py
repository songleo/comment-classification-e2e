from __future__ import annotations

import json
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from .settings import ID_TO_LABEL, PROJECT_ROOT


class Predictor:
    def __init__(self, model_dir: Path | None = None) -> None:
        self.model_dir = model_dir or PROJECT_ROOT / "artifacts" / "model"
        if not (self.model_dir / "config.json").exists():
            raise FileNotFoundError(
                f"trained model not found at {self.model_dir}; run comment-train first"
            )
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir, local_files_only=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            self.model_dir, local_files_only=True
        ).to(self.device)
        self.model.eval()
        metadata_path = self.model_dir / "training_metadata.json"
        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    def predict(self, text: str) -> dict:
        normalized = text.strip()
        if not normalized:
            raise ValueError("text must not be empty")
        encoded = self.tokenizer(
            normalized,
            truncation=True,
            max_length=int(self.metadata["max_length"]),
            return_tensors="pt",
        ).to(self.device)
        with torch.inference_mode():
            probabilities = torch.softmax(self.model(**encoded).logits, dim=-1)[0]
        best_id = int(torch.argmax(probabilities).item())
        scores = {
            ID_TO_LABEL[index]: round(float(score), 6)
            for index, score in enumerate(probabilities.cpu().tolist())
        }
        return {
            "label": ID_TO_LABEL[best_id],
            "confidence": scores[ID_TO_LABEL[best_id]],
            "scores": scores,
            "model_version": self.metadata["model_version"],
        }
