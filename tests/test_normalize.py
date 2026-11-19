from contract_search.normalize import strip_diacritics, surname_key


def test_diacritics():
        assert strip_diacritics("Dvořák") == "Dvorak", strip_diacritics("Dvořák")
        assert strip_diacritics("Šťastná") == "Stastna"

def test_surname():
        for v in ["Novák", "Nováka", "Novákovi", "Nováková", "NOVÁKOVÁ"]:
            assert surname_key(v) == "novak", f"{v} -> {surname_key(v)}"
        for v in ["Dvořák", "Dvořáka", "Dvořáková"]:
            assert surname_key(v) == "dvorak", f"{v} -> {surname_key(v)}"
        for v in ["Svoboda", "Svobodová", "Svobodovi"]:
            assert surname_key(v) == "svobod", f"{v} -> {surname_key(v)}"