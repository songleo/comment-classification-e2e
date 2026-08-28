#!/bin/sh
set -eu

python -m ruff check .
python -m pytest -q
python -m comment_classifier.data_validation
python -m comment_classifier.train
python -m comment_classifier.evaluate
python -m comment_classifier.predict --text '客服一直不处理退款'
