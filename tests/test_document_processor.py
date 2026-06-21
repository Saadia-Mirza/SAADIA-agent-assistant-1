"""Tests for agent.document_processor."""

import os
import tempfile
import textwrap

import pytest

from agent.document_processor import (
    Document,
    ImagePlaceholder,
    OutputFormat,
    Section,
    apply_type_formatting,
    insert_image_placeholder,
    parse_markdown_to_document,
    parse_text_to_document,
    read_document,
    suggest_missing_sections,
    write_document,
)
from agent.document_types import DocumentType, get_spec


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_MARKDOWN = textwrap.dedent("""\
    # Employee Onboarding Guide

    ## Introduction

    Welcome to the company. This guide will help you get started.

    ## Step 1: Set Up Your Workstation

    1. Unbox the laptop.
    2. Connect to the corporate Wi-Fi.
    3. Log in with your company credentials.

    ## Step 2: Install Required Software

    1. Open the Software Centre.
    2. Install the required applications.
""")

SAMPLE_PLAIN_TEXT = textwrap.dedent("""\
    Data Retention Policy

    PURPOSE
    This policy establishes requirements for data retention.

    SCOPE
    This policy applies to all employees who handle data.

    REQUIREMENTS
    All data shall be retained for a minimum of seven years.
""")


# ---------------------------------------------------------------------------
# parse_markdown_to_document
# ---------------------------------------------------------------------------

class TestParseMarkdownToDocument:
    def test_parses_title(self):
        doc = parse_markdown_to_document(SAMPLE_MARKDOWN)
        assert doc.title == "Employee Onboarding Guide"

    def test_parses_sections(self):
        doc = parse_markdown_to_document(SAMPLE_MARKDOWN)
        headings = [s.heading for s in doc.sections]
        assert "Introduction" in headings
        assert "Step 1: Set Up Your Workstation" in headings

    def test_section_content_is_populated(self):
        doc = parse_markdown_to_document(SAMPLE_MARKDOWN)
        intro = next(s for s in doc.sections if s.heading == "Introduction")
        assert "Welcome" in intro.content

    def test_detects_doc_type_when_not_specified(self):
        doc = parse_markdown_to_document(SAMPLE_MARKDOWN)
        # Contains "step", "install", "log in" → instruction_manual
        assert doc.doc_type == DocumentType.INSTRUCTION_MANUAL

    def test_respects_explicit_doc_type(self):
        doc = parse_markdown_to_document(SAMPLE_MARKDOWN, DocumentType.GUIDANCE)
        assert doc.doc_type == DocumentType.GUIDANCE

    def test_parses_image_placeholder(self):
        md = "# Title\n\n## Section\n\n<!-- PLACEHOLDER: Login Screen -->\n\nSome content."
        doc = parse_markdown_to_document(md)
        section = doc.sections[0]
        assert len(section.images) == 1
        assert section.images[0].label == "Login Screen"

    def test_parses_inline_image(self):
        md = "# Title\n\n## Section\n\n![Alt text](images/screenshot.png)\n"
        doc = parse_markdown_to_document(md)
        assert doc.sections[0].images[0].path == "images/screenshot.png"

    def test_empty_document_has_untitled(self):
        doc = parse_markdown_to_document("")
        assert doc.title == "Untitled"


# ---------------------------------------------------------------------------
# parse_text_to_document
# ---------------------------------------------------------------------------

class TestParseTextToDocument:
    def test_uses_first_line_as_title(self):
        doc = parse_text_to_document(SAMPLE_PLAIN_TEXT)
        assert doc.title == "Data Retention Policy"

    def test_detects_uppercase_headings(self):
        doc = parse_text_to_document(SAMPLE_PLAIN_TEXT)
        headings = [s.heading for s in doc.sections]
        assert "PURPOSE" in headings or "Purpose" in headings

    def test_section_content_populated(self):
        doc = parse_text_to_document(SAMPLE_PLAIN_TEXT)
        purpose_section = next(
            (s for s in doc.sections if "purpose" in s.heading.lower()), None
        )
        assert purpose_section is not None
        assert "retention" in purpose_section.content.lower()


# ---------------------------------------------------------------------------
# Document serialisation
# ---------------------------------------------------------------------------

class TestDocumentSerialization:
    def _make_doc(self) -> Document:
        return Document(
            title="Test Document",
            doc_type=DocumentType.GENERAL,
            sections=[
                Section(heading="Intro", level=1, content="Some content here."),
                Section(
                    heading="Steps",
                    level=1,
                    content="Follow these steps.",
                    images=[ImagePlaceholder(label="Diagram", caption="A diagram", alt_text="diagram")],
                ),
            ],
        )

    def test_as_markdown_includes_title(self):
        doc = self._make_doc()
        md = doc.as_markdown()
        assert "# Test Document" in md

    def test_as_markdown_includes_headings(self):
        doc = self._make_doc()
        md = doc.as_markdown()
        assert "## Intro" in md
        assert "## Steps" in md

    def test_as_markdown_includes_placeholder(self):
        doc = self._make_doc()
        md = doc.as_markdown()
        assert "PLACEHOLDER: Diagram" in md

    def test_plain_text_includes_title(self):
        doc = self._make_doc()
        text = doc.plain_text()
        assert "Test Document" in text

    def test_plain_text_includes_image_label(self):
        doc = self._make_doc()
        text = doc.plain_text()
        assert "IMAGE: Diagram" in text


