# SAADIA Agent Assistant

A document editing and formatting agent that transforms drafts into
professionally structured publications.

## Features

| Capability | Details |
|---|---|
| **Format conversion** | Markdown ↔ Word (.docx) ↔ HTML ↔ Plain text |
| **Document type customisation** | Guidance documents, Instruction manuals, Process workflow docs |
| **Style enforcement** | Tone, heading case, list style, sentence length per type |
| **Vocabulary guidance** | Preferred terms, words to avoid, modal-verb rules |
| **Section scaffolding** | Detects missing recommended sections for each document type |
| **Image suggestions** | Recommends where to insert screenshots, diagrams, or flowcharts |
| **AI-assisted editing** | Optional OpenAI integration for content rewrites |
| **Version-based updates** | Pass a previous version as the base; the agent produces an updated version |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run from the command line

```bash
# Basic: reformat a document (auto-detects type)
python -m agent --input v1_manual.md --output v2_manual.md

# Specify document type and output format
python -m agent \
    --input   draft_policy.md \
    --output  policy_v2.html \
    --type    guidance \
    --format  html

# AI-assisted editing (requires OPENAI_API_KEY)
export OPENAI_API_KEY="sk-..."
python -m agent \
    --input        v1_manual.md \
    --output       v2_manual.md \
    --type         instruction_manual \
    --instructions "Update section 3 to reflect the new login flow."
```

**CLI options**

| Flag | Description |
|---|---|
| `--input` / `-i` | Source document path |
| `--output` / `-o` | Output document path |
| `--type` / `-t` | `guidance` \| `instruction_manual` \| `process_workflow` \| `general` |
| `--format` / `-f` | `markdown` \| `plain_text` \| `docx` \| `html` |
| `--instructions` | Editing instructions (AI-assisted mode) |
| `--no-style` | Skip type-specific style formatting |
| `--no-image-suggestions` | Suppress image placement suggestions |
| `--verbose` / `-v` | Print progress to stderr |

### 3. Use as a library

```python
from agent import DocumentAgent, AgentConfig, DocumentType, OutputFormat

config = AgentConfig(
    doc_type=DocumentType.INSTRUCTION_MANUAL,
    output_format=OutputFormat.MARKDOWN,
    openai_api_key="sk-...",   # optional
)
agent = DocumentAgent(config)
result = agent.process(
    input_path="v1_manual.md",
    output_path="v2_manual.md",
    instructions="Update section 3 to reflect the new login flow.",
)
print(result.summary)
```

---

## Document Types

### Guidance Document (`guidance`)
Authoritative, policy-level direction.
- Headings: Title Case with hierarchical numbering
- Modal verbs: *shall* (mandatory), *should* (recommended), *may* (permitted)
- Sections: Purpose, Scope, Definitions, Roles & Responsibilities, Policy Statements, Procedures, References

### Instruction Manual (`instruction_manual`)
Step-by-step task guides.
- Each step begins with an imperative verb (*Click*, *Select*, *Enter*)
- One action per step
- Callout types: NOTE, TIP, WARNING, CAUTION, IMPORTANT
- Screenshots recommended for every non-obvious UI step

### Process Workflow Documentation (`process_workflow`)
End-to-end business or technical process descriptions.
- Paired with a flowchart or swimlane diagram
- Includes RACI table, inputs/outputs, decision points, and SLAs
- Standard BPMN or flowchart notation for diagrams

---

## Project Layout

```
agent/
  __init__.py              Public API re-exports
  agent.py                 Main orchestrator + CLI entry point
  document_processor.py    Read / write / parse / format documents
  document_types.py        Type definitions, style guides, vocabulary
  format_converter.py      Format conversion helpers

examples/
  guidance_template.md           Sample guidance document
  instruction_manual_template.md Sample instruction manual
  process_workflow_template.md   Sample process workflow doc

tests/
  test_agent.py
  test_document_processor.py
  test_document_types.py
  test_format_converter.py

requirements.txt
```

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## AI-Assisted Editing

Set the `OPENAI_API_KEY` environment variable (or pass `openai_api_key` in
`AgentConfig`) to unlock AI-powered content rewriting. The agent sends the
document and a type-specific system prompt to the OpenAI API and returns the
revised Markdown.

Without an API key the agent still applies all rule-based formatting,
vocabulary checks, missing-section detection, and image suggestions.
