from typing import Optional
from urllib.parse import quote, urlencode

from ._transport import AsyncTransport, Transport
from ._uploads import PreparedUpload, optional_text_parts, serialize_document_data, text_part
from .binary_response import AsyncBinaryResponse, BinaryResponse
from .errors import PritsetTransportError
from .models import DocumentData, Template, TemplateDetails, TemplatePage, TemplateSort, Upload, _as_mapping


class TemplatesClient:
    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    def list(
        self,
        *,
        search: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        sort: Optional[TemplateSort] = None,
    ) -> TemplatePage:
        path = _list_path(search, page, page_size, sort)
        return _parse_model(TemplatePage.from_dict, self._transport.json("GET", path))

    def get(self, template_id: str) -> TemplateDetails:
        value = self._transport.json("GET", "/api/template/%s" % _encoded_id(template_id, "template_id"))
        return _parse_model(TemplateDetails.from_dict, value)

    def download(self, template_id: str) -> BinaryResponse:
        return self._transport.binary(
            "GET", "/api/template/download/%s" % _encoded_id(template_id, "template_id")
        )

    def create(self, *, name: str, template: Upload, tags: Optional[str] = None) -> Template:
        _required(name, "name")
        with PreparedUpload("template", template) as upload:
            parts = optional_text_parts(name, tags) + [upload]
            value = self._transport.json("POST", "/api/template", files=parts)
        return _parse_model(Template.from_dict, value)

    def update(
        self,
        template_id: str,
        *,
        name: str,
        tags: Optional[str] = None,
        template: Optional[Upload] = None,
    ) -> Template:
        _required(name, "name")
        path = "/api/template/%s" % _encoded_id(template_id, "template_id")
        if template is None:
            value = self._transport.json("PUT", path, files=optional_text_parts(name, tags))
        else:
            with PreparedUpload("template", template) as upload:
                value = self._transport.json(
                    "PUT", path, files=optional_text_parts(name, tags) + [upload]
                )
        return _parse_model(Template.from_dict, value)

    def delete(self, template_id: str) -> None:
        self._transport.void("DELETE", "/api/template/%s" % _encoded_id(template_id, "template_id"))

    def validate(self, *, file: Upload, data: DocumentData) -> bool:
        with PreparedUpload("file", file) as upload:
            value = self._transport.json(
                "POST",
                "/api/template/process/validate",
                files=[upload, text_part("data", serialize_document_data(data))],
            )
        if not isinstance(value, bool):
            raise PritsetTransportError("Pritset API returned an invalid JSON response.")
        return value


class AsyncTemplatesClient:
    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def list(
        self,
        *,
        search: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        sort: Optional[TemplateSort] = None,
    ) -> TemplatePage:
        value = await self._transport.json("GET", _list_path(search, page, page_size, sort))
        return _parse_model(TemplatePage.from_dict, value)

    async def get(self, template_id: str) -> TemplateDetails:
        value = await self._transport.json(
            "GET", "/api/template/%s" % _encoded_id(template_id, "template_id")
        )
        return _parse_model(TemplateDetails.from_dict, value)

    async def download(self, template_id: str) -> AsyncBinaryResponse:
        return await self._transport.binary(
            "GET", "/api/template/download/%s" % _encoded_id(template_id, "template_id")
        )

    async def create(self, *, name: str, template: Upload, tags: Optional[str] = None) -> Template:
        _required(name, "name")
        with PreparedUpload("template", template) as upload:
            value = await self._transport.json(
                "POST", "/api/template", files=optional_text_parts(name, tags) + [upload]
            )
        return _parse_model(Template.from_dict, value)

    async def update(
        self,
        template_id: str,
        *,
        name: str,
        tags: Optional[str] = None,
        template: Optional[Upload] = None,
    ) -> Template:
        _required(name, "name")
        path = "/api/template/%s" % _encoded_id(template_id, "template_id")
        if template is None:
            value = await self._transport.json("PUT", path, files=optional_text_parts(name, tags))
        else:
            with PreparedUpload("template", template) as upload:
                value = await self._transport.json(
                    "PUT", path, files=optional_text_parts(name, tags) + [upload]
                )
        return _parse_model(Template.from_dict, value)

    async def delete(self, template_id: str) -> None:
        await self._transport.void(
            "DELETE", "/api/template/%s" % _encoded_id(template_id, "template_id")
        )

    async def validate(self, *, file: Upload, data: DocumentData) -> bool:
        with PreparedUpload("file", file) as upload:
            value = await self._transport.json(
                "POST",
                "/api/template/process/validate",
                files=[upload, text_part("data", serialize_document_data(data))],
            )
        if not isinstance(value, bool):
            raise PritsetTransportError("Pritset API returned an invalid JSON response.")
        return value


def _list_path(
    search: Optional[str],
    page: Optional[int],
    page_size: Optional[int],
    sort: Optional[TemplateSort],
) -> str:
    query = []
    if search is not None:
        query.append(("q", search))
    if page is not None:
        query.append(("p", str(_positive_integer(page, "page"))))
    if page_size is not None:
        query.append(("s", str(_positive_integer(page_size, "page_size"))))
    if sort is not None:
        query.append(("sorts[0].sortBy", _required(sort.sort_by, "sort.sort_by")))
        if isinstance(sort.sort_direction, bool) or sort.sort_direction not in (0, 1):
            raise ValueError("sort.sort_direction must be 0 or 1.")
        query.append(("sorts[0].sortDirection", str(sort.sort_direction)))
    return "/api/template" + (("?" + urlencode(query)) if query else "")


def _encoded_id(value: str, name: str) -> str:
    return quote(_required(value, name), safe="")


def _required(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must not be empty." % name)
    return value


def _positive_integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("%s must be a positive integer." % name)
    return value


def _parse_model(factory: object, value: object):
    try:
        return factory(_as_mapping(value, "response"))
    except (KeyError, TypeError, ValueError):
        raise PritsetTransportError("Pritset API returned an invalid JSON response.") from None
