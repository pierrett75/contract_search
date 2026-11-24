from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from contract_search import api
from contract_search.db import get_db, ingest_folder

SAMPLES = Path(__file__).parent / "sample_contracts"


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Dočasná DB se vzorovými smlouvami. Nepoužíváme ":memory:", protože
    # endpoint si otevírá vlastní spojení a každé ":memory:" je jiná prázdná DB.
    db_file = tmp_path / "test.db"
    conn = get_db(str(db_file))
    ingest_folder(str(SAMPLES), conn)
    conn.close()

    monkeypatch.setenv("CONTRACTS_DB", str(db_file))
    return TestClient(api.app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_search_finds_client(client):
    r = client.get("/search", params={"q": "Nováka"})
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "Nováka"
    assert body["count"] == len(body["results"]) >= 1
    assert body["results"][0]["client_name"] == "Jana Nováková"


def test_search_hit_shape(client):
    hit = client.get("/search", params={"q": "Dvorak"}).json()["results"][0]
    assert set(hit) == {"id","client_name", "file_path", "score"}, \
        "full_text nemá být v seznamu výsledků"
    assert 0.0 <= hit["score"] <= 1.0


def test_search_unknown_client(client):
    body = client.get("/search", params={"q": "Horáček"}).json()
    assert body == {"query": "Horáček", "count": 0, "results": []}


def test_search_requires_q(client):
    assert client.get("/search").status_code == 422


def test_search_too_short(client):
    r = client.get("/search", params={"q": "N"})
    assert r.status_code == 422
    # FastAPI v detailu říká, co a kde je špatně:
    assert r.json()["detail"][0]["loc"] == ["query", "q"]


def test_openapi_has_models(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert "SearchResponse" in schemas and "SearchHit" in schemas
    score = schemas["SearchHit"]["properties"]["score"]
    assert score.get("minimum") == 0 and score.get("maximum") == 1, \
        "score má mít v modelu omezení ge=0, le=1"
