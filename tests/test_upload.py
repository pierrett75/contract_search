from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from contract_search import api
from contract_search.db import get_contract, get_db, ingest_file, ingest_folder
from contract_search.search import search
from contract_search.storage import (
    MAX_BYTES,
    EmptyFile,
    FileTooLarge,
    UnsupportedFileType,
    save_upload,
    validate_upload,
)

SAMPLES = Path(__file__).parent / "sample_contracts"
SAMPLE = SAMPLES / "smlouva_01.txt"  # Klient: Jana Nováková


def test_validate_returns_lowercase_suffix():
    assert validate_upload("Smlouva.PDF", 100) == ".pdf"


@pytest.mark.parametrize("name", ["virus.exe", "smlouva", "smlouva.pdf.exe"])
def test_validate_rejects_unsupported_type(name):
    with pytest.raises(UnsupportedFileType):
        validate_upload(name, 100)


def test_validate_rejects_empty():
    with pytest.raises(EmptyFile):
        validate_upload("smlouva.pdf", 0)


def test_validate_rejects_too_large():
    with pytest.raises(FileTooLarge):
        validate_upload("smlouva.pdf", MAX_BYTES + 1)


def test_validate_accepts_exactly_max_size():
    assert validate_upload("smlouva.pdf", MAX_BYTES) == ".pdf"


def test_save_writes_content(tmp_path):
    path = save_upload(b"obsah", "smlouva.txt", tmp_path)
    assert path.read_bytes() == b"obsah"
    assert path.suffix == ".txt"


def test_save_ignores_user_path(tmp_path):
    upload_dir = tmp_path / "uploads"
    path = save_upload(b"x", "../../evil.pdf", upload_dir)
    assert path.parent == upload_dir
    assert path.name != "evil.pdf"


def test_save_creates_missing_dir(tmp_path):
    path = save_upload(b"x", "smlouva.pdf", tmp_path / "a" / "b")
    assert path.exists()


def test_same_name_does_not_overwrite(tmp_path):
    first = save_upload(b"prvni", "smlouva.txt", tmp_path)
    second = save_upload(b"druha", "smlouva.txt", tmp_path)
    assert first != second
    assert first.read_bytes() == b"prvni"


def test_rejected_file_is_not_written(tmp_path):
    with pytest.raises(UnsupportedFileType):
        save_upload(b"MZ...", "virus.exe", tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_ingest_file_returns_id_of_saved_contract():
    conn = get_db(":memory:")
    contract_id = ingest_file(SAMPLE, conn)
    assert isinstance(contract_id, int)
    c = get_contract(conn, contract_id)
    assert c["client_name"] == "Jana Nováková"
    assert c["file_path"] == str(SAMPLE)


def test_ingest_file_is_searchable_without_diacritics():
    conn = get_db(":memory:")
    contract_id = ingest_file(SAMPLE, conn)
    assert contract_id in [r["id"] for r in search("Novakova", conn)]


def test_ingest_folder_still_works():
    # ingest_folder má po refaktoru jen volat ingest_file v cyklu
    conn = get_db(":memory:")
    ingest_folder(str(SAMPLES), conn)
    assert conn.execute("SELECT COUNT(*) FROM contracts").fetchone()[0] == 3


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CONTRACTS_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("CONTRACTS_UPLOAD_DIR", str(tmp_path / "uploads"))
    return TestClient(api.app)


def upload(client, name, data):
    return client.post("/contracts", files={"file": (name, data, "text/plain")})


def test_upload_returns_201_and_is_searchable(client):
    r = upload(client, "smlouva_01.txt", SAMPLE.read_bytes())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["client_name"] == "Jana Nováková"
    assert body["original_filename"] == "smlouva_01.txt"

    hits = client.get("/search", params={"q": "Nováková"}).json()["results"]
    assert body["id"] in [h["id"] for h in hits]


def test_upload_saves_file_to_upload_dir(client, tmp_path):
    upload(client, "smlouva_01.txt", SAMPLE.read_bytes())
    saved = list((tmp_path / "uploads").iterdir())
    assert len(saved) == 1
    assert saved[0].name != "smlouva_01.txt"


def test_upload_unsupported_type_is_415(client):
    r = upload(client, "virus.exe", b"MZ\x90\x00")
    assert r.status_code == 415
    assert ".pdf" in r.json()["detail"], "napiš do zprávy, co je povolené"


def test_upload_empty_is_400(client):
    assert upload(client, "prazdna.txt", b"").status_code == 400


def test_upload_too_large_is_413(client, monkeypatch):
    monkeypatch.setattr("contract_search.storage.MAX_BYTES", 10)
    assert upload(client, "smlouva.txt", b"x" * 11).status_code == 413


def test_upload_without_file_is_422(client):
    # Tohle nepíšeš ty: chybějící povinný parametr hlídá FastAPI.
    assert client.post("/contracts").status_code == 422
