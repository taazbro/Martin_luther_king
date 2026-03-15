# Plugin SDK

Plugins extend EduClawn without modifying the core engine.

## Location

Store plugins under `community/plugins/<plugin-id>/plugin.json`.

Each plugin can also ship a `README.md` in the same folder describing install and workflow expectations.

## Minimal Manifest

```json
{
  "id": "standards-mapper",
  "label": "Standards Mapper Pack",
  "version": "0.1.0",
  "description": "Adds curriculum-alignment metadata and rubric helpers.",
  "capabilities": ["rubrics", "teacher_review", "metadata"]
}
```

## Suggested Capability Categories

- `templates`
- `document_parsers`
- `rubrics`
- `teacher_review`
- `metadata`
- `design_tokens`
- `export_targets`
- `evaluations`

## Design Rules

- declare stable IDs and semantic versions
- keep plugin behavior local-first
- make every extension optional
- document any new files or conventions the plugin expects
- prefer additive behavior over changing core project manifests

## Plugin Ideas

- standards alignment packs
- oral history ingestion helpers
- science fair rubric packs
- map and timeline export helpers
- language-learning adaptation packs
- peer review workflow helpers
