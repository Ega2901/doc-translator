"""
Утилиты для вызова Pandoc: конвертация docx ↔ markdown с сохранением структуры.

Требуется установленный Pandoc: https://pandoc.org/installing.html
"""

import shutil
import subprocess
from pathlib import Path


def check_pandoc() -> bool:
    """Проверить, доступен ли pandoc в PATH."""
    return shutil.which("pandoc") is not None


def docx_to_markdown(
    docx_path: str | Path,
    wrap: str = "none",
    extract_media_dir: str | Path | None = None,
) -> str:
    """
    Конвертировать DOCX в Markdown (строгий формат для передачи в модель).

    Parameters
    ----------
    docx_path : str or Path
        Путь к .docx файлу.
    wrap : str
        Режим переноса строк для pandoc: "none", "auto", "preserve".
    extract_media_dir : str or Path, optional
        Директория для извлечения изображений из документа.

    Returns
    -------
    str
        Содержимое документа в формате Markdown.

    Raises
    ------
    FileNotFoundError
        Если pandoc не найден в PATH.
    RuntimeError
        Если конвертация завершилась с ошибкой.
    """
    if not check_pandoc():
        raise FileNotFoundError(
            "Pandoc не найден. Установите: https://pandoc.org/installing.html"
        )

    docx_path = Path(docx_path).resolve()
    if not docx_path.exists():
        raise FileNotFoundError(f"Файл не найден: {docx_path}")

    cmd = [
        "pandoc",
        "-f", "docx",
        "-t", "markdown",
        "--wrap", wrap,
    ]
    if extract_media_dir:
        out_dir = Path(extract_media_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd.append(f"--extract-media={out_dir}")
    cmd.append(str(docx_path))

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Pandoc docx→markdown failed: {result.stderr or result.stdout}"
        )
    return result.stdout


def markdown_to_docx(
    markdown_content: str,
    output_path: str | Path,
    reference_docx: str | Path | None = None,
) -> None:
    """
    Конвертировать Markdown в DOCX, опционально сохраняя стили из reference.docx.

    Parameters
    ----------
    markdown_content : str
        Исходный текст в формате Markdown.
    output_path : str or Path
        Путь для сохранения .docx.
    reference_docx : str or Path, optional
        Референсный .docx для копирования стилей (как у исходного документа).

    Raises
    ------
    FileNotFoundError
        Если pandoc не найден в PATH.
    RuntimeError
        Если конвертация завершилась с ошибкой.
    """
    if not check_pandoc():
        raise FileNotFoundError(
            "Pandoc не найден. Установите: https://pandoc.org/installing.html"
        )

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "pandoc",
        "-f", "markdown",
        "-t", "docx",
        "-o", str(output_path),
    ]
    if reference_docx:
        ref = Path(reference_docx).resolve()
        if ref.exists():
            cmd.extend(["--reference-doc", str(ref)])

    result = subprocess.run(
        cmd,
        input=markdown_content,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Pandoc markdown→docx failed: {result.stderr or result.stdout}"
        )
