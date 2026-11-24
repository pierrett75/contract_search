"""
Sdílené závislosti pro FastAPI (Depends).

Analogie z Javy/Springu:
- get_conn je něco jako bean s request scope, který si endpoint nechá vstříknout.
- Část za `yield` se spustí až po odeslání odpovědi, podobně jako `finally`
  v try-with-resources: spojení se zavře vždycky, i když endpoint spadne.
"""
import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends

from contract_search.db import get_db

ENV_VAR = "CONTRACTS_DB"
DEFAULT_DB_PATH = "contracts.db"
UPLOAD_DIR_ENV_VAR = "CONTRACTS_UPLOAD_DIR"
DEFAULT_UPLOAD_DIR = "data/uploads"


def get_db_path() -> str:
    return os.environ.get(ENV_VAR, DEFAULT_DB_PATH)

def get_conn() -> Iterator[sqlite3.Connection]:
    conn = get_db(get_db_path())
    try:
        yield conn
    finally:
        conn.close()

DbConn = Annotated[sqlite3.Connection, Depends(get_conn)]


def get_upload_dir() -> Path:
    return Path(os.environ.get(UPLOAD_DIR_ENV_VAR, DEFAULT_UPLOAD_DIR))


UploadDir = Annotated[Path, Depends(get_upload_dir)]
