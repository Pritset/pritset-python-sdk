import os
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pritset import PritsetApiError, PritsetClient, Upload


PRODUCTION_URL = "https://api.pritset.com"
DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "staging-template.docx"


@dataclass(frozen=True)
class Config:
    base_url: str
    access_token: str
    secret: str
    webhook_url: str
    template_path: Path
    run_prefix: str

    @classmethod
    def from_environment(cls) -> "Config":
        base_url = os.environ.get("PRITSET_BASE_URL", PRODUCTION_URL).rstrip("/")
        access_token = _required_environment("PRITSET_ACCESS_TOKEN")
        secret = _required_environment("PRITSET_SECRET")
        webhook_url = _required_environment("PRITSET_WEBHOOK_URL")
        template_path = Path(os.environ.get("PRITSET_TEMPLATE_PATH", str(DEFAULT_FIXTURE)))
        run_prefix = os.environ.get("PRITSET_TEST_RUN_PREFIX", "pritset-python-production-test")

        if not re.fullmatch(r"[a-z0-9-]+", run_prefix):
            raise RuntimeError("PRITSET_TEST_RUN_PREFIX must contain only lowercase letters, digits, and dashes.")
        if not template_path.is_file():
            raise RuntimeError("The configured production test template does not exist.")
        _validate_webhook(webhook_url)
        if base_url == PRODUCTION_URL:
            if os.environ.get("PRITSET_ALLOW_PRODUCTION", "").lower() != "true":
                raise RuntimeError("PRITSET_ALLOW_PRODUCTION=true is required for production.")
            if os.environ.get("PRITSET_PRODUCTION_TEST_USER_CONFIRMED", "").lower() != "true":
                raise RuntimeError(
                    "PRITSET_PRODUCTION_TEST_USER_CONFIRMED=true is required for production."
                )
            if urlsplit(webhook_url).scheme.lower() != "https":
                raise RuntimeError("Production lifecycle tests require an HTTPS webhook URL.")
        return cls(base_url, access_token, secret, webhook_url, template_path, run_prefix)


def main() -> None:
    config = Config.from_environment()
    suffix = uuid.uuid4().hex[:12]
    original_name = "%s-%s" % (config.run_prefix, suffix)
    updated_name = original_name + "-updated"
    document_data = _document_data(suffix)
    template_id: Optional[str] = None

    with PritsetClient(
        access_token=config.access_token,
        secret=config.secret,
        base_url=config.base_url,
    ) as client:
        try:
            print("Validating the production test template...")
            valid = client.templates.validate(
                file=Upload(config.template_path),
                data=document_data,
            )
            if not valid:
                raise RuntimeError("The production API reported that the test template is invalid.")

            print("Creating a temporary template...")
            created = client.templates.create(
                name=original_name,
                tags=config.run_prefix,
                template=Upload(config.template_path),
            )
            template_id = created.id

            print("Checking list, details, and update operations...")
            page = client.templates.list(search=original_name, page=1, page_size=20)
            if not any(item.id == template_id for item in page.data):
                raise RuntimeError("The temporary template was not returned by list().")
            details = client.templates.get(template_id)
            if details.template.id != template_id:
                raise RuntimeError("Template details returned a different id.")
            updated = client.templates.update(
                template_id,
                name=updated_name,
                tags=config.run_prefix + ",updated",
            )
            if updated.name != updated_name:
                raise RuntimeError("Template update did not return the updated name.")

            print("Checking template download and direct PDF generation...")
            downloaded = client.templates.download(template_id).to_bytes()
            if not downloaded:
                raise RuntimeError("Template download returned an empty body.")
            pdf = client.documents.generate(
                template_id,
                document_data,
            ).to_bytes()
            if not pdf.startswith(b"%PDF-"):
                raise RuntimeError("Direct generation did not return a PDF signature.")

            print("Submitting webhook generation...")
            job = client.documents.generate_webhook(
                template_id,
                document_data,
                config.webhook_url,
            )
            if not job.id:
                raise RuntimeError("Webhook generation returned an empty job id.")
        finally:
            if template_id is not None:
                print("Deleting the temporary template...")
                client.templates.delete(template_id)

        if template_id is None:
            raise RuntimeError("The production lifecycle did not create a template.")
        try:
            client.templates.get(template_id)
        except PritsetApiError as error:
            if error.status != 404:
                raise RuntimeError("Expected 404 after cleanup, received %d." % error.status) from None
        else:
            raise RuntimeError("The temporary template still exists after cleanup.")
    print("Production test-user lifecycle passed.")


def _document_data(run_id: str) -> Dict[str, Any]:
    return {
        "title": "Pritset SDK production test-user validation",
        "description": "Lifecycle run %s" % run_id,
        "advantages": [
            {
                "title": "Contract",
                "description": "All public template operations completed.",
            },
            {
                "title": "Cleanup",
                "description": "The temporary template is deleted after validation.",
            },
        ],
    }


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value or not value.strip():
        raise RuntimeError("%s must be set." % name)
    return value


def _validate_webhook(value: str) -> None:
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError:
        raise RuntimeError("PRITSET_WEBHOOK_URL must be an absolute HTTP or HTTPS URL.") from None
    if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
        raise RuntimeError("PRITSET_WEBHOOK_URL must be an absolute HTTP or HTTPS URL.")
    if parsed.username is not None or parsed.password is not None:
        raise RuntimeError("PRITSET_WEBHOOK_URL must not contain credentials.")


if __name__ == "__main__":
    main()
