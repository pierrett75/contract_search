"""
Vyhledávání smluv podle jména klienta — CVIČENÍ
================================================

Pipeline:
    1. načtení dokumentu (TXT / PDF s textem / sken nebo fotka -> OCR)
    2. extrakce metadat (jméno klienta, IČO, datum)
    3. normalizace jmen (diakritika, přechýlení, skloňování)
    4. uložení do SQLite
    5. vyhledávání podle jména (přesná shoda na normalizovaném klíči + fuzzy)
    6. vrácení CELÉ smlouvy (originální soubor + plný text)

Místa označená  # TODO  doplníš sama. Zbytek (databáze, CLI, testy) funguje.

Použití:
    python contract_search.py test                 # spustí testy tvých funkcí
    python contract_search.py ingest sample_contracts
    python contract_search.py search "Nováková"
    python contract_search.py search "Dvorak"      # bez diakritiky / s překlepem

Knihovny: pypdf, pytesseract + Pillow (OCR potřebuje nainstalovaný tesseract
s češtinou: balíček tesseract-ocr-ces). Zbytek je standardní knihovna.
"""

import re
import sqlite3
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

DB_PATH = "contracts.db"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


# ---------------------------------------------------------------------------
# 1) NAČTENÍ DOKUMENTU
# ---------------------------------------------------------------------------

def read_pdf_text(path: Path) -> str:
    """Vytáhne textovou vrstvu z PDF. U naskenovaného PDF vrátí (skoro) prázdný řetězec."""
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def ocr_image(path: Path) -> str:
    """OCR jedné fotky / obrázku."""
    # TODO 1: pomocí pytesseract převeď obrázek na text.
    #   - otevři obrázek přes PIL.Image.open
    #   - zavolej pytesseract.image_to_string(..., lang="ces")
    #   Tip: když lang="ces" není nainstalovaný, zkus dočasně lang="eng"
    #        (diakritika pak bude rozbitá — přesně proto potřebujeme fuzzy hledání).
    raise NotImplementedError("TODO 1: ocr_image")


def load_document(path: Path) -> str:
    """Vrátí text dokumentu bez ohledu na formát."""
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8")
    if suffix in IMAGE_EXT:
        return ocr_image(path)
    if suffix == ".pdf":
        text = read_pdf_text(path)
        # TODO 2: PDF může být sken bez textové vrstvy (přesně kolegův případ!).
        #   Když je text po odstranění bílých znaků kratší než ~50 znaků,
        #   je to pravděpodobně sken -> převeď stránky na obrázky a pusť OCR.
        #   (Jednodušší varianta pro začátek: jen vypiš varování, že soubor
        #    potřebuje OCR, ať ho neuložíš potichu prázdný.)
        return text
    raise ValueError(f"Nepodporovaný formát: {path}")


# ---------------------------------------------------------------------------
# 2) EXTRAKCE METADAT
# ---------------------------------------------------------------------------

def extract_metadata(text: str) -> dict:
    """
    Vrátí slovník:
        {"client_name": "Jana Nováková" | None,
         "ico": "12345678" | None,
         "date": "2024-03-15" | None}   # ISO formát

    Ve vzorových smlouvách vypadají řádky třeba takto:
        Klient: Jana Nováková
        Objednatel: Petr Dvořák, IČO: 12345678
        Datum uzavření: 15. 3. 2024
    """
    meta = {"client_name": None, "ico": None, "date": None}

    # TODO 3a: jméno klienta — regex, který zachytí text za "Klient:" NEBO
    #          "Objednatel:" až do čárky nebo konce řádku. Ořízni mezery.
    # TODO 3b: IČO — přesně 8 číslic za "IČO:" (mezera za dvojtečkou je volitelná).
    #          Pozor: IČO má i poskytovatel/zhotovitel! Hledej ho jen na řádku
    #          klienta/objednatele, jinak klientovi přiřadíš cizí IČO.
    # TODO 3c: datum ve tvaru "15. 3. 2024" nebo "15.3.2024" převeď na "2024-03-15".

    # BONUS: místo regexů nech metadata vytáhnout LLM (lokálně přes LM Studio,
    #        které má OpenAI-kompatibilní API) a vrátit JSON. Porovnej spolehlivost.
    return meta


# ---------------------------------------------------------------------------
# 3) NORMALIZACE JMEN
# ---------------------------------------------------------------------------

def strip_diacritics(s: str) -> str:
    """'Dvořák' -> 'Dvorak'"""
    # TODO 4: použij unicodedata.normalize("NFD", s) a vyhoď znaky,
    #         jejichž unicodedata.category(ch) == "Mn" (kombinující diakritika).
    raise NotImplementedError("TODO 4: strip_diacritics")


