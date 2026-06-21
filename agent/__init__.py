"""Document Editing & Formatting Agent package."""

from agent.document_types import DocumentType, get_spec, detect_document_type
from agent.document_processor import (
    Document,
    Section,
    ImagePlaceholder,
    OutputFormat,
    read_document,
    write_document,
    parse_markdown_to_document,
    parse_text_to_document,
    apply_type_formatting,
    suggest_missing_sections,
    insert_image_placeholder,
)
from agent.format_converter import load_document, convert_document, convert_text
from agent.agent import DocumentAgent, AgentConfig, AgentResult

__all__ = [
    "DocumentType",
    "get_spec",
    "detect_document_type",
    "Document",
    "Section",
    "ImagePlaceholder",
    "OutputFormat",
    "read_document",
    "write_document",
    "parse_markdown_to_document",
    "parse_text_to_document",
    "apply_type_formatting",
    "suggest_missing_sections",
    "insert_image_placeholder",
    "load_document",
    "convert_document",
    "convert_text",
    "DocumentAgent",
    "AgentConfig",
    "AgentResult",
]
