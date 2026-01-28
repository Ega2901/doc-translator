import tempfile
import warnings
from pathlib import Path
from typing import Any

from doc_translator.models.chunk import Chunk, TranslatedChunk
from doc_translator.processors.base import DocumentProcessor
from doc_translator.processors.word import WordDocumentProcessor


class PDFDocumentProcessor(DocumentProcessor):
    """
    Процессор для PDF документов.
    
    Конвертирует PDF в DOCX, обрабатывает как Word документ,
    сохраняет результат как DOCX.
    
    Parameters
    ----------
    max_chars : int, default=4000
        Максимальное количество символов в одном чанке.
    
    Notes
    -----
    Для конвертации используется библиотека pdf2docx.
    Результат всегда сохраняется как DOCX (редактирование PDF не поддерживается).
    
    Examples
    --------
    >>> processor = PDFDocumentProcessor(max_chars=3000)
    >>> chunks = processor.chunk("document.pdf")
    >>> # После перевода результат сохраняется как .docx
    >>> processor.concatenate(translated_chunks, "output.docx")
    """
    
    def __init__(self, max_chars: int = 4000) -> None:
        super().__init__(max_chars)
        self._word_processor = WordDocumentProcessor(max_chars)
        self._temp_docx_path: Path | None = None

    def get_supported_extensions(self) -> list[str]:
        """
        Получить список поддерживаемых расширений.
        
        Returns
        -------
        list[str]
            Возвращает ['.pdf'].
        """
        return [".pdf"]

    def load(self, path: str | Path) -> Any:
        """
        Загрузить PDF документ (конвертировать в DOCX).
        
        Parameters
        ----------
        path : str or Path
            Путь к PDF файлу.
        
        Returns
        -------
        Path
            Путь к временному DOCX файлу.
        
        Raises
        ------
        ImportError
            Если библиотека pdf2docx не установлена.
        """
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
        """
        Сохранить документ.
        
        Parameters
        ----------
        document : Any
            Путь к DOCX файлу или объект Document.
        path : str or Path
            Путь для сохранения.
        
        Warnings
        --------
        Если указан путь с расширением .pdf, файл будет сохранён как .docx.
        """
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
        """
        Разбить PDF документ на чанки.
        
        Parameters
        ----------
        path : str or Path
            Путь к PDF файлу.
        
        Returns
        -------
        list[Chunk]
            Список чанков с текстом и метаданными.
        
        Notes
        -----
        PDF конвертируется в DOCX, затем используется WordDocumentProcessor.
        
        Examples
        --------
        >>> processor = PDFDocumentProcessor()
        >>> chunks = processor.chunk("document.pdf")
        >>> print(f"Создано {len(chunks)} чанков")
        """
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
        """
        Собрать переведённые чанки в документ.
        
        Parameters
        ----------
        translated_chunks : list[TranslatedChunk]
            Список переведённых чанков.
        output_path : str or Path
            Путь для сохранения результата.
        
        Warnings
        --------
        Результат всегда сохраняется как DOCX. Если указан путь .pdf,
        расширение будет автоматически заменено на .docx.
        
        Examples
        --------
        >>> processor = PDFDocumentProcessor()
        >>> chunks = processor.chunk("input.pdf")
        >>> translated = translator.translate_batch(chunks, "English")
        >>> processor.concatenate(translated, "output.docx")
        """
        output_path = Path(output_path)

        if output_path.suffix.lower() == ".pdf":
            output_path = output_path.with_suffix(".docx")
            warnings.warn(f"Результат сохраняется как DOCX (не PDF): {output_path}")

        self._word_processor.concatenate(translated_chunks, output_path)

    def cleanup(self) -> None:
        """
        Удалить временные файлы.
        
        Вызывается автоматически при удалении объекта.
        """
        import shutil

        if self._temp_docx_path and self._temp_docx_path.parent.exists():
            shutil.rmtree(self._temp_docx_path.parent, ignore_errors=True)
            self._temp_docx_path = None

    def __del__(self) -> None:
        self.cleanup()
