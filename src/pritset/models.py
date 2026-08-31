from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Dict, List, Mapping, Optional, Union


JsonPrimitive = Union[str, int, float, bool, None]
JsonValue = Union[JsonPrimitive, List["JsonValue"], Dict[str, "JsonValue"]]
DocumentData = Union[JsonValue, str]
UploadData = Union[str, Path, bytes, bytearray, memoryview, BinaryIO]


@dataclass(frozen=True)
class Upload:
    data: UploadData
    filename: Optional[str] = None
    content_type: Optional[str] = None


@dataclass(frozen=True)
class Template:
    id: str
    name: str
    tags: Optional[str]
    template_object: Optional[str]

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "Template":
        return cls(
            id=_string(value, "id"),
            name=_string(value, "name"),
            tags=_optional_string(value, "tags"),
            template_object=_optional_string(value, "templateObject"),
        )


@dataclass(frozen=True)
class TemplateFileInfo:
    content_type: str
    last_modified: str
    object_name: str
    size: int

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "TemplateFileInfo":
        return cls(
            content_type=_string(value, "contentType"),
            last_modified=_string(value, "lastModified"),
            object_name=_string(value, "objectName"),
            size=_integer(value, "size"),
        )


@dataclass(frozen=True)
class TemplateDetails:
    template: Template
    file_info: TemplateFileInfo

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "TemplateDetails":
        return cls(
            template=Template.from_dict(_mapping(value, "template")),
            file_info=TemplateFileInfo.from_dict(_mapping(value, "fileInfo")),
        )


@dataclass(frozen=True)
class TemplatePage:
    data: List[Template]
    total: int

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "TemplatePage":
        items = value.get("data")
        if not isinstance(items, list):
            raise ValueError("data must be a list")
        return cls(
            data=[Template.from_dict(_as_mapping(item, "data item")) for item in items],
            total=_integer(value, "total"),
        )


@dataclass(frozen=True)
class TemplateSort:
    sort_by: str
    sort_direction: int = 0


@dataclass(frozen=True)
class WebhookJob:
    id: str

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "WebhookJob":
        return cls(id=_string(value, "id"))


def _as_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("%s must be an object" % name)
    return value


def _mapping(value: Mapping[str, object], key: str) -> Mapping[str, object]:
    return _as_mapping(value.get(key), key)


def _string(value: Mapping[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str):
        raise ValueError("%s must be a string" % key)
    return item


def _optional_string(value: Mapping[str, object], key: str) -> Optional[str]:
    item = value.get(key)
    if item is not None and not isinstance(item, str):
        raise ValueError("%s must be a string or null" % key)
    return item


def _integer(value: Mapping[str, object], key: str) -> int:
    item = value.get(key)
    if isinstance(item, bool) or not isinstance(item, int):
        raise ValueError("%s must be an integer" % key)
    return item
