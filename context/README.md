# Context

This folder holds reference material that gives the agent more context before
you prompt it to do a task. Anything you add here (notes, policies,
requirements, publications, data) will be read by the agent on its next run.

## How to add your files

- **GitHub web UI:** Open this folder, then **Add file → Upload files** and drag
  your documents in.
- **Git:** Copy files into this `context/` folder, then `git add`, `git commit`,
  and `git push`.

## Tips for best results

- Plain-text formats (`.md`, `.txt`, `.csv`, `.json`) are read most reliably.
- `.pdf` and `.docx` work, but pasting the key content into a Markdown file
  gives the cleanest results.
- Keep related material together and give files clear, descriptive names.

## Suggested files

- `overview.md` — what this project is and its goals
- `requirements.md` — what you want the agent to build or do
- `domain-notes.md` — background knowledge, terminology, and policies
- `publications/` — publication documents and related policies (e.g. the
  "4.2 Document Management" doc and Publications policy docs)
