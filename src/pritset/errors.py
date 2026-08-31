import json
from typing import Any, Dict, List, Mapping, Optional

import httpx


MAX_ERROR_BODY_BYTES = 64 * 1024


class PritsetApiError(Exception):
    def __init__(
        self,
        message: str,
        status: int,
        field_errors: Dict[str, List[str]],
        raw_body: str,
        retry_after: Optional[str] = None,
        trace: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.field_errors = field_errors
        self.raw_body = raw_body
        self.retry_after = retry_after
        self.trace = trace

    @classmethod
    def from_response(cls, response: httpx.Response) -> "PritsetApiError":
        raw_body = _read_error_body(response)
        return cls._from_raw(response, raw_body)

    @classmethod
    async def from_async_response(cls, response: httpx.Response) -> "PritsetApiError":
        raw_body = await _read_error_body_async(response)
        return cls._from_raw(response, raw_body)

    @classmethod
    def _from_raw(cls, response: httpx.Response, raw_body: str) -> "PritsetApiError":
        parsed = _parse_json(raw_body)
        field_errors = _normalize_field_errors(parsed)
        return cls(
            _error_message(response.status_code, parsed, raw_body, field_errors),
            response.status_code,
            field_errors,
            raw_body,
            response.headers.get("retry-after"),
            response.headers.get("x-trace"),
        )


class PritsetTransportError(Exception):
    def __init__(self, message: str, code: Optional[str] = None) -> None:
        super().__init__(message)
        self.code = code


def _read_error_body(response: httpx.Response) -> str:
    body = bytearray()
    try:
        for chunk in response.iter_bytes():
            remaining = MAX_ERROR_BODY_BYTES - len(body)
            if remaining <= 0:
                break
            body.extend(chunk[:remaining])
            if len(chunk) >= remaining:
                break
    finally:
        response.close()
    return bytes(body).decode("utf-8", errors="replace")


async def _read_error_body_async(response: httpx.Response) -> str:
    body = bytearray()
    try:
        async for chunk in response.aiter_bytes():
            remaining = MAX_ERROR_BODY_BYTES - len(body)
            if remaining <= 0:
                break
            body.extend(chunk[:remaining])
            if len(chunk) >= remaining:
                break
    finally:
        await response.aclose()
    return bytes(body).decode("utf-8", errors="replace")


def _parse_json(raw_body: str) -> Any:
    if not raw_body.strip():
        return None
    try:
        return json.loads(raw_body)
    except (TypeError, ValueError):
        return None


def _normalize_field_errors(value: Any) -> Dict[str, List[str]]:
    if not isinstance(value, Mapping):
        return {}
    nested = value.get("errors")
    if isinstance(nested, Mapping):
        return _normalize_error_record(nested)
    excluded = {"type", "title", "status", "traceId", "message"}
    return _normalize_error_record({key: item for key, item in value.items() if key not in excluded})


def _normalize_error_record(value: Mapping[str, Any]) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    for field, messages in value.items():
        if isinstance(messages, str):
            result[str(field)] = [messages]
        elif isinstance(messages, list):
            strings = [message for message in messages if isinstance(message, str)]
            if strings:
                result[str(field)] = strings
    return result


def _error_message(
    status: int,
    parsed: Any,
    raw_body: str,
    field_errors: Dict[str, List[str]],
) -> str:
    if isinstance(parsed, Mapping):
        for key in ("title", "message"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return "Pritset API request failed (%d): %s" % (status, value)
    for messages in field_errors.values():
        if messages:
            return "Pritset API request failed (%d): %s" % (status, messages[0])
    if raw_body.strip():
        return "Pritset API request failed (%d): %s" % (status, raw_body.strip())
    return "Pritset API request failed (%d)." % status
