import sqlite3
from pathlib import Path

from contract_search.loaders import IMAGE_EXT, load_document
from contract_search.metadata import extract_metadata
from contract_search.normalize import name_key

DB_PATH = "contracts.db"
COLUMNS = ("id", "file_path", "client_name", "ico", "date", "full_text")


def get_db(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contracts (
            id          INTEGER PRIMARY KEY,
            file_path   TEXT UNIQUE,
            client_name TEXT,
            name_key    TEXT,
            ico         TEXT,
            date        TEXT,
            full_text   TEXT
        )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_name_key ON contracts(name_key)")
    return conn


def ingest_folder(folder: str, conn: sqlite3.Connection) -> None:
    for path in sorted(Path(folder).iterdir()):
        if path.suffix.lower() not in {".txt", ".pdf"} | IMAGE_EXT:
            continue
        contract_id = ingest_file(path, conn)
        print(f"  {path.name:30} -> {contract_id}")


def ingest_file(path: Path, conn: sqlite3.Connection) -> int:
    """Načte jeden soubor, uloží ho do DB a vrátí id nové smlouvy."""
    text = load_document(path)
    meta = extract_metadata(text)
    key = name_key(meta["client_name"]) if meta["client_name"] else None
    cursor = conn.execute(
        """INSERT OR REPLACE INTO contracts
        (file_path, client_name, name_key, ico, date, full_text)
        VALUES (?, ?, ?, ?, ?, ?)""",
        (str(path), meta["client_name"], key, meta["ico"], meta["date"], text),
    )
    conn.commit()
    return cursor.lastrowid   


def get_contract(conn: sqlite3.Connection, contract_id: int) -> dict | None:
    row = conn.execute(
        f"SELECT {', '.join(COLUMNS)} FROM contracts WHERE id = ?",
        (contract_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(zip(COLUMNS, row))


def _fetch_dicts(cursor: sqlite3.Cursor) -> list[dict]:
    """Převede řádky z kurzoru na slovníky {název sloupce: hodnota}."""
    names = [col[0] for col in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def find_by_name_key(conn: sqlite3.Connection, key: str) -> list[dict]:
    """Smlouvy s přesně tímto klíčem jména (využije index idx_name_key)."""
    return _fetch_dicts(conn.execute(
        "SELECT id, file_path, client_name, full_text FROM contracts WHERE name_key = ?",
        (key,),
    ))


def find_fuzzy_candidates(conn: sqlite3.Connection, exclude_key: str) -> list[dict]:
    """Všechny ostatní smlouvy se známým klientem, i s jejich name_key pro porovnání."""
    return _fetch_dicts(conn.execute(
        "SELECT id, file_path, client_name, name_key, full_text FROM contracts "
        "WHERE name_key IS NOT NULL AND name_key != ?",
        (exclude_key,),
    ))
