from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ElementType(Enum):
    PARAGRAPH = "paragraph"
    TABLE = "table"
    HEADER = "header"
    FOOTER = "footer"
    IMAGE = "image"


@dataclass
class ElementMetadata:
    element_type: ElementType
    style_name: str | None = None
    font_name: str | None = None
    font_size: float | None = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    alignment: str | None = None
    rows: int | None = None
    cols: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    index: int
    text: str
    char_count: int
    metadata: list[ElementMetadata] = field(default_factory=list)
    original_elements: list[Any] = field(default_factory=list)
    source_file: str | None = None

    def __post_init__(self) -> None:
        if self.char_count == 0:
            self.char_count = len(self.text)


@dataclass
class TranslatedChunk:
    original: Chunk
    translated_text: str
    target_language: str
    model_used: str | None = None

    @property
    def index(self) -> int:
        return self.original.index

    @property
    def metadata(self) -> list[ElementMetadata]:
        return self.original.metadata

    @property
    def original_elements(self) -> list[Any]:
        return self.original.original_elements
