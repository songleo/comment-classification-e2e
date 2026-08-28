from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .dataset import load_split
from .metrics import calculate_metrics
from .runtime import Predictor
from .settings import LABEL_TO_ID, PROJECT_ROOT, load_config


def evaluate(model_dir: Path | None = None, reports_dir: Path | None = None) -> dict:
    predictor = Predictor(model_dir)
    comments = load_split("test")
    rows = []
    y_true: list[int] = []
    y_pred: list[int] = []
    for item in comments:
        result = predictor.predict(item.text)
        rows.append(
            {
                "text": item.text,
                "expected": item.label,
                "predicted": result["label"],
                "confidence": result["confidence"],
                "correct": item.label == result["label"],
            }
        )
        y_true.append(LABEL_TO_ID[item.label])
        y_pred.append(LABEL_TO_ID[result["label"]])
    metrics = calculate_metrics(y_true, y_pred)
    config = load_config()
    metrics["acceptance"] = {
        "complaint_recall_threshold": config.min_complaint_recall,
        "complaint_recall_pass": metrics["complaint_recall"] >= config.min_complaint_recall,
    }
    target = reports_dir or PROJECT_ROOT / "artifacts" / "reports"
    target.mkdir(parents=True, exist_ok=True)
    (target / "test_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (target / "test_predictions.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report_lines = [
        "# 测试集评估报告",
        "",
        f"- 准确率（Accuracy）：{metrics['accuracy']:.3f}",
        f"- 宏平均 F1（Macro F1）：{metrics['macro_f1']:.3f}",
        f"- 投诉召回率（Complaint recall）：{metrics['complaint_recall']:.3f}",
        f"- 投诉召回率门槛：{'PASS' if metrics['acceptance']['complaint_recall_pass'] else 'FAIL'}",
        "",
        "## 混淆矩阵",
        "",
        "行表示正确标签，列表示模型预测。固定顺序为：positive、negative、neutral、complaint。",
        "",
        "```text",
        *[str(row) for row in metrics["confusion_matrix"]],
        "```",
    ]
    (target / "test_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--reports-dir", type=Path)
    args = parser.parse_args()
    evaluate(args.model_dir, args.reports_dir)


if __name__ == "__main__":
    main()
