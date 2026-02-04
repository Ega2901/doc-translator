from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from doc_translator.models.chunk import Chunk, TranslatedChunk


class DocumentProcessor(ABC):
    def __init__(self, max_chars: int = 4000) -> None:
        self.max_chars = max_chars

    @abstractmethod
    def load(self, path: str | Path) -> Any:
        pass

    @abstractmethod
    def save(self, document: Any, path: str | Path) -> None:
        pass

    @abstractmethod
    def chunk(self, path: str | Path) -> list[Chunk]:
        pass

    @abstractmethod
    def concatenate(
        self,
        translated_chunks: list[TranslatedChunk],
        output_path: str | Path,
    ) -> None:
        pass

    def get_supported_extensions(self) -> list[str]:
        return []

    def can_process(self, path: str | Path) -> bool:
        path = Path(path)
        return path.suffix.lower() in self.get_supported_extensions()
