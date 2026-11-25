"""
Den 4 – testy pro fixtures z conftest.py (dependency_overrides).

Tyhle testy nepiš, jen je rozběhni: všechno se dělá v conftest.py.
Fixtures `client`, `db_conn` a `upload_dir` se sem dostanou samy podle jména
parametru – žádný import není potřeba.

Spuštění:  pytest tests/test_overrides.py -v
"""

from contract_search import api
from contract_search.deps import get_conn

SAMPLE_TEXT = "Smlouva\nKlient: Petr Horáček, IČO: 87654321\nČlánek 1\nText smlouvy."


def upload(client, name, data):
    return client.post("/contracts", files={"file": (name, data, "text/plain")})


# --- TODO 1: db_conn ---------------------------------------------------------
def test_db_conn_has_samples(db_conn):
    assert db_conn.execute("SELECT COUNT(*) FROM contracts").fetchone()[0] == 3


# --- TODO 2: API používá db_conn, ne proměnnou prostředí ----------------------
def test_api_ignores_env_db(client, monkeypatch, tmp_path):
    # Kdyby API pořád četlo CONTRACTS_DB, vytvořilo by tenhle soubor
    # a hledání by v prázdné DB nic nenašlo.
    fake = tmp_path / "nemelo_by_vzniknout.db"
    monkeypatch.setenv("CONTRACTS_DB", str(fake))

    hits = client.get("/search", params={"q": "Nováková"}).json()["results"]
    assert hits, "override get_conn nefunguje – API nevidí db_conn"
    assert not fake.exists()


def test_connection_survives_two_requests(client):
    # Když override spojení zavře, druhý request spadne na
    # sqlite3.ProgrammingError: Cannot operate on a closed database.
    assert client.get("/contracts/1").status_code == 200
    assert client.get("/contracts/2").status_code == 200


def test_api_and_test_share_connection(client, db_conn):
    r = upload(client, "horacek.txt", SAMPLE_TEXT.encode())
    assert r.status_code == 201, r.text
    # Zápis přes API je hned vidět i přímo v testu – stejné spojení.
    row = db_conn.execute(
        "SELECT client_name FROM contracts WHERE id = ?", (r.json()["id"],)
    ).fetchone()
    assert row == ("Petr Horáček",)


def test_test_can_prepare_data_directly(client, db_conn):
    # Opačný směr: data vložená v testu SQLem vidí API.
    cur = db_conn.execute(
        "INSERT INTO contracts (file_path, client_name, full_text) VALUES (?, ?, ?)",
        ("rucne.txt", "Ruční Vložení", "Článek 1"),
    )
    db_conn.commit()
    r = client.get(f"/contracts/{cur.lastrowid}")
    assert r.status_code == 200
    assert r.json()["client_name"] == "Ruční Vložení"


# --- TODO 3: upload_dir -------------------------------------------------------
def test_upload_goes_to_overridden_dir(client, upload_dir):
    upload(client, "horacek.txt", SAMPLE_TEXT.encode())
    assert len(list(upload_dir.iterdir())) == 1


# --- TODO 5: úklid ------------------------------------------------------------
def test_overrides_are_set_during_test(client):
    assert get_conn in api.app.dependency_overrides


def test_overrides_are_cleared_after_test():
    # Tenhle test client NEPOUŽÍVÁ. Pytest pouští testy v pořadí v souboru,
    # takže před ním proběhly testy výše – a jejich override tu nemá být.
    assert api.app.dependency_overrides == {}


# --- Bonus: override na selhání ----------------------------------------------
def test_broken_db_returns_500(db_conn):
    """
    Bonus (nepovinné): ověř, co klient dostane, když DB spadne.

    1. Napiš override pro get_conn, který vyhodí sqlite3.OperationalError.
    2. Vytvoř TestClient(api.app, raise_server_exceptions=False)
       – jinak by TestClient výjimku poslal rovnou do testu místo odpovědi 500.
    3. Zavolej /search?q=Novak a ověř status 500.
    4. Na konci overrides ukliď (try/finally), jinak spadne
       test_overrides_are_cleared_after_test při dalším běhu.

    Až budeš hotová, smaž řádek se skip.
    """
    import pytest
    pytest.skip("Bonus – odstraň skip, až ho napíšeš")
