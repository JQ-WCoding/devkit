# Blueprint: visual-docs skill

Saves findings to `docs/` as Markdown docs with Mermaid diagrams and tables.

## Description skeleton

`Writes and updates explanation docs with Mermaid diagrams (sequenceDiagram, flowchart, stateDiagram, erDiagram) and tables in the {{project}} repo's docs/. Use when asked to document a process flow, sequence diagram, structure diagram or ERD, or to update an existing explanation doc. Not for pictures shown only in chat, HTML pages, or automatic documentation of findings.`

## Criteria for the body

- Write only on request. Before creating a file, look for the same topic in `docs/` and edit that doc if found. File names are short kebab-case.
- Confirm the current implementation and measurements from source and logs, and separate measured facts from guesses. Write a one- or two-sentence conclusion first.
- Picking a diagram: request/event order → sequence, structure/branches → flowchart, lifecycle → state, data relations → er, numbers → table.
- Exact values go in a table next to the diagram; at the end, sources as paths relative to `docs/` and assumptions not verified.
- Do not mix different things such as first visit vs cache hit, or HTTP requests vs DB queries. No secrets or production identifiers.
- Before finishing: check diagrams and tables agree, Mermaid fences pair up, and source links open. Do not change app code or commit because of the doc ({{if: docs/ is tracked by Git — commit on request with devkit:commit}}).
