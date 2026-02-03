"""
Общие утилиты для разбиения Markdown на блоки и чанки.

Используются процессорами Pandoc (docx) и MinerU (PDF) для единообразного
разбиения извлечённого Markdown перед передачей в модель.
"""


def split_markdown_into_blocks(markdown: str) -> list[str]:
    """
    Разбить Markdown на блоки по пустым строкам (двойной перевод строки).

    Сохраняет многострочные блоки (таблицы, код) как один блок.
    """
    if not markdown.strip():
        return []
    blocks = []
    current: list[str] = []
    for line in markdown.split("\n"):
        if line.strip() == "":
            if current:
                blocks.append("\n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    return blocks


def chunk_blocks(blocks: list[str], max_chars: int) -> list[list[str]]:
    """Сгруппировать блоки в чанки, не превышающие max_chars."""
    if not blocks:
        return []
    chunks: list[list[str]] = []
    current: list[str] = []
    current_len = 0
    sep_len = 2  # "\n\n"

    for block in blocks:
        block_len = len(block) + (sep_len if current else 0)
        if current_len + block_len > max_chars and current:
            chunks.append(current)
            current = []
            current_len = 0
            block_len = len(block)
        current.append(block)
        current_len += block_len

    if current:
        chunks.append(current)
    return chunks
