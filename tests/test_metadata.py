from contract_search.metadata import extract_metadata

def test_metadata():
        m = extract_metadata("SMLOUVA O DÍLO\nObjednatel: Petr Dvořák, IČO: 12345678\n"
                             "Datum uzavření: 5. 3. 2024\n")
        assert m["client_name"] == "Petr Dvořák", m
        assert m["ico"] == "12345678", m
        assert m["date"] == "2024-03-05", m
        m2 = extract_metadata("Klient: Jana Nováková\nDatum uzavření: 15.11.2023")
        assert m2["client_name"] == "Jana Nováková", m2
        assert m2["date"] == "2023-11-15", m2