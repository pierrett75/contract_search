from pathlib import Path
from uuid import uuid4

from contract_search.loaders import IMAGE_EXT

ALLOWED_SUFFIXES = {".txt", ".pdf"} | IMAGE_EXT
MAX_BYTES = 10 * 1024 * 1024  # 10 MB


class UploadError(ValueError):
    """Společný předek, ať jde v API chytat všechny najednou."""


class UnsupportedFileType(UploadError):
    pass


class FileTooLarge(UploadError):
    pass


class EmptyFile(UploadError):
    pass


def validate_upload(filename: str, size: int) -> str:
    """Zkontroluje název a velikost, vrátí příponu malými písmeny (např. ".pdf")."""
    suff = Path(filename).suffix.lower()

    if  suff not in ALLOWED_SUFFIXES:
        raise UnsupportedFileType

    if size == 0:
        raise EmptyFile

    if size > MAX_BYTES:
        raise FileTooLarge

    return suff


def save_upload(data: bytes, filename: str, upload_dir: Path) -> Path:
    """Uloží bajty do upload_dir pod bezpečným jménem a vrátí cestu."""
    suffix = validate_upload(filename=filename, size=len(data))  
    upload_dir.mkdir(parents=True, exist_ok=True)   
    name = uuid4().hex + suffix
    path = upload_dir/name
    path.write_bytes(data)  

    return path
