# Development Guide for Automate

## Running Tests
Run the pytest suite:
```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests/ -v
```

## Adding a New Transformation Rule
1. Register the rule metadata in `automate/theory/rules.py`.
2. Add support in the appropriate backend (`SymPyChecker`, `LeanChecker`, etc.).
3. Add a unit test verifying the rule in `tests/`.
4. Include an example theory file in `examples/`.

## Code Formatting and Linting
Automate follows modern Python conventions (PEP 8, type hints via Pydantic).
