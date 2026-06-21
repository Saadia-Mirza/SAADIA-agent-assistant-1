"""Tests for agent.document_types."""

import pytest

from agent.document_types import (
    DocumentType,
    DOCUMENT_TYPE_REGISTRY,
    detect_document_type,
    get_spec,
    GUIDANCE_SPEC,
    INSTRUCTION_MANUAL_SPEC,
    PROCESS_WORKFLOW_SPEC,
    GENERAL_SPEC,
)


class TestDocumentTypeRegistry:
    def test_all_types_in_registry(self):
        for dt in DocumentType:
            assert dt in DOCUMENT_TYPE_REGISTRY

    def test_get_spec_returns_correct_spec(self):
        assert get_spec(DocumentType.GUIDANCE) is GUIDANCE_SPEC
        assert get_spec(DocumentType.INSTRUCTION_MANUAL) is INSTRUCTION_MANUAL_SPEC
        assert get_spec(DocumentType.PROCESS_WORKFLOW) is PROCESS_WORKFLOW_SPEC
        assert get_spec(DocumentType.GENERAL) is GENERAL_SPEC

    def test_specs_have_required_fields(self):
        for dt, spec in DOCUMENT_TYPE_REGISTRY.items():
            assert spec.display_name
            assert spec.description
            assert spec.style_guide is not None
            assert len(spec.sections) > 0
            assert spec.image_guidance


class TestDocumentTypeSpecs:
    def test_guidance_uses_title_case_headings(self):
        assert "Title Case" in GUIDANCE_SPEC.style_guide.heading_style

    def test_instruction_manual_uses_numbered_steps(self):
        assert INSTRUCTION_MANUAL_SPEC.style_guide.use_numbered_steps is True

    def test_process_workflow_uses_numbered_steps(self):
        assert PROCESS_WORKFLOW_SPEC.style_guide.use_numbered_steps is True

    def test_guidance_has_modal_verbs(self):
        modal = GUIDANCE_SPEC.vocabulary.get("modal_verbs", {})
        assert isinstance(modal, dict)
        assert "mandatory" in modal
        assert modal["mandatory"] == "shall"

    def test_instruction_manual_has_step_verbs(self):
        verbs = INSTRUCTION_MANUAL_SPEC.vocabulary.get("step_verbs", [])
        assert "click" in verbs
        assert "select" in verbs

    def test_instruction_manual_includes_rail_signaling_terms(self):
        terms = INSTRUCTION_MANUAL_SPEC.vocabulary.get("industry_terms", [])
        assert "interlocking" in terms
        assert "axle counter" in terms

    def test_process_workflow_includes_rail_signaling_terms(self):
        terms = PROCESS_WORKFLOW_SPEC.vocabulary.get("industry_terms", [])
        assert "movement authority" in terms
        assert "route locking" in terms

    def test_guidance_sections_include_purpose(self):
        section_names_lower = [s.lower() for s in GUIDANCE_SPEC.sections]
        assert any("purpose" in s for s in section_names_lower)

    def test_process_workflow_sections_include_flowchart(self):
        section_names_lower = [s.lower() for s in PROCESS_WORKFLOW_SPEC.sections]
        assert any("flowchart" in s or "diagram" in s for s in section_names_lower)


class TestDetectDocumentType:
    def test_detects_guidance_from_policy_text(self):
        text = "This policy shall apply to all employees. Compliance is mandatory."
        assert detect_document_type(text) == DocumentType.GUIDANCE

    def test_detects_instruction_manual_from_step_text(self):
        text = "Step 1: Click the button. Step 2: Enter your password. Step 3: Press OK."
        assert detect_document_type(text) == DocumentType.INSTRUCTION_MANUAL

    def test_detects_process_workflow_from_workflow_text(self):
        text = "The workflow is triggered by a new request. Refer to the swimlane diagram."
        assert detect_document_type(text) == DocumentType.PROCESS_WORKFLOW

    def test_falls_back_to_general_for_empty_text(self):
        assert detect_document_type("") == DocumentType.GENERAL

    def test_falls_back_to_general_for_ambiguous_text(self):
        text = "The quick brown fox jumps over the lazy dog."
        assert detect_document_type(text) == DocumentType.GENERAL

    def test_detects_guidance_with_requirement_keyword(self):
        text = "All systems shall meet the security requirements defined herein."
        assert detect_document_type(text) == DocumentType.GUIDANCE

    def test_detects_instruction_manual_from_signaling_terms(self):
        text = "Step 1: Open the wayside cabinet and verify interlocking status."
        assert detect_document_type(text) == DocumentType.INSTRUCTION_MANUAL

    def test_detects_process_workflow_from_signaling_terms(self):
        text = "This workflow controls movement authority and route locking through signaling."
        assert detect_document_type(text) == DocumentType.PROCESS_WORKFLOW
