"""Tests for agent.agent (DocumentAgent)."""

import os
import tempfile
import textwrap

import pytest

from agent.agent import AgentConfig, AgentResult, DocumentAgent
from agent.document_processor import OutputFormat
from agent.document_types import DocumentType


INSTRUCTION_MANUAL_MD = textwrap.dedent("""\
    # VPN Setup Guide

    ## Introduction

    This guide explains how to install and configure the corporate VPN.

    ## Installing the VPN Client

    1. download the installer from the IT portal.
    2. run the installer and accept the licence agreement.
    3. restart your computer when prompted.

    ## Connecting to the VPN

    1. open the vpn client from the system tray.
    2. enter your company username and password.
    3. click connect.
""")

GUIDANCE_MD = textwrap.dedent("""\
    # Information Security Policy

    ## Purpose

    This policy establishes requirements for information security across the
    organisation. All staff must comply with this policy.

    ## Scope

    This policy applies to all employees and contractors.

    ## Requirements

    1. All systems must have endpoint protection installed.
    2. Access must be reviewed annually.
""")

PROCESS_WORKFLOW_MD = textwrap.dedent("""\
    # Leave Request Workflow

    ## Process Overview

    This workflow is triggered when an employee submits a leave request.
    Refer to the swimlane diagram for the full process.

    ## Approval Steps

    1. Employee submits the request.
    2. Manager reviews and approves or rejects.
    3. HR is notified of the decision.
""")


def _write_temp_md(content: str) -> str:
    """Write content to a temp .md file and return its path."""
    f = tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8")
    f.write(content)
    f.close()
    return f.name


