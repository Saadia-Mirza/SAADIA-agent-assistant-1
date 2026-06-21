"""
Document processor — read, write, and transform documents.

Supported formats:
  - Markdown (.md)
  - Plain text (.txt)
  - Microsoft Word (.docx)
  - HTML (.html)

Key responsibilities:
  - Parse documents into a normalised internal representation
  - Apply type-specific formatting rules
  - Insert image / screenshot placeholders
  - Serialise back to the target format
"""

from __future__ import annotations

import os
import re
import textwrap
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

from agent.document_types import DocumentType, DocumentTypeSpec, get_spec


class OutputFormat(str, Enum):
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"
    DOCX = "docx"
    HTML = "html"


@dataclass
class ImagePlaceholder:
    """Represents an image or screenshot to be inserted into a document."""

    label: str
    caption: str
    alt_text: str
    position_hint: str = ""  # e.g. "after Step 3"
    path: Optional[str] = None  # populated when an actual image file is provided


@dataclass
class Section:
    """A single logical section of a document."""

    heading: str
    level: int  # 1 = top-level, 2 = sub-heading, etc.
    content: str
    images: List[ImagePlaceholder] = field(default_factory=list)


@dataclass
class Document:
    """Normalised in-memory representation of a document."""

    title: str
    doc_type: DocumentType
    sections: List[Section] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def plain_text(self) -> str:
        """Return the full document as plain text (no Markdown markers)."""
        parts: List[str] = [self.title, "=" * len(self.title), ""]
        for sec in self.sections:
            if sec.heading:
                parts.append(sec.heading)
                parts.append("-" * len(sec.heading))
            parts.append(sec.content)
            for img in sec.images:
                parts.append(f"[IMAGE: {img.label} — {img.caption}]")
            parts.append("")
        return "\n".join(parts).strip()

    def as_markdown(self) -> str:
        """Serialise to Markdown."""
        parts: List[str] = [f"# {self.title}", ""]
        for sec in self.sections:
            hashes = "#" * (sec.level + 1)
            parts.append(f"{hashes} {sec.heading}")
            parts.append("")
            parts.append(sec.content)
            for img in sec.images:
                alt = img.alt_text or img.label
                if img.path:
                    parts.append(f"![{alt}]({img.path})")
                else:
                    parts.append(f"<!-- PLACEHOLDER: {img.label} -->")
                    parts.append(f"*Figure: {img.caption}*")
            parts.append("")
        return "\n".join(parts).strip()


# ---------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------

def read_markdown(path: str) -> str:
    """Read a Markdown or plain-text file and return its contents."""
    return Path(path).read_text(encoding="utf-8")


def read_docx(path: str) -> str:
    """Read a .docx file and return its plain text content."""
    try:
        import docx  # python-docx
    except ImportError as exc:
        raise ImportError("python-docx is required to read .docx files. Run: pip install python-docx") from exc

    doc = docx.Document(path)
    lines: List[str] = []
    for para in doc.paragraphs:
        lines.append(para.text)
    return "\n".join(lines)


