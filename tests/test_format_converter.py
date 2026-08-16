"""Tests for agent.format_converter."""

import os
import tempfile
import textwrap

import pytest

from agent.format_converter import (
    convert_document,
    convert_text,
    conversion_summary,
    load_document,
)
from agent.document_processor import OutputFormat
from agent.document_types import DocumentType


SAMPLE_MARKDOWN = textwrap.dedent("""\
    # Release Approval Process

    ## Process Overview

    This workflow is triggered by a new sprint completion.
    The swimlane diagram below shows the full process.

    ## Approval Steps

    1. Submit the release request.
    2. QA review and testing.
    3. Approve and deploy.
""")


class TestLoadDocument:
    def test_loads_markdown_file(self):
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
            f.write(SAMPLE_MARKDOWN)
            path = f.name
        try:
            doc = load_document(path)
            assert doc.title == "Release Approval Process"
        finally:
            os.unlink(path)

    def test_auto_detects_process_workflow(self):
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
            f.write(SAMPLE_MARKDOWN)
            path = f.name
        try:
            doc = load_document(path)
            assert doc.doc_type == DocumentType.PROCESS_WORKFLOW
        finally:
            os.unlink(path)

    def test_overrides_doc_type(self):
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
            f.write(SAMPLE_MARKDOWN)
            path = f.name
        try:
            doc = load_document(path, doc_type=DocumentType.GUIDANCE)
            assert doc.doc_type == DocumentType.GUIDANCE
        finally:
            os.unlink(path)

    def test_loads_plain_text_file(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8") as f:
            f.write("My Policy\n\nSCOPE\nAll staff.\n")
            path = f.name
        try:
            doc = load_document(path)
            assert doc.title == "My Policy"
        finally:
            os.unlink(path)


class TestConvertDocument:
    def test_md_to_txt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "input.md")
            dst = os.path.join(tmpdir, "output.txt")
            with open(src, "w", encoding="utf-8") as f:
                f.write(SAMPLE_MARKDOWN)
            doc = convert_document(src, dst)
            assert os.path.exists(dst)
            content = open(dst, encoding="utf-8").read()
            assert "Release Approval Process" in content

    def test_md_to_html(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "input.md")
            dst = os.path.join(tmpdir, "output.html")
            with open(src, "w", encoding="utf-8") as f:
                f.write(SAMPLE_MARKDOWN)
            convert_document(src, dst)
            assert os.path.exists(dst)
            html = open(dst, encoding="utf-8").read()
            assert "<html" in html.lower()

    def test_md_to_docx(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "input.md")
            dst = os.path.join(tmpdir, "output.docx")
            with open(src, "w", encoding="utf-8") as f:
                f.write(SAMPLE_MARKDOWN)
            convert_document(src, dst)
            assert os.path.exists(dst)

    def test_returns_document_object(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "input.md")
            dst = os.path.join(tmpdir, "output.md")
            with open(src, "w", encoding="utf-8") as f:
                f.write(SAMPLE_MARKDOWN)
            doc = convert_document(src, dst)
            assert doc.title == "Release Approval Process"


class TestConvertText:
    def test_converts_markdown_text_to_html(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dst = os.path.join(tmpdir, "output.html")
            doc = convert_text(SAMPLE_MARKDOWN, dst, input_is_markdown=True)
            assert os.path.exists(dst)
            assert doc.title == "Release Approval Process"

    def test_converts_plain_text_to_markdown(self):
        plain = "My Guide\n\nINTRODUCTION\nThis is the introduction.\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            dst = os.path.join(tmpdir, "output.md")
            doc = convert_text(plain, dst, input_is_markdown=False)
            assert doc.title == "My Guide"
            assert os.path.exists(dst)

    def test_explicit_output_format_overrides_extension(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dst = os.path.join(tmpdir, "output.md")
            convert_text(
                SAMPLE_MARKDOWN,
                dst,
                input_is_markdown=True,
                output_format=OutputFormat.PLAIN_TEXT,
            )
            content = open(dst, encoding="utf-8").read()
            # Plain text should not contain Markdown headings like "##"
            assert "##" not in content


class TestConversionSummary:
    def test_produces_human_readable_summary(self):
        summary = conversion_summary("docs/policy.md", "output/policy.html")
        assert "policy.md" in summary
        assert "policy.html" in summary
        assert "HTML" in summary or "html" in summary

    def test_includes_format_names(self):
        summary = conversion_summary("input.docx", "output.txt")
        assert "docx" in summary.lower() or "word" in summary.lower()
        assert "txt" in summary or "plain text" in summary.lower()
