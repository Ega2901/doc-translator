import warnings
from pathlib import Path
from typing import Any

from docx import Document
from docx.document import Document as DocumentType
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn

from doc_translator.models.chunk import Chunk, ElementMetadata, ElementType, TranslatedChunk
from doc_translator.processors.base import DocumentProcessor


class WordDocumentProcessor(DocumentProcessor):
    """
    Процессор для документов Microsoft Word (.docx).
    
    Использует библиотеку python-docx для работы с документами.
    Поддерживает сохранение форматирования при разбиении и сборке.
    
    Parameters
    ----------
    max_chars : int, default=4000
        Максимальное количество символов в одном чанке.
    
    Examples
    --------
    >>> processor = WordDocumentProcessor(max_chars=2000)
    >>> chunks = processor.chunk("document.docx")
    >>> print(f"Создано {len(chunks)} чанков")
    
    >>> # После перевода
    >>> processor.concatenate(translated_chunks, "output.docx")
    """
    
    def get_supported_extensions(self) -> list[str]:
        """
        Получить список поддерживаемых расширений.
        
        Returns
        -------
        list[str]
            Возвращает ['.docx'].
        """
        return [".docx"]

    def load(self, path: str | Path) -> DocumentType:
        """
        Загрузить документ Word.
        
        Parameters
        ----------
        path : str or Path
            Путь к .docx файлу.
        
        Returns
        -------
        Document
            Объект документа python-docx.
        """
        return Document(str(path))

    def save(self, document: DocumentType, path: str | Path) -> None:
        """
        Сохранить документ Word.
        
        Parameters
        ----------
        document : Document
            Объект документа python-docx.
        path : str or Path
            Путь для сохранения.
        """
        document.save(str(path))

    def _extract_paragraph_metadata(self, paragraph: Paragraph) -> ElementMetadata:
        style_name = paragraph.style.name if paragraph.style else None
        font_name = None
        font_size = None
        bold = False
        italic = False
        underline = False

        if paragraph.runs:
            run = paragraph.runs[0]
            font = run.font
            font_name = font.name
            font_size = font.size.pt if font.size else None
            bold = font.bold or False
            italic = font.italic or False
            underline = font.underline or False

        alignment = None
        if paragraph.alignment is not None:
            alignment = str(paragraph.alignment)

        return ElementMetadata(
            element_type=ElementType.PARAGRAPH,
            style_name=style_name,
            font_name=font_name,
            font_size=font_size,
            bold=bold,
            italic=italic,
            underline=underline,
            alignment=alignment,
        )

    def _extract_table_metadata(self, table: Table) -> ElementMetadata:
        return ElementMetadata(
            element_type=ElementType.TABLE,
            rows=len(table.rows),
            cols=len(table.columns),
        )

    def _get_table_text(self, table: Table) -> str:
        rows_text = []
        for row in table.rows:
            cells_text = []
            for cell in row.cells:
                cells_text.append(cell.text.strip())
            rows_text.append(" | ".join(cells_text))
        return "\n".join(rows_text)

    def _iter_block_items(self, document: DocumentType):
        body = document.element.body
        for child in body.iterchildren():
            if child.tag == qn("w:p"):
                yield Paragraph(child, document)
            elif child.tag == qn("w:tbl"):
                yield Table(child, document)

    def chunk(self, path: str | Path) -> list[Chunk]:
        """
        Разбить документ Word на чанки.
        
        Parameters
        ----------
        path : str or Path
            Путь к .docx файлу.
        
        Returns
        -------
        list[Chunk]
            Список чанков с текстом и метаданными.
        
        Notes
        -----
        - Итерирует по параграфам и таблицам в порядке появления
        - Группирует элементы пока не достигнет max_chars
        - Таблицы не разрываются — идут целиком в один чанк
        - Если таблица превышает max_chars, выдаётся предупреждение
        
        Examples
        --------
        >>> processor = WordDocumentProcessor(max_chars=2000)
        >>> chunks = processor.chunk("document.docx")
        >>> for chunk in chunks:
        ...     print(f"Чанк {chunk.index}: {chunk.char_count} символов")
        """
        document = self.load(path)
        chunks: list[Chunk] = []

        current_texts: list[str] = []
        current_metadata: list[ElementMetadata] = []
        current_elements: list[Any] = []
        current_char_count = 0
        chunk_index = 0

        def flush_chunk():
            nonlocal chunk_index, current_texts, current_metadata, current_elements, current_char_count

            if current_texts:
                text = "\n\n".join(current_texts)
                chunks.append(
                    Chunk(
                        index=chunk_index,
                        text=text,
                        char_count=len(text),
                        metadata=current_metadata.copy(),
                        original_elements=current_elements.copy(),
                        source_file=str(path),
                    )
                )
                chunk_index += 1

            current_texts = []
            current_metadata = []
            current_elements = []
            current_char_count = 0

        for element in self._iter_block_items(document):
            if isinstance(element, Paragraph):
                text = element.text.strip()
                if not text:
                    continue

                text_len = len(text)
                separator_len = 2 if current_texts else 0

                if current_char_count + separator_len + text_len > self.max_chars and current_texts:
                    flush_chunk()
                    separator_len = 0

                current_texts.append(text)
                current_metadata.append(self._extract_paragraph_metadata(element))
                current_elements.append(("paragraph", element._element))
                current_char_count += separator_len + text_len

            elif isinstance(element, Table):
                table_text = self._get_table_text(element)
                full_table_text = f"[ТАБЛИЦА]\n{table_text}\n[/ТАБЛИЦА]"
                table_len = len(full_table_text)
                separator_len = 2 if current_texts else 0

                if table_len > self.max_chars:
                    warnings.warn(
                        f"Таблица ({table_len} символов) превышает max_chars ({self.max_chars}). "
                        "Таблица будет добавлена отдельным чанком."
                    )

                if current_char_count + separator_len + table_len > self.max_chars and current_texts:
                    flush_chunk()
                    separator_len = 0

                current_texts.append(full_table_text)
                current_metadata.append(self._extract_table_metadata(element))
                current_elements.append(("table", element._tbl))
                current_char_count += separator_len + table_len

                if table_len > self.max_chars:
                    flush_chunk()

        flush_chunk()

        return chunks

    def concatenate(
        self,
        translated_chunks: list[TranslatedChunk],
        output_path: str | Path,
    ) -> None:
        """
        Собрать переведённые чанки обратно в документ Word.
        
        Parameters
        ----------
        translated_chunks : list[TranslatedChunk]
            Список переведённых чанков (должны быть отсортированы по index).
        output_path : str or Path
            Путь для сохранения результата (.docx).
        
        Raises
        ------
        ValueError
            Если список чанков пуст.
        
        Examples
        --------
        >>> processor = WordDocumentProcessor()
        >>> chunks = processor.chunk("input.docx")
        >>> translated = translator.translate_batch(chunks, "English")
        >>> processor.concatenate(translated, "output.docx")
        """
        if not translated_chunks:
            raise ValueError("Список переведённых чанков пуст")

        sorted_chunks = sorted(translated_chunks, key=lambda c: c.index)

        source_file = sorted_chunks[0].original.source_file
        if source_file:
            template_doc = self.load(source_file)
        else:
            template_doc = Document()

        new_doc = Document()
        self._copy_styles(template_doc, new_doc)

        for chunk in sorted_chunks:
            translated_lines = chunk.translated_text.split("\n\n")
            line_idx = 0

            for i, (elem_type, _) in enumerate(chunk.original_elements):
                if line_idx >= len(translated_lines):
                    break

                metadata = chunk.metadata[i] if i < len(chunk.metadata) else None

                if elem_type == "paragraph":
                    text = translated_lines[line_idx]
                    line_idx += 1

                    para = new_doc.add_paragraph()

                    if metadata and metadata.style_name:
                        try:
                            para.style = metadata.style_name
                        except KeyError:
                            pass

                    run = para.add_run(text)
                    if metadata:
                        if metadata.bold:
                            run.bold = True
                        if metadata.italic:
                            run.italic = True
                        if metadata.underline:
                            run.underline = True
                        if metadata.font_name:
                            run.font.name = metadata.font_name
                        if metadata.font_size:
                            run.font.size = int(metadata.font_size * 12700)

                elif elem_type == "table":
                    table_text = translated_lines[line_idx]
                    line_idx += 1

                    table_text = table_text.replace("[ТАБЛИЦА]", "").replace("[/ТАБЛИЦА]", "").strip()
                    rows_data = [line.split(" | ") for line in table_text.split("\n") if line.strip()]

                    if rows_data and metadata:
                        num_rows = len(rows_data)
                        num_cols = max(len(row) for row in rows_data) if rows_data else 1

                        table = new_doc.add_table(rows=num_rows, cols=num_cols)
                        table.style = "Table Grid"

                        for row_idx, row_data in enumerate(rows_data):
                            for col_idx, cell_text in enumerate(row_data):
                                if col_idx < num_cols:
                                    table.rows[row_idx].cells[col_idx].text = cell_text.strip()

        self.save(new_doc, output_path)

    def _copy_styles(self, source: DocumentType, target: DocumentType) -> None:
        pass
