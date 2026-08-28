FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_DIR=/app/artifacts/model

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY artifacts/model ./artifacts/model

EXPOSE 8000
USER 65532:65532
CMD ["uvicorn", "comment_classifier.api:app", "--host", "0.0.0.0", "--port", "8000"]
