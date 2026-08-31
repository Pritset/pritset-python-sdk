from pathlib import Path
from typing import AsyncIterator, Iterator, Optional, Union

import httpx


PathLike = Union[str, Path]


class BinaryResponse:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response
        self.content_type: Optional[str] = response.headers.get("content-type")
        self.content_length: Optional[int] = _content_length(response)
        self.trace: Optional[str] = response.headers.get("x-trace")

    def iter_bytes(self, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
        return self._response.iter_bytes(chunk_size=chunk_size)

    def to_bytes(self) -> bytes:
        try:
            return self._response.read()
        finally:
            self.close()

    def save_to_file(self, path: PathLike) -> None:
        target = _output_path(path)
        try:
            with target.open("wb") as output:
                for chunk in self.iter_bytes():
                    output.write(chunk)
        finally:
            self.close()

    def close(self) -> None:
        self._response.close()

    def __enter__(self) -> "BinaryResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


class AsyncBinaryResponse:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response
        self.content_type: Optional[str] = response.headers.get("content-type")
        self.content_length: Optional[int] = _content_length(response)
        self.trace: Optional[str] = response.headers.get("x-trace")

    def iter_bytes(self, chunk_size: int = 64 * 1024) -> AsyncIterator[bytes]:
        return self._response.aiter_bytes(chunk_size=chunk_size)

    async def to_bytes(self) -> bytes:
        try:
            return await self._response.aread()
        finally:
            await self.close()

    async def save_to_file(self, path: PathLike) -> None:
        target = _output_path(path)
        try:
            with target.open("wb") as output:
                async for chunk in self.iter_bytes():
                    output.write(chunk)
        finally:
            await self.close()

    async def close(self) -> None:
        await self._response.aclose()

    async def __aenter__(self) -> "AsyncBinaryResponse":
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.close()


def _content_length(response: httpx.Response) -> Optional[int]:
    raw = response.headers.get("content-length")
    if raw is None:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value >= 0 else None


def _output_path(path: PathLike) -> Path:
    if isinstance(path, str) and not path.strip():
        raise ValueError("Output path must not be empty.")
    return Path(path)