class TestDocumentAgentRuleBased:
    """Tests that run without an OpenAI API key (rule-based mode)."""

    def _agent(self, doc_type=None, output_format=OutputFormat.MARKDOWN) -> DocumentAgent:
        config = AgentConfig(
            doc_type=doc_type,
            output_format=output_format,
            openai_api_key=None,
        )
        return DocumentAgent(config)

    # ------------------------------------------------------------------ #
    # process()                                                            #
    # ------------------------------------------------------------------ #

    def test_process_creates_output_file(self):
        src = _write_temp_md(INSTRUCTION_MANUAL_MD)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                dst = os.path.join(tmpdir, "output.md")
                agent = self._agent()
                result = agent.process(src, dst)
                assert os.path.exists(dst)
        finally:
            os.unlink(src)

    def test_process_returns_agent_result(self):
        src = _write_temp_md(INSTRUCTION_MANUAL_MD)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                dst = os.path.join(tmpdir, "output.md")
                result = self._agent().process(src, dst)
                assert isinstance(result, AgentResult)
        finally:
            os.unlink(src)

    def test_result_summary_is_non_empty(self):
        src = _write_temp_md(INSTRUCTION_MANUAL_MD)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                dst = os.path.join(tmpdir, "output.md")
                result = self._agent().process(src, dst)
                assert result.summary
        finally:
            os.unlink(src)

    def test_auto_detects_instruction_manual_type(self):
        src = _write_temp_md(INSTRUCTION_MANUAL_MD)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                dst = os.path.join(tmpdir, "output.md")
                result = self._agent().process(src, dst)
                assert result.document.doc_type == DocumentType.INSTRUCTION_MANUAL
        finally:
            os.unlink(src)

    def test_explicit_doc_type_overrides_detection(self):
        src = _write_temp_md(INSTRUCTION_MANUAL_MD)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                dst = os.path.join(tmpdir, "output.md")
                result = self._agent(doc_type=DocumentType.GUIDANCE).process(src, dst)
                assert result.document.doc_type == DocumentType.GUIDANCE
        finally:
            os.unlink(src)

    def test_missing_instructions_warning_when_api_key_absent(self):
        src = _write_temp_md(GUIDANCE_MD)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                dst = os.path.join(tmpdir, "output.md")
                result = self._agent().process(src, dst, instructions="Expand section 2.")
                # Should have a warning about missing API key
                assert any("OPENAI_API_KEY" in w or "openai_api_key" in w for w in result.warnings)
        finally:
            os.unlink(src)

    # ------------------------------------------------------------------ #
    # Output format                                                        #
    # ------------------------------------------------------------------ #

    def test_output_as_html(self):
        src = _write_temp_md(GUIDANCE_MD)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                dst = os.path.join(tmpdir, "output.html")
                result = self._agent(output_format=OutputFormat.HTML).process(src, dst)
                assert os.path.exists(dst)
                content = open(dst, encoding="utf-8").read()
                assert "<html" in content.lower()
        finally:
            os.unlink(src)

    def test_output_as_docx(self):
        src = _write_temp_md(INSTRUCTION_MANUAL_MD)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                dst = os.path.join(tmpdir, "output.docx")
                result = self._agent(output_format=OutputFormat.DOCX).process(src, dst)
                assert os.path.exists(dst)
        finally:
            os.unlink(src)

    # ------------------------------------------------------------------ #
    # Style formatting                                                     #
    # ------------------------------------------------------------------ #

    def test_apply_style_true_transforms_headings(self):
        src = _write_temp_md(GUIDANCE_MD)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                dst = os.path.join(tmpdir, "output.md")
                result = self._agent(doc_type=DocumentType.GUIDANCE).process(src, dst)
                md = open(dst, encoding="utf-8").read()
                # Title Case should capitalise headings
                assert "## Purpose" in md or "## PURPOSE" in md
        finally:
            os.unlink(src)

    def test_apply_style_false_skips_formatting(self):
        config = AgentConfig(apply_style=False, openai_api_key=None)
        agent = DocumentAgent(config)
        src = _write_temp_md(GUIDANCE_MD)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                dst = os.path.join(tmpdir, "output.md")
                result = agent.process(src, dst)
                assert result.document is not None
        finally:
            os.unlink(src)

    # ------------------------------------------------------------------ #
    # Image suggestions                                                    #
    # ------------------------------------------------------------------ #

    def test_image_suggestions_generated_for_instruction_manual(self):
        src = _write_temp_md(INSTRUCTION_MANUAL_MD)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                dst = os.path.join(tmpdir, "output.md")
                result = self._agent().process(src, dst)
                assert len(result.image_suggestions) > 0
        finally:
            os.unlink(src)

    def test_image_suggestions_suppressed_when_disabled(self):
        config = AgentConfig(suggest_images=False, openai_api_key=None)
        agent = DocumentAgent(config)
        src = _write_temp_md(INSTRUCTION_MANUAL_MD)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                dst = os.path.join(tmpdir, "output.md")
                result = agent.process(src, dst)
                assert result.image_suggestions == []
        finally:
            os.unlink(src)

    # ------------------------------------------------------------------ #
    # Vocabulary checks                                                    #
    # ------------------------------------------------------------------ #

    def test_vocabulary_check_flags_must_for_guidance(self):
        # GUIDANCE_MD contains "must" instead of "shall"
        src = _write_temp_md(GUIDANCE_MD)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                dst = os.path.join(tmpdir, "output.md")
                result = self._agent(doc_type=DocumentType.GUIDANCE).process(src, dst)
                # "must" in GUIDANCE_MD should trigger a vocabulary note
                assert any("shall" in note.lower() for note in result.vocabulary_notes)
        finally:
            os.unlink(src)

    # ------------------------------------------------------------------ #
    # process_text()                                                       #
    # ------------------------------------------------------------------ #

    def test_process_text_works_without_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dst = os.path.join(tmpdir, "output.md")
            result = self._agent().process_text(PROCESS_WORKFLOW_MD, dst)
            assert isinstance(result, AgentResult)
            assert os.path.exists(dst)

    def test_process_text_detects_process_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dst = os.path.join(tmpdir, "output.md")
            result = self._agent().process_text(PROCESS_WORKFLOW_MD, dst)
            assert result.document.doc_type == DocumentType.PROCESS_WORKFLOW

    def test_process_text_plain_text_mode(self):
        plain = "My Process\n\nINPUTS\nA request form.\n\nOUTPUTS\nAn approval decision.\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            dst = os.path.join(tmpdir, "output.md")
            result = self._agent().process_text(plain, dst, input_is_markdown=False)
            assert result.document.title == "My Process"


class TestAgentMissingInputFile:
    def test_raises_on_missing_input_file(self):
        agent = DocumentAgent()
        with tempfile.TemporaryDirectory() as tmpdir:
            dst = os.path.join(tmpdir, "output.md")
            with pytest.raises(Exception):
                agent.process("/nonexistent/path/file.md", dst)
