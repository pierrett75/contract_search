
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from contract_search.db import get_contract
from contract_search.deps import DbConn
from contract_search.search import search

app = FastAPI(title="contract-search API", version="0.1.0")


# ---------------------------------------------------------------- modely ---

class SearchHit(BaseModel):
    """Jedna nalezená smlouva v seznamu výsledků (BEZ celého textu)."""
    id: int
    client_name: str
    file_path: str
    score: float = Field(ge=0, le=1, description="Podobnost 0–1, 1.0 = přesná shoda")


class SearchResponse(BaseModel):
    """Obálka odpovědi na /search."""

    query: str
    count: int = Field(ge=0)
    results: list[SearchHit]

class HealthResponse(BaseModel):
    status: str

class ContractDetailResponse(BaseModel):
    id: int
    file_path: str
    client_name: str | None
    ico: str | None
    date: str | None
    full_text : str

# ------------------------------------------------------------- endpointy ---


@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/search")
def search_contracts(
    q: Annotated[str, Query(min_length=2, description="Dotaz musí mít alespoň dva znaky")],
    conn: DbConn
) -> SearchResponse:
    """Vrací odpověď na dotaz"""
    results = search(q, conn)
    return SearchResponse(query= q, count= len(results),results = results)
     
@app.get("/contracts/{contract_id}",
         responses={404: {"description": "Smlouva neexistuje"}},)
def search_by_contract_id(
    contract_id: int,
    conn: DbConn
) -> ContractDetailResponse:
    contract = get_contract(conn,contract_id)
    if contract is None:
        detail=f"Smlouva s id {contract_id} neexistuje"
        raise HTTPException(404, detail=detail)
    else:
        return contract
        
