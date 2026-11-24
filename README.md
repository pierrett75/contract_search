install
python -m pip install -e ".[dev]"

uvicorn contract_search.api:app --reload