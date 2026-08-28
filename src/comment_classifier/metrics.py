from __future__ import annotations

from typing import Sequence

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from .settings import LABELS


def calculate_metrics(y_true: Sequence[int], y_pred: Sequence[int]) -> dict:
    report = classification_report(
        y_true,
        y_pred,
        labels=list(range(len(LABELS))),
        target_names=list(LABELS),
        output_dict=True,
        zero_division=0,
    )
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(report["macro avg"]["f1-score"]),
        "weighted_f1": float(report["weighted avg"]["f1-score"]),
        "complaint_recall": float(report["complaint"]["recall"]),
        "per_class": {label: report[label] for label in LABELS},
        "confusion_matrix": confusion_matrix(
            y_true, y_pred, labels=list(range(len(LABELS)))
        ).tolist(),
    }
