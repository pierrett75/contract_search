"""Testy pro Den 2 (detail, 404, Depends, CONTRACTS_DB). Spuštění: pytest tests/test_api_detail.py -v"""
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from contract_search import api
from contract_search.db import get_contract, get_db, ingest_folder
from contract_search.deps import get_conn, get_db_path

SAMPLES = Path(__file__).parent / "sample_contracts"


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Dočasná DB se vzorovými smlouvami; API ji najde přes CONTRACTS_DB."""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("CONTRACTS_DB", str(db_file))
    conn = get_db(str(db_file))
    ingest_folder(str(SAMPLES), conn)
    conn.close()
    return TestClient(api.app)


# --- TODO 1: cesta z proměnné prostředí ---------------------------------------
def test_db_path_from_env(monkeypatch):
    monkeypatch.setenv("CONTRACTS_DB", "jina.db")
    assert get_db_path() == "jina.db"


def test_db_path_default(monkeypatch):
    monkeypatch.delenv("CONTRACTS_DB", raising=False)
    assert get_db_path() == "contracts.db"


# --- TODO 2: dependency zavře spojení -----------------------------------------
def test_get_conn_closes_connection(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTRACTS_DB", str(tmp_path / "x.db"))
    gen = get_conn()
    conn = next(gen)                       # tohle udělá FastAPI před endpointem
    conn.execute("SELECT 1")
    with pytest.raises(StopIteration):     # a tohle po odeslání odpovědi
        next(gen)
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")           # zavřené spojení už nejde použít


# --- TODO 3: get_contract ------------------------------------------------------
def test_get_contract_missing_returns_none():
    conn = get_db(":memory:")
    assert get_contract(conn, 1) is None


def test_get_contract_returns_dict():
    conn = get_db(":memory:")
    ingest_folder(str(SAMPLES), conn)
    c = get_contract(conn, 1)
    assert c is not None
    assert set(c) == {"id", "file_path", "client_name", "ico", "date", "full_text"}
    assert c["id"] == 1


# --- TODO 4 + 5: hledání vrací id a jde přes Depends --------------------------
def test_search_uses_env_db_and_returns_id(client):
    r = client.get("/search", params={"q": "Nováka"})
    assert r.status_code == 200, r.text
    hits = r.json()["results"]
    assert hits, "hledání nic nenašlo – bere API opravdu DB z CONTRACTS_DB?"
    assert isinstance(hits[0]["id"], int)


# --- TODO 6: detail a 404 ------------------------------------------------------
def test_detail_after_search(client):
    hit = client.get("/search", params={"q": "Nováka"}).json()["results"][0]
    r = client.get(f"/contracts/{hit['id']}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == hit["id"]
    assert body["client_name"] == "Jana Nováková"
    assert "Článek" in body["full_text"], "detail má vracet celou smlouvu"


def test_detail_not_found(client):
    r = client.get("/contracts/99999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Smlouva s id 99999 neexistuje"


def test_detail_invalid_id_is_422(client):
    # Tohle nepíšeš ty: FastAPI zvaliduje `contract_id: int` samo.
    r = client.get("/contracts/abc")
    assert r.status_code == 422


def test_openapi_documents_404(client):
    # Bonus: do dekorátoru přidej responses={404: {"description": "..."}},
    # ať je 404 vidět i na /docs.
    op = client.get("/openapi.json").json()["paths"]["/contracts/{contract_id}"]["get"]
    assert "404" in op["responses"]
