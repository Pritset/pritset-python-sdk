import json
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, BinaryIO, List, Optional, Tuple, Union

from .models import DocumentData, Upload


MultipartPart = Tuple[str, Tuple[Optional[str], Any, Optional[str]]]


class PreparedUpload(AbstractContextManager[MultipartPart]):
    def __init__(self, field: str, upload: Upload) -> None:
        self._field = field
        self._upload = upload
        self._opened: Optional[BinaryIO] = None

    def __enter__(self) -> MultipartPart:
        data = self._upload.data
        if isinstance(data, (str, Path)):
            path = Path(data)
            if isinstance(data, str) and not data.strip():
                raise ValueError("%s path must not be empty." % self._field)
            self._opened = path.open("rb")
            filename = self._upload.filename or path.name
            return self._part(self._opened, filename)

        if not self._upload.filename or not self._upload.filename.strip():
            raise ValueError("%s filename is required for bytes and file objects." % self._field)
        if isinstance(data, (bytearray, memoryview)):
            data = bytes(data)
        return self._part(data, self._upload.filename)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._opened is not None:
            self._opened.close()

    def _part(self, data: Any, filename: str) -> MultipartPart:
        return (
            self._field,
            (filename, data, self._upload.content_type or "application/octet-stream"),
        )


def text_part(field: str, value: str) -> MultipartPart:
    return (field, (None, value, None))


def serialize_document_data(data: DocumentData) -> str:
    if isinstance(data, str):
        return data
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def optional_text_parts(name: str, tags: Optional[str]) -> List[MultipartPart]:
    parts = [text_part("name", name)]
    if tags is not None:
        parts.append(text_part("tags", tags))
    return parts
