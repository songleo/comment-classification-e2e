from fastapi.testclient import TestClient

from comment_classifier.api import app, get_predictor


class FakePredictor:
    metadata = {"model_version": "test-model"}

    def predict(self, text: str) -> dict:
        return {
            "label": "complaint",
            "confidence": 0.9,
            "scores": {"positive": 0.02, "negative": 0.04, "neutral": 0.04, "complaint": 0.9},
            "model_version": "test-model",
        }


def test_health_and_predict_contract() -> None:
    app.dependency_overrides[get_predictor] = lambda: FakePredictor()
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok", "model_version": "test-model"}
    response = client.post("/predict", json={"text": "客服一直不处理退款"})
    assert response.status_code == 200
    assert response.json()["label"] == "complaint"
    app.dependency_overrides.clear()
