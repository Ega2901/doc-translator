from pathlib import Path

from doc_translator.models.chunk import Chunk, ElementMetadata, ElementType, TranslatedChunk
from doc_translator.processors.base import DocumentProcessor
from doc_translator.processors.markdown_utils import chunk_blocks, split_markdown_into_blocks
from doc_translator.processors.mineru_utils import check_mineru, pdf_to_markdown
from doc_translator.processors.pandoc_utils import check_pandoc, markdown_to_docx


class MinerUPDFProcessor(DocumentProcessor):
    def __init__(
        self,
        max_chars: int = 4000,
        *,
        mineru_backend: str = "pipeline",
    ) -> None:
        super().__init__(max_chars)
        self.mineru_backend = mineru_backend

    def get_supported_extensions(self) -> list[str]:
        return [".pdf"]

    def load(self, path: str | Path) -> str:
        return pdf_to_markdown(path, backend=self.mineru_backend)

    def save(self, document: str, path: str | Path) -> None:
        markdown_to_docx(document, path)

    def chunk(self, path: str | Path) -> list[Chunk]:
        if not check_mineru():
            raise FileNotFoundError(
                "MinerU не найден. Установите: pip install \"mineru[all]\" "
                "или см. https://opendatalab.github.io/MinerU/"
            )
        path = Path(path).resolve()
        full_markdown = pdf_to_markdown(path, backend=self.mineru_backend)
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
        if output_path.suffix.lower() == ".pdf":
            output_path = output_path.with_suffix(".docx")
        markdown_to_docx(full_markdown, output_path, reference_docx=None)
