from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error as urllib_error, request as urllib_request
from uuid import uuid4

import numpy as np
import yaml
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from app.core.config import Settings
from app.services.studio_agents import ProjectAgentRuntime
from app.services.provider_ai import ProviderAIService
from app.services.warehouse import WarehouseService


BUILTIN_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "id": "mlk-legacy-lab",
        "label": "MLK Legacy Lab",
        "description": "An interactive civil-rights learning experience with analytics, historical evidence, and local mission planning.",
        "project_type": "interactive_history_app",
        "category": "history",
        "supports_simulation": True,
        "layout_direction": "immersive_story_panels",
        "export_targets": ["static_site", "react_app", "pdf_report", "project_bundle"],
        "starter_prompts": [
            "Which movement scene anchors the project?",
            "What should students understand by the end?",
            "Which sources must be preserved as evidence?",
        ],
        "theme_tokens": {
            "accent": "#cf7f2e",
            "ink": "#1e3547",
            "paper": "#f8f1e3",
            "font_display": "Baskerville",
            "font_body": "Source Serif",
            "motion_style": "staggered archival reveal",
        },
        "sections": [
            {"section_id": "introduction", "title": "Introduction", "objective": "Frame the core historical question."},
            {"section_id": "timeline", "title": "Timeline", "objective": "Show chronology and turning points."},
            {"section_id": "evidence", "title": "Evidence Gallery", "objective": "Display cited documents and annotations."},
            {"section_id": "reflection", "title": "Reflection", "objective": "Connect the history to civic understanding."},
        ],
        "workflow": [
            {"stage_id": "ingest", "label": "Ingest", "description": "Extract and index uploaded sources.", "enabled": True},
            {"stage_id": "retrieve", "label": "Retrieve", "description": "Rank evidence for the project goals.", "enabled": True},
            {"stage_id": "cite", "label": "Cite", "description": "Attach provenance to sections.", "enabled": True},
            {"stage_id": "plan", "label": "Plan", "description": "Build the project graph and outline.", "enabled": True},
            {"stage_id": "design", "label": "Design", "description": "Apply theme and presentation tokens.", "enabled": True},
            {"stage_id": "export", "label": "Export", "description": "Generate local project bundles.", "enabled": True},
        ],
    },
    {
        "id": "research-portfolio",
        "label": "Research Portfolio",
        "description": "A cited local research portfolio for essays, panels, and document interpretation.",
        "project_type": "research_portfolio",
        "category": "research",
        "supports_simulation": False,
        "layout_direction": "editorial_columns",
        "export_targets": ["static_site", "pdf_report", "project_bundle"],
        "starter_prompts": ["What claim is the portfolio defending?", "Which documents matter most?", "Who is the intended reviewer?"],
        "theme_tokens": {
            "accent": "#23527a",
            "ink": "#1f1b16",
            "paper": "#f7f2e8",
            "font_display": "Iowan Old Style",
            "font_body": "Georgia",
            "motion_style": "subtle reveal",
        },
        "sections": [
            {"section_id": "claim", "title": "Research Claim", "objective": "State the argument or inquiry."},
            {"section_id": "source-matrix", "title": "Source Matrix", "objective": "Compare and classify sources."},
            {"section_id": "analysis", "title": "Analysis", "objective": "Interpret evidence and connect themes."},
            {"section_id": "bibliography", "title": "Annotated Bibliography", "objective": "Track citations and takeaways."},
        ],
        "workflow": [
            {"stage_id": "ingest", "label": "Ingest", "description": "Extract and index uploaded sources.", "enabled": True},
            {"stage_id": "retrieve", "label": "Retrieve", "description": "Rank evidence for the project goals.", "enabled": True},
            {"stage_id": "cite", "label": "Cite", "description": "Attach provenance to sections.", "enabled": True},
            {"stage_id": "plan", "label": "Plan", "description": "Build the project graph and outline.", "enabled": True},
            {"stage_id": "design", "label": "Design", "description": "Apply theme and presentation tokens.", "enabled": True},
            {"stage_id": "export", "label": "Export", "description": "Generate local project bundles.", "enabled": True},
        ],
    },
    {
        "id": "civic-campaign-simulator",
        "label": "Civic Campaign Simulator",
        "description": "A branching local simulator for strategy, public messaging, and tradeoff analysis.",
        "project_type": "civic_campaign_simulator",
        "category": "simulation",
        "supports_simulation": True,
        "layout_direction": "decision_map",
        "export_targets": ["static_site", "react_app", "pdf_report", "project_bundle"],
        "starter_prompts": ["What civic problem are students navigating?", "Which decisions should branch?", "What evidence should constrain choices?"],
        "theme_tokens": {
            "accent": "#8f321f",
            "ink": "#1e3547",
            "paper": "#f6ede1",
            "font_display": "Palatino",
            "font_body": "Source Sans 3",
            "motion_style": "branch transitions",
        },
        "sections": [
            {"section_id": "brief", "title": "Challenge Brief", "objective": "Introduce the decision environment."},
            {"section_id": "stakeholders", "title": "Stakeholders", "objective": "Map competing interests and constraints."},
            {"section_id": "branches", "title": "Decision Branches", "objective": "Turn evidence into branching choices."},
            {"section_id": "debrief", "title": "Debrief", "objective": "Explain outcomes and learning signals."},
        ],
        "workflow": [
            {"stage_id": "ingest", "label": "Ingest", "description": "Extract and index uploaded sources.", "enabled": True},
            {"stage_id": "retrieve", "label": "Retrieve", "description": "Rank evidence for the project goals.", "enabled": True},
            {"stage_id": "cite", "label": "Cite", "description": "Attach provenance to sections.", "enabled": True},
            {"stage_id": "plan", "label": "Plan", "description": "Build the project graph and outline.", "enabled": True},
            {"stage_id": "design", "label": "Design", "description": "Apply theme and presentation tokens.", "enabled": True},
            {"stage_id": "export", "label": "Export", "description": "Generate local project bundles.", "enabled": True},
        ],
    },
    {
        "id": "museum-exhibit-site",
        "label": "Museum Exhibit Site",
        "description": "A local exhibit builder for captions, object labels, timelines, and curator notes.",
        "project_type": "museum_exhibit_site",
        "category": "museum",
        "supports_simulation": False,
        "layout_direction": "gallery_grid",
        "export_targets": ["static_site", "pdf_report", "project_bundle"],
        "starter_prompts": ["Which objects or sources anchor the exhibit?", "What story should each gallery room tell?", "How should visitors move through it?"],
        "theme_tokens": {
            "accent": "#47674f",
            "ink": "#1d201b",
            "paper": "#f2eee3",
            "font_display": "Baskerville",
            "font_body": "Spectral",
            "motion_style": "gallery fade",
        },
        "sections": [
            {"section_id": "curator-note", "title": "Curator Note", "objective": "Frame the exhibit thesis."},
            {"section_id": "gallery", "title": "Gallery", "objective": "Present sources as artifacts with captions."},
            {"section_id": "timeline", "title": "Timeline", "objective": "Show chronology and movement across rooms."},
            {"section_id": "visitor-guide", "title": "Visitor Guide", "objective": "Support interpretation and reflection."},
        ],
        "workflow": [
            {"stage_id": "ingest", "label": "Ingest", "description": "Extract and index uploaded sources.", "enabled": True},
            {"stage_id": "retrieve", "label": "Retrieve", "description": "Rank evidence for the project goals.", "enabled": True},
            {"stage_id": "cite", "label": "Cite", "description": "Attach provenance to sections.", "enabled": True},
            {"stage_id": "plan", "label": "Plan", "description": "Build the project graph and outline.", "enabled": True},
            {"stage_id": "design", "label": "Design", "description": "Apply theme and presentation tokens.", "enabled": True},
            {"stage_id": "export", "label": "Export", "description": "Generate local project bundles.", "enabled": True},
        ],
    },
    {
        "id": "lesson-module",
        "label": "Lesson Module",
        "description": "A teacher-ready lesson module with objectives, evidence, activities, and review prompts.",
        "project_type": "lesson_module",
        "category": "education",
        "supports_simulation": False,
        "layout_direction": "lesson_stack",
        "export_targets": ["static_site", "pdf_report", "project_bundle"],
        "starter_prompts": ["What standard or skill does this lesson target?", "How should students interact with the evidence?", "What assessment closes the lesson?"],
        "theme_tokens": {
            "accent": "#6f4f9b",
            "ink": "#1c1730",
            "paper": "#f5effb",
            "font_display": "Book Antiqua",
            "font_body": "Atkinson Hyperlegible",
            "motion_style": "minimal",
        },
        "sections": [
            {"section_id": "objectives", "title": "Objectives", "objective": "Define the learning target and skills."},
            {"section_id": "materials", "title": "Materials", "objective": "List evidence, tools, and setup."},
            {"section_id": "activities", "title": "Activities", "objective": "Describe the lesson sequence."},
            {"section_id": "assessment", "title": "Assessment", "objective": "Explain how understanding is checked."},
        ],
        "workflow": [
            {"stage_id": "ingest", "label": "Ingest", "description": "Extract and index uploaded sources.", "enabled": True},
            {"stage_id": "retrieve", "label": "Retrieve", "description": "Rank evidence for the project goals.", "enabled": True},
            {"stage_id": "cite", "label": "Cite", "description": "Attach provenance to sections.", "enabled": True},
            {"stage_id": "plan", "label": "Plan", "description": "Build the project graph and outline.", "enabled": True},
            {"stage_id": "design", "label": "Design", "description": "Apply theme and presentation tokens.", "enabled": True},
            {"stage_id": "export", "label": "Export", "description": "Generate local project bundles.", "enabled": True},
        ],
    },
    {
        "id": "documentary-story",
        "label": "Documentary Story Project",
        "description": "A documentary-style story with acts, scenes, evidence captions, and a printable brief.",
        "project_type": "documentary_story",
        "category": "storytelling",
        "supports_simulation": False,
        "layout_direction": "scene_scroll",
        "export_targets": ["static_site", "react_app", "pdf_report", "project_bundle"],
        "starter_prompts": ["What is the opening scene?", "Which voices carry the story?", "How should evidence appear on screen?"],
        "theme_tokens": {
            "accent": "#304b41",
            "ink": "#151515",
            "paper": "#f1ede7",
            "font_display": "Cormorant Garamond",
            "font_body": "Libre Baskerville",
            "motion_style": "cinematic panels",
        },
        "sections": [
            {"section_id": "opening", "title": "Opening Scene", "objective": "Introduce stakes and voice."},
            {"section_id": "acts", "title": "Acts", "objective": "Sequence the story into evidence-backed beats."},
            {"section_id": "voices", "title": "Voices and Sources", "objective": "Show perspectives and citations."},
            {"section_id": "closing", "title": "Closing Reflection", "objective": "Resolve the narrative and extend meaning."},
        ],
        "workflow": [
            {"stage_id": "ingest", "label": "Ingest", "description": "Extract and index uploaded sources.", "enabled": True},
            {"stage_id": "retrieve", "label": "Retrieve", "description": "Rank evidence for the project goals.", "enabled": True},
            {"stage_id": "cite", "label": "Cite", "description": "Attach provenance to sections.", "enabled": True},
            {"stage_id": "plan", "label": "Plan", "description": "Build the project graph and outline.", "enabled": True},
            {"stage_id": "design", "label": "Design", "description": "Apply theme and presentation tokens.", "enabled": True},
            {"stage_id": "export", "label": "Export", "description": "Generate local project bundles.", "enabled": True},
        ],
    },
    {
        "id": "science-fair-lab",
        "label": "Science Fair Lab",
        "description": "A local science fair builder for hypotheses, methods, data visuals, and evidence-backed conclusions.",
        "project_type": "science_fair_project",
        "category": "science",
        "supports_simulation": False,
        "layout_direction": "lab_notebook",
        "export_targets": ["static_site", "pdf_report", "project_bundle"],
        "starter_prompts": ["What question is being tested?", "Which evidence proves the result?", "How should students present the method?"],
        "theme_tokens": {
            "accent": "#2e6e62",
            "ink": "#162029",
            "paper": "#eef6f2",
            "font_display": "Avenir Next",
            "font_body": "IBM Plex Sans",
            "motion_style": "measured reveal",
        },
        "sections": [
            {"section_id": "question", "title": "Research Question", "objective": "State the problem and hypothesis."},
            {"section_id": "method", "title": "Method", "objective": "Explain procedure, controls, and materials."},
            {"section_id": "results", "title": "Results", "objective": "Show findings, tables, and evidence."},
            {"section_id": "conclusion", "title": "Conclusion", "objective": "Interpret the results and next steps."},
        ],
        "workflow": [
            {"stage_id": "ingest", "label": "Ingest", "description": "Extract and index uploaded sources.", "enabled": True},
            {"stage_id": "retrieve", "label": "Retrieve", "description": "Rank evidence for the project goals.", "enabled": True},
            {"stage_id": "cite", "label": "Cite", "description": "Attach provenance to sections.", "enabled": True},
            {"stage_id": "plan", "label": "Plan", "description": "Build the project graph and outline.", "enabled": True},
            {"stage_id": "design", "label": "Design", "description": "Apply theme and presentation tokens.", "enabled": True},
            {"stage_id": "export", "label": "Export", "description": "Generate local project bundles.", "enabled": True},
        ],
    },
    {
        "id": "debate-prep-kit",
        "label": "Debate Prep Kit",
        "description": "A structured debate builder for claims, rebuttals, evidence cards, and speaking notes.",
        "project_type": "debate_preparation",
        "category": "civics",
        "supports_simulation": True,
        "layout_direction": "argument_map",
        "export_targets": ["static_site", "pdf_report", "project_bundle"],
        "starter_prompts": ["What resolution is being debated?", "Which evidence supports each side?", "How should rebuttals be organized?"],
        "theme_tokens": {
            "accent": "#7b3a24",
            "ink": "#1d1f23",
            "paper": "#f8f1ea",
            "font_display": "Plantin",
            "font_body": "Merriweather Sans",
            "motion_style": "argument cascade",
        },
        "sections": [
            {"section_id": "resolution", "title": "Resolution", "objective": "Frame the debate question and position."},
            {"section_id": "case", "title": "Case Construction", "objective": "Build claims and supporting evidence."},
            {"section_id": "rebuttal", "title": "Rebuttal Bank", "objective": "Prepare responses to opposing arguments."},
            {"section_id": "delivery", "title": "Speaking Notes", "objective": "Convert evidence into usable speaking points."},
        ],
        "workflow": [
            {"stage_id": "ingest", "label": "Ingest", "description": "Extract and index uploaded sources.", "enabled": True},
            {"stage_id": "retrieve", "label": "Retrieve", "description": "Rank evidence for the project goals.", "enabled": True},
            {"stage_id": "cite", "label": "Cite", "description": "Attach provenance to sections.", "enabled": True},
            {"stage_id": "plan", "label": "Plan", "description": "Build the project graph and outline.", "enabled": True},
            {"stage_id": "design", "label": "Design", "description": "Apply theme and presentation tokens.", "enabled": True},
            {"stage_id": "export", "label": "Export", "description": "Generate local project bundles.", "enabled": True},
        ],
    },
    {
        "id": "reading-intervention-path",
        "label": "Reading Intervention Path",
        "description": "A scaffolded literacy support project with reading-level adaptation, evidence checks, and teacher review.",
        "project_type": "reading_intervention",
        "category": "literacy",
        "supports_simulation": False,
        "layout_direction": "support_track",
        "export_targets": ["static_site", "pdf_report", "project_bundle"],
        "starter_prompts": ["Which reading skill needs support?", "What evidence will students annotate?", "How should teacher scaffolds appear?"],
        "theme_tokens": {
            "accent": "#47609b",
            "ink": "#1a2238",
            "paper": "#f2f5fb",
            "font_display": "Century Schoolbook",
            "font_body": "Atkinson Hyperlegible",
            "motion_style": "guided steps",
        },
        "sections": [
            {"section_id": "focus", "title": "Skill Focus", "objective": "Define the reading target and support need."},
            {"section_id": "text-set", "title": "Text Set", "objective": "Organize leveled materials and annotations."},
            {"section_id": "practice", "title": "Practice Sequence", "objective": "Guide scaffolded reading moves and checks."},
            {"section_id": "reflection", "title": "Growth Reflection", "objective": "Track student progress and teacher notes."},
        ],
        "workflow": [
            {"stage_id": "ingest", "label": "Ingest", "description": "Extract and index uploaded sources.", "enabled": True},
            {"stage_id": "retrieve", "label": "Retrieve", "description": "Rank evidence for the project goals.", "enabled": True},
            {"stage_id": "cite", "label": "Cite", "description": "Attach provenance to sections.", "enabled": True},
            {"stage_id": "plan", "label": "Plan", "description": "Build the project graph and outline.", "enabled": True},
            {"stage_id": "design", "label": "Design", "description": "Apply theme and presentation tokens.", "enabled": True},
            {"stage_id": "export", "label": "Export", "description": "Generate local project bundles.", "enabled": True},
        ],
    },
)


