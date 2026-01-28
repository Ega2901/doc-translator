# Document Translator

Инструмент для разбиения и перевода клинических/регуляторных документов с использованием локальной LLM (Ollama).

## Особенности

- Разбиение документов Word (.docx) и PDF на части для перевода
- Сохранение форматирования (стили, таблицы)
- Перевод через локальную LLM (Ollama) — данные не передаются в облако
- Сборка переведённых частей обратно в единый документ

## Установка

```bash
# Клонировать репозиторий
git clone <repo-url>
cd doc_translator

# Установить с помощью uv
uv sync

# Или pip
pip install -e .
```

## Требования

- Python 3.13+
- [Ollama](https://ollama.ai/) для локального запуска LLM

### Установка Ollama

```bash
# macOS
brew install ollama

# Запуск сервера
ollama serve

# Скачать модель (например, llama3.2)
ollama pull llama3.2
```

## Использование

### CLI

```bash
# Показать доступные модели Ollama
doc-translator models

# Разбить документ на чанки (без перевода)
doc-translator chunk document.docx -o ./chunks/

# Перевести документ на английский
doc-translator translate document.docx -l English -m llama3.2

# Перевести с указанием выходного файла
doc-translator translate document.docx -o translated.docx -l English
```

### Python API

```python
from doc_translator import WordDocumentProcessor, OllamaTranslator

# Инициализация
processor = WordDocumentProcessor(max_chars=4000)
translator = OllamaTranslator(model="llama3.2")

# Разбиение на чанки
chunks = processor.chunk("document.docx")
print(f"Создано {len(chunks)} чанков")

# Перевод
translated = translator.translate_batch(chunks, "English")

# Сборка результата
processor.concatenate(translated, "translated.docx")
```

## Архитектура

```
doc_translator/
├── src/doc_translator/
│   ├── models/
│   │   └── chunk.py         # Модели данных (Chunk, TranslatedChunk)
│   ├── processors/
│   │   ├── base.py          # Абстрактный класс DocumentProcessor
│   │   ├── word.py          # WordDocumentProcessor
│   │   └── pdf.py           # PDFDocumentProcessor
│   ├── translator/
│   │   └── ollama.py        # OllamaTranslator
│   └── cli.py               # CLI интерфейс
└── examples/                # Примеры документов
```

## Ограничения

- **Таблицы**: Не разбиваются — идут целиком в один чанк
- **PDF**: Конвертируется в DOCX, результат сохраняется как DOCX
- **Изображения**: Сохраняются на месте, но не переводятся

## Лицензия

MIT
