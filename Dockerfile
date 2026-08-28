ARG PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.13.15-slim
FROM ${PYTHON_IMAGE}

ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG TORCH_FIND_LINKS=https://mirrors.aliyun.com/pytorch-wheels/cpu/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_DIR=/app/artifacts/model \
    HF_HOME=/cache/huggingface

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" \
        --find-links "${TORCH_FIND_LINKS}" torch==2.8.0+cpu \
    && python -m pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" ".[dev]"

COPY configs ./configs
COPY data ./data
COPY tests ./tests
COPY AGENTS.md CONTRIBUTING.md SECURITY.md ./
COPY docs ./docs
COPY scripts/run-e2e.sh ./scripts/run-e2e.sh
RUN python -m pip install --no-deps --editable . \
    && chmod 0755 ./scripts/run-e2e.sh

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=12 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "comment_classifier.api:app", "--host", "0.0.0.0", "--port", "8000"]
