import json
import re
import httpx
from typing import Callable

from doc_translator.models.chunk import Chunk, TranslatedChunk


def _strip_thinking_blocks(text: str) -> str:
    """
    Удалить из ответа модели блоки рассуждений (think-теги).
    Некоторые модели (например DeepSeek R1) могут вставлять «мысли» в ответ;
    для перевода нужен только итоговый текст.
    """
    if not text.strip():
        return text
    # Удаляем блоки think (рассуждения модели)
    pattern = re.compile(
        r" <think>.*?<\/think>",
        re.DOTALL | re.IGNORECASE,
    )
    cleaned = pattern.sub("", text)
    return cleaned.strip()


class OllamaTranslator:
    """
    Переводчик документов с использованием локальной LLM через Ollama.
    
    Parameters
    ----------
    model : str, default="llama3.2"
        Название модели Ollama (например, "llama3.2", "mistral", "qwen2.5").
    base_url : str, default="http://localhost:11434"
        URL сервера Ollama.
    timeout : float, default=120.0
        Таймаут запроса в секундах.
    system_prompt : str, optional
        Системный промпт для модели. Если не указан, используется стандартный.
    
    Notes
    -----
    Ollama должен быть запущен локально: `ollama serve`
    
    Examples
    --------
    >>> translator = OllamaTranslator(model="llama3.2")
    >>> if translator.check_connection():
    ...     chunks = processor.chunk("document.docx")
    ...     translated = translator.translate_batch(chunks, "English")
    
    >>> # Использование как context manager
    >>> with OllamaTranslator() as translator:
    ...     result = translator.translate(chunk, "English")
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are a professional translator specializing in clinical and regulatory documents.
Your task is to translate the text accurately while:
- Preserving the exact meaning and terminology
- Maintaining the document structure (paragraphs, lists, tables)
- Keeping any special markers like [ТАБЛИЦА] and [/ТАБЛИЦА] unchanged
- Not adding any explanations or comments
- Translating ONLY the content, nothing else

If you see text formatted as a table (with | separators), preserve that format exactly."""

    # Промпт для формата Markdown (Pandoc): модель должна сохранять разметку 1:1
    MARKDOWN_SYSTEM_PROMPT = """You are a professional translator. The input is a fragment of a document in Markdown format.
Translate ONLY the natural language text to the target language. You MUST:
- Keep all Markdown syntax exactly as in the input: headers (# ## ###), tables (| ... |), lists (- * 1.), bold/italic (** *), code blocks (```), links, etc.
- Do not add or remove any structural markup; only translate the visible text content.
- Output valid Markdown with the same structure. Do not add explanations or comments."""

    def __init__(
        self,
        model: str = "llama3.2",
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
        """
        Перевести один чанк.
        
        Parameters
        ----------
        chunk : Chunk
            Чанк для перевода.
        target_language : str
            Целевой язык (например, "English", "Russian", "German").
        progress_callback : callable, optional
            Функция для отображения прогресса стриминга.
            Принимает str — часть ответа модели.
        
        Returns
        -------
        TranslatedChunk
            Переведённый чанк с оригиналом и переводом.
        
        Examples
        --------
        >>> chunk = chunks[0]
        >>> translated = translator.translate(chunk, "English")
        >>> print(translated.translated_text)
        """
        prompt = self._build_prompt(chunk.text, target_language)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": self.system_prompt,
            "stream": progress_callback is not None,
            "think": False,  # только итоговый ответ, без блоков рассуждений (DeepSeek R1 и др.)
        }

        url = f"{self.base_url}/api/generate"

        if progress_callback:
            translated_text = self._stream_response(url, payload, progress_callback)
        else:
            response = self._client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            translated_text = result.get("response", "")

        translated_text = _strip_thinking_blocks(translated_text.strip())

        return TranslatedChunk(
            original=chunk,
            translated_text=translated_text,
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
        """
        Перевести список чанков.
        
        Parameters
        ----------
        chunks : list[Chunk]
            Список чанков для перевода.
        target_language : str
            Целевой язык (например, "English", "Russian").
        progress_callback : callable, optional
            Функция прогресса. Принимает (current: int, total: int, status: str).
        
        Returns
        -------
        list[TranslatedChunk]
            Список переведённых чанков в том же порядке.
        
        Examples
        --------
        >>> def on_progress(current, total, status):
        ...     print(f"[{current}/{total}] {status}")
        >>> 
        >>> translated = translator.translate_batch(
        ...     chunks, 
        ...     "English",
        ...     progress_callback=on_progress
        ... )
        """
        translated = []
        total = len(chunks)

        for i, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(i + 1, total, f"Переводится чанк {i + 1}/{total}...")

            translated_chunk = self.translate(chunk, target_language)
            translated.append(translated_chunk)

            if progress_callback:
                progress_callback(i + 1, total, f"Чанк {i + 1}/{total} переведён")

        return translated

    def check_connection(self) -> bool:
        """
        Проверить соединение с Ollama.
        
        Returns
        -------
        bool
            True если сервер доступен, False иначе.
        
        Examples
        --------
        >>> translator = OllamaTranslator()
        >>> if not translator.check_connection():
        ...     print("Запустите Ollama: ollama serve")
        """
        try:
            response = self._client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def list_models(self) -> list[str]:
        """
        Получить список доступных моделей.
        
        Returns
        -------
        list[str]
            Список названий моделей. Пустой список если ошибка.
        
        Examples
        --------
        >>> models = translator.list_models()
        >>> print(models)
        ['llama3.2:latest', 'mistral:latest']
        """
        try:
            response = self._client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except httpx.HTTPError:
            return []

    def close(self) -> None:
        """Закрыть HTTP клиент."""
        self._client.close()

    def __enter__(self) -> "OllamaTranslator":
        return self

    def __exit__(self, *args) -> None:
        self.close()
