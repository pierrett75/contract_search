import re
from datetime import date

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

    m_client = re.search(r"(?:Klient|Objednatel):[ \t]*([^,\n]+)", text)
    if m_client:
        meta["client_name"] = m_client.group(1).strip()
    
    m_ico = re.search(r"(?:Klient|Objednatel):[^\n]*?IČO:[ \t]*(\d{8})\b", text)
    if m_ico:
        meta["ico"] = m_ico.group(1)
    m_date = re.search(r"Datum[^:\n]*:[ \t]*(\d{1,2})\.[ \t]*(\d{1,2})\.[ \t]*(\d{4})", text)
    if m_date:
        day, month, year = (int(g) for g in m_date.groups())
        try:
            meta["date"] = date(year, month, day).isoformat()
        except ValueError:  # nesmyslné datum, např. 31. 2. 2024 nebo OCR chyba
            pass
    return meta