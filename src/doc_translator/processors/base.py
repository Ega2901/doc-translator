from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from doc_translator.models.chunk import Chunk, TranslatedChunk


class DocumentProcessor(ABC):
    """
    Абстрактный базовый класс для обработки документов.
    
    Определяет интерфейс для разбиения документа на части (chunk)
    и сборки переведённых частей обратно в документ (concatenate).
    
    Parameters
    ----------
    max_chars : int, default=4000
        Максимальное количество символов в одном чанке.
    
    Examples
    --------
    >>> from doc_translator import WordDocumentProcessor
    >>> processor = WordDocumentProcessor(max_chars=2000)
    >>> chunks = processor.chunk("document.docx")
    """
    
    def __init__(self, max_chars: int = 4000) -> None:
        self.max_chars = max_chars

    @abstractmethod
    def load(self, path: str | Path) -> Any:
        """
        Загрузить документ из файла.
        
        Parameters
        ----------
        path : str or Path
            Путь к файлу документа.
        
        Returns
        -------
        Any
            Объект документа (зависит от типа процессора).
        """
        pass

    @abstractmethod
    def save(self, document: Any, path: str | Path) -> None:
        """
        Сохранить документ в файл.
        
        Parameters
        ----------
        document : Any
            Объект документа для сохранения.
        path : str or Path
            Путь для сохранения файла.
        """
        pass

    @abstractmethod
    def chunk(self, path: str | Path) -> list[Chunk]:
        """
        Разбить документ на части для перевода.
        
        Parameters
        ----------
        path : str or Path
            Путь к файлу документа.
        
        Returns
        -------
        list[Chunk]
            Список чанков документа.
        
        Notes
        -----
        - Каждая часть не превышает max_chars символов
        - Таблицы не разрываются (идут целиком)
        - Сохраняются метаданные о форматировании
        """
        pass

    @abstractmethod
    def concatenate(
        self,
        translated_chunks: list[TranslatedChunk],
        output_path: str | Path,
    ) -> None:
        """
        Собрать переведённые части обратно в документ.
        
        Parameters
        ----------
        translated_chunks : list[TranslatedChunk]
            Список переведённых чанков.
        output_path : str or Path
            Путь для сохранения результата.
        """
        pass

    def get_supported_extensions(self) -> list[str]:
        """
        Получить список поддерживаемых расширений файлов.
        
        Returns
        -------
        list[str]
            Список расширений (например, ['.docx']).
        """
        return []

    def can_process(self, path: str | Path) -> bool:
        """
        Проверить, может ли процессор обработать данный файл.
        
        Parameters
        ----------
        path : str or Path
            Путь к файлу.
        
        Returns
        -------
        bool
            True если файл поддерживается, False иначе.
        """
        path = Path(path)
        return path.suffix.lower() in self.get_supported_extensions()
