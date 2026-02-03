from doc_translator.processors.base import DocumentProcessor
from doc_translator.processors.word import WordDocumentProcessor
from doc_translator.processors.pdf import PDFDocumentProcessor
from doc_translator.processors.pandoc_word import PandocWordProcessor
from doc_translator.processors.mineru_pdf import MinerUPDFProcessor

__all__ = [
    "DocumentProcessor",
    "WordDocumentProcessor",
    "PDFDocumentProcessor",
    "PandocWordProcessor",
    "MinerUPDFProcessor",
]
