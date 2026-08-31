# Contributing

1. Use Python 3.9 or newer.
2. Create a virtual environment and run `python -m pip install -e .`.
3. Run `python scripts/verify.py` before opening a pull request.
4. Add tests for every behavior change.
5. Never commit credentials, generated customer documents, or real customer data.

Public API changes must remain compatible with the pinned contract or update the contract through a separate reviewed release.
