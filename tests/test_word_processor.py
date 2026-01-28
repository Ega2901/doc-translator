"""Тесты для WordDocumentProcessor."""

import tempfile
from pathlib import Path

import pytest

from doc_translator.processors.word import WordDocumentProcessor
from doc_translator.models.chunk import Chunk, TranslatedChunk, ElementType


# Путь к тестовому документу
TEST_DOC = Path(__file__).parent.parent / "examples" / "3. PSR-L08-0623_Протокол_1.0 от 10.06.2024_clean.docx"


class TestWordDocumentProcessor:
    """Тесты для WordDocumentProcessor."""

    def test_get_supported_extensions(self):
        """Проверяем список поддерживаемых расширений."""
        processor = WordDocumentProcessor()
        assert processor.get_supported_extensions() == [".docx"]

    def test_can_process_docx(self):
        """Проверяем, что .docx файлы распознаются."""
        processor = WordDocumentProcessor()
        assert processor.can_process("document.docx") is True
        assert processor.can_process("document.pdf") is False
        assert processor.can_process("document.txt") is False

    @pytest.mark.skipif(not TEST_DOC.exists(), reason="Тестовый документ не найден")
    def test_chunk_creates_chunks(self):
        """Проверяем, что chunk() создаёт чанки."""
        processor = WordDocumentProcessor(max_chars=4000)
        chunks = processor.chunk(TEST_DOC)

        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)

    @pytest.mark.skipif(not TEST_DOC.exists(), reason="Тестовый документ не найден")
    def test_chunk_respects_max_chars(self):
        """Проверяем, что большинство чанков не превышают max_chars."""
        processor = WordDocumentProcessor(max_chars=2000)
        chunks = processor.chunk(TEST_DOC)

        # Считаем чанки, которые превышают лимит (это могут быть только таблицы)
        oversized = [c for c in chunks if c.char_count > 2000]

        # Проверяем, что превышающие лимит — это таблицы
        for chunk in oversized:
            assert "[ТАБЛИЦА]" in chunk.text, f"Чанк {chunk.index} превышает лимит без таблицы"

    @pytest.mark.skipif(not TEST_DOC.exists(), reason="Тестовый документ не найден")
    def test_chunk_has_metadata(self):
        """Проверяем, что чанки содержат метаданные."""
        processor = WordDocumentProcessor(max_chars=4000)
        chunks = processor.chunk(TEST_DOC)

        for chunk in chunks[:5]:  # Проверяем первые 5
            assert chunk.metadata is not None
            assert len(chunk.metadata) > 0

    @pytest.mark.skipif(not TEST_DOC.exists(), reason="Тестовый документ не найден")
    def test_chunk_indices_are_sequential(self):
        """Проверяем, что индексы чанков последовательны."""
        processor = WordDocumentProcessor(max_chars=4000)
        chunks = processor.chunk(TEST_DOC)

        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    @pytest.mark.skipif(not TEST_DOC.exists(), reason="Тестовый документ не найден")
    def test_concatenate_creates_document(self):
        """Проверяем, что concatenate() создаёт документ."""
        processor = WordDocumentProcessor(max_chars=4000)
        chunks = processor.chunk(TEST_DOC)

        # Создаём "переведённые" чанки (просто копируем текст)
        translated = [
            TranslatedChunk(
                original=chunk,
                translated_text=chunk.text,  # Без реального перевода
                target_language="English",
                model_used="test",
            )
            for chunk in chunks[:3]  # Берём только первые 3 для скорости
        ]

        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            output_path = Path(f.name)

        try:
            processor.concatenate(translated, output_path)
            assert output_path.exists()
            assert output_path.stat().st_size > 0
        finally:
            output_path.unlink(missing_ok=True)


class TestChunkModel:
    """Тесты для модели Chunk."""

    def test_chunk_auto_calculates_char_count(self):
        """Проверяем автоматический расчёт char_count."""
        chunk = Chunk(index=0, text="Hello World", char_count=0)
        assert chunk.char_count == 11

    def test_translated_chunk_properties(self):
        """Проверяем свойства TranslatedChunk."""
        original = Chunk(index=5, text="Test", char_count=4)
        translated = TranslatedChunk(
            original=original,
            translated_text="Тест",
            target_language="Russian",
        )

        assert translated.index == 5
        assert translated.original.text == "Test"
        assert translated.translated_text == "Тест"
