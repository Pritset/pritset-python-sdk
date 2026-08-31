from typing import Any, List, Mapping, Optional
from urllib.parse import urljoin, urlsplit

import httpx

from ._uploads import MultipartPart
from ._version import __version__
from .binary_response import AsyncBinaryResponse, BinaryResponse
from .errors import PritsetApiError, PritsetTransportError


DEFAULT_BASE_URL = "https://api.pritset.com"
DEFAULT_TIMEOUT = 120.0


class Transport:
    def __init__(
        self,
        access_token: str,
        secret: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        allow_insecure_http: bool = False,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._access_token = _required_secret(access_token, "access_token")
        self._secret = _required_secret(secret, "secret")
        self._base_url = _normalize_base_url(base_url, allow_insecure_http)
        self._timeout = _positive_timeout(timeout)
        self._client = http_client or httpx.Client(timeout=self._timeout, follow_redirects=False)
        self._owns_client = http_client is None

    def json(
        self,
        method: str,
        path: str,
        *,
        files: Optional[List[MultipartPart]] = None,
    ) -> Any:
        response = self._send(method, path, files=files)
        failure = None
        try:
            response.read()
            value = response.json()
        except Exception as error:
            failure = PritsetTransportError(
                "Pritset API returned an invalid JSON response.",
                type(error).__name__ if isinstance(error, httpx.RequestError) else None,
            )
        finally:
            response.close()
        if failure is not None:
            raise failure
        return value

    def void(self, method: str, path: str) -> None:
        self._send(method, path).close()

    def binary(
        self,
        method: str,
        path: str,
        *,
        files: Optional[List[MultipartPart]] = None,
    ) -> BinaryResponse:
        return BinaryResponse(self._send(method, path, files=files))

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def _send(
        self,
        method: str,
        path: str,
        *,
        files: Optional[List[MultipartPart]] = None,
    ) -> httpx.Response:
        failure = None
        try:
            request = self._client.build_request(
                method,
                _request_url(self._base_url, path),
                headers=_headers(self._access_token, self._secret),
                files=files,
                timeout=self._timeout,
            )
            response = self._client.send(request, stream=True, follow_redirects=False)
        except Exception as error:
            failure = PritsetTransportError(
                "Pritset API request could not be completed.",
                type(error).__name__ if isinstance(error, httpx.RequestError) else None,
            )
        if failure is not None:
            raise failure
        if response.status_code < 200 or response.status_code >= 300:
            raise PritsetApiError.from_response(response)
        return response

    def __repr__(self) -> str:
        return "Transport(base_url=%r, timeout=%r)" % (self._base_url, self._timeout)


class AsyncTransport:
    def __init__(
        self,
        access_token: str,
        secret: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        allow_insecure_http: bool = False,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._access_token = _required_secret(access_token, "access_token")
        self._secret = _required_secret(secret, "secret")
        self._base_url = _normalize_base_url(base_url, allow_insecure_http)
        self._timeout = _positive_timeout(timeout)
        self._client = http_client or httpx.AsyncClient(timeout=self._timeout, follow_redirects=False)
        self._owns_client = http_client is None

    async def json(
        self,
        method: str,
        path: str,
        *,
        files: Optional[List[MultipartPart]] = None,
    ) -> Any:
        response = await self._send(method, path, files=files)
        failure = None
        try:
            await response.aread()
            value = response.json()
        except Exception as error:
            failure = PritsetTransportError(
                "Pritset API returned an invalid JSON response.",
                type(error).__name__ if isinstance(error, httpx.RequestError) else None,
            )
        finally:
            await response.aclose()
        if failure is not None:
            raise failure
        return value

    async def void(self, method: str, path: str) -> None:
        response = await self._send(method, path)
        await response.aclose()

    async def binary(
        self,
        method: str,
        path: str,
        *,
        files: Optional[List[MultipartPart]] = None,
    ) -> AsyncBinaryResponse:
        return AsyncBinaryResponse(await self._send(method, path, files=files))

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _send(
        self,
        method: str,
        path: str,
        *,
        files: Optional[List[MultipartPart]] = None,
    ) -> httpx.Response:
        failure = None
        try:
            request = self._client.build_request(
                method,
                _request_url(self._base_url, path),
                headers=_headers(self._access_token, self._secret),
                files=files,
                timeout=self._timeout,
            )
            response = await self._client.send(request, stream=True, follow_redirects=False)
        except Exception as error:
            failure = PritsetTransportError(
                "Pritset API request could not be completed.",
                type(error).__name__ if isinstance(error, httpx.RequestError) else None,
            )
        if failure is not None:
            raise failure
        if response.status_code < 200 or response.status_code >= 300:
            raise await PritsetApiError.from_async_response(response)
        return response

    def __repr__(self) -> str:
        return "AsyncTransport(base_url=%r, timeout=%r)" % (self._base_url, self._timeout)


def _headers(access_token: str, secret: str) -> Mapping[str, str]:
    return {
        "Authorization": access_token,
        "X-Secret": secret,
        "User-Agent": "pritset-python-sdk/%s" % __version__,
    }


def _request_url(base_url: str, path: str) -> str:
    return urljoin(base_url + "/", path.lstrip("/"))


def _normalize_base_url(value: str, allow_insecure_http: bool) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("base_url must be an absolute URL.")
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError:
        raise ValueError("base_url must be an absolute URL.") from None
    if not parsed.scheme or not parsed.hostname:
        raise ValueError("base_url must be an absolute URL.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("base_url must not contain credentials.")
    if parsed.query or parsed.fragment:
        raise ValueError("base_url must not contain a query string or fragment.")
    loopback_hosts = {"localhost", "127.0.0.1", "::1"}
    allowed_loopback_http = (
        allow_insecure_http
        and parsed.scheme.lower() == "http"
        and parsed.hostname.lower() in loopback_hosts
    )
    if parsed.scheme.lower() != "https" and not allowed_loopback_http:
        raise ValueError("base_url must use HTTPS unless allow_insecure_http is enabled for localhost.")
    return value.rstrip("/")


def _required_secret(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must not be empty." % name)
    return value


def _positive_timeout(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError("timeout must be a positive number.")
    return float(value)