DEFAULT_SAMPLE_PROJECTS: tuple[dict[str, Any], ...] = (
    {
        "title": "MLK Movement Strategy Exhibit",
        "slug": "mlk-movement-strategy-exhibit",
        "template_id": "mlk-legacy-lab",
        "summary": "Interactive civil-rights exhibit with timeline, evidence cards, and reflection prompts.",
    },
    {
        "title": "Community Water Justice Portfolio",
        "slug": "community-water-justice-portfolio",
        "template_id": "research-portfolio",
        "summary": "Research portfolio built from local policy documents, interviews, and maps.",
    },
    {
        "title": "Neighborhood Transit Campaign Simulator",
        "slug": "neighborhood-transit-campaign-simulator",
        "template_id": "civic-campaign-simulator",
        "summary": "Branching project on transit advocacy, coalition strategy, and evidence-led decisions.",
    },
)


DEFAULT_PLUGIN_PACKS: tuple[dict[str, Any], ...] = (
    {
        "id": "standards-mapper",
        "label": "Standards Mapper Pack",
        "version": "0.1.0",
        "description": "Adds curriculum-alignment metadata and standards-aware rubric extensions.",
        "capabilities": ["rubrics", "teacher_review", "metadata"],
    },
    {
        "id": "oral-history-pack",
        "label": "Oral History Pack",
        "version": "0.1.0",
        "description": "Adds interview-focused prompts, transcript parsing notes, and exhibit presets.",
        "capabilities": ["templates", "document_parsers", "design_tokens"],
    },
)


