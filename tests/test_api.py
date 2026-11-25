def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_search_finds_client(client):
    r = client.get("/search", params={"q": "Nováka"})
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "Nováka"
    assert body["count"] == len(body["results"]) >= 1
    assert body["results"][0]["client_name"] == "Jana Nováková"


def test_search_hit_shape(client):
    hit = client.get("/search", params={"q": "Dvorak"}).json()["results"][0]
    assert set(hit) == {"id","client_name", "file_path", "score"}, \
        "full_text nemá být v seznamu výsledků"
    assert 0.0 <= hit["score"] <= 1.0


def test_search_unknown_client(client):
    body = client.get("/search", params={"q": "Horáček"}).json()
    assert body == {"query": "Horáček", "count": 0, "results": []}


def test_search_requires_q(client):
    assert client.get("/search").status_code == 422


def test_search_too_short(client):
    r = client.get("/search", params={"q": "N"})
    assert r.status_code == 422
    # FastAPI v detailu říká, co a kde je špatně:
    assert r.json()["detail"][0]["loc"] == ["query", "q"]


def test_openapi_has_models(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert "SearchResponse" in schemas and "SearchHit" in schemas
    score = schemas["SearchHit"]["properties"]["score"]
    assert score.get("minimum") == 0 and score.get("maximum") == 1, \
        "score má mít v modelu omezení ge=0, le=1"
