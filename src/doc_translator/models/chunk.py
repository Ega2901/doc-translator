from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ElementType(Enum):
    """
    Тип элемента документа.
    
    Attributes
    ----------
    PARAGRAPH : str
        Параграф текста.
    TABLE : str
        Таблица.
    HEADER : str
        Колонтитул (верхний).
    FOOTER : str
        Колонтитул (нижний).
    IMAGE : str
        Изображение.
    """
    PARAGRAPH = "paragraph"
    TABLE = "table"
    HEADER = "header"
    FOOTER = "footer"
    IMAGE = "image"


@dataclass
class ElementMetadata:
    """
    Метаданные элемента документа.
    
    Attributes
    ----------
    element_type : ElementType
        Тип элемента (PARAGRAPH, TABLE и т.д.).
    style_name : str, optional
        Название стиля Word.
    font_name : str, optional
        Название шрифта.
    font_size : float, optional
        Размер шрифта в пунктах.
    bold : bool
        Жирный текст.
    italic : bool
        Курсив.
    underline : bool
        Подчёркнутый текст.
    alignment : str, optional
        Выравнивание (LEFT, CENTER, RIGHT, JUSTIFY).
    rows : int, optional
        Количество строк (для таблиц).
    cols : int, optional
        Количество столбцов (для таблиц).
    extra : dict
        Дополнительные данные.
    """
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
    """
    Часть документа для перевода.
    
    Attributes
    ----------
    index : int
        Порядковый номер чанка в документе (начиная с 0).
    text : str
        Текст для перевода.
    char_count : int
        Количество символов в тексте.
    metadata : list[ElementMetadata]
        Список метаданных для каждого элемента в чанке.
    original_elements : list
        Ссылки на оригинальные элементы документа (для сборки).
    source_file : str, optional
        Путь к исходному файлу.
    
    Examples
    --------
    >>> chunk = chunks[0]
    >>> print(f"Чанк {chunk.index}: {chunk.char_count} символов")
    >>> print(chunk.text[:100])
    """
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
    """
    Переведённый чанк документа.
    
    Attributes
    ----------
    original : Chunk
        Оригинальный чанк.
    translated_text : str
        Переведённый текст.
    target_language : str
        Целевой язык перевода.
    model_used : str, optional
        Модель, использованная для перевода.
    
    Properties
    ----------
    index : int
        Порядковый номер чанка (из оригинала).
    metadata : list[ElementMetadata]
        Метаданные оригинального чанка.
    original_elements : list
        Оригинальные элементы документа.
    
    Examples
    --------
    >>> translated = translator.translate(chunk, "English")
    >>> print(f"Оригинал: {translated.original.text[:50]}...")
    >>> print(f"Перевод: {translated.translated_text[:50]}...")
    """
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
