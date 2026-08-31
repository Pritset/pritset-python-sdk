# Pritset Python SDK

Official Python client for managing Pritset DOCX templates and generating PDFs.

> Preview: the package is currently `0.1.5`. Public method names may be refined before `1.0.0`.

## Requirements

- Python 3.9 or newer.
- A Pritset access token and secret from your profile.

## Installation

```bash
python -m pip install pritset
```

The PyPI project name must be verified before the first public release. For development from this repository:

```bash
python -m pip install -e .
```

## Create a client

```python
import os

from pritset import PritsetClient

pritset = PritsetClient(
    access_token=os.environ["PRITSET_ACCESS_TOKEN"],
    secret=os.environ["PRITSET_SECRET"],
)
```

The SDK sends the token as the `Authorization` header without adding a `Bearer` prefix. It sends the secret as `X-Secret`. Do not expose either value to browser code or logs.

Clients own their default HTTP connection pool and should be closed. A context manager is the simplest option:

```python
with PritsetClient(access_token="...", secret="...") as pritset:
    page = pritset.templates.list()
```

## Generate a PDF

```python
with PritsetClient(access_token="...", secret="...") as pritset:
    pdf = pritset.documents.generate(
        "YOUR_TEMPLATE_ID",
        {
            "title": "Monthly report",
            "totals": {"revenue": 12500, "currency": "USD"},
        },
    )
    print(pdf.content_type)  # application/pdf
    pdf.save_to_file("monthly-report.pdf")
```

Binary responses are stream-first. `save_to_file()` and `to_bytes()` consume and close the response, so call only one of them. Use `iter_bytes()` for custom streaming and close the response yourself or use it as a context manager.

## Template management

### List templates

```python
from pritset import TemplateSort

page = pritset.templates.list(
    search="invoice",
    page=1,
    page_size=20,
    sort=TemplateSort(sort_by="Name", sort_direction=0),
)

for template in page.data:
    print(template.id, template.name)
```

### Get and download a template

```python
details = pritset.templates.get("YOUR_TEMPLATE_ID")
print(details.file_info.object_name, details.file_info.size)

download = pritset.templates.download("YOUR_TEMPLATE_ID")
download.save_to_file("template.docx")
```

### Create a template

```python
from pritset import Upload

template = pritset.templates.create(
    name="Monthly invoice",
    tags="invoice,monthly",
    template=Upload("./invoice.docx"),
)
```

Bytes and file objects require an explicit filename:

```python
template = pritset.templates.create(
    name="Monthly invoice",
    template=Upload(
        docx_bytes,
        filename="invoice.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
)
```

### Update and delete

```python
pritset.templates.update(
    "YOUR_TEMPLATE_ID",
    name="Monthly invoice 2026",
    tags="invoice,monthly,2026",
)

pritset.templates.delete("YOUR_TEMPLATE_ID")
```

## Validate a template

```python
valid = pritset.templates.validate(
    file=Upload("./invoice.docx"),
    data={"invoiceNumber": "INV-1024", "total": "200.00"},
)
```

Template validation uses the same token-and-secret authentication as the other public template operations and is supported by contract `1.0.0`.

## Webhook generation

```python
job = pritset.documents.generate_webhook(
    "YOUR_TEMPLATE_ID",
    {"title": "Asynchronous report"},
    "https://example.com/webhooks/pritset",
)

print(job.id)
```

Pritset posts the generated PDF to the supplied URL and includes the job ID as an `id` query parameter. The SDK does not run or verify your webhook receiver.

## Raw JSON

Pass a JSON string when exact serialization matters:

```python
pdf = pritset.documents.generate("YOUR_TEMPLATE_ID", '{"amount":"10.00"}')
```

## Async usage and cancellation

`AsyncPritsetClient` mirrors the synchronous surface. Cancel the surrounding asyncio task to cancel an in-flight request.

```python
import asyncio
import os

from pritset import AsyncPritsetClient


async def main() -> None:
    async with AsyncPritsetClient(
        access_token=os.environ["PRITSET_ACCESS_TOKEN"],
        secret=os.environ["PRITSET_SECRET"],
    ) as pritset:
        pdf = await pritset.documents.generate("YOUR_TEMPLATE_ID", {"title": "Async report"})
        await pdf.save_to_file("async-report.pdf")


asyncio.run(main())
```

## Errors

```python
from pritset import PritsetApiError, PritsetTransportError

try:
    pritset.templates.get("missing-id")
except PritsetApiError as error:
    print(error.status, error.field_errors, error.retry_after)
except PritsetTransportError:
    print("The request did not complete.")
```

`PritsetApiError` supports field-error JSON, ASP.NET validation-problem JSON, and plain-text errors. Raw error bodies are capped at 64 KiB. Credentials and request bodies are not added to SDK error messages.

The SDK performs no automatic retries. This avoids accidentally repeating document generation or mutations. If you add a retry layer, restrict it to operations that are safe for your application.

## Configuration and custom transports

```python
import httpx

http_client = httpx.Client(verify=True)
pritset = PritsetClient(
    access_token="...",
    secret="...",
    base_url="https://api.pritset.com",
    timeout=120.0,
    http_client=http_client,
)
```

An injected `httpx.Client` or `httpx.AsyncClient` remains caller-owned and is not closed by the SDK. Per-request redirects are always disabled.

HTTPS is required. For an explicit local test server only:

```python
local = PritsetClient(
    access_token="test-token",
    secret="test-secret",
    base_url="http://127.0.0.1:5000",
    allow_insecure_http=True,
)
```

Automatic redirects are disabled so credentials cannot be forwarded to another origin.

## Contract and API documentation

- SDK contract: `pritset/pritset-sdk-contract`, version 1.0.0.
- API documentation: https://pritset.com/docs/api

## Verification

The complete offline-capable check runs contract verification, unit tests, bytecode compilation, wheel creation, wheel-content inspection, and a clean import from the built wheel:

```bash
python scripts/verify.py
```

## Production test-user lifecycle validation

The opt-in production test validates template upload, listing, details, update, download, direct PDF generation, webhook submission, deletion, and the final `404` response. It must use a dedicated production test user. It creates a uniquely named template and removes it in a `finally` cleanup block.

Copy `.env.example` to `.env`, fill in dedicated test-user credentials and a controlled webhook URL, and set both production confirmation flags to `true`. Then run the guarded launcher:

```powershell
pwsh ./scripts/run-production-test.ps1
```

The launcher requires typing `RUN-PRODUCTION-TEST` before contacting production. The test may consume production test-user credit and create webhook traffic.

## Contributing and security

See [CONTRIBUTING.md](./CONTRIBUTING.md) and [SECURITY.md](./SECURITY.md). Do not include access tokens, secrets, document data, or customer files in issues.

## License

MIT
