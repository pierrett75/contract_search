"""
Vyhledávání smluv podle jména klienta.

Použití:
    contract-search ingest <složka>      # načte smlouvy do databáze
    contract-search search <jméno>       # např. "Nováková", "Dvorak"
"""
import sys

from contract_search.db import get_db, ingest_folder
from contract_search.search import search


def main() -> None:
    args = sys.argv[1:]
    cmd = args[0] if args else ""

    if cmd == "ingest" and len(args) == 2:
        ingest_folder(args[1], get_db())
    elif cmd == "search" and len(args) >= 2:
        results = search(" ".join(args[1:]), get_db())
        if not results:
            print("Nic nenalezeno.")
        for r in results:
            print(f"\n=== {r['client_name']}  (score {r['score']:.2f})  {r['file_path']} ===")
            print(r["full_text"])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
