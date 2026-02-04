import shutil
import subprocess
from pathlib import Path


def check_pandoc() -> bool:
    return shutil.which("pandoc") is not None


def docx_to_markdown(
    docx_path: str | Path,
    wrap: str = "none",
    extract_media_dir: str | Path | None = None,
) -> str:
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
