from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runtime import Predictor


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--model-dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(Predictor(args.model_dir).predict(args.text), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