def surname_key(surname: str) -> str:
    """
    Převede příjmení na společný klíč, aby se našly všechny tvary:
        'Nováková', 'Novák', 'Nováka', 'Novákovi', 'Nováková' -> 'novak'
        'Dvořák', 'Dvořáka', 'Dvořáková'                      -> 'dvorak'
        'Svoboda', 'Svobodová', 'Svobodovi'                   -> 'svobod'

    Postup:
        - malá písmena + bez diakritiky (použij strip_diacritics)
        - odstraň přechýlení: koncovka 'ova' (z '-ová')
        - odstraň pádové koncovky, od nejdelší: 'ovi', 'em', 'a', 'u', 'e', 'y', 'o'
          ale jen tehdy, když po odříznutí zůstanou aspoň 3 znaky
    Je to záměrně hrubé (žádná plná lemmatizace) — pro jména to stačí.
    """
    # TODO 5
    raise NotImplementedError("TODO 5: surname_key")


def name_key(full_name: str) -> str:
    """Klíč pro celé jméno = klíč příjmení (poslední slovo)."""
    parts = full_name.strip().split()
    return surname_key(parts[-1]) if parts else ""


# ---------------------------------------------------------------------------
# 4) DATABÁZE  (hotové)
# ---------------------------------------------------------------------------

def get_db(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
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
        text = load_document(path)
        meta = extract_metadata(text)
        key = name_key(meta["client_name"]) if meta["client_name"] else None
        conn.execute(
            """INSERT OR REPLACE INTO contracts
               (file_path, client_name, name_key, ico, date, full_text)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (str(path), meta["client_name"], key, meta["ico"], meta["date"], text),
        )
        print(f"  {path.name:30} -> {meta}")
    conn.commit()


# ---------------------------------------------------------------------------
# 5) VYHLEDÁVÁNÍ
# ---------------------------------------------------------------------------

def similarity(a: str, b: str) -> float:
    """0.0 – 1.0"""
    return SequenceMatcher(None, a, b).ratio()


def search(query: str, conn: sqlite3.Connection, threshold: float = 0.8) -> list[dict]:
    """
    Vrátí seznam celých smluv seřazený od nejlepší shody:
        [{"file_path": ..., "client_name": ..., "score": 1.0, "full_text": ...}, ...]

    Dvě fáze:
        a) přesná shoda: name_key(query) == name_key v DB  -> score 1.0
        b) fuzzy: pro ostatní řádky spočítej similarity(name_key(query), name_key)
           a vezmi ty se score >= threshold (zachytí překlepy z OCR)

    Dotaz může být jen příjmení ('Nováka') i celé jméno ('Jana Nováková').
    """
    # TODO 6a: přesná shoda přes SQL (WHERE name_key = ?) — využije index
    # TODO 6b: fuzzy shoda nad zbylými řádky
    # TODO 6c: spoj výsledky, odstraň duplicity, seřaď podle score sestupně
    # Otázka k zamyšlení: proč tady NEPOUŽÍVÁME embeddingy?
    raise NotImplementedError("TODO 6: search")


# ---------------------------------------------------------------------------
# TESTY  (neupravuj — podle nich poznáš, že máš hotovo)
# ---------------------------------------------------------------------------

def run_tests() -> None:
    def check(name, fn):
        try:
            fn()
            print(f"  OK    {name}")
            return True
        except NotImplementedError as e:
            print(f"  TODO  {name}  ({e})")
        except AssertionError as e:
            print(f"  FAIL  {name}  {e}")
        return False

    def t_diacritics():
        assert strip_diacritics("Dvořák") == "Dvorak", strip_diacritics("Dvořák")
        assert strip_diacritics("Šťastná") == "Stastna"

    def t_surname():
        for v in ["Novák", "Nováka", "Novákovi", "Nováková", "NOVÁKOVÁ"]:
            assert surname_key(v) == "novak", f"{v} -> {surname_key(v)}"
        for v in ["Dvořák", "Dvořáka", "Dvořáková"]:
            assert surname_key(v) == "dvorak", f"{v} -> {surname_key(v)}"
        for v in ["Svoboda", "Svobodová", "Svobodovi"]:
            assert surname_key(v) == "svobod", f"{v} -> {surname_key(v)}"

    def t_metadata():
        m = extract_metadata("SMLOUVA O DÍLO\nObjednatel: Petr Dvořák, IČO: 12345678\n"
                             "Datum uzavření: 5. 3. 2024\n")
        assert m["client_name"] == "Petr Dvořák", m
        assert m["ico"] == "12345678", m
        assert m["date"] == "2024-03-05", m
        m2 = extract_metadata("Klient: Jana Nováková\nDatum uzavření: 15.11.2023")
        assert m2["client_name"] == "Jana Nováková", m2
        assert m2["date"] == "2023-11-15", m2

    def t_search():
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

    print("Testy:")
    results = [check("strip_diacritics", t_diacritics),
               check("surname_key", t_surname),
               check("extract_metadata", t_metadata),
               check("search (end-to-end)", t_search)]
    print(f"\n{sum(results)}/{len(results)} hotovo")


# ---------------------------------------------------------------------------
# CLI  (hotové)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    if cmd == "test":
        run_tests()
    elif cmd == "ingest":
        ingest_folder(sys.argv[2], get_db())
    elif cmd == "search":
        for r in search(" ".join(sys.argv[2:]), get_db()):
            print(f"\n=== {r['client_name']}  (score {r['score']:.2f})  {r['file_path']} ===")
            print(r["full_text"])
    else:
        print(__doc__)
