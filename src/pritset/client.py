from typing import Optional

import httpx

from ._transport import AsyncTransport, DEFAULT_BASE_URL, DEFAULT_TIMEOUT, Transport
from .documents import AsyncDocumentsClient, DocumentsClient
from .templates import AsyncTemplatesClient, TemplatesClient


class PritsetClient:
    def __init__(
        self,
        *,
        access_token: str,
        secret: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        allow_insecure_http: bool = False,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        transport = Transport(
            access_token,
            secret,
            base_url,
            timeout,
            allow_insecure_http,
            http_client,
        )
        self._transport = transport
        self.templates = TemplatesClient(transport)
        self.documents = DocumentsClient(transport)

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> "PritsetClient":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return "PritsetClient()"


class AsyncPritsetClient:
    def __init__(
        self,
        *,
        access_token: str,
        secret: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        allow_insecure_http: bool = False,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        transport = AsyncTransport(
            access_token,
            secret,
            base_url,
            timeout,
            allow_insecure_http,
            http_client,
        )
        self._transport = transport
        self.templates = AsyncTemplatesClient(transport)
        self.documents = AsyncDocumentsClient(transport)

    async def close(self) -> None:
        await self._transport.close()

    async def __aenter__(self) -> "AsyncPritsetClient":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.close()

    def __repr__(self) -> str:
        return "AsyncPritsetClient()"
