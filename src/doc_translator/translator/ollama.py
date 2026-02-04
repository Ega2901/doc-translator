import json
import re
import time
import httpx
from typing import Callable

from doc_translator.models.chunk import Chunk, TranslatedChunk

TRANSLATE_MAX_RETRIES = 3
TRANSLATE_RETRY_DELAY = 10


def _strip_thinking_blocks(text: str) -> str:
    if not text.strip():
        return text
    pattern = re.compile(
        r" <think>.*?<\/think>",
        re.DOTALL | re.IGNORECASE,
    )
    cleaned = pattern.sub("", text)
    return cleaned.strip()


def _extract_translation_only(text: str) -> str:
    if not text.strip():
        return text
    s = text.strip()
    for marker in ("TRANSLATION:", "Translation:", "Перевод:", "Перевод :"):
        idx = s.rfind(marker)
        if idx != -1:
            s = s[idx + len(marker) :].strip()
            break
    code_block = re.compile(r"^```\w*\n?(.*?)\n?```\s*$", re.DOTALL)
    m = code_block.match(s)
    if m:
        s = m.group(1).strip()
    s = s.strip().strip('"\'')
    return s.strip()


def _is_table_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if s.startswith("+") or s.startswith("="):
        return True
    if s.startswith("|") and "|" in s:
        return True
    return False


def _remove_blank_lines_inside_tables(text: str) -> str:
    if not text.strip():
        return text
    lines = text.split("\n")
    result: list[str] = []
    for i, line in enumerate(lines):
        if line.strip() == "" and result:
            prev_ok = _is_table_line(result[-1])
            next_ok = (
                i + 1 < len(lines) and _is_table_line(lines[i + 1])
            )
            if prev_ok and next_ok:
                continue
        result.append(line)
    return "\n".join(result)


def _remove_garbage_from_translation(text: str) -> str:
    if not text.strip():
        return text
    lines = text.split("\n")
    cleaned_lines = []
    data_url = re.compile(r"data:[a-zA-Z0-9+/]+/[a-zA-Z0-9+.-]+;base64,[A-Za-z0-9+/=]{50,}")
    noise_line = re.compile(r"^[\sA-Za-z0-9+/=_-]{100,}$")
    for line in lines:
        line = data_url.sub("", line)
        if noise_line.match(line.strip()) and not re.search(r"[а-яА-Яa-zA-Z]{3,}", line):
            continue
        if line.strip() and not re.search(r"[\w\u0400-\u04ff]", line):
            continue
        cleaned_lines.append(line)
    s = "\n".join(cleaned_lines)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


