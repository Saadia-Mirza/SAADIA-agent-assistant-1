"""
Document type definitions, style guides, and vocabulary recommendations.

Each document type carries:
- display_name: human-readable label
- description: one-line purpose
- style_guide: formatting rules (headings, lists, tone, etc.)
- vocabulary: preferred terms and phrases
- sections: recommended section structure
- image_guidance: when and how to include visuals
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class DocumentType(str, Enum):
    GUIDANCE = "guidance"
    INSTRUCTION_MANUAL = "instruction_manual"
    PROCESS_WORKFLOW = "process_workflow"
    GENERAL = "general"


@dataclass
class StyleGuide:
    tone: str
    heading_style: str
    list_style: str
    sentence_length: str
    paragraph_length: str
    use_active_voice: bool
    use_numbered_steps: bool
    notes: List[str] = field(default_factory=list)


@dataclass
class DocumentTypeSpec:
    document_type: DocumentType
    display_name: str
    description: str
    style_guide: StyleGuide
    vocabulary: Dict[str, List[str]]
    sections: List[str]
    image_guidance: str


# ---------------------------------------------------------------------------
# Guidance Document
# ---------------------------------------------------------------------------
GUIDANCE_SPEC = DocumentTypeSpec(
    document_type=DocumentType.GUIDANCE,
    display_name="Guidance Document",
    description=(
        "Provides authoritative, policy-level direction on a subject. "
        "Readers consult it to understand expectations and best practices."
    ),
    style_guide=StyleGuide(
        tone="formal and authoritative",
        heading_style="Title Case with hierarchical numbering (1, 1.1, 1.1.1)",
        list_style="bullet points for non-sequential items; numbered lists for ordered requirements",
        sentence_length="medium (15–25 words)",
        paragraph_length="3–5 sentences per paragraph",
        use_active_voice=True,
        use_numbered_steps=False,
        notes=[
            "Use 'shall' for mandatory requirements, 'should' for recommendations.",
            "Define acronyms on first use.",
            "Include a purpose statement in the introduction.",
            "Add a revision history table.",
        ],
    ),
    vocabulary={
        "preferred_verbs": ["ensure", "establish", "maintain", "require", "review", "verify"],
        "avoid": ["do", "stuff", "things", "get", "make sure"],
        "modal_verbs": {
            "mandatory": "shall",
            "recommended": "should",
            "permitted": "may",
            "prohibited": "shall not",
        },
        "common_phrases": [
            "in accordance with",
            "as outlined in",
            "subject to review",
            "consistent with",
            "as applicable",
        ],
        "industry_terms": [
            "wayside signaling",
            "interlocking",
            "signal aspect",
            "track occupancy",
            "fail-safe design",
            "TC CTC standards",
            "Transport Canada oversight",
        ],
    },
    sections=[
        "Cover Page",
        "Revision History",
        "Table of Contents",
        "1. Purpose",
        "2. Scope",
        "3. Definitions and Acronyms",
        "4. Roles and Responsibilities",
        "5. Policy / Guidance Statements",
        "6. Procedures",
        "7. References",
        "8. Appendices",
    ],
    image_guidance=(
        "Include diagrams for organizational hierarchies, decision trees, or "
        "regulatory frameworks. Label all figures with a caption and reference them "
        "in the body text (e.g., 'See Figure 1')."
    ),
)

# ---------------------------------------------------------------------------
# Instruction Manual
# ---------------------------------------------------------------------------
INSTRUCTION_MANUAL_SPEC = DocumentTypeSpec(
    document_type=DocumentType.INSTRUCTION_MANUAL,
    display_name="Instruction Manual",
    description=(
        "Step-by-step guide that enables a user to complete a specific task or "
        "operate a system. Clarity and precision are paramount."
    ),
    style_guide=StyleGuide(
        tone="clear, direct, and user-focused",
        heading_style="Sentence case; use task-oriented headings (e.g., 'Installing the software')",
        list_style="numbered steps for procedures; bullet points for prerequisites or notes",
        sentence_length="short to medium (10–20 words)",
        paragraph_length="1–3 sentences; each step should be a single action",
        use_active_voice=True,
        use_numbered_steps=True,
        notes=[
            "Begin each step with an imperative verb (Click, Enter, Select, Press).",
            "One action per step — do not combine multiple actions.",
            "Use callout boxes for warnings, cautions, and notes.",
            "Include a 'Before You Begin' / prerequisites section.",
        ],
    ),
    vocabulary={
        "step_verbs": [
            "click", "select", "enter", "type", "press", "choose",
            "navigate to", "open", "close", "save", "confirm", "verify",
        ],
        "avoid": ["you might want to", "perhaps", "maybe", "sort of"],
        "callout_types": ["NOTE", "TIP", "WARNING", "CAUTION", "IMPORTANT"],
        "common_phrases": [
            "To complete this task",
            "Before you begin",
            "Follow these steps",
            "When finished",
            "If you encounter",
        ],
        "industry_terms": [
            "wayside cabinet",
            "signal bungalow",
            "interlocking",
            "point machine",
            "balise",
            "axle counter",
            "vital relay",
            "commissioning checklist",
        ],
    },
    sections=[
        "Cover Page",
        "Table of Contents",
        "Introduction",
        "Safety / Warnings",
        "Prerequisites / Before You Begin",
        "Getting Started",
        "Procedures (numbered tasks)",
        "Troubleshooting",
        "Frequently Asked Questions",
        "Glossary",
        "Index",
    ],
    image_guidance=(
        "Include a screenshot or diagram for every non-obvious UI step. "
        "Annotate screenshots with numbered callouts that match step numbers. "
        "Use arrows, highlights, or boxes to draw attention to the relevant area."
    ),
)

# ---------------------------------------------------------------------------
# Process Workflow Documentation
# ---------------------------------------------------------------------------
PROCESS_WORKFLOW_SPEC = DocumentTypeSpec(
    document_type=DocumentType.PROCESS_WORKFLOW,
    display_name="Process Workflow Documentation",
    description=(
        "Describes a repeatable business or technical process end-to-end, "
        "including inputs, outputs, decision points, and responsible parties."
    ),
    style_guide=StyleGuide(
        tone="neutral and descriptive",
        heading_style="Title Case; use verb phrases (e.g., 'Approving a Request')",
        list_style="numbered steps within each sub-process; RACI table for responsibilities",
        sentence_length="short to medium (10–20 words)",
        paragraph_length="2–4 sentences for context; steps should be brief",
        use_active_voice=True,
        use_numbered_steps=True,
        notes=[
            "Pair each textual description with a flowchart or swimlane diagram.",
            "Clearly mark decision points (diamond shapes in diagrams).",
            "Specify inputs (triggers) and outputs (deliverables) for each step.",
            "Document the 'happy path' first, then exception/error paths.",
            "Include process owner, frequency, and SLA where applicable.",
        ],
    ),
    vocabulary={
        "process_verbs": [
            "initiate", "submit", "review", "approve", "reject",
            "notify", "escalate", "complete", "archive", "trigger",
        ],
        "avoid": ["do it", "handle it", "deal with"],
        "structural_terms": [
            "input", "output", "trigger", "decision point", "swimlane",
            "process owner", "stakeholder", "SLA", "exception path",
        ],
        "common_phrases": [
            "Upon receipt of",
            "This process is triggered by",
            "The responsible party shall",
            "In the event of",
            "Refer to [document] for",
        ],
        "industry_terms": [
            "movement authority",
            "route locking",
            "signal proving",
            "degraded mode operations",
            "maintenance possession",
            "block section release",
            "incident response control center",
        ],
    },
    sections=[
        "Cover Page",
        "Revision History",
        "Table of Contents",
        "1. Process Overview",
        "2. Scope and Applicability",
        "3. Process Roles (RACI)",
        "4. Process Inputs and Outputs",
        "5. Detailed Process Steps",
        "6. Decision Points and Exception Paths",
        "7. Process Flowchart / Swimlane Diagram",
        "8. Metrics and SLAs",
        "9. Related Documents",
        "10. Appendices",
    ],
    image_guidance=(
        "A flowchart or swimlane diagram is required. Place it prominently after "
        "the overview section. Each step in the diagram should have a matching "
        "reference number in the detailed steps table. Use standard BPMN or "
        "flowchart notation for shapes."
    ),
)

# ---------------------------------------------------------------------------
# General / Fallback
# ---------------------------------------------------------------------------
GENERAL_SPEC = DocumentTypeSpec(
    document_type=DocumentType.GENERAL,
    display_name="General Document",
    description="A general-purpose document with no specific type constraints.",
    style_guide=StyleGuide(
        tone="clear and professional",
        heading_style="Title Case",
        list_style="bullet points or numbered lists as appropriate",
        sentence_length="varies",
        paragraph_length="3–5 sentences",
        use_active_voice=True,
        use_numbered_steps=False,
        notes=[],
    ),
    vocabulary={
        "preferred_verbs": ["describe", "explain", "outline", "detail", "summarize"],
        "avoid": [],
        "common_phrases": [],
    },
    sections=[
        "Title",
        "Introduction",
        "Main Content",
        "Conclusion",
        "References",
    ],
    image_guidance=(
        "Include visuals where they add clarity. Caption all images and reference "
        "them in the body text."
    ),
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
DOCUMENT_TYPE_REGISTRY: Dict[DocumentType, DocumentTypeSpec] = {
    DocumentType.GUIDANCE: GUIDANCE_SPEC,
    DocumentType.INSTRUCTION_MANUAL: INSTRUCTION_MANUAL_SPEC,
    DocumentType.PROCESS_WORKFLOW: PROCESS_WORKFLOW_SPEC,
    DocumentType.GENERAL: GENERAL_SPEC,
}


def get_spec(doc_type: DocumentType) -> DocumentTypeSpec:
    """Return the DocumentTypeSpec for the given DocumentType."""
    return DOCUMENT_TYPE_REGISTRY[doc_type]


def detect_document_type(text: str) -> DocumentType:
    """
    Heuristic detection of document type based on keyword presence in the text.

    Returns the most likely DocumentType, falling back to GENERAL.
    """
    text_lower = text.lower()

    guidance_keywords = [
        "policy", "guidance", "shall", "requirement", "compliance",
        "regulation", "mandate", "standard", "directive",
        "railway", "signaling", "hitachi rail", "transport canada",
    ]
    instruction_keywords = [
        "step", "click", "select", "install", "press", "enter",
        "instruction", "how to", "procedure", "tutorial",
        "wayside", "interlocking", "point machine", "axle counter", "balise",
    ]
    workflow_keywords = [
        "workflow", "process", "swimlane", "flowchart", "trigger",
        "approval", "escalat", "raci", "decision point", "bpmn",
        "movement authority", "route locking", "track occupancy", "signal aspect",
    ]

    scores = {
        DocumentType.GUIDANCE: sum(1 for kw in guidance_keywords if kw in text_lower),
        DocumentType.INSTRUCTION_MANUAL: sum(1 for kw in instruction_keywords if kw in text_lower),
        DocumentType.PROCESS_WORKFLOW: sum(1 for kw in workflow_keywords if kw in text_lower),
    }

    best_type, best_score = max(scores.items(), key=lambda x: x[1])
    return best_type if best_score > 0 else DocumentType.GENERAL