def read_html(path: str) -> str:
    """Read an HTML file and return its text content (tags stripped)."""
    raw = Path(path).read_text(encoding="utf-8")
    # Strip HTML tags with a simple regex (sufficient for round-trip text extraction)
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def read_document(path: str) -> str:
    """Detect file format and read its text content."""
    ext = Path(path).suffix.lower()
    if ext in {".md", ".txt"}:
        return read_markdown(path)
    if ext in {".docx"}:
        return read_docx(path)
    if ext in {".html", ".htm"}:
        return read_html(path)
    # Fallback: treat as plain text
    return Path(path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Parsers — text → Document
# ---------------------------------------------------------------------------

def _heading_level_from_hashes(line: str) -> int:
    """Return heading level (1–6) from a Markdown-style #-prefixed line."""
    match = re.match(r"^(#{1,6})\s", line)
    return len(match.group(1)) if match else 0


def parse_markdown_to_document(text: str, doc_type: Optional[DocumentType] = None) -> Document:
    """
    Parse Markdown text into a Document.

    The first H1 is used as the document title.  Subsequent headings
    delimit sections.  Images are extracted into ImagePlaceholder objects.
    """
    from agent.document_types import detect_document_type

    if doc_type is None:
        doc_type = detect_document_type(text)

    lines = text.splitlines()
    title = ""
    sections: List[Section] = []
    current_heading = ""
    current_level = 1
    current_lines: List[str] = []
    current_images: List[ImagePlaceholder] = []

    def _flush():
        nonlocal current_heading, current_level, current_lines, current_images
        has_content = any(line.strip() for line in current_lines)
        if current_heading or has_content or current_images:
            sections.append(
                Section(
                    heading=current_heading,
                    level=current_level,
                    content="\n".join(current_lines).strip(),
                    images=list(current_images),
                )
            )
        current_heading = ""
        current_level = 1
        current_lines = []
        current_images = []

    for line in lines:
        lvl = _heading_level_from_hashes(line)
        if lvl == 1 and not title:
            title = line.lstrip("#").strip()
            continue
        if lvl >= 1:
            _flush()
            current_heading = line.lstrip("#").strip()
            current_level = lvl
            continue

        # Inline image: ![alt](src)
        img_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
        if img_match:
            alt, src = img_match.group(1), img_match.group(2)
            current_images.append(
                ImagePlaceholder(label=alt or src, caption=alt, alt_text=alt, path=src)
            )
            continue

        # Placeholder comment: <!-- PLACEHOLDER: label -->
        ph_match = re.match(r"<!--\s*PLACEHOLDER:\s*(.+?)\s*-->", line)
        if ph_match:
            current_images.append(
                ImagePlaceholder(label=ph_match.group(1), caption=ph_match.group(1), alt_text="")
            )
            continue

        current_lines.append(line)

    _flush()

    return Document(title=title or "Untitled", doc_type=doc_type, sections=sections)


def parse_text_to_document(text: str, doc_type: Optional[DocumentType] = None) -> Document:
    """
    Parse plain text into a Document by treating ALL-CAPS or numbered headings
    as section delimiters.
    """
    from agent.document_types import detect_document_type

    if doc_type is None:
        doc_type = detect_document_type(text)

    lines = text.splitlines()
    title = lines[0].strip() if lines else "Untitled"
    sections: List[Section] = []
    current_heading = "Content"
    current_lines: List[str] = []

    for line in lines[1:]:
        # Heuristic: a line is a heading if it is short, title-like, and followed by content
        is_heading = (
            line.isupper()
            or re.match(r"^\d+(\.\d+)*\s+[A-Z]", line)
            or re.match(r"^[A-Z][A-Za-z\s]{2,40}$", line.rstrip(":"))
        )
        if is_heading and line.strip():
            if current_lines:
                sections.append(
                    Section(heading=current_heading, level=1, content="\n".join(current_lines).strip())
                )
            current_heading = line.strip().rstrip(":")
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append(
            Section(heading=current_heading, level=1, content="\n".join(current_lines).strip())
        )

    return Document(title=title, doc_type=doc_type, sections=sections)


# ---------------------------------------------------------------------------
# Formatters — apply type-specific style to a Document
# ---------------------------------------------------------------------------

def _wrap(text: str, width: int = 88) -> str:
    """Re-wrap paragraphs to the given column width."""
    paragraphs = re.split(r"\n{2,}", text)
    wrapped = []
    for para in paragraphs:
        # Don't re-wrap list items or code blocks
        if re.match(r"^\s*[\-\*\d]", para) or para.startswith("```"):
            wrapped.append(para)
        else:
            wrapped.append(textwrap.fill(para.replace("\n", " "), width=width))
    return "\n\n".join(wrapped)


def apply_type_formatting(doc: Document, spec: DocumentTypeSpec) -> Document:
    """
    Return a new Document with headings and content adjusted to match the
    style guide for the given DocumentTypeSpec.
    """
    sg = spec.style_guide

    new_sections: List[Section] = []
    for i, sec in enumerate(doc.sections):
        heading = sec.heading
        content = sec.content

        # Apply Title Case or Sentence case to headings
        if "Title Case" in sg.heading_style:
            heading = heading.title()
        elif "Sentence case" in sg.heading_style:
            heading = heading.capitalize()

        # Re-wrap body text
        content = _wrap(content)

        new_sections.append(
            Section(
                heading=heading,
                level=sec.level,
                content=content,
                images=sec.images,
            )
        )

    return Document(
        title=doc.title,
        doc_type=doc.doc_type,
        sections=new_sections,
        metadata=doc.metadata,
    )


def suggest_missing_sections(doc: Document, spec: DocumentTypeSpec) -> List[str]:
    """
    Return a list of recommended section titles that are present in the spec
    but absent from the document.
    """
    existing = {s.heading.lower() for s in doc.sections}
    missing = []
    for recommended in spec.sections:
        # Strip numbering prefix for comparison (e.g. "1. Purpose" → "purpose")
        clean = re.sub(r"^\d+(\.\d+)*\.\s*", "", recommended).lower()
        if clean not in existing and recommended.lower() not in existing:
            missing.append(recommended)
    return missing


# ---------------------------------------------------------------------------
# Image placeholder insertion
# ---------------------------------------------------------------------------

def insert_image_placeholder(
    doc: Document,
    section_heading: str,
    label: str,
    caption: str,
    alt_text: str = "",
    position: str = "end",
) -> Document:
    """
    Insert an ImagePlaceholder into the section whose heading matches
    *section_heading*.  *position* can be 'end' (default) or 'start'.

    Returns a new Document with the placeholder inserted.
    """
    new_sections: List[Section] = []
    placed = False

    for sec in doc.sections:
        if sec.heading.lower() == section_heading.lower():
            placeholder = ImagePlaceholder(
                label=label, caption=caption, alt_text=alt_text or label
            )
            images = (
                [placeholder] + list(sec.images)
                if position == "start"
                else list(sec.images) + [placeholder]
            )
            new_sections.append(
                Section(
                    heading=sec.heading,
                    level=sec.level,
                    content=sec.content,
                    images=images,
                )
            )
            placed = True
        else:
            new_sections.append(sec)

    if not placed:
        # Append a new section with just the placeholder
        new_sections.append(
            Section(
                heading=section_heading,
                level=2,
                content="",
                images=[ImagePlaceholder(label=label, caption=caption, alt_text=alt_text or label)],
            )
        )

    return Document(title=doc.title, doc_type=doc.doc_type, sections=new_sections, metadata=doc.metadata)


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def write_markdown(doc: Document, path: str) -> None:
    """Write a Document to a Markdown file."""
    Path(path).write_text(doc.as_markdown(), encoding="utf-8")


def write_plain_text(doc: Document, path: str) -> None:
    """Write a Document to a plain-text file."""
    Path(path).write_text(doc.plain_text(), encoding="utf-8")


def write_docx(doc: Document, path: str) -> None:
    """Write a Document to a .docx file."""
    try:
        import docx
        from docx.shared import Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError as exc:
        raise ImportError("python-docx is required. Run: pip install python-docx") from exc

    word_doc = docx.Document()

    # Title
    word_doc.add_heading(doc.title, level=0)

    for sec in doc.sections:
        word_doc.add_heading(sec.heading, level=min(sec.level, 9))
        if sec.content:
            word_doc.add_paragraph(sec.content)
        for img in sec.images:
            if img.path and os.path.exists(img.path):
                word_doc.add_picture(img.path)
                word_doc.add_paragraph(f"Figure: {img.caption}").alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p = word_doc.add_paragraph()
                run = p.add_run(f"[PLACEHOLDER: {img.label} — {img.caption}]")
                run.italic = True

    word_doc.save(path)


def write_html(doc: Document, path: str) -> None:
    """Write a Document to an HTML file."""
    try:
        import markdown as md_lib
    except ImportError as exc:
        raise ImportError("Markdown is required. Run: pip install Markdown") from exc

    md_text = doc.as_markdown()
    body = md_lib.markdown(md_text, extensions=["extra", "toc"])
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{doc.title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 860px; margin: 2rem auto; line-height: 1.6; color: #333; }}
    h1, h2, h3, h4 {{ color: #1a1a2e; }}
    img {{ max-width: 100%; height: auto; display: block; margin: 1rem 0; }}
    .placeholder {{ background: #f0f4ff; border: 1px dashed #6699cc; padding: 1rem; color: #336; font-style: italic; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ccc; padding: .5rem; text-align: left; }}
  </style>
</head>
<body>
{body}
</body>
</html>"""
    Path(path).write_text(html, encoding="utf-8")


def write_document(doc: Document, path: str, fmt: Optional[OutputFormat] = None) -> None:
    """
    Write a Document to *path* in the specified format.

    If *fmt* is None the format is inferred from the file extension.
    """
    if fmt is None:
        ext = Path(path).suffix.lower()
        fmt = {
            ".md": OutputFormat.MARKDOWN,
            ".txt": OutputFormat.PLAIN_TEXT,
            ".docx": OutputFormat.DOCX,
            ".html": OutputFormat.HTML,
            ".htm": OutputFormat.HTML,
        }.get(ext, OutputFormat.MARKDOWN)

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    if fmt == OutputFormat.MARKDOWN:
        write_markdown(doc, path)
    elif fmt == OutputFormat.PLAIN_TEXT:
        write_plain_text(doc, path)
    elif fmt == OutputFormat.DOCX:
        write_docx(doc, path)
    elif fmt == OutputFormat.HTML:
        write_html(doc, path)
    else:
        raise ValueError(f"Unsupported output format: {fmt}")
