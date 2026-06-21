"""
Document Editing & Formatting Agent.

The agent takes a *previous version* of a document (or a fresh draft) and
produces a revised, properly-formatted version according to:

  1. The detected (or specified) document type
  2. The type-specific style guide and vocabulary
  3. User-supplied editing instructions
  4. Image / screenshot placeholder suggestions

Usage (programmatic)
---------------------
    from agent.agent import DocumentAgent, AgentConfig
    from agent.document_types import DocumentType
    from agent.document_processor import OutputFormat

    config = AgentConfig(
        doc_type=DocumentType.INSTRUCTION_MANUAL,
        output_format=OutputFormat.MARKDOWN,
        openai_api_key="sk-...",   # optional — AI-powered editing
    )
    agent = DocumentAgent(config)
    result = agent.process(
        input_path="v1_manual.md",
        output_path="v2_manual.md",
        instructions="Update section 3 to reflect the new login flow.",
    )
    print(result.summary)

Usage (CLI)
-----------
    python -m agent.agent \\
        --input  v1_manual.md \\
        --output v2_manual.md \\
        --type   instruction_manual \\
        --format markdown \\
        --instructions "Update section 3 to reflect the new login flow."
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

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
from agent.document_types import (
    DocumentType,
    DocumentTypeSpec,
    detect_document_type,
    get_spec,
)
from agent.format_converter import load_document


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class AgentConfig:
    """Configuration for the DocumentAgent."""

    doc_type: Optional[DocumentType] = None
    """Override the auto-detected document type."""

    output_format: OutputFormat = OutputFormat.MARKDOWN
    """Target output format."""

    openai_api_key: Optional[str] = None
    """OpenAI API key for AI-powered editing.  Falls back to rule-based editing if not set."""

    openai_model: str = "gpt-4o"
    """OpenAI model to use for AI-powered editing."""

    suggest_images: bool = True
    """Whether to suggest image placeholder positions based on document type."""

    apply_style: bool = True
    """Whether to apply type-specific style formatting."""

    verbose: bool = False
    """Print detailed progress information."""


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    """Outcome of a document processing run."""

    document: Document
    output_path: str
    summary: str
    missing_sections: List[str] = field(default_factory=list)
    image_suggestions: List[str] = field(default_factory=list)
    vocabulary_notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class DocumentAgent:
    """
    Orchestrates document editing, formatting, and format conversion.

    The agent can operate in two modes:
    - **Rule-based** (default): applies style guides, detects missing sections,
      suggests image placements, and flags vocabulary issues.
    - **AI-assisted**: additionally uses the OpenAI API to rewrite or expand
      content according to the instructions provided.
    """

    def __init__(self, config: Optional[AgentConfig] = None) -> None:
        self.config = config or AgentConfig()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(
        self,
        input_path: str,
        output_path: str,
        instructions: str = "",
    ) -> AgentResult:
        """
        Process a document: load, edit, format, and write to *output_path*.

        Parameters
        ----------
        input_path:   Path to the source document (previous version).
        output_path:  Path for the updated document.
        instructions: Free-text editing instructions, e.g.
                      "Update section 3 to reflect the new login flow."
        """
        self._log(f"Loading document: {input_path}")
        doc = load_document(input_path, self.config.doc_type)

        return self._process_document(doc, output_path, instructions)

    def process_text(
        self,
        text: str,
        output_path: str,
        instructions: str = "",
        input_is_markdown: bool = True,
    ) -> AgentResult:
        """
        Process document text directly (no file input required).
        """
        doc_type = self.config.doc_type or detect_document_type(text)
        if input_is_markdown:
            doc = parse_markdown_to_document(text, doc_type)
        else:
            doc = parse_text_to_document(text, doc_type)

        return self._process_document(doc, output_path, instructions)

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    def _process_document(
        self,
        doc: Document,
        output_path: str,
        instructions: str,
    ) -> AgentResult:
        spec = get_spec(doc.doc_type)
        warnings: List[str] = []
        image_suggestions: List[str] = []
        vocabulary_notes: List[str] = []

        self._log(f"Document type detected: {spec.display_name}")

        # 1. AI-assisted content editing (if API key provided)
        if instructions and self.config.openai_api_key:
            self._log("Applying AI-assisted edits …")
            doc = self._apply_ai_edits(doc, spec, instructions)
        elif instructions:
            self._log("No OpenAI API key — skipping AI-assisted edits.")
            warnings.append(
                "AI-assisted editing was requested but no OPENAI_API_KEY is set. "
                "Set the environment variable or pass openai_api_key in AgentConfig."
            )

        # 2. Apply type-specific style formatting
        if self.config.apply_style:
            self._log("Applying type-specific formatting …")
            doc = apply_type_formatting(doc, spec)

        # 3. Detect missing recommended sections
        missing = suggest_missing_sections(doc, spec)
        if missing:
            warnings.append(f"Recommended sections not found: {', '.join(missing)}")

        # 4. Suggest image placements
        if self.config.suggest_images:
            image_suggestions = self._suggest_image_placements(doc, spec)
            self._log(f"Image suggestions: {len(image_suggestions)}")

        # 5. Vocabulary notes
        vocabulary_notes = self._check_vocabulary(doc, spec)

        # 6. Write output
        self._log(f"Writing output to: {output_path}")
        write_document(doc, output_path, self.config.output_format)

        summary = self._build_summary(doc, spec, missing, image_suggestions, vocabulary_notes, warnings)

        return AgentResult(
            document=doc,
            output_path=output_path,
            summary=summary,
            missing_sections=missing,
            image_suggestions=image_suggestions,
            vocabulary_notes=vocabulary_notes,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # AI editing
    # ------------------------------------------------------------------

    def _apply_ai_edits(
        self,
        doc: Document,
        spec: DocumentTypeSpec,
        instructions: str,
    ) -> Document:
        """
        Use the OpenAI API to apply the user's editing instructions to the
        document, guided by the document type's style guide.
        """
        try:
            from openai import OpenAI
        except ImportError:
            return doc  # graceful degradation

        client = OpenAI(api_key=self.config.openai_api_key)

        system_prompt = textwrap.dedent(f"""
            You are an expert technical writer specialising in {spec.display_name}s.

            Style guide:
            - Tone: {spec.style_guide.tone}
            - Heading style: {spec.style_guide.heading_style}
            - List style: {spec.style_guide.list_style}
            - Sentence length: {spec.style_guide.sentence_length}
            - Use active voice: {spec.style_guide.use_active_voice}
            {"- Begin steps with imperative verbs." if spec.style_guide.use_numbered_steps else ""}

            Additional rules:
            {chr(10).join(f"- {n}" for n in spec.style_guide.notes)}

            Return ONLY the revised Markdown document.  Do not add commentary.
        """).strip()

        user_prompt = textwrap.dedent(f"""
            Here is the current document in Markdown:

            ---
            {doc.as_markdown()}
            ---

            Editing instructions:
            {instructions}

            Please apply the instructions and reformat the document according to the style guide.
        """).strip()

        response = client.chat.completions.create(
            model=self.config.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        revised_md = response.choices[0].message.content or ""
        return parse_markdown_to_document(revised_md, doc.doc_type)

    # ------------------------------------------------------------------
    # Heuristic helpers
    # ------------------------------------------------------------------

    def _suggest_image_placements(
        self, doc: Document, spec: DocumentTypeSpec
    ) -> List[str]:
        """Return natural-language suggestions for where to insert images."""
        suggestions: List[str] = []
        for sec in doc.sections:
            content_lower = sec.content.lower()
            # Suggest screenshots for step-heavy sections
            if spec.document_type == DocumentType.INSTRUCTION_MANUAL:
                import re
                step_count = len(re.findall(r"^\s*\d+\.", sec.content, re.MULTILINE))
                if step_count >= 2 and not sec.images:
                    suggestions.append(
                        f"Add annotated screenshot(s) to section '{sec.heading}' "
                        f"(contains {step_count} numbered steps)."
                    )
            # Suggest flowchart for process workflow overviews
            elif spec.document_type == DocumentType.PROCESS_WORKFLOW:
                if any(kw in content_lower for kw in ("overview", "process", "workflow")) and not sec.images:
                    suggestions.append(
                        f"Add a flowchart or swimlane diagram to section '{sec.heading}'."
                    )
            # Suggest diagrams for guidance documents' scope/procedure sections
            elif spec.document_type == DocumentType.GUIDANCE:
                if any(kw in content_lower for kw in ("procedure", "scope", "responsibility")) and not sec.images:
                    suggestions.append(
                        f"Consider adding a diagram or decision tree to section '{sec.heading}'."
                    )

        # Always remind if no images at all
        if not any(sec.images for sec in doc.sections):
            suggestions.append(spec.image_guidance)

        return suggestions

    def _check_vocabulary(
        self, doc: Document, spec: DocumentTypeSpec
    ) -> List[str]:
        """Flag vocabulary issues based on the doc type's vocabulary guide."""
        notes: List[str] = []
        full_text = doc.plain_text().lower()

        avoid = spec.vocabulary.get("avoid", [])
        for term in avoid:
            if term.lower() in full_text:
                notes.append(
                    f"Consider replacing '{term}' with more appropriate vocabulary "
                    f"for a {spec.display_name}."
                )

        # Guidance documents: check modal verb usage
        if spec.document_type == DocumentType.GUIDANCE:
            modal_verbs = spec.vocabulary.get("modal_verbs", {})
            if isinstance(modal_verbs, dict):
                if "must" in full_text and "shall" not in full_text:
                    notes.append(
                        "Use 'shall' instead of 'must' for mandatory requirements "
                        "in Guidance Documents."
                    )

        return notes

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _build_summary(
        self,
        doc: Document,
        spec: DocumentTypeSpec,
        missing: List[str],
        image_suggestions: List[str],
        vocabulary_notes: List[str],
        warnings: List[str],
    ) -> str:
        lines = [
            f"Document: {doc.title}",
            f"Type:     {spec.display_name}",
            f"Sections: {len(doc.sections)}",
        ]

        if missing:
            lines.append("\nMissing recommended sections:")
            lines += [f"  - {s}" for s in missing]

        if image_suggestions:
            lines.append("\nImage / graphic suggestions:")
            lines += [f"  • {s}" for s in image_suggestions]

        if vocabulary_notes:
            lines.append("\nVocabulary notes:")
            lines += [f"  ⚠  {n}" for n in vocabulary_notes]

        if warnings:
            lines.append("\nWarnings:")
            lines += [f"  ! {w}" for w in warnings]

        return "\n".join(lines)

    def _log(self, msg: str) -> None:
        if self.config.verbose:
            print(f"[agent] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m agent.agent",
        description="Document Editing & Formatting Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Examples:
              python -m agent.agent --input v1.md --output v2.md
              python -m agent.agent --input draft.docx --output manual.md --type instruction_manual
              python -m agent.agent --input policy.md --output policy_v2.html --type guidance \\
                                    --instructions "Add a new section on data retention."
        """),
    )
    parser.add_argument("--input", "-i", required=True, help="Path to the source document")
    parser.add_argument("--output", "-o", required=True, help="Path for the updated document")
    parser.add_argument(
        "--type", "-t",
        choices=[dt.value for dt in DocumentType],
        default=None,
        help="Override document type (default: auto-detect)",
    )
    parser.add_argument(
        "--format", "-f",
        choices=[fmt.value for fmt in OutputFormat],
        default=None,
        help="Override output format (default: inferred from --output extension)",
    )
    parser.add_argument(
        "--instructions",
        default="",
        help="Editing instructions for the AI-assisted mode",
    )
    parser.add_argument(
        "--no-style",
        action="store_true",
        help="Skip type-specific style formatting",
    )
    parser.add_argument(
        "--no-image-suggestions",
        action="store_true",
        help="Suppress image placement suggestions",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = _parse_args(argv)

    doc_type = DocumentType(args.type) if args.type else None
    output_format = OutputFormat(args.format) if args.format else None

    config = AgentConfig(
        doc_type=doc_type,
        output_format=output_format or OutputFormat.MARKDOWN,
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        apply_style=not args.no_style,
        suggest_images=not args.no_image_suggestions,
        verbose=args.verbose,
    )

    agent = DocumentAgent(config)
    result = agent.process(
        input_path=args.input,
        output_path=args.output,
        instructions=args.instructions,
    )

    print(result.summary)


if __name__ == "__main__":
    main()
