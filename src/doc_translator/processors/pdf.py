import tempfile
import warnings
from pathlib import Path
from typing import Any

from doc_translator.models.chunk import Chunk, TranslatedChunk
from doc_translator.processors.base import DocumentProcessor
from doc_translator.processors.word import WordDocumentProcessor


class PDFDocumentProcessor(DocumentProcessor):
    def __init__(self, max_chars: int = 4000) -> None:
        super().__init__(max_chars)
        self._word_processor = WordDocumentProcessor(max_chars)
        self._temp_docx_path: Path | None = None

    def get_supported_extensions(self) -> list[str]:
        return [".pdf"]

    def load(self, path: str | Path) -> Any:
        try:
            from pdf2docx import Converter
        except ImportError:
            raise ImportError(
                "Для работы с PDF необходима библиотека pdf2docx. "
                "Установите её: pip install pdf2docx"
            )

        path = Path(path)
        temp_dir = tempfile.mkdtemp()
        self._temp_docx_path = Path(temp_dir) / f"{path.stem}.docx"

        cv = Converter(str(path))
        cv.convert(str(self._temp_docx_path))
        cv.close()

        return self._temp_docx_path

    def save(self, document: Any, path: str | Path) -> None:
        import shutil

        path = Path(path)

        if path.suffix.lower() == ".pdf":
            path = path.with_suffix(".docx")
            warnings.warn(f"PDF документы сохраняются как DOCX. Файл сохранён как: {path}")

        if isinstance(document, (str, Path)):
            shutil.copy2(str(document), str(path))
        else:
            self._word_processor.save(document, path)

    def chunk(self, path: str | Path) -> list[Chunk]:
        docx_path = self.load(path)
        chunks = self._word_processor.chunk(docx_path)

        for chunk in chunks:
            chunk.source_file = str(path)

        return chunks

    def concatenate(
        self,
        translated_chunks: list[TranslatedChunk],
        output_path: str | Path,
    ) -> None:
        output_path = Path(output_path)

        if output_path.suffix.lower() == ".pdf":
            output_path = output_path.with_suffix(".docx")
            warnings.warn(f"Результат сохраняется как DOCX (не PDF): {output_path}")

        self._word_processor.concatenate(translated_chunks, output_path)

    def cleanup(self) -> None:
        import shutil

        if self._temp_docx_path and self._temp_docx_path.parent.exists():
            shutil.rmtree(self._temp_docx_path.parent, ignore_errors=True)
            self._temp_docx_path = None

    def __del__(self) -> None:
        self.cleanup()
