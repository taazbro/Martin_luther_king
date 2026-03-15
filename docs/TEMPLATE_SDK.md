# Template SDK

Templates define how EduClawn turns a manifest plus source documents into a structured project.

## Location

Store template manifests in `studio/templates/*.json`.

Starter manifests for template authors can live in `community/template_starters/`.

## Required Fields

```json
{
  "id": "museum-exhibit-site",
  "label": "Museum Exhibit Site",
  "description": "Local exhibit builder for cited student work.",
  "project_type": "museum_exhibit_site",
  "category": "museum",
  "supports_simulation": false,
  "layout_direction": "gallery_grid",
  "export_targets": ["static_site", "pdf_report", "project_bundle"],
  "starter_prompts": ["Which sources anchor the exhibit?"],
  "theme_tokens": {
    "accent": "#47674f",
    "ink": "#1d201b",
    "paper": "#f2eee3",
    "font_display": "Baskerville",
    "font_body": "Spectral",
    "motion_style": "gallery fade"
  },
  "sections": [
    {
      "section_id": "curator-note",
      "title": "Curator Note",
      "objective": "Frame the exhibit thesis."
    }
  ],
  "workflow": [
    {
      "stage_id": "ingest",
      "label": "Ingest",
      "description": "Extract and index uploaded sources.",
      "enabled": true
    }
  ]
}
```

## Design Rules

- keep section IDs stable after release
- define enough sections for the writer and citation agents to target
- keep export targets compatible with deterministic generation
- do not depend on cloud-only model behavior
- prefer theme tokens that render well on both desktop and mobile

## Workflow Stages

Supported built-in stages:

- `ingest`
- `retrieve`
- `cite`
- `plan`
- `design`
- `export`

The studio compile endpoint will run enabled stages in order and persist the resulting artifacts and exports.

## Simulation Support

If `supports_simulation` is `true`, the planner and simulation blueprint will generate branch nodes from the evidence board.

## Testing

After adding a template:

1. create a project from it in the UI or API
2. upload at least one document
3. run compile
4. verify exports and citations render correctly

## Starter Workflow

If you are authoring a new template for open-source reuse:

1. copy a starter from `community/template_starters/`
2. create the final template manifest in `studio/templates/`
3. add one sample project in `community/sample_projects/`
4. document any companion plugin pack in `community/plugins/`
