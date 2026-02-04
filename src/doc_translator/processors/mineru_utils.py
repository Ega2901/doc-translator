import shutil
import subprocess
import tempfile
from pathlib import Path


def check_mineru() -> bool:
    return shutil.which("mineru") is not None


def pdf_to_markdown(
    pdf_path: str | Path,
    backend: str = "pipeline",
    timeout: int = 600,
) -> str:
    if not check_mineru():
        raise FileNotFoundError(
            "MinerU не найден. Установите: pip install \"mineru[all]\" или см. https://opendatalab.github.io/MinerU/"
        )

    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"Файл не найден: {pdf_path}")

    with tempfile.TemporaryDirectory(prefix="doc_translator_mineru_") as tmpdir:
        out_dir = Path(tmpdir) / "out"
        out_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "mineru",
            "-p", str(pdf_path),
            "-o", str(out_dir),
            "-b", backend,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(out_dir),
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"MinerU завершился с ошибкой (код {result.returncode}): "
                f"{result.stderr or result.stdout}"
            )

        md_files = list(Path(out_dir).rglob("*.md"))
        stem = pdf_path.stem
        main_md = None
        for f in md_files:
            if f.stem == stem and f.name.endswith(".md"):
                main_md = f
                break
        if not main_md and md_files:
            main_md = md_files[0]
        if not main_md:
            raise RuntimeError(
                f"MinerU не создал Markdown в {out_dir}. Проверьте вывод: {result.stdout}"
            )
        return main_md.read_text(encoding="utf-8")
