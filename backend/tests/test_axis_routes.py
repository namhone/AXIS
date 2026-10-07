import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.deps import get_current_user
from app.api.routes.axis import AxisEvaluatePayload, _benchmark
from app.core.database import get_db
from app.main import app
from app.models.axis import CareerBenchmark
from app.models.user import User
from app.services.career_matching import INDUSTRIES


class Query:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    def order_by(self, *_):
        return self


class CatalogSession:
    def __init__(self):
        self.rows = []
        for industry in INDUSTRIES:
            data = _benchmark(industry)
            self.rows.append(CareerBenchmark(
                code=data["code"], name=data["name"],
                requirements_json=data["requirements"],
                ahp_matrix_json=data["ahp_matrix"], roc_order_json=data["roc_order"],
            ))

    def query(self, entity):
        if entity is CareerBenchmark.code:
            return Query([SimpleNamespace(code=row.code) for row in self.rows])
        if entity is CareerBenchmark:
            return Query(self.rows)
        raise AssertionError(f"Unexpected database query: {entity}")

    def add(self, _):
        pass

    def flush(self):
        pass

    def commit(self):
        pass


def test_axis_evaluation_uses_server_catalog_and_explains_weighted_score():
    user = User(
        id=uuid.uuid4(), email="axis@example.com", full_name="AXIS",
        password_hash="unused", is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = CatalogSession
    try:
        response = TestClient(app, raise_server_exceptions=True).post(
            "/api/v1/axis/evaluate",
            json={
                "scores": {"S1": 8, "S2": 7, "S3": 6, "S4": 9, "S5": 5},
                "benchmarks": [{"code": "EVIL", "name": "Client supplied catalog"}],
            },
        )
        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 24
        assert all(result["code"] != "EVIL" for result in results)
        assert [result["rank"] for result in results] == list(range(1, 25))
        for result in results:
            contributions = result["explanation"]
            assert set(contributions) == {"S1", "S2", "S3", "S4", "S5"}
            assert sum(item["contribution"] for item in contributions.values()) == pytest.approx(
                result["match_score"], abs=0.03
            )
            assert sum(result["weights"].values()) == pytest.approx(1.0)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "scores",
    [
        {"S1": 1, "S2": 2, "S3": 3, "S4": 4},
        {"S1": 1, "S2": 2, "S3": 3, "S4": 4, "S5": 11},
        {"S1": 1, "S2": 2, "S3": 3, "S4": 4, "S6": 5},
    ],
)
def test_axis_payload_rejects_incomplete_or_out_of_range_scores(scores):
    with pytest.raises(ValidationError):
        AxisEvaluatePayload(scores=scores)
