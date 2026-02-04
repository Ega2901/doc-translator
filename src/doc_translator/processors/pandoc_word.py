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
    def get_supported_extensions(self) -> list[str]:
        return [".docx"]

    def load(self, path: str | Path) -> str:
        return docx_to_markdown(path, wrap="none")

    def save(self, document: str, path: str | Path) -> None:
        markdown_to_docx(document, path)

    def chunk(self, path: str | Path) -> list[Chunk]:
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
            meta = ElementMetadata(element_type=ElementType.PARAGRAPH)
            chunks.append(
                Chunk(
                    index=index,
                    text=text,
                    char_count=len(text),
                    metadata=[meta] * len(group),
                    original_elements=[],
                    source_file=str(path),
                )
            )
        return chunks

    def concatenate(
        self,
        translated_chunks: list[TranslatedChunk],
        output_path: str | Path,
    ) -> None:
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
        ref = sorted_chunks[0].original.source_file
        reference_docx = Path(ref).resolve() if ref else None
        if reference_docx and not reference_docx.exists():
            reference_docx = None
        markdown_to_docx(
            full_markdown,
            output_path,
            reference_docx=reference_docx,
        )
