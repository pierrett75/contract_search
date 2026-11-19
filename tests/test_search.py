from pathlib import Path

from contract_search.db import get_db, ingest_folder
from contract_search.search import search


def test_search():
        conn = get_db(":memory:")
        ingest_folder(str(Path(__file__).parent / "sample_contracts"), conn)
        r = search("Nováka", conn)
        assert r and r[0]["client_name"] == "Jana Nováková", r[:1]
        assert "Článek" in r[0]["full_text"], "má se vracet CELÁ smlouva"
        r = search("Dvorak", conn)                      # bez diakritiky
        assert r and r[0]["client_name"] == "Petr Dvořák", r[:1]
        r = search("Svobodova", conn)                   # 'Svobodová' bez čárky
        assert r and "Svobod" in r[0]["client_name"], r[:1]
        r = search("Svpboda", conn)                     # překlep jako z OCR
        assert r and "Svobod" in r[0]["client_name"], "fuzzy nenašlo překlep"
        assert search("Horáček", conn) == [], "neexistující klient má vrátit []"