@dataclass(slots=True)
class WorkspaceIndex:
    chunk_records: list[dict[str, Any]]
    vectorizer: TfidfVectorizer | None
    projection: TruncatedSVD | None
    embeddings: np.ndarray


class TemplateRegistryService:
    def __init__(self, template_dir: Path, community_root: Path) -> None:
        self.template_dir = template_dir
        self.community_root = community_root
        self._ensure_builtins()

    def list_templates(self) -> list[dict[str, Any]]:
        return [self._load_json(path) for path in sorted(self.template_dir.glob("*.json"))]

    def get_template(self, template_id: str) -> dict[str, Any]:
        for template in self.list_templates():
            if template["id"] == template_id:
                return template
        raise KeyError(template_id)

    def list_sample_projects(self) -> list[dict[str, Any]]:
        sample_dir = self.community_root / "sample_projects"
        sample_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_default_samples(sample_dir)
        samples = []
        for path in sorted(sample_dir.glob("*.yaml")):
            with path.open("r", encoding="utf-8") as handle:
                samples.append(yaml.safe_load(handle) or {})
        return samples

    def list_plugins(self) -> list[dict[str, Any]]:
        plugin_dir = self.community_root / "plugins"
        plugin_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_default_plugins(plugin_dir)
        plugins = []
        for path in sorted(plugin_dir.glob("*/plugin.json")):
            plugins.append(self._load_json(path))
        return plugins

    def _ensure_builtins(self) -> None:
        self.template_dir.mkdir(parents=True, exist_ok=True)
        for template in BUILTIN_TEMPLATES:
            path = self.template_dir / f"{template['id']}.json"
            if not path.exists():
                path.write_text(json.dumps(template, indent=2), encoding="utf-8")

    def _ensure_default_samples(self, sample_dir: Path) -> None:
        for sample in DEFAULT_SAMPLE_PROJECTS:
            path = sample_dir / f"{sample['slug']}.yaml"
            if not path.exists():
                path.write_text(yaml.safe_dump(sample, sort_keys=False), encoding="utf-8")

    def _ensure_default_plugins(self, plugin_dir: Path) -> None:
        for plugin in DEFAULT_PLUGIN_PACKS:
            plugin_path = plugin_dir / plugin["id"]
            plugin_path.mkdir(parents=True, exist_ok=True)
            manifest_path = plugin_path / "plugin.json"
            if not manifest_path.exists():
                manifest_path.write_text(json.dumps(plugin, indent=2), encoding="utf-8")

    def _load_json(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)


