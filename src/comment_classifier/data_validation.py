from __future__ import annotations

from collections import Counter

from .dataset import load_split
from .settings import LABELS


def validate() -> dict[str, dict[str, int]]:
    seen: dict[str, str] = {}
    summary: dict[str, dict[str, int]] = {}
    errors: list[str] = []
    for split in ("train", "validation", "test"):
        comments = load_split(split)
        counts = Counter(item.label for item in comments)
        summary[split] = dict(sorted(counts.items()))
        if not comments:
            errors.append(f"{split}: empty split")
        unknown = sorted(set(counts) - set(LABELS))
        if unknown:
            errors.append(f"{split}: unknown labels {unknown}")
        missing = sorted(set(LABELS) - set(counts))
        if missing:
            errors.append(f"{split}: missing labels {missing}")
        for item in comments:
            if not item.text:
                errors.append(f"{split}: empty text")
                continue
            normalized = "".join(item.text.split()).lower()
            if normalized in seen:
                errors.append(f"duplicate across {seen[normalized]} and {split}: {item.text}")
            else:
                seen[normalized] = split
    if errors:
        raise ValueError("Dataset validation failed:\n- " + "\n- ".join(errors))
    return summary


def main() -> None:
    summary = validate()
    print("dataset validation: PASS")
    for split, counts in summary.items():
        print(f"{split}: {counts}")


if __name__ == "__main__":
    main()
