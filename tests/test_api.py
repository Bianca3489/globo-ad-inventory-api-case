"""
tests/test_api.py
-----------------
Testes de integração dos endpoints da REST API usando TestClient do FastAPI.
"""

import sys
from pathlib import Path
import pandas as pd
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.preprocessing as preprocessing_module
from app.main import app

client = TestClient(app)


# ─── Fixture: substituir dataframe real por um controlado ─────────────────────

MOCK_DATA = pd.DataFrame(
    [
        {
            "signal": "SP1",
            "program_code": "HUCK",
            "weekday": 5,
            "date": pd.Timestamp("2020-08-01"),
            "available_time": 300,
            "predicted_audience": 1500000.0,
        },
        {
            "signal": "BH",
            "program_code": "HUCK",
            "weekday": 5,
            "date": pd.Timestamp("2020-08-01"),
            "available_time": 200,
            "predicted_audience": 500000.0,
        },
        {
            "signal": "SP1",
            "program_code": "JN",
            "weekday": 0,
            "date": pd.Timestamp("2020-08-03"),
            "available_time": 600,
            "predicted_audience": 8000000.0,
        },
    ]
)


@pytest.fixture(autouse=True)
def patch_master_df(monkeypatch):
    """Injeta o dataframe mock em todos os testes."""
    monkeypatch.setattr(preprocessing_module, "_master_df", MOCK_DATA)


# ─── /health ──────────────────────────────────────────────────────────────────

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["total_records"] == 3


# ─── /program ─────────────────────────────────────────────────────────────────

def test_program_found():
    r = client.get("/program?program_code=HUCK&exhibition_date=2020-08-01")
    assert r.status_code == 200
    body = r.json()
    assert body["program_code"] == "HUCK"
    assert len(body["records"]) == 2  # SP1 e BH


def test_program_case_insensitive():
    r = client.get("/program?program_code=huck&exhibition_date=2020-08-01")
    assert r.status_code == 200


def test_program_not_found():
    r = client.get("/program?program_code=XPTO&exhibition_date=2020-08-01")
    assert r.status_code == 404


def test_program_wrong_date():
    r = client.get("/program?program_code=HUCK&exhibition_date=2020-01-01")
    assert r.status_code == 404


def test_program_response_fields():
    r = client.get("/program?program_code=HUCK&exhibition_date=2020-08-01")
    record = r.json()["records"][0]
    assert "available_time" in record
    assert "predicted_audience" in record
    assert "signal" in record
    assert "exhibition_date" in record


# ─── /period ──────────────────────────────────────────────────────────────────

def test_period_found():
    r = client.get("/period?start_date=2020-08-01&end_date=2020-08-03")
    assert r.status_code == 200
    body = r.json()
    assert len(body["records"]) == 3


def test_period_single_day():
    r = client.get("/period?start_date=2020-08-01&end_date=2020-08-01")
    assert r.status_code == 200
    assert len(r.json()["records"]) == 2


def test_period_not_found():
    r = client.get("/period?start_date=2019-01-01&end_date=2019-12-31")
    assert r.status_code == 404


def test_period_invalid_range():
    r = client.get("/period?start_date=2020-08-10&end_date=2020-08-01")
    assert r.status_code == 422
