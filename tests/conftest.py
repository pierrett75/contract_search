from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from contract_search import api
from contract_search.db import get_db, ingest_folder
from contract_search.deps import get_conn, get_upload_dir

SAMPLES = Path(__file__).parent / "sample_contracts"


@pytest.fixture
def db_conn():
    """In-memory DB naplněná třemi vzorovými smlouvami (id 1–3)."""
    conn = get_db(":memory:")
    ingest_folder(SAMPLES, conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def upload_dir(tmp_path) -> Path:
    """Složka pro nahrané soubory – v tmp, ať testy nešpiní data/uploads."""
    return tmp_path / "uploads"


@pytest.fixture
def client(db_conn, upload_dir) -> Iterator[TestClient]:
    """TestClient, který místo skutečných závislostí dostane db_conn a upload_dir."""
    def override_get_conn():
        return db_conn

    def override_get_upload_dir():
       return upload_dir
    
    api.app.dependency_overrides[get_conn] = override_get_conn

    api.app.dependency_overrides[get_upload_dir] = override_get_upload_dir
    
    try:
        with TestClient(api.app) as c:
            yield c
    finally:
        api.app.dependency_overrides.clear()