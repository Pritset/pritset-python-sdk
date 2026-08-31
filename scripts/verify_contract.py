import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contract"


def main() -> None:
    lock = json.loads((CONTRACT / "contract.lock.json").read_text(encoding="utf-8"))
    openapi = (CONTRACT / "openapi.yaml").read_bytes()
    digest = hashlib.sha256(openapi).hexdigest()
    if digest != lock["openapiSha256"]:
        raise RuntimeError(
            "Vendored OpenAPI hash %s does not match contract.lock.json." % digest
        )
    text = openapi.decode("utf-8")
    if "  version: %s" % lock["contractVersion"] not in text:
        raise RuntimeError("Vendored OpenAPI version does not match contract.lock.json.")
    for relative in (
        "fixtures/templates/list.json",
        "fixtures/templates/get.json",
        "fixtures/documents/webhook-job.json",
        "fixtures/errors/field-errors.json",
        "fixtures/errors/validation-problem.json",
        "fixtures/errors/plain-text.txt",
    ):
        if not (CONTRACT / relative).is_file():
            raise RuntimeError("Missing contract fixture: %s" % relative)
    print("Contract 1.0.0 verified.")


if __name__ == "__main__":
    main()
