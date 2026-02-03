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
- (опционально) [Pandoc](https://pandoc.org/installing.html) — для режима **Pandoc** (docx) и для сборки docx при режиме **MinerU** (PDF)
- (опционально) [MinerU](https://opendatalab.github.io/MinerU/) — для режима **MinerU**: корректное извлечение PDF в Markdown (структура, таблицы, формулы, OCR)

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

# Режим Pandoc: docx → Markdown → модель → docx со стилями исходного документа
doc-translator translate document.docx -o translated.docx -l English --pandoc

# Режим MinerU: PDF → Markdown (корректное извлечение) → модель → docx
doc-translator translate document.pdf -o translated.docx -l English --mineru
```

### Python API

```python
from doc_translator import (
    WordDocumentProcessor,
    PandocWordProcessor,
    MinerUPDFProcessor,
    OllamaTranslator,
)

# Обычный режим (python-docx)
processor = WordDocumentProcessor(max_chars=4000)
translator = OllamaTranslator(model="llama3.2")

# Режим Pandoc: строгий Markdown для модели, docx со стилями исходного документа
# processor = PandocWordProcessor(max_chars=4000)
# translator = OllamaTranslator(model="llama3.2", use_markdown_prompt=True)

# Режим MinerU: PDF → Markdown (корректное извлечение) → модель → docx
# processor = MinerUPDFProcessor(max_chars=4000)
# translator = OllamaTranslator(model="llama3.2", use_markdown_prompt=True)

# Разбиение на чанки
chunks = processor.chunk("document.docx")  # или "document.pdf"
print(f"Создано {len(chunks)} чанков")

# Перевод
translated = translator.translate_batch(chunks, "English")

# Сборка результата
processor.concatenate(translated, "translated.docx")
```

## Режим Pandoc (строгий формат)

С флагом `--pandoc` документ обрабатывается через [Pandoc](https://pandoc.org/):

1. **docx → Markdown** — в модель уходит строгая разметка (заголовки `#`, таблицы `|---|`, списки).
2. Модель переводит только текст, сохраняя Markdown-синтаксис (промпт `use_markdown_prompt`).
3. **Markdown → docx** — Pandoc собирает docx с `--reference-doc=исходный.docx`, сохраняя стили и форматирование исходного документа.

Так данные в модель и обратно идут в одном строгом формате, что уменьшает потери структуры и форматирования.

## Режим MinerU (PDF)

С флагом `--mineru` PDF обрабатывается через [MinerU](https://opendatalab.github.io/MinerU/):

1. **PDF → Markdown** — MinerU извлекает содержимое с сохранением структуры (заголовки, таблицы, формулы, списки, OCR для сканов).
2. Модель переводит только текст, сохраняя Markdown-синтаксис (тот же промпт `use_markdown_prompt`).
3. **Markdown → docx** — Pandoc собирает docx из переведённого Markdown.

Установка MinerU: `pip install "mineru[all]"` (или `mineru[pipeline]` для CPU). Для сборки docx нужен также Pandoc.

## Архитектура

```
doc_translator/
├── src/doc_translator/
│   ├── models/
│   │   └── chunk.py         # Модели данных (Chunk, TranslatedChunk)
│   ├── processors/
│   │   ├── base.py          # Абстрактный класс DocumentProcessor
│   │   ├── word.py          # WordDocumentProcessor (python-docx)
│   │   ├── pandoc_word.py   # PandocWordProcessor (docx↔Markdown)
│   │   ├── pandoc_utils.py  # Вызовы Pandoc
│   │   ├── mineru_pdf.py    # MinerUPDFProcessor (PDF→Markdown через MinerU)
│   │   ├── mineru_utils.py  # Вызовы MinerU CLI
│   │   ├── markdown_utils.py # Разбиение Markdown на блоки/чанки
│   │   └── pdf.py           # PDFDocumentProcessor (pdf2docx)
│   ├── translator/
│   │   └── ollama.py        # OllamaTranslator
│   └── cli.py               # CLI интерфейс
└── examples/                # Примеры документов
```

## Ограничения

- **Таблицы**: Не разбиваются — идут целиком в один чанк
- **PDF**: Конвертируется в DOCX, результат сохраняется как DOCX
- **Изображения**: Сохраняются на месте, но не переводятся
- **Pandoc**: Требуется установленный Pandoc; для docx→docx со стилями используется `--reference-doc`
- **MinerU**: Тяжёлые зависимости (модели); по умолчанию используется бэкенд `pipeline` (CPU). Для сборки docx из PDF в режиме MinerU нужен Pandoc

## Лицензия

MIT
