
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

from contract_search.db import get_contract, ingest_file
from contract_search.deps import DbConn, UploadDir
from contract_search.search import search
from contract_search.storage import (
    ALLOWED_SUFFIXES,
    MAX_BYTES,
    EmptyFile,
    FileTooLarge,
    UnsupportedFileType,
    save_upload,
)

app = FastAPI(title="contract-search API", version="0.1.0")

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

class ContractCreated(BaseModel):
    id: int
    client_name: str | None
    file_path: str
    original_filename: str


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
def get_by_contract_id(
    contract_id: int,
    conn: DbConn
) -> ContractDetailResponse:
    contract = get_contract(conn,contract_id)
    if contract is None:
        detail=f"Smlouva s id {contract_id} neexistuje"
        raise HTTPException(404, detail=detail)
    
    return contract


@app.post(
    "/contracts",
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Prázdný soubor"},
        413: {"description": "Soubor je příliš velký"},
        415: {"description": "Nepodporovaný typ souboru"},
    },
)
def upload_contract(file: UploadFile, conn: DbConn, upload_dir: UploadDir) -> ContractCreated:
    data = file.file.read()
    try:
        path = save_upload(data, file.filename, upload_dir)    
    except UnsupportedFileType:
        detail = "Povolené soubory jsou: " + ", ".join(sorted(ALLOWED_SUFFIXES))
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail)
    except EmptyFile:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Soubor je prázdný")
    except FileTooLarge:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"Soubor je větší než {MAX_BYTES // (1024 * 1024)} MB")

    file_id = ingest_file(path, conn)
    contract = get_contract(conn, file_id)
    return ContractCreated(**contract, original_filename=file.filename)