from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path

import torch
from torch.utils.data import Dataset

from .settings import LABEL_TO_ID, PROJECT_ROOT


@dataclass(frozen=True)
class Comment:
    text: str
    label: str


def load_split(split: str, data_dir: Path | None = None) -> list[Comment]:
    path = (data_dir or PROJECT_ROOT / "data") / f"{split}.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [Comment(text=row["text"].strip(), label=row["label"].strip()) for row in rows]


def seed_everything(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class TokenizedComments(Dataset):
    def __init__(self, comments: list[Comment], tokenizer, max_length: int) -> None:
        self.comments = comments
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.comments)

    def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
        item = self.comments[index]
        encoded = self.tokenizer(
            item.text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        return {
            "input_ids": encoded["input_ids"].squeeze(0),
            "attention_mask": encoded["attention_mask"].squeeze(0),
            "labels": torch.tensor(LABEL_TO_ID[item.label], dtype=torch.long),
        }
