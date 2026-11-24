import sqlite3
from difflib import SequenceMatcher

from contract_search.db import find_by_name_key, find_fuzzy_candidates
from contract_search.normalize import name_key


def similarity(a: str, b: str) -> float:
    """0.0 – 1.0"""
    return SequenceMatcher(None, a, b).ratio()


def search(query: str, conn: sqlite3.Connection, threshold: float = 0.8) -> list[dict]:
    """
    Vrátí seznam celých smluv seřazený od nejlepší shody:
        [{"id": 1, "file_path": ..., "client_name": ..., "score": 1.0, "full_text": ...}, ...]
    Dotaz může být jen příjmení ('Nováka') i celé jméno ('Jana Nováková').
    """
    key = name_key(query)
    if not key:
        return []

    # přesná shoda
    results = [{**contract, "score": 1.0} for contract in find_by_name_key(conn, key)]

    # fuzzy shoda (překlepy z OCR)
    for contract in find_fuzzy_candidates(conn, exclude_key=key):
        score = similarity(key, contract.pop("name_key"))
        if score >= threshold:
            results.append({**contract, "score": score})

    results.sort(key=lambda r: r["score"], reverse=True)
    return results
