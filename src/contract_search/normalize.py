
import re
import unicodedata

padove_koncovky = ['ovi', 'em', 'a', 'u', 'e', 'y', 'o']

def strip_diacritics(s: str) -> str:
    """'Dvořák' -> 'Dvorak'"""
    name = unicodedata.normalize("NFD", s)        
    bez = [ch for ch in name if unicodedata.category(ch) != "Mn"]   
    return "".join(bez)                            


def surname_key(surname: str) -> str:
    """
    Převede příjmení na společný klíč, aby se našly všechny tvary:
        'Nováková', 'Novák', 'Nováka', 'Novákovi', 'Nováková' -> 'novak'
        'Dvořák', 'Dvořáka', 'Dvořáková'                      -> 'dvorak'
        'Svoboda', 'Svobodová', 'Svobodovi'                   -> 'svobod'
    """
    sur = strip_diacritics(surname.lower())
    upraveno = re.sub(r"ova$", "", sur)
    serazene_koncovky = sorted(padove_koncovky, key=len, reverse=True)

    for koncovka in serazene_koncovky:
        if upraveno.endswith(koncovka) and len(upraveno) - len(koncovka) >= 3:
            return upraveno[:-len(koncovka)]
            
    return upraveno


def name_key(full_name: str) -> str:
    """Klíč pro celé jméno = klíč příjmení (poslední slovo)."""
    parts = full_name.strip().split()
    return surname_key(parts[-1]) if parts else ""