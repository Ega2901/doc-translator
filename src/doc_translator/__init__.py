from importlib.metadata import version, PackageNotFoundError

from doc_translator.models.chunk import Chunk, TranslatedChunk
from doc_translator.processors.word import WordDocumentProcessor
from doc_translator.processors.pdf import PDFDocumentProcessor
from doc_translator.processors.pandoc_word import PandocWordProcessor
from doc_translator.processors.mineru_pdf import MinerUPDFProcessor
from doc_translator.translator.ollama import OllamaTranslator

try:
    __version__ = version("doc-translator")
except PackageNotFoundError:
    __version__ = "0.0.0+dev"
__all__ = [
    "Chunk",
    "TranslatedChunk",
    "WordDocumentProcessor",
    "PDFDocumentProcessor",
    "PandocWordProcessor",
    "MinerUPDFProcessor",
    "OllamaTranslator",
]
