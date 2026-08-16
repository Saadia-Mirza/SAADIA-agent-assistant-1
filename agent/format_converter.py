"""
Format converter — convert documents between supported formats.

Supported conversions:
  markdown  → plain_text, docx, html
  plain_text → markdown, docx, html
  docx      → markdown, plain_text, html
  html      → markdown, plain_text

The converter uses the Document intermediate representation so all
type-specific formatting rules are preserved during conversion.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from agent.document_processor import (
    Document,
    OutputFormat,
    parse_markdown_to_document,
    parse_text_to_document,
    read_document,
    write_document,
)
from agent.document_types import DocumentType, detect_document_type


def _infer_input_format(path: str) -> OutputFormat:
    """Infer the input format from the file extension."""
    ext = Path(path).suffix.lower()
    return {
        ".md": OutputFormat.MARKDOWN,
        ".txt": OutputFormat.PLAIN_TEXT,
        ".docx": OutputFormat.DOCX,
        ".html": OutputFormat.HTML,
        ".htm": OutputFormat.HTML,
    }.get(ext, OutputFormat.MARKDOWN)


def load_document(path: str, doc_type: Optional[DocumentType] = None) -> Document:
    """
    Load a document from *path* into the internal Document representation.

    The document type is detected automatically if not provided.
    """
    raw_text = read_document(path)
    fmt = _infer_input_format(path)

    if doc_type is None:
        doc_type = detect_document_type(raw_text)

    if fmt in {OutputFormat.MARKDOWN, OutputFormat.HTML}:
        # HTML is stripped to text first by read_document, then parsed as plain text
        return parse_markdown_to_document(raw_text, doc_type)

    return parse_text_to_document(raw_text, doc_type)


def convert_document(
    input_path: str,
    output_path: str,
    doc_type: Optional[DocumentType] = None,
    output_format: Optional[OutputFormat] = None,
) -> Document:
    """
    Convert the document at *input_path* and write the result to *output_path*.

    Parameters
    ----------
    input_path:    Path to the source document.
    output_path:   Destination path (extension determines the format unless
                   *output_format* is explicitly set).
    doc_type:      Override the detected document type.
    output_format: Override the output format inferred from *output_path*.

    Returns the in-memory Document after conversion.
    """
    doc = load_document(input_path, doc_type)
    write_document(doc, output_path, output_format)
    return doc


def convert_text(
    text: str,
    output_path: str,
    input_is_markdown: bool = True,
    doc_type: Optional[DocumentType] = None,
    output_format: Optional[OutputFormat] = None,
) -> Document:
    """
    Convert raw text to the target format and write to *output_path*.

    Useful when the source content is already in memory rather than on disk.
    """
    if doc_type is None:
        doc_type = detect_document_type(text)

    if input_is_markdown:
        doc = parse_markdown_to_document(text, doc_type)
    else:
        doc = parse_text_to_document(text, doc_type)

    write_document(doc, output_path, output_format)
    return doc


def conversion_summary(input_path: str, output_path: str) -> str:
    """Return a human-readable summary of the conversion."""
    in_fmt = _infer_input_format(input_path).value
    out_ext = Path(output_path).suffix.lower()
    out_fmt = {
        ".md": "markdown",
        ".txt": "plain text",
        ".docx": "Word document",
        ".html": "HTML",
    }.get(out_ext, out_ext)
    return f"Converted '{Path(input_path).name}' ({in_fmt}) → '{Path(output_path).name}' ({out_fmt})"