class OllamaTranslator:
    DEFAULT_SYSTEM_PROMPT = """You are a professional translator specializing in clinical and regulatory documents.
Your task is to translate the text accurately while:
- Preserving the exact meaning and terminology
- Maintaining the document structure (paragraphs, lists, tables)
- Keeping any special markers like [ТАБЛИЦА] and [/ТАБЛИЦА] unchanged
- Not adding any explanations or comments
- Translating ONLY the content, nothing else

If you see text formatted as a table (with | separators), preserve that format exactly."""

    MARKDOWN_SYSTEM_PROMPT = """You are a professional translator. The input is a fragment of a document in Markdown format.
Translate ONLY the natural language text to the target language. You MUST:
- Keep all Markdown syntax exactly as in the input: headers (# ## ###), lists (- * 1.), bold/italic (** *), code blocks (```), links, etc.
- Tables: preserve EXACTLY. Both grid tables (lines starting with +, |, or =) and pipe tables (| col | col |). Do not add or remove any border characters, rows, or columns. Do NOT insert blank lines inside a table — tables must have no empty lines between rows. Only translate the text inside cells (after | and >).
- Do not add or remove any structural markup; only translate the visible text content.
- Output valid Markdown with the same structure. Do not add explanations or comments."""

    def __init__(
        self,
        model: str = "translategemma",
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
        system_prompt: str | None = None,
        *,
        use_markdown_prompt: bool = False,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        if system_prompt is not None:
            self.system_prompt = system_prompt
        elif use_markdown_prompt:
            self.system_prompt = self.MARKDOWN_SYSTEM_PROMPT
        else:
            self.system_prompt = self.DEFAULT_SYSTEM_PROMPT
        self._client = httpx.Client(timeout=timeout)

    def _build_prompt(self, text: str, target_language: str) -> str:
        return f"""Translate the following text to {target_language}.

TEXT TO TRANSLATE:
{text}

TRANSLATION:"""

    def translate(
        self,
        chunk: Chunk,
        target_language: str,
        progress_callback: Callable[[str], None] | None = None,
    ) -> TranslatedChunk:
        prompt = self._build_prompt(chunk.text, target_language)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": self.system_prompt,
            "stream": progress_callback is not None,
        }

        url = f"{self.base_url}/api/generate"

        if progress_callback:
            translated_text = self._stream_response(url, payload, progress_callback)
        else:
            translated_text = ""
            for attempt in range(TRANSLATE_MAX_RETRIES):
                try:
                    response = self._client.post(url, json=payload)
                    response.raise_for_status()
                    result = response.json()
                    translated_text = result.get("response", "")
                    break
                except httpx.ReadTimeout:
                    if attempt == TRANSLATE_MAX_RETRIES - 1:
                        raise
                    time.sleep(TRANSLATE_RETRY_DELAY)

        raw = translated_text.strip()
        translated_text = _strip_thinking_blocks(raw)
        translated_text = _extract_translation_only(translated_text)
        translated_text = _remove_garbage_from_translation(translated_text)
        fallback = ""
        if not translated_text or not translated_text.strip():
            fallback = _strip_thinking_blocks(raw)
            fallback = _remove_garbage_from_translation(fallback)
            if fallback.strip():
                translated_text = fallback.strip()
        final_text = (translated_text or "").strip() or (fallback or "").strip() or raw
        final_text = final_text.strip()
        final_text = _remove_blank_lines_inside_tables(final_text)
        if not final_text or "<think>" in final_text or "</think>" in final_text:
            final_text = "[не переведено]\n\n" + chunk.text
        return TranslatedChunk(
            original=chunk,
            translated_text=final_text,
            target_language=target_language,
            model_used=self.model,
        )

    def _stream_response(
        self,
        url: str,
        payload: dict,
        progress_callback: Callable[[str], None],
    ) -> str:
        full_response = []

        with self._client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if "response" in data:
                        chunk_text = data["response"]
                        full_response.append(chunk_text)
                        progress_callback(chunk_text)

        return "".join(full_response)

    def translate_batch(
        self,
        chunks: list[Chunk],
        target_language: str,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[TranslatedChunk]:
        translated: list[TranslatedChunk] = []
        total = len(chunks)

        for i, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(i + 1, total, f"Переводится чанк {i + 1}/{total}...")

            try:
                translated_chunk = self.translate(chunk, target_language)
            except httpx.ReadTimeout:
                translated_chunk = TranslatedChunk(
                    original=chunk,
                    translated_text="[не переведено]\n\n" + chunk.text,
                    target_language=target_language,
                    model_used=self.model,
                )
                if progress_callback:
                    progress_callback(
                        i + 1,
                        total,
                        f"Таймаут на чанке {i + 1}/{total} — помечен как [не переведено], продолжаю...",
                    )
            except httpx.HTTPError as e:
                translated_chunk = TranslatedChunk(
                    original=chunk,
                    translated_text=f"[не переведено: {type(e).__name__}]\n\n" + chunk.text,
                    target_language=target_language,
                    model_used=self.model,
                )
                if progress_callback:
                    progress_callback(
                        i + 1,
                        total,
                        f"Ошибка {type(e).__name__} на чанке {i + 1}/{total} — помечен как [не переведено], продолжаю...",
                    )
            translated.append(translated_chunk)

            if progress_callback:
                progress_callback(i + 1, total, f"Чанк {i + 1}/{total} переведён")

        return translated

    def check_connection(self) -> bool:
        try:
            response = self._client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def list_models(self) -> list[str]:
        try:
            response = self._client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except httpx.HTTPError:
            return []

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "OllamaTranslator":
        return self

    def __exit__(self, *args) -> None:
        self.close()
