import argparse
import sys
from pathlib import Path

from doc_translator.processors.word import WordDocumentProcessor
from doc_translator.processors.pdf import PDFDocumentProcessor
from doc_translator.translator.ollama import OllamaTranslator


def get_processor(file_path: Path):
    suffix = file_path.suffix.lower()

    if suffix == ".docx":
        return WordDocumentProcessor()
    elif suffix == ".pdf":
        return PDFDocumentProcessor()
    else:
        raise ValueError(f"Неподдерживаемый формат файла: {suffix}")


def cmd_chunk(args: argparse.Namespace) -> int:
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Ошибка: файл не найден: {input_path}", file=sys.stderr)
        return 1

    processor = get_processor(input_path)
    processor.max_chars = args.max_chars

    print(f"Разбиваем документ: {input_path}")
    print(f"Максимум символов на чанк: {args.max_chars}")

    chunks = processor.chunk(input_path)

    print(f"\nСоздано чанков: {len(chunks)}")
    print("-" * 50)

    output_dir = Path(args.output) if args.output else input_path.parent / "chunks"
    output_dir.mkdir(parents=True, exist_ok=True)

    for chunk in chunks:
        chunk_file = output_dir / f"chunk_{chunk.index:03d}.txt"
        with open(chunk_file, "w", encoding="utf-8") as f:
            f.write(chunk.text)

        print(f"  Чанк {chunk.index}: {chunk.char_count} символов -> {chunk_file.name}")

    print("-" * 50)
    print(f"Чанки сохранены в: {output_dir}")

    return 0


def cmd_translate(args: argparse.Namespace) -> int:
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Ошибка: файл не найден: {input_path}", file=sys.stderr)
        return 1

    translator = OllamaTranslator(
        model=args.model,
        base_url=args.ollama_url,
    )

    if not translator.check_connection():
        print(
            f"Ошибка: не удалось подключиться к Ollama ({args.ollama_url})",
            file=sys.stderr,
        )
        print("Убедитесь, что Ollama запущен: ollama serve", file=sys.stderr)
        return 1

    available_models = translator.list_models()
    if args.model not in available_models:
        print(f"Предупреждение: модель '{args.model}' не найдена в списке доступных")
        print(f"Доступные модели: {', '.join(available_models) or 'нет моделей'}")
        if not args.force:
            print("Используйте --force чтобы продолжить")
            return 1

    processor = get_processor(input_path)
    processor.max_chars = args.max_chars

    print(f"Документ: {input_path}")
    print(f"Целевой язык: {args.language}")
    print(f"Модель: {args.model}")
    print(f"Максимум символов на чанк: {args.max_chars}")
    print("-" * 50)

    print("Разбиваем документ на чанки...")
    chunks = processor.chunk(input_path)
    print(f"Создано чанков: {len(chunks)}")

    print("\nПеревод...")

    def progress_callback(current: int, total: int, status: str):
        print(f"  [{current}/{total}] {status}")

    translated_chunks = translator.translate_batch(
        chunks,
        args.language,
        progress_callback=progress_callback,
    )

    output_path = Path(args.output) if args.output else input_path.with_stem(
        f"{input_path.stem}_translated_{args.language}"
    )

    print(f"\nСобираем документ...")
    processor.concatenate(translated_chunks, output_path)

    print("-" * 50)
    print(f"Готово! Результат сохранён: {output_path}")

    translator.close()
    return 0


def cmd_models(args: argparse.Namespace) -> int:
    translator = OllamaTranslator(base_url=args.ollama_url)

    if not translator.check_connection():
        print(
            f"Ошибка: не удалось подключиться к Ollama ({args.ollama_url})",
            file=sys.stderr,
        )
        return 1

    models = translator.list_models()

    if models:
        print("Доступные модели Ollama:")
        for model in models:
            print(f"  - {model}")
    else:
        print("Модели не найдены. Установите модель: ollama pull llama3.2")

    translator.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="doc-translator",
        description="Инструмент для перевода документов с использованием локальной LLM",
    )

    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="URL сервера Ollama (по умолчанию: http://localhost:11434)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Доступные команды")

    chunk_parser = subparsers.add_parser("chunk", help="Разбить документ на чанки (без перевода)")
    chunk_parser.add_argument("input", help="Путь к входному документу (.docx или .pdf)")
    chunk_parser.add_argument("-o", "--output", help="Директория для сохранения чанков")
    chunk_parser.add_argument(
        "--max-chars",
        type=int,
        default=4000,
        help="Максимум символов на чанк (по умолчанию: 4000)",
    )

    translate_parser = subparsers.add_parser("translate", help="Перевести документ")
    translate_parser.add_argument("input", help="Путь к входному документу (.docx или .pdf)")
    translate_parser.add_argument("-o", "--output", help="Путь для сохранения результата")
    translate_parser.add_argument(
        "-l", "--language",
        default="English",
        help="Целевой язык (по умолчанию: English)",
    )
    translate_parser.add_argument(
        "-m", "--model",
        default="llama3.2",
        help="Модель Ollama для перевода (по умолчанию: llama3.2)",
    )
    translate_parser.add_argument(
        "--max-chars",
        type=int,
        default=4000,
        help="Максимум символов на чанк (по умолчанию: 4000)",
    )
    translate_parser.add_argument(
        "--force",
        action="store_true",
        help="Продолжить даже если модель не найдена",
    )

    subparsers.add_parser("models", help="Показать доступные модели Ollama")

    args = parser.parse_args()

    if args.command == "chunk":
        return cmd_chunk(args)
    elif args.command == "translate":
        return cmd_translate(args)
    elif args.command == "models":
        return cmd_models(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
