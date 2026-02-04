def _is_table_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if s.startswith("+") or s.startswith("=") or (s.startswith("|") and "|" in s[1:]):
        return True
    if s.startswith("|"):
        return True
    return False


def split_markdown_into_blocks(markdown: str) -> list[str]:
    if not markdown.strip():
        return []
    lines = markdown.split("\n")
    blocks = []
    current: list[str] = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if stripped == "":
            if current:
                if not in_table:
                    blocks.append("\n".join(current))
                    current = []
                    in_table = False
        else:
            line_is_table = _is_table_line(line)
            if line_is_table:
                in_table = True
                current.append(line)
            else:
                if current and in_table:
                    blocks.append("\n".join(current))
                    current = []
                in_table = False
                current.append(line)
    if current:
        blocks.append("\n".join(current))

    merged: list[str] = []
    for block in blocks:
        block_lines = block.split("\n")
        first_line = (block_lines[0].strip() if block_lines else "")
        if merged and _is_table_line(first_line):
            prev = merged[-1]
            if _is_table_line((prev.split("\n")[0] or "").strip()):
                merged[-1] = prev + "\n" + block
                continue
        merged.append(block)
    return merged


def chunk_blocks(blocks: list[str], max_chars: int) -> list[list[str]]:
    if not blocks:
        return []
    chunks: list[list[str]] = []
    current: list[str] = []
    current_len = 0
    sep_len = 2

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
