from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import torch
from torch.optim import AdamW
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from .data_validation import validate
from .dataset import TokenizedComments, load_split, seed_everything
from .metrics import calculate_metrics
from .settings import ID_TO_LABEL, LABEL_TO_ID, PROJECT_ROOT, load_config


def run_epoch(model, loader, device, optimizer=None) -> tuple[float, list[int], list[int]]:
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    y_true: list[int] = []
    y_pred: list[int] = []
    context = torch.enable_grad() if training else torch.inference_mode()
    with context:
        for batch in loader:
            batch = {key: value.to(device) for key, value in batch.items()}
            if training:
                optimizer.zero_grad(set_to_none=True)
            output = model(**batch)
            if training:
                output.loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
            total_loss += float(output.loss.item()) * batch["labels"].size(0)
            y_true.extend(batch["labels"].cpu().tolist())
            y_pred.extend(torch.argmax(output.logits, dim=-1).cpu().tolist())
    return total_loss / len(loader.dataset), y_true, y_pred


def train(config_path: Path | None = None, output_dir: Path | None = None) -> Path:
    config = load_config(config_path)
    validate()
    seed_everything(config.seed)
    output = output_dir or PROJECT_ROOT / "artifacts" / "model"
    output.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(
        config.base_model, revision=config.model_revision
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        config.base_model,
        revision=config.model_revision,
        num_labels=len(LABEL_TO_ID),
        label2id=LABEL_TO_ID,
        id2label=ID_TO_LABEL,
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    train_loader = DataLoader(
        TokenizedComments(load_split("train"), tokenizer, config.max_length),
        batch_size=config.batch_size,
        shuffle=True,
    )
    validation_loader = DataLoader(
        TokenizedComments(load_split("validation"), tokenizer, config.max_length),
        batch_size=config.batch_size,
    )
    optimizer = AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    best_f1 = -1.0
    best_state = None
    stale_epochs = 0
    history: list[dict] = []
    for epoch in range(1, config.epochs + 1):
        train_loss, train_true, train_pred = run_epoch(model, train_loader, device, optimizer)
        validation_loss, validation_true, validation_pred = run_epoch(
            model, validation_loader, device
        )
        train_metrics = calculate_metrics(train_true, train_pred)
        validation_metrics = calculate_metrics(validation_true, validation_pred)
        row = {
            "epoch": epoch,
            "train_loss": train_loss,
            "train_macro_f1": train_metrics["macro_f1"],
            "validation_loss": validation_loss,
            "validation_macro_f1": validation_metrics["macro_f1"],
        }
        history.append(row)
        print(json.dumps(row, ensure_ascii=False))
        if validation_metrics["macro_f1"] > best_f1:
            best_f1 = validation_metrics["macro_f1"]
            best_state = copy.deepcopy(model.state_dict())
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= config.early_stopping_patience:
                break
    if best_state is None:
        raise RuntimeError("training did not produce a model state")
    model.load_state_dict(best_state)
    model.save_pretrained(output, safe_serialization=True)
    tokenizer.save_pretrained(output)
    metadata = {
        "model_version": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "base_model": config.base_model,
        "base_model_revision": config.model_revision,
        "max_length": config.max_length,
        "labels": list(LABEL_TO_ID),
        "seed": config.seed,
        "device_used": str(device),
        "best_validation_macro_f1": best_f1,
        "history": history,
    }
    (output / "training_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"saved model: {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    train(args.config, args.output_dir)


if __name__ == "__main__":
    main()