# ---------------------------------------------------------------------------
# apply_type_formatting
# ---------------------------------------------------------------------------

class TestApplyTypeFormatting:
    def test_title_case_headings_for_guidance(self):
        doc = Document(
            title="My Document",
            doc_type=DocumentType.GUIDANCE,
            sections=[Section(heading="data retention requirements", level=1, content="Content.")],
        )
        spec = get_spec(DocumentType.GUIDANCE)
        formatted = apply_type_formatting(doc, spec)
        assert formatted.sections[0].heading == "Data Retention Requirements"

    def test_sentence_case_for_instruction_manual(self):
        doc = Document(
            title="Guide",
            doc_type=DocumentType.INSTRUCTION_MANUAL,
            sections=[Section(heading="installing the software", level=1, content="Steps here.")],
        )
        spec = get_spec(DocumentType.INSTRUCTION_MANUAL)
        formatted = apply_type_formatting(doc, spec)
        assert formatted.sections[0].heading[0].isupper()

    def test_formatting_preserves_content(self):
        doc = Document(
            title="Guide",
            doc_type=DocumentType.GENERAL,
            sections=[Section(heading="Overview", level=1, content="This is the overview.")],
        )
        spec = get_spec(DocumentType.GENERAL)
        formatted = apply_type_formatting(doc, spec)
        assert "overview" in formatted.sections[0].content.lower()


# ---------------------------------------------------------------------------
# suggest_missing_sections
# ---------------------------------------------------------------------------

class TestSuggestMissingSections:
    def test_detects_missing_sections(self):
        doc = Document(
            title="Minimal Guide",
            doc_type=DocumentType.INSTRUCTION_MANUAL,
            sections=[Section(heading="Introduction", level=1, content="Some text.")],
        )
        spec = get_spec(DocumentType.INSTRUCTION_MANUAL)
        missing = suggest_missing_sections(doc, spec)
        # Should flag most recommended sections as missing
        assert len(missing) > 3

    def test_no_missing_sections_when_all_present(self):
        spec = get_spec(DocumentType.GENERAL)
        sections = [
            Section(heading=s.lstrip("0123456789. "), level=1, content="Content.")
            for s in spec.sections
        ]
        doc = Document(title="Full Doc", doc_type=DocumentType.GENERAL, sections=sections)
        missing = suggest_missing_sections(doc, spec)
        assert missing == []


# ---------------------------------------------------------------------------
# insert_image_placeholder
# ---------------------------------------------------------------------------

class TestInsertImagePlaceholder:
    def _base_doc(self) -> Document:
        return Document(
            title="Guide",
            doc_type=DocumentType.INSTRUCTION_MANUAL,
            sections=[Section(heading="Step 1", level=1, content="Do this.")],
        )

    def test_inserts_placeholder_into_existing_section(self):
        doc = self._base_doc()
        updated = insert_image_placeholder(doc, "Step 1", "Screenshot 1", "Step 1 screenshot")
        assert len(updated.sections[0].images) == 1
        assert updated.sections[0].images[0].label == "Screenshot 1"

    def test_creates_new_section_when_not_found(self):
        doc = self._base_doc()
        updated = insert_image_placeholder(doc, "Appendix", "Diagram A", "A diagram")
        headings = [s.heading for s in updated.sections]
        assert "Appendix" in headings

    def test_position_start_inserts_first(self):
        doc = Document(
            title="Guide",
            doc_type=DocumentType.GENERAL,
            sections=[
                Section(
                    heading="Overview",
                    level=1,
                    content="Content.",
                    images=[ImagePlaceholder(label="Existing", caption="Existing image", alt_text="")],
                )
            ],
        )
        updated = insert_image_placeholder(doc, "Overview", "New Image", "New", position="start")
        assert updated.sections[0].images[0].label == "New Image"

    def test_original_document_is_not_mutated(self):
        doc = self._base_doc()
        _ = insert_image_placeholder(doc, "Step 1", "Screenshot 1", "Step 1 screenshot")
        assert len(doc.sections[0].images) == 0


# ---------------------------------------------------------------------------
# write_document / read_document (round-trip)
# ---------------------------------------------------------------------------

class TestWriteReadRoundTrip:
    def _make_doc(self) -> Document:
        return Document(
            title="Round-Trip Test",
            doc_type=DocumentType.GENERAL,
            sections=[
                Section(heading="Section A", level=1, content="Content A."),
                Section(heading="Section B", level=1, content="Content B."),
            ],
        )

    def _round_trip(self, fmt: OutputFormat, ext: str):
        doc = self._make_doc()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, f"test{ext}")
            write_document(doc, path, fmt)
            assert os.path.exists(path)
            raw = read_document(path)
            assert "Round-Trip Test" in raw or "Section A" in raw

    def test_markdown_round_trip(self):
        self._round_trip(OutputFormat.MARKDOWN, ".md")

    def test_plain_text_round_trip(self):
        self._round_trip(OutputFormat.PLAIN_TEXT, ".txt")

    def test_docx_round_trip(self):
        self._round_trip(OutputFormat.DOCX, ".docx")

    def test_html_round_trip(self):
        self._round_trip(OutputFormat.HTML, ".html")
