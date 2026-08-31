from urllib.parse import quote, urlsplit

from ._transport import AsyncTransport, Transport
from ._uploads import serialize_document_data, text_part
from .binary_response import AsyncBinaryResponse, BinaryResponse
from .errors import PritsetTransportError
from .models import DocumentData, WebhookJob, _as_mapping


class DocumentsClient:
    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def generate(self, template_id: str, data: DocumentData) -> BinaryResponse:
        return self._transport.binary(
            "POST",
            "/api/template/process/direct/%s" % _encoded_template_id(template_id),
            files=[text_part("data", serialize_document_data(data))],
        )

    def generate_webhook(
        self, template_id: str, data: DocumentData, webhook_url: str
    ) -> WebhookJob:
        _validate_webhook_url(webhook_url)
        value = self._transport.json(
            "POST",
            "/api/template/process/webhook/%s" % _encoded_template_id(template_id),
            files=[
                text_part("data", serialize_document_data(data)),
                text_part("url", webhook_url),
            ],
        )
        return _webhook_job(value)


class AsyncDocumentsClient:
    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def generate(self, template_id: str, data: DocumentData) -> AsyncBinaryResponse:
        return await self._transport.binary(
            "POST",
            "/api/template/process/direct/%s" % _encoded_template_id(template_id),
            files=[text_part("data", serialize_document_data(data))],
        )

    async def generate_webhook(
        self, template_id: str, data: DocumentData, webhook_url: str
    ) -> WebhookJob:
        _validate_webhook_url(webhook_url)
        value = await self._transport.json(
            "POST",
            "/api/template/process/webhook/%s" % _encoded_template_id(template_id),
            files=[
                text_part("data", serialize_document_data(data)),
                text_part("url", webhook_url),
            ],
        )
        return _webhook_job(value)


def _encoded_template_id(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("template_id must not be empty.")
    return quote(value, safe="")


def _validate_webhook_url(value: str) -> None:
    if not isinstance(value, str):
        raise ValueError("webhook_url must be an absolute HTTP or HTTPS URL.")
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError:
        raise ValueError("webhook_url must be an absolute HTTP or HTTPS URL.") from None
    if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
        raise ValueError("webhook_url must be an absolute HTTP or HTTPS URL.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("webhook_url must not contain credentials.")


def _webhook_job(value: object) -> WebhookJob:
    try:
        return WebhookJob.from_dict(_as_mapping(value, "response"))
    except (KeyError, TypeError, ValueError):
        raise PritsetTransportError("Pritset API returned an invalid JSON response.") from None
