"""
Процессор документов Word через Pandoc: строгий формат Markdown для модели.

Использует Pandoc для конвертации docx → Markdown и обратно docx с сохранением
стилей через --reference-doc. Модель получает и возвращает только Markdown,
что даёт предсказуемую структуру (заголовки, таблицы, списки).
"""

from pathlib import Path

from doc_translator.models.chunk import Chunk, ElementMetadata, ElementType, TranslatedChunk
from doc_translator.processors.base import DocumentProcessor
from doc_translator.processors.markdown_utils import chunk_blocks, split_markdown_into_blocks
from doc_translator.processors.pandoc_utils import (
    check_pandoc,
    docx_to_markdown,
    markdown_to_docx,
)


class PandocWordProcessor(DocumentProcessor):
    """
    Процессор Word через Pandoc: docx → Markdown → модель → docx.

    Передаёт в модель строгий Markdown (заголовки #, таблицы |---|, списки),
    после перевода собирает результат обратно в docx с форматированием
    исходного документа через --reference-doc.

    Parameters
    ----------
    max_chars : int, default=4000
        Максимальное количество символов в одном чанке.

    Raises
    ------
    FileNotFoundError
        Если Pandoc не установлен (см. https://pandoc.org/installing.html).
    """

    def get_supported_extensions(self) -> list[str]:
        return [".docx"]

    def load(self, path: str | Path) -> str:
        """Загрузить документ как Markdown (через Pandoc)."""
        return docx_to_markdown(path, wrap="none")

    def save(self, document: str, path: str | Path) -> None:
        """Сохранить Markdown как docx (через Pandoc)."""
        markdown_to_docx(document, path)

    def chunk(self, path: str | Path) -> list[Chunk]:
        """
        Разбить документ на чанки в формате Markdown.

        Сначала docx конвертируется в Markdown, затем разбивается по блокам
        (параграфы, заголовки, таблицы) с учётом max_chars.
        """
        if not check_pandoc():
            raise FileNotFoundError(
                "Pandoc не найден. Установите: https://pandoc.org/installing.html"
            )
        path = Path(path).resolve()
        full_markdown = docx_to_markdown(path, wrap="none")
        blocks = split_markdown_into_blocks(full_markdown)
        block_groups = chunk_blocks(blocks, self.max_chars)

        chunks: list[Chunk] = []
        for index, group in enumerate(block_groups):
            text = "\n\n".join(group)
            # Метаданные для совместимости с Chunk; для Pandoc путь сборки не использует elements
            meta = ElementMetadata(element_type=ElementType.PARAGRAPH)
            chunks.append(
                Chunk(
                    index=index,
                    text=text,
                    char_count=len(text),
                    metadata=[meta] * len(group),
                    original_elements=[],  # не используются при сборке через pandoc
                    source_file=str(path),
                )
            )
        return chunks

    def concatenate(
        self,
        translated_chunks: list[TranslatedChunk],
        output_path: str | Path,
    ) -> None:
        """
        Собрать переведённые чанки в один docx через Pandoc.

        Склеивает Markdown из всех чанков и конвертирует в docx с использованием
        исходного документа как reference-doc (сохраняются стили и форматирование).
        """
        if not translated_chunks:
            raise ValueError("Список переведённых чанков пуст")
        if not check_pandoc():
            raise FileNotFoundError(
                "Pandoc не найден. Установите: https://pandoc.org/installing.html"
            )

        sorted_chunks = sorted(translated_chunks, key=lambda c: c.index)
        full_markdown = "\n\n".join(
            c.translated_text.strip() for c in sorted_chunks
        )
        output_path = Path(output_path).resolve()
        reference_docx = sorted_chunks[0].original.source_file
        markdown_to_docx(
            full_markdown,
            output_path,
            reference_docx=reference_docx if reference_docx else None,
        )
