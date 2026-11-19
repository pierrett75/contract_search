import sqlite3
from difflib import SequenceMatcher

from contract_search.normalize import name_key


def similarity(a: str, b: str) -> float:
    """0.0 – 1.0"""
    return SequenceMatcher(None, a, b).ratio()


def search(query: str, conn: sqlite3.Connection, threshold: float = 0.8) -> list[dict]:
    """
    Vrátí seznam celých smluv seřazený od nejlepší shody:
        [{"file_path": ..., "client_name": ..., "score": 1.0, "full_text": ...}, ...]
    Dotaz může být jen příjmení ('Nováka') i celé jméno ('Jana Nováková').
    """
    key = name_key(query)
    if  not key:
        return []

    rows = conn.execute(
        "SELECT file_path, client_name, full_text FROM contracts WHERE name_key = ?",
        (key,),
    ).fetchall()

    results = []
    for file_path, client_name, full_text in rows:
        results.append(
            {
                "file_path": file_path, 
                "client_name": client_name, 
                "score" : 1.0, 
                "full_text": full_text,
            }
        )

    rows = conn.execute(
    "SELECT file_path, client_name, name_key, full_text FROM contracts "
    "WHERE name_key IS NOT NULL AND name_key != ?",
    (key,),
    ).fetchall()

    for file_path, client_name, row_key, full_text in rows:
       score = similarity(key, row_key)
       if score >= threshold:
          results.append({
            "file_path": file_path,
            "client_name": client_name,
            "score": score,
            "full_text": full_text,
        })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results