class ProjectStudioService:
    def __init__(
        self,
        settings: Settings,
        warehouse: WarehouseService,
        template_registry: TemplateRegistryService,
        agent_runtime: ProjectAgentRuntime,
        ai_provider_service: ProviderAIService,
    ) -> None:
        self.settings = settings
        self.warehouse = warehouse
        self.template_registry = template_registry
        self.agent_runtime = agent_runtime
        self.ai_provider_service = ai_provider_service
        self.education_service: Any | None = None
        self.projects_dir = settings.studio_root_dir / "projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self._indices: dict[str, WorkspaceIndex] = {}
        self._rebuild_all_indices()

    def bind_education_service(self, education_service: Any) -> None:
        self.education_service = education_service

    def get_overview(self) -> dict[str, Any]:
        projects = self.list_projects()
        templates = self.template_registry.list_templates()
        plugins = self.template_registry.list_plugins()
        sample_projects = self.template_registry.list_sample_projects()
        document_total = sum(len(project["documents"]) for project in projects)
        export_total = sum(len(project["exports"]) for project in projects)
        return {
            "studio_name": self.settings.app_name,
            "local_modes": [
                {
                    "mode": "no-llm",
                    "supported": True,
                    "description": "Deterministic local generation, retrieval, provenance, and export.",
                },
                {
                    "mode": "local-llm",
                    "supported": bool(self.settings.local_llm_model),
                    "description": "Optional local model mode. Deterministic fallback remains available.",
                },
                {
                    "mode": "provider-ai",
                    "supported": True,
                    "description": "Use a saved provider profile from OpenAI, Anthropic, Gemini, Groq, Mistral, Cohere, or xAI.",
                },
            ],
            "install_modes": [
                {"mode": "desktop_app", "available": True, "description": "Electron desktop shell and packaged app workflow are available."},
                {"mode": "docker_compose", "available": True, "description": "Containerized local startup path is available."},
                {"mode": "developer_mode", "available": True, "description": "FastAPI + React local development path."},
            ],
            "counts": {
                "templates": len(templates),
                "projects": len(projects),
                "documents": document_total,
                "exports": export_total,
                "plugins": len(plugins),
            },
            "templates": templates,
            "sample_projects": sample_projects,
            "plugins": plugins,
        }

    def list_projects(self) -> list[dict[str, Any]]:
        projects = []
        for path in sorted(self.projects_dir.glob("*/project.yaml")):
            manifest = self._load_manifest(path.parent.name)
            projects.append(self._project_summary(manifest))
        return sorted(projects, key=lambda item: item["updated_at"], reverse=True)

    def get_project(self, slug: str) -> dict[str, Any]:
        manifest = self._load_manifest(slug)
        manifest["template"] = self.template_registry.get_template(manifest["template_id"])
        manifest["plugins"] = self.template_registry.list_plugins()
        return manifest

    def get_system_status(self, startup_status: dict[str, Any] | None = None) -> dict[str, Any]:
        ollama_models = self._fetch_ollama_models()
        tesseract_path = shutil.which("tesseract")
        release_notes = Path(
            os.getenv("EDUCLAWN_RELEASE_NOTES_PATH")
            or os.getenv("MLK_RELEASE_NOTES_PATH")
            or self.settings.root_dir / "desktop" / "RELEASE_NOTES.md"
        )
        packaged_app = Path(
            os.getenv("EDUCLAWN_PACKAGED_APP_PATH")
            or os.getenv("MLK_PACKAGED_APP_PATH")
            or self.settings.root_dir / "desktop" / "release" / "mac-arm64" / "EduClawn.app"
        )
        provider_profiles = self.ai_provider_service.list_profiles()
        return {
            "workspace_root": str(self.settings.studio_root_dir),
            "frontend_dist": str(self.settings.frontend_dist_dir),
            "startup": startup_status
            or {
                "mode": "eager" if self.settings.eager_model_training else "lazy",
                "state": "unknown",
                "models": "unknown",
                "snapshot": "unknown",
                "started_at": None,
                "completed_at": None,
                "last_error": "",
            },
            "tools": {
                "tesseract_available": bool(tesseract_path),
                "tesseract_path": tesseract_path,
            },
            "local_ai": {
                "configured_model": self.settings.local_llm_model,
                "base_url": self.settings.local_llm_base_url,
                "configured": bool(self.settings.local_llm_model),
                "ollama_reachable": bool(ollama_models),
                "available_models": ollama_models,
            },
            "provider_ai": {
                "configured_profiles": len(provider_profiles),
                "managed_profiles": len([profile for profile in provider_profiles if profile["auth_mode"] == "managed-subscription"]),
                "providers_available": len(self.ai_provider_service.provider_catalog()),
            },
            "portability": {
                "backup_export_type": "project_bundle",
                "import_supported": True,
                "duplicate_supported": True,
            },
            "release": {
                "desktop_version": os.getenv("EDUCLAWN_DESKTOP_VERSION")
                or os.getenv("MLK_DESKTOP_VERSION")
                or self._desktop_version(),
                "release_notes_path": str(release_notes),
                "packaged_app_path": str(packaged_app) if packaged_app.exists() else "",
            },
        }

    def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        template = self.template_registry.get_template(str(payload["template_id"]))
        slug = self._unique_slug(self._slugify(str(payload.get("slug") or payload["title"])))
        now = self._timestamp()
        project_id = f"project-{uuid4().hex[:10]}"
        rubric = payload.get("rubric") or [
            "Evidence Quality",
            "Clarity",
            "Audience Fit",
            "Design",
            "Revision Quality",
        ]

        manifest = {
            "version": "1.0",
            "project_id": project_id,
            "slug": slug,
            "title": str(payload["title"]),
            "summary": str(payload.get("summary") or ""),
            "topic": str(payload["topic"]),
            "audience": str(payload["audience"]),
            "goals": [str(item) for item in payload.get("goals", [])],
            "rubric": [str(item) for item in rubric],
            "template_id": template["id"],
            "template_label": template["label"],
            "project_type": template["project_type"],
            "local_mode": str(payload.get("local_mode") or "no-llm"),
            "ai_profile_id": self._normalize_ai_profile_id(payload.get("ai_profile_id")),
            "status": "draft",
            "created_at": now,
            "updated_at": now,
            "theme_tokens": template["theme_tokens"],
            "workflow": {"stages": template["workflow"]},
            "sections": [
                {
                    "section_id": section["section_id"],
                    "title": section["title"],
                    "objective": section["objective"],
                    "content": "",
                    "citations": [],
                }
                for section in template["sections"]
            ],
            "documents": [],
            "artifacts": {},
            "exports": [],
            "teacher_review": None,
            "teacher_comments": [],
            "provenance": {"chunks": [], "updated_at": now},
            "simulation": {"enabled": template.get("supports_simulation", False), "nodes": [], "branches": []},
            "standards_alignment": self._build_standards_alignment(
                template=template,
                topic=str(payload["topic"]),
                goals=[str(item) for item in payload.get("goals", [])],
                rubric=[str(item) for item in rubric],
            ),
            "revision_history": [],
            "plugin_ids": [plugin["id"] for plugin in self.template_registry.list_plugins()],
            "classroom_context": dict(payload.get("classroom_context") or {}),
            "quality_gates": self._quality_gate_defaults(),
            "submission_readiness": self._empty_submission_readiness(),
        }
        self._record_revision(manifest, action="created", summary="Project manifest created from starter wizard.", actor="system")

        project_dir = self.projects_dir / slug
        (project_dir / "documents").mkdir(parents=True, exist_ok=True)
        (project_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        (project_dir / "exports").mkdir(parents=True, exist_ok=True)
        (project_dir / "provenance").mkdir(parents=True, exist_ok=True)
        self._write_manifest(slug, manifest)
        self._write_json(project_dir / "provenance" / "chunks.json", [])
        self._write_json(project_dir / "artifacts" / "knowledge_graph.json", self._empty_graph(manifest))

        self.warehouse.record_event(
            event_type="studio_project_created",
            source="studio_service",
            learner_id=slug,
            payload={"template_id": template["id"], "project_type": template["project_type"]},
        )
        return self.get_project(slug)

    def update_project(self, slug: str, payload: dict[str, Any]) -> dict[str, Any]:
        manifest = self._load_manifest(slug)
        editable_fields = {
            "title",
            "summary",
            "topic",
            "audience",
            "goals",
            "rubric",
            "local_mode",
            "theme_tokens",
            "ai_profile_id",
            "classroom_context",
            "quality_gates",
        }
        for field in editable_fields:
            if field in payload:
                manifest[field] = (
                    self._normalize_ai_profile_id(payload[field])
                    if field == "ai_profile_id"
                    else payload[field]
                )
        if "sections" in payload:
            manifest["sections"] = payload["sections"]
        if "workflow" in payload:
            manifest["workflow"] = payload["workflow"]
        manifest["standards_alignment"] = self._build_standards_alignment(
            template=self.template_registry.get_template(manifest["template_id"]),
            topic=manifest["topic"],
            goals=manifest.get("goals", []),
            rubric=manifest.get("rubric", []),
        )
        manifest["updated_at"] = self._timestamp()
        self._record_revision(
            manifest,
            action="updated",
            summary=f"Manifest updated: {', '.join(sorted(payload.keys()))}.",
            actor="author",
        )
        self._write_manifest(slug, manifest)
        self.warehouse.record_event(
            event_type="studio_project_updated",
            source="studio_service",
            learner_id=slug,
            payload={"fields": sorted(payload.keys())},
        )
        return self.get_project(slug)

    def clone_project(self, slug: str, new_title: str) -> dict[str, Any]:
        source_dir = self.projects_dir / slug
        if not source_dir.exists():
            raise FileNotFoundError(slug)
        new_slug = self._unique_slug(self._slugify(new_title))
        target_dir = self.projects_dir / new_slug
        shutil.copytree(source_dir, target_dir)
        manifest = self._load_manifest(new_slug)
        now = self._timestamp()
        manifest["project_id"] = f"project-{uuid4().hex[:10]}"
        manifest["slug"] = new_slug
        manifest["title"] = new_title
        manifest["created_at"] = now
        manifest["updated_at"] = now
        manifest["teacher_comments"] = []
        self._record_revision(manifest, action="cloned", summary=f"Project duplicated from {slug}.", actor="system")
        self._write_manifest(new_slug, manifest)
        self._rebuild_index(new_slug)
        self.warehouse.record_event(
            event_type="studio_project_cloned",
            source="studio_service",
            learner_id=new_slug,
            payload={"source_slug": slug},
        )
        return self.get_project(new_slug)

    def list_documents(self, slug: str) -> list[dict[str, Any]]:
        manifest = self._load_manifest(slug)
        return manifest["documents"]

    def ingest_document(
        self,
        slug: str,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        manifest = self._load_manifest(slug)
        project_dir = self.projects_dir / slug
        documents_dir = project_dir / "documents"
        safe_name = self._safe_filename(filename)
        document_id = f"doc-{uuid4().hex[:10]}"
        storage_path = documents_dir / f"{document_id}-{safe_name}"
        storage_path.write_bytes(content)

        extraction = self._extract_text(storage_path, content)
        chunk_records = self._chunk_text(document_id, safe_name, extraction["text"])
        existing_docs = manifest["documents"]
        duplicate_similarity = self._duplicate_similarity(extraction["text"], existing_docs)
        summary = self._summarize_text(extraction["text"])
        entities = self._extract_entities(extraction["text"])
        years = self._extract_years(extraction["text"])
        reading_level = self._reading_level(extraction["text"])

        document_record = {
            "document_id": document_id,
            "title": self._title_from_filename(safe_name),
            "file_name": safe_name,
            "content_type": content_type or "application/octet-stream",
            "source_path": str(storage_path.relative_to(project_dir)),
            "citation_label": f"{self._title_from_filename(safe_name)} ({document_id})",
            "summary": summary,
            "word_count": len(extraction["text"].split()),
            "reading_level": reading_level,
            "entities": entities[:8],
            "years": years[:8],
            "chunk_count": len(chunk_records),
            "duplicate_similarity": round(duplicate_similarity, 1),
            "extraction_method": extraction["method"],
            "ocr_status": extraction["ocr_status"],
            "uploaded_at": self._timestamp(),
        }
        existing_docs.append(document_record)

        all_chunks = self._load_chunks(slug)
        all_chunks = [chunk for chunk in all_chunks if chunk["document_id"] != document_id] + chunk_records
        manifest["documents"] = existing_docs
        manifest["provenance"] = {
            "chunks": [chunk["chunk_id"] for chunk in all_chunks],
            "updated_at": self._timestamp(),
        }
        manifest["updated_at"] = self._timestamp()
        self._record_revision(
            manifest,
            action="document_ingested",
            summary=f"Added source {document_record['file_name']} with {document_record['chunk_count']} chunks.",
            actor="author",
        )

        self._write_manifest(slug, manifest)
        self._write_json(project_dir / "provenance" / "chunks.json", all_chunks)
        graph = self.compile_knowledge_graph(slug)
        self._rebuild_index(slug)
        self.warehouse.record_event(
            event_type="studio_document_ingested",
            source="studio_service",
            learner_id=slug,
            payload={
                "document_id": document_id,
                "chunk_count": len(chunk_records),
                "extraction_method": extraction["method"],
            },
        )
        document_record["knowledge_graph_nodes"] = len(graph["nodes"])
        return document_record

    def import_project_bundle(self, filename: str, content: bytes, title: str | None = None) -> dict[str, Any]:
        bundle_name = self._safe_filename(filename)
        with tempfile.TemporaryDirectory(prefix="cps-import-") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            bundle_path = temp_dir / bundle_name
            bundle_path.write_bytes(content)
            with zipfile.ZipFile(bundle_path, "r") as archive:
                archive.extractall(temp_dir / "bundle")

            extracted_root = temp_dir / "bundle"
            manifest_path = extracted_root / "project.yaml"
            if not manifest_path.exists():
                raise FileNotFoundError("project.yaml")

            with manifest_path.open("r", encoding="utf-8") as handle:
                manifest = yaml.safe_load(handle) or {}

            new_title = title or str(manifest.get("title") or "Imported Project")
            new_slug = self._unique_slug(self._slugify(str(manifest.get("slug") or new_title)))
            target_dir = self.projects_dir / new_slug
            shutil.copytree(extracted_root, target_dir)
            imported_manifest = self._load_manifest(new_slug)
            now = self._timestamp()
            imported_manifest["project_id"] = f"project-{uuid4().hex[:10]}"
            imported_manifest["slug"] = new_slug
            imported_manifest["title"] = new_title
            imported_manifest["created_at"] = now
            imported_manifest["updated_at"] = now
            self._record_revision(imported_manifest, action="imported", summary=f"Imported from backup {bundle_name}.", actor="system")
            self._write_manifest(new_slug, imported_manifest)

        self._rebuild_index(new_slug)
        self.warehouse.record_event(
            event_type="studio_project_imported",
            source="studio_service",
            learner_id=new_slug,
            payload={"source_bundle": bundle_name},
        )
        return self.get_project(new_slug)

    def add_teacher_comment(self, slug: str, author: str, body: str, criterion: str | None = None) -> dict[str, Any]:
        manifest = self._load_manifest(slug)
        comment = {
            "comment_id": f"comment-{uuid4().hex[:8]}",
            "author": author.strip() or "teacher",
            "criterion": (criterion or "").strip(),
            "body": body.strip(),
            "created_at": self._timestamp(),
        }
        manifest["teacher_comments"].append(comment)
        manifest["updated_at"] = self._timestamp()
        self._record_revision(
            manifest,
            action="teacher_comment",
            summary=f"Teacher comment added by {comment['author']}.",
            actor=comment["author"],
        )
        self._write_manifest(slug, manifest)
        self.warehouse.record_event(
            event_type="studio_teacher_comment",
            source="studio_service",
            learner_id=slug,
            payload={"criterion": comment["criterion"] or "general"},
        )
        return self.get_project(slug)

    def search_project(self, slug: str, query: str, limit: int = 6) -> list[dict[str, Any]]:
        index = self._indices.get(slug)
        if index is None or not index.chunk_records:
            return []
        query_vector = self._encode_query(index, query)
        scores = index.embeddings @ query_vector
        ranked_indices = np.argsort(scores)[::-1][:limit]
        results = []
        for index_position in ranked_indices:
            chunk = index.chunk_records[int(index_position)]
            results.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "document_id": chunk["document_id"],
                    "citation_label": chunk["citation_label"],
                    "excerpt": chunk["excerpt"],
                    "score": round(float(max(0.0, scores[int(index_position)]) * 100.0), 1),
                    "match_reason": "semantic retrieval",
                }
            )
        return results

    def compile_knowledge_graph(self, slug: str) -> dict[str, Any]:
        manifest = self._load_manifest(slug)
        chunks = self._load_chunks(slug)
        nodes = [
            {"id": f"project-{slug}", "label": manifest["title"], "node_type": "project"},
            {"id": f"topic-{slug}", "label": manifest["topic"], "node_type": "topic"},
        ]
        edges = [{"source": f"project-{slug}", "target": f"topic-{slug}", "relationship": "about"}]
        seen_node_ids = {node["id"] for node in nodes}

        for document in manifest["documents"]:
            document_node = {"id": document["document_id"], "label": document["title"], "node_type": "document"}
            if document_node["id"] not in seen_node_ids:
                nodes.append(document_node)
                seen_node_ids.add(document_node["id"])
            edges.append({"source": f"project-{slug}", "target": document["document_id"], "relationship": "uses"})
            for entity in document.get("entities", [])[:5]:
                entity_id = f"entity-{self._slugify(entity)}"
                if entity_id not in seen_node_ids:
                    nodes.append({"id": entity_id, "label": entity, "node_type": "entity"})
                    seen_node_ids.add(entity_id)
                edges.append({"source": document["document_id"], "target": entity_id, "relationship": "mentions"})
            for year in document.get("years", [])[:3]:
                year_id = f"year-{year}"
                if year_id not in seen_node_ids:
                    nodes.append({"id": year_id, "label": year, "node_type": "year"})
                    seen_node_ids.add(year_id)
                edges.append({"source": document["document_id"], "target": year_id, "relationship": "dates"})

        highlights = [
            f"{manifest['title']} links {len(manifest['documents'])} uploaded sources to {len(nodes)} graph nodes.",
            f"Template {manifest['template_label']} can reuse this graph for timeline, exhibit, or simulation views.",
            f"Topic {manifest['topic']} is now traceable through exact document and chunk provenance.",
        ]
        graph = {
            "nodes": nodes,
            "edges": edges,
            "highlights": highlights,
        }
        self._write_json(self.projects_dir / slug / "artifacts" / "knowledge_graph.json", graph)
        return graph

    def run_workflow(self, slug: str, stages: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        manifest = self._load_manifest(slug)
        template = self.template_registry.get_template(manifest["template_id"])
        workflow_stages = stages or manifest["workflow"]["stages"]
        query = " ".join([manifest["topic"], *manifest.get("goals", []), manifest["template_label"]]).strip()
        retrieval_results = self.search_project(slug, query or manifest["topic"], limit=8)
        graph = self.compile_knowledge_graph(slug)
        stage_results = []

        artifact_bundle: dict[str, Any] | None = None
        if any(stage["enabled"] for stage in workflow_stages if stage["stage_id"] in {"retrieve", "cite", "plan", "design"}):
            artifact_bundle = self.agent_runtime.run(
                manifest=manifest,
                template=template,
                documents=manifest["documents"],
                retrieval_results=retrieval_results,
                knowledge_graph=graph,
            )
            self._write_json(self.projects_dir / slug / "artifacts" / "artifact_bundle.json", artifact_bundle)
            manifest["artifacts"] = artifact_bundle["artifacts"]
            manifest["simulation"] = artifact_bundle["artifacts"]["simulation_blueprint"]
            manifest["teacher_review"] = artifact_bundle["artifacts"]["teacher_review"]
            manifest["standards_alignment"] = self._build_standards_alignment(
                template=template,
                topic=manifest["topic"],
                goals=manifest.get("goals", []),
                rubric=manifest.get("rubric", []),
            )
        manifest["submission_readiness"] = self._evaluate_submission_readiness(
            slug=slug,
            manifest=manifest,
            artifact_bundle=artifact_bundle,
        )

        exports = manifest.get("exports", [])
        for stage in workflow_stages:
            if not stage["enabled"]:
                stage_results.append({"stage_id": stage["stage_id"], "status": "skipped"})
                continue

            if stage["stage_id"] == "ingest":
                stage_results.append({"stage_id": "ingest", "status": "success", "details": {"documents": len(manifest["documents"])}})
            elif stage["stage_id"] == "retrieve":
                stage_results.append({"stage_id": "retrieve", "status": "success", "details": {"matches": len(retrieval_results)}})
            elif stage["stage_id"] == "cite":
                stage_results.append({"stage_id": "cite", "status": "success", "details": {"sections": len(manifest["sections"])}})
            elif stage["stage_id"] == "plan":
                stage_results.append({"stage_id": "plan", "status": "success", "details": {"graph_nodes": len(graph["nodes"])}})
            elif stage["stage_id"] == "design":
                stage_results.append({"stage_id": "design", "status": "success", "details": {"theme_tokens": len(template["theme_tokens"])}})
            elif stage["stage_id"] == "export":
                exports = self.export_project(slug, template=template, manifest=manifest, artifact_bundle=artifact_bundle)
                export_status = "success" if manifest["submission_readiness"]["ready_for_export"] else "blocked"
                stage_results.append(
                    {
                        "stage_id": "export",
                        "status": export_status,
                        "details": {
                            "exports": len(exports),
                            "ready_for_export": manifest["submission_readiness"]["ready_for_export"],
                            "blocking_reasons": manifest["submission_readiness"]["blocking_reasons"],
                        },
                    }
                )

        manifest["exports"] = exports
        manifest["status"] = "compiled" if manifest["submission_readiness"]["ready_for_export"] else "compiled_blocked"
        manifest["workflow"] = {"stages": workflow_stages}
        manifest["updated_at"] = self._timestamp()
        self._record_revision(
            manifest,
            action="compiled",
            summary=f"Workflow executed with {len([stage for stage in workflow_stages if stage['enabled']])} enabled stages.",
            actor="system",
        )
        self._write_manifest(slug, manifest)
        self.warehouse.record_event(
            event_type="studio_workflow_run",
            source="studio_service",
            learner_id=slug,
            payload={"stages": [stage["stage_id"] for stage in workflow_stages if stage["enabled"]]},
        )
        return {
            "project": self.get_project(slug),
            "workflow_results": stage_results,
            "retrieval_results": retrieval_results,
            "knowledge_graph": graph,
            "artifacts": artifact_bundle or self._load_artifact_bundle(slug),
            "exports": exports,
        }

    def export_project(
        self,
        slug: str,
        *,
        template: dict[str, Any] | None = None,
        manifest: dict[str, Any] | None = None,
        artifact_bundle: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        manifest = manifest or self._load_manifest(slug)
        template = template or self.template_registry.get_template(manifest["template_id"])
        artifact_bundle = artifact_bundle or self._load_artifact_bundle(slug)
        project_dir = self.projects_dir / slug
        export_dir = project_dir / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        readiness = self._evaluate_submission_readiness(slug=slug, manifest=manifest, artifact_bundle=artifact_bundle)
        manifest["submission_readiness"] = readiness

        exports = []
        rubric_path = export_dir / f"{slug}-rubric-report.md"
        self._write_rubric_report(rubric_path, manifest, artifact_bundle)
        exports.append(self._export_record("rubric_report", rubric_path, project_dir))
        if readiness["ready_for_export"]:
            static_path = export_dir / f"{slug}-site.html"
            static_path.write_text(self._render_static_site(manifest, template, artifact_bundle), encoding="utf-8")
            exports.append(self._export_record("static_site", static_path, project_dir))

            react_dir = export_dir / f"{slug}-react"
            react_dir.mkdir(parents=True, exist_ok=True)
            self._write_react_export(react_dir, manifest, artifact_bundle)
            exports.append(self._export_record("react_app", react_dir / "README.md", project_dir, directory="exports/" + react_dir.name))

            pdf_path = export_dir / f"{slug}-report.pdf"
            self._write_pdf_report(pdf_path, manifest, artifact_bundle)
            exports.append(self._export_record("pdf_report", pdf_path, project_dir))

            bundle_path = export_dir / f"{slug}.cpsbundle"
            self._write_project_bundle(project_dir, bundle_path)
            exports.append(self._export_record("project_bundle", bundle_path, project_dir))
            self.warehouse.record_event(
                event_type="project_export",
                source="studio_service",
                learner_id=slug,
                payload={"export_types": [export["export_type"] for export in exports]},
            )
        else:
            self.warehouse.record_event(
                event_type="project_export_blocked",
                source="studio_service",
                learner_id=slug,
                payload={"blocking_reasons": readiness["blocking_reasons"]},
            )

        return exports

    def get_export_path(self, slug: str, export_type: str) -> Path:
        manifest = self._load_manifest(slug)
        readiness = manifest.get("submission_readiness") or self._evaluate_submission_readiness(slug=slug, manifest=manifest)
        protected_exports = set(readiness.get("export_policy", {}).get("protected_export_types", []))
        if export_type in protected_exports and not readiness.get("ready_for_export", False):
            raise PermissionError("; ".join(readiness.get("blocking_reasons", [])))
        project_dir = self.projects_dir / slug
        for export in manifest.get("exports", []):
            if export["export_type"] == export_type:
                return project_dir / export["path"]
        raise FileNotFoundError(export_type)

    def get_submission_readiness(self, slug: str) -> dict[str, Any]:
        manifest = self._load_manifest(slug)
        readiness = manifest.get("submission_readiness") or self._evaluate_submission_readiness(slug=slug, manifest=manifest)
        manifest["submission_readiness"] = readiness
        self._write_manifest(slug, manifest)
        return readiness

    def get_artifact_bundle(self, slug: str) -> dict[str, Any] | None:
        self._load_manifest(slug)
        return self._load_artifact_bundle(slug)

    def _project_summary(self, manifest: dict[str, Any]) -> dict[str, Any]:
        return {
            "project_id": manifest["project_id"],
            "slug": manifest["slug"],
            "title": manifest["title"],
            "summary": manifest["summary"],
            "topic": manifest["topic"],
            "audience": manifest["audience"],
            "template_id": manifest["template_id"],
            "template_label": manifest["template_label"],
            "project_type": manifest["project_type"],
            "local_mode": manifest["local_mode"],
            "ai_profile_id": manifest.get("ai_profile_id", ""),
            "status": manifest["status"],
            "document_count": len(manifest["documents"]),
            "export_count": len(manifest["exports"]),
            "documents": manifest["documents"],
            "exports": manifest["exports"],
            "submission_readiness": manifest.get("submission_readiness", self._empty_submission_readiness()),
            "updated_at": manifest["updated_at"],
        }

    def _load_manifest(self, slug: str) -> dict[str, Any]:
        path = self.projects_dir / slug / "project.yaml"
        if not path.exists():
            raise FileNotFoundError(slug)
        with path.open("r", encoding="utf-8") as handle:
            manifest = yaml.safe_load(handle) or {}
        return self._ensure_manifest_defaults(manifest)

    def _write_manifest(self, slug: str, manifest: dict[str, Any]) -> None:
        path = self.projects_dir / slug / "project.yaml"
        with path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(manifest, handle, sort_keys=False)

    def _load_chunks(self, slug: str) -> list[dict[str, Any]]:
        path = self.projects_dir / slug / "provenance" / "chunks.json"
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_json(self, path: Path, payload: Any) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def _ensure_manifest_defaults(self, manifest: dict[str, Any]) -> dict[str, Any]:
        manifest.setdefault("teacher_comments", [])
        manifest.setdefault("revision_history", [])
        manifest.setdefault("standards_alignment", [])
        manifest.setdefault("ai_profile_id", "")
        manifest.setdefault("classroom_context", {})
        manifest.setdefault("quality_gates", self._quality_gate_defaults())
        manifest.setdefault("submission_readiness", self._empty_submission_readiness())
        return manifest

    def _quality_gate_defaults(self) -> dict[str, Any]:
        return {
            "min_citation_coverage": 75.0,
            "min_overall_score": 70.0,
            "min_rubric_score": 65.0,
            "min_documents": 1,
            "require_no_pending_approvals": True,
        }

    def _empty_submission_readiness(self) -> dict[str, Any]:
        return {
            "status": "draft",
            "ready_for_export": False,
            "progress_state": "not_started",
            "blocking_reasons": ["Compile the project to calculate readiness."],
            "recommendations": ["Run the project workflow before exporting."],
            "metrics": {
                "citation_coverage": 0.0,
                "overall_score": 0.0,
                "min_rubric_score": 0.0,
                "document_count": 0,
                "pending_approvals": 0,
                "export_count": 0,
            },
            "gates": self._quality_gate_defaults(),
            "export_policy": {
                "protected_export_types": ["static_site", "react_app", "pdf_report", "project_bundle"],
                "always_allowed_export_types": ["rubric_report"],
            },
        }

    def _evaluate_submission_readiness(
        self,
        *,
        slug: str,
        manifest: dict[str, Any],
        artifact_bundle: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        artifact_bundle = artifact_bundle or self._load_artifact_bundle(slug)
        gates = {**self._quality_gate_defaults(), **dict(manifest.get("quality_gates") or {})}
        teacher_review = dict((artifact_bundle or {}).get("artifacts", {}).get("teacher_review") or manifest.get("teacher_review") or {})
        rubric_scores = teacher_review.get("rubric_scores", []) if isinstance(teacher_review.get("rubric_scores", []), list) else []
        overall_score = float(teacher_review.get("overall_score") or 0.0)
        min_rubric_score = min((float(item.get("score") or 0.0) for item in rubric_scores), default=0.0)
        citation_map = (
            dict((artifact_bundle or {}).get("artifacts", {}).get("citation_map") or {}).get("citation_map", [])
            if artifact_bundle
            else []
        )
        total_sections = max(1, len(citation_map) or len(manifest.get("sections", [])))
        cited_sections = sum(1 for entry in citation_map if entry.get("citations"))
        citation_coverage = round((cited_sections / total_sections) * 100.0, 1)
        pending_approvals = self._pending_project_approvals(slug)
        document_count = len(manifest.get("documents", []))
        export_count = len(manifest.get("exports", []))

        blocking_reasons: list[str] = []
        if document_count < int(gates["min_documents"]):
            blocking_reasons.append("Upload at least one approved source before exporting.")
        if citation_coverage < float(gates["min_citation_coverage"]):
            blocking_reasons.append("Citation coverage is below the export threshold.")
        if overall_score < float(gates["min_overall_score"]):
            blocking_reasons.append("Teacher review score is below the export threshold.")
        if min_rubric_score < float(gates["min_rubric_score"]):
            blocking_reasons.append("At least one rubric criterion is still below the minimum score.")
        if bool(gates["require_no_pending_approvals"]) and pending_approvals:
            blocking_reasons.append("Pending approvals must be resolved before final export.")

        ready_for_export = not blocking_reasons
        progress_state = self._progress_state(
            ready_for_export=ready_for_export,
            export_count=export_count,
            pending_approvals=pending_approvals,
            document_count=document_count,
            artifact_bundle=artifact_bundle,
        )
        recommendations = (
            [
                "Resolve the pending approval queue and rerun compile.",
                "Strengthen sections with missing citations.",
                "Revise low-scoring rubric criteria before publishing.",
            ]
            if blocking_reasons
            else ["All quality gates passed. Final exports and family-safe sharing are unlocked."]
        )
        return {
            "status": "ready" if ready_for_export else "blocked",
            "ready_for_export": ready_for_export,
            "progress_state": progress_state,
            "blocking_reasons": blocking_reasons,
            "recommendations": recommendations,
            "metrics": {
                "citation_coverage": citation_coverage,
                "overall_score": round(overall_score, 1),
                "min_rubric_score": round(min_rubric_score, 1),
                "document_count": document_count,
                "pending_approvals": pending_approvals,
                "export_count": export_count,
            },
            "gates": gates,
            "export_policy": {
                "protected_export_types": ["static_site", "react_app", "pdf_report", "project_bundle"],
                "always_allowed_export_types": ["rubric_report"],
            },
        }

    def _pending_project_approvals(self, slug: str) -> int:
        if self.education_service is None:
            return 0
        approvals = self.education_service.list_approvals()
        return len(
            [
                approval
                for approval in approvals
                if approval.get("project_slug") == slug and approval.get("status") == "pending"
            ]
        )

    def _progress_state(
        self,
        *,
        ready_for_export: bool,
        export_count: int,
        pending_approvals: int,
        document_count: int,
        artifact_bundle: dict[str, Any] | None,
    ) -> str:
        if export_count and ready_for_export:
            return "exported"
        if ready_for_export:
            return "ready_for_export"
        if pending_approvals:
            return "under_review"
        if artifact_bundle:
            return "drafting"
        if document_count:
            return "researching"
        return "not_started"

    def _normalize_ai_profile_id(self, value: Any) -> str:
        raw_value = str(value or "").strip()
        if not raw_value:
            return ""
        self.ai_provider_service.get_profile_summary(raw_value)
        return raw_value

    def _record_revision(self, manifest: dict[str, Any], action: str, summary: str, actor: str) -> None:
        revisions = manifest.setdefault("revision_history", [])
        revisions.insert(
            0,
            {
                "revision_id": f"rev-{uuid4().hex[:8]}",
                "action": action,
                "summary": summary,
                "actor": actor,
                "created_at": self._timestamp(),
            },
        )
        del revisions[20:]

    def _empty_graph(self, manifest: dict[str, Any]) -> dict[str, Any]:
        return {
            "nodes": [
                {"id": f"project-{manifest['slug']}", "label": manifest["title"], "node_type": "project"},
            ],
            "edges": [],
            "highlights": ["Upload sources to enrich the knowledge graph."],
        }

    def _rebuild_all_indices(self) -> None:
        for path in sorted(self.projects_dir.glob("*/project.yaml")):
            self._rebuild_index(path.parent.name)

    def _rebuild_index(self, slug: str) -> None:
        chunks = self._load_chunks(slug)
        self._indices[slug] = self._build_index(chunks)

    def _build_index(self, chunk_records: list[dict[str, Any]]) -> WorkspaceIndex:
        if not chunk_records:
            return WorkspaceIndex([], None, None, np.zeros((0, 0), dtype=float))

        corpus = [chunk["text"] for chunk in chunk_records]
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform(corpus)
        max_components = min(32, tfidf_matrix.shape[0] - 1, tfidf_matrix.shape[1] - 1)
        projection: TruncatedSVD | None = None
        if max_components >= 2:
            projection = TruncatedSVD(n_components=max_components, random_state=1968)
            embeddings = projection.fit_transform(tfidf_matrix)
        else:
            embeddings = tfidf_matrix.toarray()
        return WorkspaceIndex(chunk_records, vectorizer, projection, self._normalize_rows(embeddings))

    def _encode_query(self, index: WorkspaceIndex, query: str) -> np.ndarray:
        if index.vectorizer is None:
            return np.zeros((0,), dtype=float)
        matrix = index.vectorizer.transform([query])
        if index.projection is not None:
            embedding = index.projection.transform(matrix)
        else:
            embedding = matrix.toarray()
        normalized = self._normalize_rows(embedding)
        return normalized[0] if len(normalized) else np.zeros((0,), dtype=float)

    def _extract_text(self, path: Path, content: bytes) -> dict[str, str]:
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".py", ".ts", ".tsx"}:
            text = content.decode("utf-8", errors="ignore")
            return {"text": text, "method": "plain_text", "ocr_status": "not_needed"}
        if suffix in {".html", ".htm"}:
            text = re.sub(r"<[^>]+>", " ", content.decode("utf-8", errors="ignore"))
            return {"text": re.sub(r"\s+", " ", text).strip(), "method": "html_strip", "ocr_status": "not_needed"}
        if suffix == ".pdf":
            reader = PdfReader(io.BytesIO(content))
            pages = [page.extract_text() or "" for page in reader.pages]
            return {"text": "\n".join(pages), "method": "pdf_text", "ocr_status": "not_needed"}
        if suffix in {".png", ".jpg", ".jpeg", ".gif", ".bmp"}:
            return self._extract_image_text(path)
        return {"text": content.decode("utf-8", errors="ignore"), "method": "fallback_decode", "ocr_status": "unknown"}

    def _extract_image_text(self, path: Path) -> dict[str, str]:
        tesseract_path = shutil.which("tesseract")
        if not tesseract_path:
            return {
                "text": "",
                "method": "image_ocr_unavailable",
                "ocr_status": "optional_local_ocr_not_configured",
            }

        try:
            result = subprocess.run(
                [tesseract_path, str(path), "stdout"],
                check=True,
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return {
                "text": "",
                "method": "image_ocr_failed",
                "ocr_status": "configured_but_failed",
            }

        return {
            "text": result.stdout.strip(),
            "method": "image_ocr_tesseract",
            "ocr_status": "completed",
        }

    def _chunk_text(self, document_id: str, file_name: str, text: str) -> list[dict[str, Any]]:
        normalized = re.sub(r"\r\n?", "\n", text).strip()
        if not normalized:
            normalized = f"No text could be extracted from {file_name}. Upload a text-friendly source or add notes manually."
        paragraphs = [part.strip() for part in re.split(r"\n{2,}", normalized) if part.strip()]
        if not paragraphs:
            paragraphs = [normalized]

        chunks = []
        for index, paragraph in enumerate(paragraphs, start=1):
            excerpt = paragraph[:260].strip()
            chunks.append(
                {
                    "chunk_id": f"{document_id}-chunk-{index}",
                    "document_id": document_id,
                    "citation_label": f"{self._title_from_filename(file_name)} chunk {index}",
                    "text": paragraph,
                    "excerpt": excerpt,
                }
            )
        return chunks

    def _duplicate_similarity(self, text: str, documents: list[dict[str, Any]]) -> float:
        current_tokens = set(re.findall(r"[a-zA-Z]{3,}", text.lower()))
        if not current_tokens or not documents:
            return 0.0
        score = 0.0
        for document in documents:
            prior_tokens = set(re.findall(r"[a-zA-Z]{3,}", str(document.get("summary", "")).lower()))
            if not prior_tokens:
                continue
            overlap = len(current_tokens.intersection(prior_tokens)) / len(current_tokens.union(prior_tokens))
            score = max(score, overlap * 100.0)
        return score

    def _summarize_text(self, text: str) -> str:
        clean = re.sub(r"\s+", " ", text).strip()
        if not clean:
            return "No extractable text was found in this document."
        return clean[:280] + ("..." if len(clean) > 280 else "")

    def _extract_entities(self, text: str) -> list[str]:
        candidates = re.findall(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b", text)
        unique = []
        for candidate in candidates:
            if candidate not in unique and len(candidate) > 2:
                unique.append(candidate)
        return unique[:16]

    def _extract_years(self, text: str) -> list[str]:
        years = re.findall(r"\b(?:18|19|20)\d{2}\b", text)
        unique = []
        for year in years:
            if year not in unique:
                unique.append(year)
        return unique

    def _reading_level(self, text: str) -> str:
        words = re.findall(r"[A-Za-z']+", text)
        sentences = re.split(r"[.!?]+", text)
        if not words:
            return "undetermined"
        avg_sentence_length = len(words) / max(1, len([sentence for sentence in sentences if sentence.strip()]))
        long_word_share = sum(1 for word in words if len(word) >= 7) / len(words)
        score = avg_sentence_length * 0.6 + long_word_share * 100 * 0.4
        if score < 10:
            return "upper-elementary"
        if score < 16:
            return "middle-school"
        if score < 24:
            return "high-school"
        return "college"

    def _load_artifact_bundle(self, slug: str) -> dict[str, Any] | None:
        path = self.projects_dir / slug / "artifacts" / "artifact_bundle.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _render_static_site(self, manifest: dict[str, Any], template: dict[str, Any], artifact_bundle: dict[str, Any]) -> str:
        sections = artifact_bundle["artifacts"]["written_sections"]["sections"]
        citation_lookup = artifact_bundle["artifacts"]["citation_map"]["citation_map"]
        citation_html = []
        for entry in citation_lookup:
            items = "".join(
                f"<li><strong>{item['citation_label']}</strong>: {item['excerpt']}</li>"
                for item in entry["citations"]
            )
            citation_html.append(f"<section class='citations'><h3>{entry['section_title']}</h3><ul>{items}</ul></section>")

        section_html = []
        for section in sections:
            section_html.append(
                "<section class='project-section'>"
                f"<h2>{section['title']}</h2>"
                f"<p>{section['body']}</p>"
                "</section>"
            )

        theme = template["theme_tokens"]
        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{manifest['title']}</title>
    <style>
      :root {{
        --accent: {theme['accent']};
        --ink: {theme['ink']};
        --paper: {theme['paper']};
      }}
      body {{
        margin: 0;
        font-family: {theme['font_body']}, Georgia, serif;
        background: linear-gradient(180deg, var(--paper), #ffffff);
        color: var(--ink);
      }}
      main {{
        width: min(1100px, calc(100vw - 2rem));
        margin: 0 auto;
        padding: 2rem 0 4rem;
      }}
      header {{
        padding: 2rem;
        border-radius: 1.5rem;
        background: linear-gradient(135deg, var(--accent), var(--ink));
        color: #fffaf4;
      }}
      .grid {{
        display: grid;
        gap: 1rem;
        margin-top: 1rem;
      }}
      .project-section, .citations, .card {{
        background: rgba(255,255,255,0.78);
        border: 1px solid rgba(0,0,0,0.08);
        border-radius: 1rem;
        padding: 1rem;
      }}
      .meta {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.8rem;
        margin-top: 1rem;
      }}
      .meta span {{
        padding: 0.4rem 0.75rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.14);
      }}
    </style>
  </head>
  <body>
    <main>
      <header>
        <p>EduClawn export</p>
        <h1>{manifest['title']}</h1>
        <p>{manifest['summary'] or manifest['topic']}</p>
        <div class="meta">
          <span>{manifest['template_label']}</span>
          <span>{manifest['audience']}</span>
          <span>{manifest['local_mode']}</span>
        </div>
      </header>
      <div class="grid">
        <section class="card">
          <h2>Research Brief</h2>
          <p>{artifact_bundle['artifacts']['research_brief']['executive_summary']}</p>
        </section>
        {''.join(section_html)}
        <section class="card">
          <h2>Teacher Review</h2>
          <p>Overall score: {artifact_bundle['artifacts']['teacher_review']['overall_score']}</p>
        </section>
        {''.join(citation_html)}
      </div>
    </main>
  </body>
</html>
"""

    def _write_react_export(self, react_dir: Path, manifest: dict[str, Any], artifact_bundle: dict[str, Any]) -> None:
        sections = artifact_bundle["artifacts"]["written_sections"]["sections"]
        sections_markup = "\n".join(
            [
                "      <section className=\"card\">"
                f"<h2>{section['title']}</h2>"
                f"<p>{section['body']}</p>"
                "</section>"
                for section in sections
            ]
        )

        (react_dir / "package.json").write_text(
            json.dumps(
                {
                    "name": self._slugify(manifest["title"]),
                    "private": True,
                    "version": "0.0.1",
                    "type": "module",
                    "scripts": {"dev": "vite", "build": "vite build"},
                    "dependencies": {"react": "^19.0.0", "react-dom": "^19.0.0"},
                    "devDependencies": {"typescript": "^5.6.0", "vite": "^8.0.0"},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        src_dir = react_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "App.tsx").write_text(
            "export default function App() {\n"
            "  return (\n"
            "    <main style={{ maxWidth: 980, margin: '0 auto', padding: '2rem', fontFamily: 'Georgia, serif' }}>\n"
            f"      <h1>{manifest['title']}</h1>\n"
            f"      <p>{manifest['summary'] or manifest['topic']}</p>\n"
            f"{sections_markup}\n"
            "    </main>\n"
            "  )\n"
            "}\n",
            encoding="utf-8",
        )
        (src_dir / "main.tsx").write_text(
            "import React from 'react'\n"
            "import ReactDOM from 'react-dom/client'\n"
            "import App from './App'\n"
            "ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>)\n",
            encoding="utf-8",
        )
        (react_dir / "index.html").write_text(
            "<!doctype html><html><body><div id='root'></div><script type='module' src='/src/main.tsx'></script></body></html>\n",
            encoding="utf-8",
        )
        (react_dir / "README.md").write_text(
            f"# {manifest['title']}\n\nGenerated locally by EduClawn.\n",
            encoding="utf-8",
        )

    def _write_pdf_report(self, path: Path, manifest: dict[str, Any], artifact_bundle: dict[str, Any]) -> None:
        pdf = canvas.Canvas(str(path), pagesize=letter)
        width, height = letter
        cursor = height - 48
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(48, cursor, manifest["title"])
        cursor -= 24
        pdf.setFont("Helvetica", 11)
        for line in [
            manifest["summary"] or manifest["topic"],
            f"Template: {manifest['template_label']}",
            f"Audience: {manifest['audience']}",
            f"Mode: {manifest['local_mode']}",
        ]:
            pdf.drawString(48, cursor, line[:100])
            cursor -= 16
        cursor -= 8
        for section in artifact_bundle["artifacts"]["written_sections"]["sections"]:
            pdf.setFont("Helvetica-Bold", 13)
            pdf.drawString(48, cursor, section["title"][:90])
            cursor -= 16
            pdf.setFont("Helvetica", 10)
            for wrapped in self._wrap_text(section["body"], width=90):
                if cursor < 60:
                    pdf.showPage()
                    cursor = height - 48
                    pdf.setFont("Helvetica", 10)
                pdf.drawString(48, cursor, wrapped)
                cursor -= 14
            cursor -= 8
        pdf.save()

    def _write_project_bundle(self, project_dir: Path, bundle_path: Path) -> None:
        with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in project_dir.rglob("*"):
                if path == bundle_path or path.is_dir():
                    continue
                archive.write(path, arcname=str(path.relative_to(project_dir)))

    def _write_rubric_report(self, path: Path, manifest: dict[str, Any], artifact_bundle: dict[str, Any]) -> None:
        teacher_review = artifact_bundle["artifacts"]["teacher_review"]
        rubric_scores = teacher_review.get("rubric_scores", [])
        teacher_comments = manifest.get("teacher_comments", [])
        revisions = manifest.get("revision_history", [])[:6]
        standards = manifest.get("standards_alignment", [])

        lines = [
            f"# {manifest['title']} Rubric Report",
            "",
            f"- Overall score: {teacher_review.get('overall_score', 'n/a')}",
            f"- Template: {manifest['template_label']}",
            f"- Audience: {manifest['audience']}",
            "",
            "## Standards Alignment",
        ]

        if standards:
            for standard in standards:
                lines.append(f"- {standard['standard_id']}: {standard['label']} ({standard['reason']})")
        else:
            lines.append("- No standards alignment has been generated yet.")

        lines.extend(["", "## Rubric Scores"])
        for item in rubric_scores:
            lines.append(f"- {item['criterion']}: {item['score']} - {item['feedback']}")

        lines.extend(["", "## Teacher Notes"])
        for note in teacher_review.get("teacher_notes", []):
            lines.append(f"- {note}")

        lines.extend(["", "## Teacher Comments"])
        if teacher_comments:
            for comment in teacher_comments:
                prefix = f"{comment['author']}"
                if comment.get("criterion"):
                    prefix += f" [{comment['criterion']}]"
                lines.append(f"- {prefix}: {comment['body']}")
        else:
            lines.append("- No teacher comments have been added yet.")

        lines.extend(["", "## Recent Revisions"])
        for revision in revisions:
            lines.append(f"- {revision['created_at']}: {revision['summary']}")

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _export_record(self, export_type: str, path: Path, project_dir: Path, directory: str | None = None) -> dict[str, Any]:
        return {
            "export_type": export_type,
            "path": directory or str(path.relative_to(project_dir)),
            "created_at": self._timestamp(),
        }

    def _normalize_rows(self, matrix: np.ndarray) -> np.ndarray:
        if matrix.size == 0:
            return matrix
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0.0, 1.0, norms)
        return matrix / norms

    def _build_standards_alignment(
        self,
        *,
        template: dict[str, Any],
        topic: str,
        goals: list[str],
        rubric: list[str],
    ) -> list[dict[str, str]]:
        lowered_text = " ".join([topic, *goals, *rubric]).lower()
        standards = [
            {
                "standard_id": "C3-D2.His.1",
                "label": "C3 History Inquiry",
                "reason": "The project frames evidence-backed historical or civic questions.",
            },
            {
                "standard_id": "ELA-W.7",
                "label": "ELA Research and Evidence Writing",
                "reason": "The workflow requires citation, drafting, and revision from uploaded sources.",
            },
        ]

        if template["supports_simulation"] or "decision" in lowered_text or "strategy" in lowered_text:
            standards.append(
                {
                    "standard_id": "C3-D2.Civ.14",
                    "label": "Civic Decision-Making",
                    "reason": "The project format supports tradeoffs, public action, or strategy simulation.",
                }
            )
        if any(keyword in lowered_text for keyword in {"presentation", "audience", "speech", "documentary", "exhibit"}):
            standards.append(
                {
                    "standard_id": "ELA-SL.4",
                    "label": "Speaking, Listening, and Presentation",
                    "reason": "The artifact set is designed for communication to a public audience.",
                }
            )
        return standards[:4]

    def _desktop_version(self) -> str:
        package_path = self.settings.root_dir / "desktop" / "package.json"
        if not package_path.exists():
            return "unknown"
        with package_path.open("r", encoding="utf-8") as handle:
            package = json.load(handle)
        return str(package.get("version") or "unknown")

    def _fetch_ollama_models(self) -> list[str]:
        try:
            response = urllib_request.urlopen(f"{self.settings.local_llm_base_url.rstrip('/')}/api/tags", timeout=2)
            payload = json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError, ValueError, urllib_error.HTTPError, urllib_error.URLError):
            return []

        models = payload.get("models", [])
        return [str(model.get("name")) for model in models if model.get("name")]

    def _timestamp(self) -> str:
        return datetime.now(UTC).isoformat()

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or f"project-{uuid4().hex[:6]}"

    def _unique_slug(self, base_slug: str) -> str:
        candidate = base_slug
        index = 2
        while (self.projects_dir / candidate).exists():
            candidate = f"{base_slug}-{index}"
            index += 1
        return candidate

    def _safe_filename(self, filename: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-")
        return cleaned or f"upload-{uuid4().hex[:8]}.txt"

    def _title_from_filename(self, filename: str) -> str:
        return Path(filename).stem.replace("-", " ").replace("_", " ").title()

    def _wrap_text(self, text: str, width: int = 90) -> list[str]:
        words = text.split()
        lines: list[str] = []
        current: list[str] = []
        current_length = 0
        for word in words:
            if current_length + len(word) + len(current) > width:
                lines.append(" ".join(current))
                current = [word]
                current_length = len(word)
            else:
                current.append(word)
                current_length += len(word)
        if current:
            lines.append(" ".join(current))
        return lines
