from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml
from pypdf import PdfReader

from app.core.config import Settings
from app.services.provider_ai import ProviderAIService
from app.services.studio_engine import ProjectStudioService, TemplateRegistryService


EDUCATION_AGENT_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "name": "lesson-planner",
        "display_name": "Lesson Planner Agent",
        "role": "teacher",
        "description": "Builds lesson sequences, discussion moves, and evidence-backed classroom plans.",
        "allowed_tool_scopes": [
            "read_classroom_materials",
            "align_rubrics_and_standards",
            "draft_lesson_artifacts",
            "queue_teacher_approval",
        ],
        "artifact_types": ["lesson_outline", "discussion_prompts", "checkpoint_plan"],
    },
    {
        "name": "rubric-designer",
        "display_name": "Rubric Designer Agent",
        "role": "teacher",
        "description": "Creates standards-aware rubric criteria and scoring guidance for assignments.",
        "allowed_tool_scopes": [
            "read_classroom_materials",
            "align_rubrics_and_standards",
            "draft_lesson_artifacts",
            "queue_teacher_approval",
        ],
        "artifact_types": ["rubric", "teacher_look_fors"],
    },
    {
        "name": "feedback-coach",
        "display_name": "Feedback Coach Agent",
        "role": "teacher",
        "description": "Produces revision guidance, conferencing notes, and next-step feedback for student work.",
        "allowed_tool_scopes": [
            "read_approved_sources",
            "review_student_projects",
            "draft_feedback_notes",
            "queue_teacher_approval",
        ],
        "artifact_types": ["feedback_notes", "revision_targets"],
    },
    {
        "name": "classroom-analyst",
        "display_name": "Classroom Analyst Agent",
        "role": "teacher",
        "description": "Summarizes classroom progress, missing evidence, and assignment momentum.",
        "allowed_tool_scopes": [
            "read_classroom_materials",
            "review_student_projects",
            "summarize_classroom_progress",
            "queue_teacher_approval",
        ],
        "artifact_types": ["classroom_snapshot", "risk_flags"],
    },
    {
        "name": "project-coach",
        "display_name": "Project Coach Agent",
        "role": "student",
        "description": "Turns assignment goals into clear next steps, milestones, and scaffolded project tasks.",
        "allowed_tool_scopes": [
            "read_approved_sources",
            "draft_project_sections",
            "propose_revisions",
            "export_local_bundle",
            "queue_teacher_approval",
        ],
        "artifact_types": ["milestone_plan", "next_steps"],
    },
    {
        "name": "research-coach",
        "display_name": "Research Coach Agent",
        "role": "student",
        "description": "Helps students ask stronger questions and locate the best approved evidence.",
        "allowed_tool_scopes": [
            "read_approved_sources",
            "summarize_evidence",
            "draft_project_sections",
            "queue_teacher_approval",
        ],
        "artifact_types": ["research_questions", "evidence_shortlist"],
    },
    {
        "name": "citation-tutor",
        "display_name": "Citation Tutor Agent",
        "role": "student",
        "description": "Explains how claims connect to approved sources and drafts citation checklists.",
        "allowed_tool_scopes": [
            "read_approved_sources",
            "map_citations",
            "propose_revisions",
            "queue_teacher_approval",
        ],
        "artifact_types": ["citation_checklist", "evidence_links"],
    },
    {
        "name": "revision-tutor",
        "display_name": "Revision Tutor Agent",
        "role": "student",
        "description": "Uses rubric targets and teacher feedback to produce a revision plan.",
        "allowed_tool_scopes": [
            "read_approved_sources",
            "review_student_projects",
            "propose_revisions",
            "queue_teacher_approval",
        ],
        "artifact_types": ["revision_plan", "quality_checks"],
    },
    {
        "name": "study-planner",
        "display_name": "Study Planner Agent",
        "role": "student",
        "description": "Builds short study blocks and checkpoint schedules around classroom due dates.",
        "allowed_tool_scopes": [
            "read_assignment_schedule",
            "draft_project_sections",
            "queue_teacher_approval",
        ],
        "artifact_types": ["study_schedule", "checkpoint_targets"],
    },
    {
        "name": "approval-guard",
        "display_name": "Approval Guard Agent",
        "role": "shared",
        "description": "Detects sensitive requests, routes them into approval, and documents the safety rationale.",
        "allowed_tool_scopes": [
            "inspect_request_context",
            "queue_teacher_approval",
            "summarize_audit_log",
        ],
        "artifact_types": ["approval_summary", "safety_rationale"],
    },
    {
        "name": "audit-reporter",
        "display_name": "Audit Reporter Agent",
        "role": "shared",
        "description": "Builds audit summaries of classroom agent activity and safety compliance.",
        "allowed_tool_scopes": [
            "summarize_audit_log",
            "inspect_request_context",
        ],
        "artifact_types": ["audit_summary", "policy_findings"],
    },
    {
        "name": "evidence-librarian",
        "display_name": "Evidence Librarian Agent",
        "role": "shared",
        "description": "Organizes shared evidence libraries and tracks which approved materials seeded student projects.",
        "allowed_tool_scopes": [
            "inspect_evidence_library",
            "read_classroom_materials",
            "summarize_evidence",
        ],
        "artifact_types": ["evidence_map", "coverage_summary"],
    },
)

BLOCKED_CAPABILITIES: tuple[str, ...] = (
    "shell_execution",
    "unrestricted_browser_automation",
    "silent_external_publish",
    "uncontrolled_messaging",
    "destructive_filesystem_actions",
)

ALLOWED_MATERIAL_CONTENT_TYPES: tuple[str, ...] = (
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
    "application/pdf",
)

PROMPT_RISK_PATTERNS: tuple[tuple[str, str, int], ...] = (
    ("policy_override", r"\b(ignore previous|override policy|bypass|jailbreak)\b", 35),
    ("secret_exfiltration", r"\b(secret|token|password|credential|api key)\b", 30),
    ("external_send", r"\b(email|message parents|send externally|post online|publish)\b", 25),
    ("browser_control", r"\b(open browser|navigate to|visit website|click link)\b", 20),
    ("shell_execution", r"\b(shell|terminal|run command|install package|execute)\b", 30),
    ("filesystem_damage", r"\b(delete file|erase workspace|remove project)\b", 25),
)

APPROVAL_REQUIRED_FOR: tuple[str, ...] = (
    "external_messaging",
    "browser_navigation",
    "public_publish",
    "shell_execution",
    "destructive_filesystem_actions",
)

ROLE_MODELS: tuple[dict[str, Any], ...] = (
    {
        "role": "teacher",
        "label": "Teacher OS",
        "description": "Lesson planning, rubric creation, standards alignment, classroom dashboards, and review guidance.",
        "agent_names": ["lesson-planner", "rubric-designer", "feedback-coach", "classroom-analyst"],
    },
    {
        "role": "student",
        "label": "Student OS",
        "description": "Project building, research support, citation tutoring, revision coaching, and study planning.",
        "agent_names": ["project-coach", "research-coach", "citation-tutor", "revision-tutor", "study-planner"],
    },
    {
        "role": "shared",
        "label": "Shared Classroom Layer",
        "description": "Evidence libraries, provenance, approval routing, audit visibility, and classroom-safe collaboration.",
        "agent_names": ["approval-guard", "audit-reporter", "evidence-librarian"],
    },
)


class EducationOperatingSystemService:
    def __init__(
        self,
        settings: Settings,
        studio_service: ProjectStudioService,
        template_registry: TemplateRegistryService,
        ai_provider_service: ProviderAIService,
    ) -> None:
        self.settings = settings
        self.studio_service = studio_service
        self.template_registry = template_registry
        self.ai_provider_service = ai_provider_service
        self.security_secret = settings.educlawn_security_secret.encode("utf-8")
        self.root_dir = settings.studio_root_dir / "education_os"
        self.classrooms_dir = self.root_dir / "classrooms"
        self.materials_dir = self.root_dir / "materials"
        self.audit_path = self.root_dir / "audit_log.json"
        self.approvals_path = self.root_dir / "approvals.json"
        self.classrooms_dir.mkdir(parents=True, exist_ok=True)
        self.materials_dir.mkdir(parents=True, exist_ok=True)
        if not self.audit_path.exists():
            self._write_json(self.audit_path, [])
        if not self.approvals_path.exists():
            self._write_json(self.approvals_path, [])

    def get_overview(self) -> dict[str, Any]:
        classrooms = self.list_classrooms()
        approvals = self.list_approvals()
        audit_entries = self.list_audit_entries(limit=250)
        return {
            "product_name": "EduClawn Education OS",
            "positioning": "An open-source local-first agent studio for teachers and students.",
            "difference_statement": "Bounded educational orchestration, not general autonomous action.",
            "role_models": [dict(item) for item in ROLE_MODELS],
            "safety_model": {
                "policy_name": "school_safe_agent_runtime",
                "approval_required_for": list(APPROVAL_REQUIRED_FOR),
                "blocked_capabilities": list(BLOCKED_CAPABILITIES),
                "allowed_tool_scopes": sorted({scope for agent in EDUCATION_AGENT_CATALOG for scope in agent["allowed_tool_scopes"]}),
            },
            "counts": {
                "classrooms": len(classrooms),
                "students": sum(classroom["student_count"] for classroom in classrooms),
                "assignments": sum(classroom["assignment_count"] for classroom in classrooms),
                "pending_approvals": len([approval for approval in approvals if approval["status"] == "pending"]),
                "audit_entries": len(audit_entries),
            },
            "agent_catalog": self.catalog(),
            "template_tracks": [
                {
                    "id": template["id"],
                    "label": template["label"],
                    "project_type": template["project_type"],
                    "category": template["category"],
                }
                for template in self.template_registry.list_templates()
            ],
        }

    def catalog(self) -> list[dict[str, Any]]:
        return [dict(entry) for entry in EDUCATION_AGENT_CATALOG]

    def list_classrooms(self) -> list[dict[str, Any]]:
        classrooms = []
        for path in sorted(self.classrooms_dir.glob("*/classroom.yaml")):
            with path.open("r", encoding="utf-8") as handle:
                classroom = yaml.safe_load(handle) or {}
            classrooms.append(self._hydrate_classroom(classroom))
        return sorted(classrooms, key=lambda item: item["updated_at"], reverse=True)

    def get_classroom(self, classroom_id: str) -> dict[str, Any]:
        return self._hydrate_classroom(self._load_classroom(classroom_id))

    def create_classroom(self, payload: dict[str, Any]) -> dict[str, Any]:
        classroom_id = f"classroom-{uuid4().hex[:10]}"
        now = self._timestamp()
        access_bootstrap = self._generate_access_bootstrap(classroom_id)
        classroom = {
            "version": "1.0",
            "classroom_id": classroom_id,
            "title": str(payload["title"]).strip(),
            "subject": str(payload["subject"]).strip(),
            "grade_band": str(payload["grade_band"]).strip(),
            "teacher_name": str(payload["teacher_name"]).strip(),
            "description": str(payload.get("description") or "").strip(),
            "default_template_id": str(payload.get("default_template_id") or "lesson-module"),
            "standards_focus": [str(item).strip() for item in payload.get("standards_focus", []) if str(item).strip()],
            "safety_mode": "bounded_education_orchestration",
            "created_at": now,
            "updated_at": now,
            "students": [],
            "assignments": [],
            "evidence_library": [],
            "shared_layer": {
                "provenance_required": True,
                "teacher_comments_enabled": True,
                "peer_collaboration_mode": "teacher_moderated",
                "version_history_source": "linked_project_manifests",
            },
            "security": {
                "policy_version": "2.0",
                "protected": True,
                "max_material_bytes": self.settings.edu_material_max_bytes,
                "allowed_content_types": list(ALLOWED_MATERIAL_CONTENT_TYPES),
                "teacher_access_key_hash": access_bootstrap["teacher_access_key_hash"],
                "student_access_key_hash": access_bootstrap["student_access_key_hash"],
                "reviewer_access_key_hash": access_bootstrap["reviewer_access_key_hash"],
                "audit_chain_valid": True,
                "approval_chain_valid": True,
                "created_at": now,
            },
        }
        self._save_classroom(classroom)
        self._append_audit(
            {
                "actor_role": "teacher",
                "agent_name": "classroom-bootstrap",
                "action": "classroom_created",
                "summary": f"Created classroom {classroom['title']}.",
                "classroom_id": classroom_id,
                "allowed_actions": ["manage_classroom_metadata"],
                "sensitive_actions_requested": [],
                "status": "completed",
            }
        )
        hydrated = self.get_classroom(classroom_id)
        hydrated["security_bootstrap"] = {
            "teacher_access_key": access_bootstrap["teacher_access_key"],
            "student_access_key": access_bootstrap["student_access_key"],
            "reviewer_access_key": access_bootstrap["reviewer_access_key"],
            "issued_at": now,
            "rotation_note": "Store these locally now. Only hashes remain in EduClawn after bootstrap.",
        }
        return hydrated

    def enroll_student(self, classroom_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        classroom = self._load_classroom(classroom_id)
        self._authorize_classroom_action(classroom, str(payload.get("access_key") or ""), {"teacher"})
        now = self._timestamp()
        student = {
            "student_id": f"student-{uuid4().hex[:10]}",
            "name": str(payload["name"]).strip(),
            "grade_level": str(payload.get("grade_level") or classroom["grade_band"]).strip(),
            "learning_goals": [str(item).strip() for item in payload.get("learning_goals", []) if str(item).strip()],
            "notes": str(payload.get("notes") or "").strip(),
            "project_slugs": [],
            "created_at": now,
            "updated_at": now,
        }
        classroom["students"].append(student)
        classroom["updated_at"] = now
        self._save_classroom(classroom)
        self._append_audit(
            {
                "actor_role": "teacher",
                "agent_name": "classroom-bootstrap",
                "action": "student_enrolled",
                "summary": f"Enrolled {student['name']} in {classroom['title']}.",
                "classroom_id": classroom_id,
                "student_id": student["student_id"],
                "allowed_actions": ["manage_student_roster"],
                "sensitive_actions_requested": [],
                "status": "completed",
            }
        )
        return self.get_classroom(classroom_id)

    def create_assignment(self, classroom_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        classroom = self._load_classroom(classroom_id)
        self._authorize_classroom_action(classroom, str(payload.get("access_key") or ""), {"teacher"})
        template_id = str(payload.get("template_id") or classroom.get("default_template_id") or "lesson-module")
        template = self.template_registry.get_template(template_id)
        now = self._timestamp()
        assignment = {
            "assignment_id": f"assignment-{uuid4().hex[:10]}",
            "title": str(payload["title"]).strip(),
            "summary": str(payload.get("summary") or "").strip(),
            "topic": str(payload["topic"]).strip(),
            "audience": str(payload.get("audience") or classroom["grade_band"]).strip(),
            "template_id": template["id"],
            "template_label": template["label"],
            "goals": [str(item).strip() for item in payload.get("goals", []) if str(item).strip()],
            "rubric": [str(item).strip() for item in payload.get("rubric", []) if str(item).strip()],
            "standards": [str(item).strip() for item in payload.get("standards", []) if str(item).strip()],
            "due_date": str(payload.get("due_date") or "").strip(),
            "local_mode": str(payload.get("local_mode") or "no-llm"),
            "ai_profile_id": self._normalize_ai_profile_id(payload.get("ai_profile_id")),
            "status": "draft",
            "created_at": now,
            "updated_at": now,
            "evidence_material_ids": [],
            "launched_projects": [],
        }
        classroom["assignments"].append(assignment)
        classroom["updated_at"] = now
        self._save_classroom(classroom)
        self._append_audit(
            {
                "actor_role": "teacher",
                "agent_name": "lesson-planner",
                "action": "assignment_created",
                "summary": f"Created assignment {assignment['title']}.",
                "classroom_id": classroom_id,
                "assignment_id": assignment["assignment_id"],
                "allowed_actions": ["draft_lesson_artifacts", "align_rubrics_and_standards"],
                "sensitive_actions_requested": [],
                "status": "completed",
            }
        )
        return self.get_classroom(classroom_id)

    def add_material(
        self,
        classroom_id: str,
        filename: str,
        content: bytes,
        *,
        content_type: str | None = None,
        assignment_id: str | None = None,
        access_key: str = "",
    ) -> dict[str, Any]:
        classroom = self._load_classroom(classroom_id)
        self._authorize_classroom_action(classroom, access_key, {"teacher"})
        if assignment_id:
            self._find_assignment(classroom, assignment_id)
        self._validate_material_upload(filename, content, content_type or "", classroom)
        safe_name = self._safe_filename(filename)
        material_id = f"material-{uuid4().hex[:10]}"
        classroom_material_dir = self.materials_dir / classroom_id
        classroom_material_dir.mkdir(parents=True, exist_ok=True)
        material_path = classroom_material_dir / f"{material_id}-{safe_name}"
        material_path.write_bytes(content)
        extracted_text, extraction_method = self._extract_material_text(material_path, content, content_type or "")
        material = {
            "material_id": material_id,
            "title": self._title_from_filename(safe_name),
            "file_name": safe_name,
            "content_type": content_type or "application/octet-stream",
            "source_path": str(material_path.relative_to(self.root_dir)),
            "summary": self._summarize_text(extracted_text),
            "word_count": len(extracted_text.split()),
            "assignment_id": assignment_id,
            "scope": "assignment" if assignment_id else "shared",
            "extraction_method": extraction_method,
            "uploaded_at": self._timestamp(),
        }
        classroom["evidence_library"].append(material)
        if assignment_id:
            assignment = self._find_assignment(classroom, assignment_id)
            assignment["evidence_material_ids"] = sorted({*assignment.get("evidence_material_ids", []), material_id})
            assignment["updated_at"] = self._timestamp()
        classroom["updated_at"] = self._timestamp()
        self._save_classroom(classroom)
        self._append_audit(
            {
                "actor_role": "teacher",
                "agent_name": "evidence-librarian",
                "action": "material_uploaded",
                "summary": f"Uploaded classroom material {safe_name}.",
                "classroom_id": classroom_id,
                "assignment_id": assignment_id,
                "allowed_actions": ["inspect_evidence_library", "read_classroom_materials"],
                "sensitive_actions_requested": [],
                "status": "completed",
            }
        )
        return material

    def launch_student_project(self, classroom_id: str, assignment_id: str, student_id: str, access_key: str) -> dict[str, Any]:
        classroom = self._load_classroom(classroom_id)
        self._authorize_classroom_action(classroom, access_key, {"teacher"})
        assignment = self._find_assignment(classroom, assignment_id)
        student = self._find_student(classroom, student_id)
        project = self.studio_service.create_project(
            {
                "title": f"{assignment['title']} - {student['name']}",
                "summary": assignment["summary"] or f"Student project for {classroom['title']}.",
                "topic": assignment["topic"],
                "audience": assignment["audience"],
                "goals": list(dict.fromkeys([*assignment.get("goals", []), *student.get("learning_goals", [])])),
                "rubric": assignment.get("rubric", []),
                "template_id": assignment["template_id"],
                "local_mode": assignment.get("local_mode", "no-llm"),
                "ai_profile_id": assignment.get("ai_profile_id", ""),
                "slug": f"{assignment['title']}-{student['name']}",
                "classroom_context": {
                    "classroom_id": classroom_id,
                    "classroom_title": classroom["title"],
                    "assignment_id": assignment_id,
                    "assignment_title": assignment["title"],
                    "student_id": student_id,
                    "student_name": student["name"],
                    "teacher_name": classroom["teacher_name"],
                },
            }
        )
        project_slug = str(project["slug"])

        seeded_count = 0
        allowed_material_ids = set(assignment.get("evidence_material_ids", []))
        for material in classroom.get("evidence_library", []):
            if material["scope"] == "shared" or material["material_id"] in allowed_material_ids:
                source_path = self.root_dir / material["source_path"]
                if source_path.exists():
                    self.studio_service.ingest_document(
                        slug=project_slug,
                        filename=material["file_name"],
                        content=source_path.read_bytes(),
                        content_type=material["content_type"],
                    )
                    seeded_count += 1

        assignment["launched_projects"].append(
            {
                "student_id": student_id,
                "student_name": student["name"],
                "project_slug": project_slug,
                "project_title": project["title"],
                "created_at": self._timestamp(),
            }
        )
        assignment["status"] = "launched"
        assignment["updated_at"] = self._timestamp()
        student["project_slugs"] = sorted({*student.get("project_slugs", []), project_slug})
        student["updated_at"] = self._timestamp()
        classroom["updated_at"] = self._timestamp()
        self._save_classroom(classroom)
        self._append_audit(
            {
                "actor_role": "teacher",
                "agent_name": "project-coach",
                "action": "student_project_launched",
                "summary": f"Launched {project['title']} with {seeded_count} approved classroom materials.",
                "classroom_id": classroom_id,
                "assignment_id": assignment_id,
                "student_id": student_id,
                "project_slug": project_slug,
                "allowed_actions": ["read_approved_sources", "draft_project_sections"],
                "sensitive_actions_requested": [],
                "status": "completed",
            }
        )
        return {
            "classroom": self.get_classroom(classroom_id),
            "project": self.studio_service.get_project(project_slug),
            "seeded_material_count": seeded_count,
        }

    def run_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        role = str(payload["role"])
        agent_name = str(payload["agent_name"])
        agent_config = self._get_agent(agent_name, role)
        prompt = str(payload.get("prompt") or "").strip()
        classroom = self._load_classroom(payload["classroom_id"]) if payload.get("classroom_id") else None
        if classroom:
            permitted_roles = {"teacher", "reviewer"} if role in {"teacher", "shared"} else {"student", "teacher"}
            self._authorize_classroom_action(classroom, str(payload.get("access_key") or ""), permitted_roles)
        assignment = self._find_assignment(classroom, payload["assignment_id"]) if classroom and payload.get("assignment_id") else None
        student = self._find_student(classroom, payload["student_id"]) if classroom and payload.get("student_id") else None
        project = self.studio_service.get_project(payload["project_slug"]) if payload.get("project_slug") else None
        ai_profile_id = self._resolve_runtime_ai_profile_id(payload, assignment, project)
        risk_assessment = self._assess_prompt_risk(prompt)
        sensitive_actions = sorted(set(self._detect_sensitive_actions(prompt) + risk_assessment["policy_actions"]))
        approval = None
        if sensitive_actions or risk_assessment["band"] in {"high", "critical"}:
            approval = self._create_approval(
                {
                    "agent_name": agent_name,
                    "role": role,
                    "classroom_id": payload.get("classroom_id"),
                    "assignment_id": payload.get("assignment_id"),
                    "student_id": payload.get("student_id"),
                    "project_slug": payload.get("project_slug"),
                    "requested_actions": sensitive_actions,
                    "prompt": prompt,
                    "risk_assessment": risk_assessment,
                }
            )

        artifacts, summary = self._agent_artifact(
            agent_name=agent_name,
            role=role,
            prompt=prompt,
            classroom=classroom,
            assignment=assignment,
            student=student,
            project=project,
        )
        provider_result = self._maybe_run_provider_ai(
            agent_name=agent_name,
            role=role,
            prompt=prompt,
            assignment=assignment,
            project=project,
            ai_profile_id=ai_profile_id,
        )
        if provider_result["used"]:
            artifacts["provider_ai_assist"] = provider_result
            summary = f"{summary} Enhanced with {provider_result['provider_label']}."
        audit_entry = self._append_audit(
            {
                "actor_role": role,
                "agent_name": agent_name,
                "action": "agent_run",
                "summary": summary,
                "classroom_id": payload.get("classroom_id"),
                "assignment_id": payload.get("assignment_id"),
                "student_id": payload.get("student_id"),
                "project_slug": payload.get("project_slug"),
                "allowed_actions": agent_config["allowed_tool_scopes"],
                "sensitive_actions_requested": sensitive_actions,
                "status": "approval_required" if approval else "completed",
                "prompt_excerpt": risk_assessment["redacted_excerpt"],
                "risk_assessment": risk_assessment,
                "ai_usage": self._audit_ai_usage(provider_result),
            }
        )
        return {
            "run_id": f"edu-run-{uuid4().hex[:10]}",
            "agent_name": agent_name,
            "display_name": agent_config["display_name"],
            "role": role,
            "summary": summary,
            "allowed_actions": agent_config["allowed_tool_scopes"],
            "blocked_capabilities": list(BLOCKED_CAPABILITIES),
            "requires_approval": approval is not None,
            "sensitive_actions_requested": sensitive_actions,
            "risk_assessment": risk_assessment,
            "approval_request": approval,
            "artifacts": artifacts,
            "provider_ai": provider_result if provider_result["used"] else None,
            "audit_entry": audit_entry,
        }

    def list_approvals(self, classroom_id: str | None = None, access_key: str = "") -> list[dict[str, Any]]:
        approvals = self._load_json(self.approvals_path)
        if classroom_id:
            classroom = self._load_classroom(classroom_id)
            self._authorize_classroom_action(classroom, access_key, {"teacher", "reviewer"})
            approvals = [approval for approval in approvals if approval.get("classroom_id") == classroom_id]
        return sorted(approvals, key=lambda item: item["requested_at"], reverse=True)

    def resolve_approval(self, approval_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        approvals = self._load_json(self.approvals_path)
        decision = str(payload["decision"]).strip()
        if decision not in {"approved", "rejected"}:
            raise ValueError("Decision must be approved or rejected.")
        for approval in approvals:
            if approval["approval_id"] == approval_id:
                classroom = self._load_classroom(str(approval.get("classroom_id")))
                self._authorize_classroom_action(classroom, str(payload.get("access_key") or ""), {"reviewer", "teacher"})
                approval["status"] = decision
                approval["reviewed_at"] = self._timestamp()
                approval["reviewer"] = str(payload["reviewer"]).strip()
                approval["note"] = str(payload.get("note") or "").strip()
                approvals = self._rebuild_chain(approvals)
                self._write_json(self.approvals_path, approvals)
                self._append_audit(
                    {
                        "actor_role": "teacher",
                        "agent_name": "approval-guard",
                        "action": "approval_resolved",
                        "summary": f"{decision.title()} approval {approval_id}.",
                        "classroom_id": approval.get("classroom_id"),
                        "assignment_id": approval.get("assignment_id"),
                        "student_id": approval.get("student_id"),
                        "project_slug": approval.get("project_slug"),
                        "allowed_actions": ["queue_teacher_approval"],
                        "sensitive_actions_requested": approval.get("requested_actions", []),
                        "status": decision,
                    }
                )
                return approval
        raise FileNotFoundError(approval_id)

    def list_audit_entries(self, limit: int = 40, classroom_id: str | None = None, access_key: str = "") -> list[dict[str, Any]]:
        entries = self._load_json(self.audit_path)
        if classroom_id:
            classroom = self._load_classroom(classroom_id)
            self._authorize_classroom_action(classroom, access_key, {"teacher", "reviewer"})
            entries = [entry for entry in entries if entry.get("classroom_id") == classroom_id]
        return entries[:limit]

    def get_safety_status(self) -> dict[str, Any]:
        approvals = self._load_json(self.approvals_path)
        audit_entries = self._load_json(self.audit_path)
        pending_approvals = [approval for approval in approvals if approval["status"] == "pending"]
        return {
            "policy_name": "school_safe_agent_runtime",
            "mode": "bounded_education_orchestration",
            "approval_required_for": list(APPROVAL_REQUIRED_FOR),
            "blocked_capabilities": list(BLOCKED_CAPABILITIES),
            "role_policies": [dict(item) for item in ROLE_MODELS],
            "allowed_tool_scopes": sorted({scope for agent in EDUCATION_AGENT_CATALOG for scope in agent["allowed_tool_scopes"]}),
            "pending_approvals": len(pending_approvals),
            "audit_entries": len(audit_entries),
            "last_audit_entries": audit_entries[:8],
            "audit_chain_valid": self._verify_chain(audit_entries),
            "approval_chain_valid": self._verify_chain(approvals),
            "material_policy": {
                "max_material_bytes": self.settings.edu_material_max_bytes,
                "allowed_content_types": list(ALLOWED_MATERIAL_CONTENT_TYPES),
            },
            "provider_ai_profiles": len(self.ai_provider_service.list_profiles()),
        }

    def _resolve_runtime_ai_profile_id(
        self,
        payload: dict[str, Any],
        assignment: dict[str, Any] | None,
        project: dict[str, Any] | None,
    ) -> str:
        explicit = self._normalize_ai_profile_id(payload.get("ai_profile_id"))
        if explicit:
            return explicit
        if assignment and assignment.get("local_mode") == "provider-ai":
            return self._normalize_ai_profile_id(assignment.get("ai_profile_id"))
        if project and project.get("local_mode") == "provider-ai":
            return self._normalize_ai_profile_id(project.get("ai_profile_id"))
        return ""

    def _maybe_run_provider_ai(
        self,
        *,
        agent_name: str,
        role: str,
        prompt: str,
        assignment: dict[str, Any] | None,
        project: dict[str, Any] | None,
        ai_profile_id: str,
    ) -> dict[str, Any]:
        if not ai_profile_id:
            return {"used": False, "error": ""}

        context = (
            f"Role: {role}. Agent: {agent_name}. "
            f"Assignment: {(assignment or {}).get('title', 'n/a')}. "
            f"Project: {(project or {}).get('title', 'n/a')}."
        )
        result = self.ai_provider_service.generate_with_profile(
            ai_profile_id,
            task="classroom",
            source="education_agent",
            metadata={
                "agent_name": agent_name,
                "role": role,
                "assignment_id": (assignment or {}).get("assignment_id", ""),
                "project_slug": (project or {}).get("slug", ""),
            },
            system_prompt="You are a classroom-safe assistant inside EduClawn. Only produce educational guidance and do not propose uncontrolled external actions.",
            prompt=f"{context} User request: {prompt}",
            classroom_id=str((assignment or {}).get("classroom_id") or (project or {}).get("classroom_context", {}).get("classroom_id") or ""),
        )
        return result

    def _audit_ai_usage(self, provider_result: dict[str, Any]) -> dict[str, Any] | None:
        if not provider_result.get("used"):
            return None
        return {
            "provider_id": provider_result["provider_id"],
            "provider_label": provider_result["provider_label"],
            "profile_id": provider_result["profile_id"],
            "profile_label": provider_result["profile_label"],
            "auth_mode": provider_result["auth_mode"],
            "model": provider_result["model"],
        }

    def _normalize_ai_profile_id(self, value: Any) -> str:
        raw_value = str(value or "").strip()
        if not raw_value:
            return ""
        self.ai_provider_service.get_profile_summary(raw_value)
        return raw_value

    def _agent_artifact(
        self,
        *,
        agent_name: str,
        role: str,
        prompt: str,
        classroom: dict[str, Any] | None,
        assignment: dict[str, Any] | None,
        student: dict[str, Any] | None,
        project: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], str]:
        material_summaries = [
            {
                "title": material["title"],
                "summary": material["summary"],
            }
            for material in (classroom or {}).get("evidence_library", [])[:4]
        ]
        project_sections = [section["title"] for section in (project or {}).get("sections", [])[:4]]
        teacher_comments = [comment["body"] for comment in (project or {}).get("teacher_comments", [])[:3]]
        standards = (assignment or {}).get("standards", []) or (classroom or {}).get("standards_focus", [])

        if agent_name == "lesson-planner":
            artifact = {
                "lesson_outline": [
                    "Launch the inquiry with a source-based opener.",
                    "Move into guided analysis of approved classroom materials.",
                    "Transition into project drafting or discussion.",
                    "Close with a rubric-aligned exit ticket.",
                ],
                "discussion_prompts": [
                    f"What evidence best explains {assignment['topic'] if assignment else classroom['title'] if classroom else 'the topic'}?",
                    "Which source most directly supports the assignment goal?",
                    "How should students cite the strongest material?",
                ],
                "checkpoint_plan": [
                    {"checkpoint": "Source annotation", "owner": "teacher"},
                    {"checkpoint": "Draft review", "owner": "students"},
                    {"checkpoint": "Revision conference", "owner": "teacher"},
                ],
                "materials": material_summaries,
                "standards": standards,
            }
            summary = f"Built a lesson sequence for {(assignment or classroom or {}).get('title', 'the classroom')}."
            return artifact, summary

        if agent_name == "rubric-designer":
            criteria = (assignment or {}).get("rubric", []) or ["Evidence Quality", "Reasoning", "Citation Accuracy", "Audience Fit"]
            artifact = {
                "rubric": [
                    {"criterion": criterion, "look_for": f"Evidence-backed performance in {criterion.lower()}."}
                    for criterion in criteria
                ],
                "teacher_look_fors": [
                    "Students cite only approved classroom materials.",
                    "Claims connect directly to documented evidence.",
                    "The final product matches the selected template and audience.",
                ],
                "standards": standards,
            }
            summary = f"Generated rubric guidance for {(assignment or classroom or {}).get('title', 'the assignment')}."
            return artifact, summary

        if agent_name == "feedback-coach":
            artifact = {
                "feedback_notes": teacher_comments or [
                    "Strengthen the explanation that links claims to evidence.",
                    "Use more precise citation callouts in the strongest section.",
                    "Add one revision target tied to the rubric.",
                ],
                "revision_targets": project_sections or ["Introduction", "Evidence", "Reflection"],
                "conference_focus": (prompt or "Use the rubric and project evidence to drive the next conference.").strip(),
            }
            summary = f"Prepared revision coaching notes for {(student or {}).get('name', 'the selected student')}."
            return artifact, summary

        if agent_name == "classroom-analyst":
            students = (classroom or {}).get("students", [])
            assignments = (classroom or {}).get("assignments", [])
            launched = sum(len(item.get("launched_projects", [])) for item in assignments)
            artifact = {
                "classroom_snapshot": {
                    "students": len(students),
                    "assignments": len(assignments),
                    "launched_projects": launched,
                    "shared_materials": len((classroom or {}).get("evidence_library", [])),
                },
                "risk_flags": [
                    "Some students have not launched a project yet." if launched < len(students) else "Project launch coverage is on track.",
                    "Upload more shared evidence if only one source is available." if len((classroom or {}).get("evidence_library", [])) < 2 else "Shared evidence coverage is healthy.",
                ],
            }
            summary = f"Summarized classroom momentum for {(classroom or {}).get('title', 'the classroom')}."
            return artifact, summary

        if agent_name == "project-coach":
            artifact = {
                "milestone_plan": [
                    "Review the assignment prompt and approved evidence.",
                    "Draft one section anchored in a specific source.",
                    "Check citations before exporting a local bundle.",
                ],
                "next_steps": [
                    f"Focus first on {project_sections[0]}." if project_sections else "Start with the opening section of the project.",
                    "Use the strongest approved source as the anchor citation.",
                    "Request teacher approval before any sensitive sharing action.",
                ],
                "project_slug": (project or {}).get("slug", ""),
            }
            summary = f"Prepared a project plan for {(student or {}).get('name', 'the student')}."
            return artifact, summary

        if agent_name == "research-coach":
            artifact = {
                "research_questions": [
                    f"What evidence best explains {(assignment or project or {}).get('topic', 'the topic')}?",
                    "Which approved source has the strongest factual support?",
                    "What citation will prove the main claim?",
                ],
                "evidence_shortlist": material_summaries or [{"title": "No materials yet", "summary": "Upload classroom materials to build a stronger evidence library."}],
            }
            summary = f"Built a research brief for {(student or {}).get('name', 'the student')}."
            return artifact, summary

        if agent_name == "citation-tutor":
            artifact = {
                "citation_checklist": [
                    "Match each claim to an approved source chunk.",
                    "Use the citation label from the evidence library or project document.",
                    "Avoid unsupported statements before export.",
                ],
                "evidence_links": material_summaries[:3],
            }
            summary = "Generated citation guidance tied to approved sources."
            return artifact, summary

        if agent_name == "revision-tutor":
            artifact = {
                "revision_plan": [
                    "Compare the current draft against the rubric.",
                    "Revise the weakest evidence-backed section first.",
                    "Recheck audience fit and citation accuracy before submitting.",
                ],
                "quality_checks": teacher_comments or [
                    "Confirm each paragraph has a cited source.",
                    "Make sure the revision directly improves a rubric criterion.",
                ],
            }
            summary = f"Prepared revision steps for {(student or {}).get('name', 'the student')}."
            return artifact, summary

        if agent_name == "study-planner":
            artifact = {
                "study_schedule": [
                    {"block": "20 minutes", "focus": "Read approved evidence and annotate two sources."},
                    {"block": "25 minutes", "focus": "Draft or revise one project section."},
                    {"block": "10 minutes", "focus": "Update citations and checklist."},
                ],
                "checkpoint_targets": [
                    assignment.get("due_date") or "Set a local due date",
                    "Midpoint draft review",
                    "Final export check",
                ],
            }
            summary = f"Created a study plan for {(student or {}).get('name', 'the student')}."
            return artifact, summary

        if agent_name == "approval-guard":
            pending = [approval for approval in self.list_approvals() if approval["status"] == "pending"]
            artifact = {
                "approval_summary": {
                    "pending": len(pending),
                    "required_for": list(APPROVAL_REQUIRED_FOR),
                },
                "safety_rationale": "Sensitive actions are queued for review and never executed silently.",
            }
            summary = "Reviewed the current approval queue and safety boundaries."
            return artifact, summary

        if agent_name == "audit-reporter":
            recent = self.list_audit_entries(limit=8)
            artifact = {
                "audit_summary": recent,
                "policy_findings": [
                    "All agents are restricted to bounded educational tool scopes.",
                    "No unrestricted shell, messaging, or browser automation is permitted.",
                ],
            }
            summary = "Summarized the recent classroom audit log."
            return artifact, summary

        artifact = {
            "evidence_map": material_summaries,
            "coverage_summary": {
                "shared_materials": len((classroom or {}).get("evidence_library", [])),
                "student_projects": len((student or {}).get("project_slugs", [])),
            },
        }
        summary = "Mapped shared evidence usage across the classroom."
        return artifact, summary

    def _create_approval(self, payload: dict[str, Any]) -> dict[str, Any]:
        approvals = self._load_json(self.approvals_path)
        prev_hash = approvals[0]["entry_hash"] if approvals else ""
        approval = {
            "approval_id": f"approval-{uuid4().hex[:10]}",
            "status": "pending",
            "requested_at": self._timestamp(),
            "reviewed_at": None,
            "reviewer": "",
            "note": "",
            "agent_name": payload["agent_name"],
            "role": payload["role"],
            "classroom_id": payload.get("classroom_id"),
            "assignment_id": payload.get("assignment_id"),
            "student_id": payload.get("student_id"),
            "project_slug": payload.get("project_slug"),
            "requested_actions": list(payload.get("requested_actions", [])),
            "prompt_excerpt": str(payload.get("risk_assessment", {}).get("redacted_excerpt") or str(payload.get("prompt") or "")[:220]),
            "rationale": "Sensitive actions require explicit teacher or admin review and are not executed automatically.",
            "risk_assessment": payload.get("risk_assessment") or self._assess_prompt_risk(str(payload.get("prompt") or "")),
            "prev_hash": prev_hash,
        }
        approval["entry_hash"] = self._sign_record(approval, exclude={"entry_hash"})
        approvals.insert(0, approval)
        self._write_json(self.approvals_path, approvals)
        return approval

    def _get_agent(self, agent_name: str, role: str) -> dict[str, Any]:
        for agent in EDUCATION_AGENT_CATALOG:
            if agent["name"] == agent_name and agent["role"] == role:
                return dict(agent)
        raise ValueError(f"Unknown agent '{agent_name}' for role '{role}'.")

    def _detect_sensitive_actions(self, prompt: str) -> list[str]:
        lowered = prompt.lower()
        matches = []
        keyword_map = {
            "shell_execution": ("terminal", "shell", "run command", "install package"),
            "browser_navigation": ("open browser", "visit website", "navigate to", "click link"),
            "external_messaging": ("email", "message", "text parents", "send to class"),
            "public_publish": ("publish publicly", "post online", "share on social", "send externally"),
            "destructive_filesystem_actions": ("delete file", "remove project", "erase workspace"),
        }
        for action, keywords in keyword_map.items():
            if any(keyword in lowered for keyword in keywords):
                matches.append(action)
        return matches

    def _hydrate_classroom(self, classroom: dict[str, Any]) -> dict[str, Any]:
        classroom = dict(classroom)
        assignments = [dict(item) for item in classroom.get("assignments", [])]
        students = [dict(item) for item in classroom.get("students", [])]
        materials = [dict(item) for item in classroom.get("evidence_library", [])]
        classroom["assignments"] = assignments
        classroom["students"] = students
        classroom["evidence_library"] = materials
        classroom["student_count"] = len(students)
        classroom["assignment_count"] = len(assignments)
        classroom["evidence_count"] = len(materials)
        classroom["project_count"] = sum(len(item.get("launched_projects", [])) for item in assignments)
        security = dict(classroom.get("security") or {})
        security["audit_chain_valid"] = self._verify_chain(self._load_json(self.audit_path))
        security["approval_chain_valid"] = self._verify_chain(self._load_json(self.approvals_path))
        classroom["security_posture"] = {
            "policy_version": security.get("policy_version", "1.0"),
            "protected": bool(security.get("protected", False)),
            "max_material_bytes": int(security.get("max_material_bytes") or self.settings.edu_material_max_bytes),
            "allowed_content_types": list(security.get("allowed_content_types") or ALLOWED_MATERIAL_CONTENT_TYPES),
            "audit_chain_valid": bool(security.get("audit_chain_valid", True)),
            "approval_chain_valid": bool(security.get("approval_chain_valid", True)),
        }
        classroom.pop("security", None)
        return classroom

    def _load_classroom(self, classroom_id: str) -> dict[str, Any]:
        path = self.classrooms_dir / classroom_id / "classroom.yaml"
        if not path.exists():
            raise FileNotFoundError(classroom_id)
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def _save_classroom(self, classroom: dict[str, Any]) -> None:
        classroom_dir = self.classrooms_dir / classroom["classroom_id"]
        classroom_dir.mkdir(parents=True, exist_ok=True)
        security = classroom.get("security") or {}
        security["audit_chain_valid"] = self._verify_chain(self._load_json(self.audit_path))
        security["approval_chain_valid"] = self._verify_chain(self._load_json(self.approvals_path))
        classroom["security"] = security
        with (classroom_dir / "classroom.yaml").open("w", encoding="utf-8") as handle:
            yaml.safe_dump(classroom, handle, sort_keys=False, allow_unicode=False)

    def _find_assignment(self, classroom: dict[str, Any], assignment_id: str) -> dict[str, Any]:
        for assignment in classroom.get("assignments", []):
            if assignment["assignment_id"] == assignment_id:
                return assignment
        raise FileNotFoundError(assignment_id)

    def _find_student(self, classroom: dict[str, Any], student_id: str) -> dict[str, Any]:
        for student in classroom.get("students", []):
            if student["student_id"] == student_id:
                return student
        raise FileNotFoundError(student_id)

    def _append_audit(self, payload: dict[str, Any]) -> dict[str, Any]:
        entries = self._load_json(self.audit_path)
        prev_hash = entries[0]["entry_hash"] if entries else ""
        entry = {
            "audit_id": f"audit-{uuid4().hex[:10]}",
            "created_at": self._timestamp(),
            "prev_hash": prev_hash,
            **payload,
        }
        entry["entry_hash"] = self._sign_record(entry, exclude={"entry_hash"})
        entries.insert(0, entry)
        self._write_json(self.audit_path, entries[:300])
        return entry

    def _generate_access_bootstrap(self, classroom_id: str) -> dict[str, str]:
        teacher_access_key = f"tch-{secrets.token_urlsafe(18)}"
        student_access_key = f"std-{secrets.token_urlsafe(18)}"
        reviewer_access_key = f"rev-{secrets.token_urlsafe(18)}"
        return {
            "teacher_access_key": teacher_access_key,
            "student_access_key": student_access_key,
            "reviewer_access_key": reviewer_access_key,
            "teacher_access_key_hash": self._hash_access_key(classroom_id, "teacher", teacher_access_key),
            "student_access_key_hash": self._hash_access_key(classroom_id, "student", student_access_key),
            "reviewer_access_key_hash": self._hash_access_key(classroom_id, "reviewer", reviewer_access_key),
        }

    def _authorize_classroom_action(self, classroom: dict[str, Any], access_key: str, permitted_roles: set[str]) -> str:
        security = classroom.get("security") or {}
        if not security.get("protected"):
            return "legacy"
        candidate = (access_key or "").strip()
        if not candidate:
            raise ValueError("Access key required for protected classroom action.")
        for role in permitted_roles:
            expected_hash = str(security.get(f"{role}_access_key_hash") or "")
            if expected_hash and hmac.compare_digest(expected_hash, self._hash_access_key(classroom["classroom_id"], role, candidate)):
                return role
        raise ValueError("Invalid classroom access key.")

    def _hash_access_key(self, classroom_id: str, role: str, access_key: str) -> str:
        digest = hmac.new(
            self.security_secret,
            f"{classroom_id}:{role}:{access_key}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return digest

    def _validate_material_upload(self, filename: str, content: bytes, content_type: str, classroom: dict[str, Any]) -> None:
        security = classroom.get("security") or {}
        max_bytes = int(security.get("max_material_bytes") or self.settings.edu_material_max_bytes)
        if len(content) > max_bytes:
            raise ValueError(f"Material exceeds max size of {max_bytes} bytes.")
        normalized_type = (content_type or "").split(";")[0].strip().lower()
        suffix = Path(filename).suffix.lower()
        inferred_text_types = {".txt", ".md", ".csv", ".json"}
        if normalized_type and normalized_type not in ALLOWED_MATERIAL_CONTENT_TYPES and suffix not in inferred_text_types:
            raise ValueError(f"Unsupported classroom material type: {normalized_type or suffix or 'unknown'}.")

    def _assess_prompt_risk(self, prompt: str) -> dict[str, Any]:
        lowered = prompt.lower().strip()
        signals = []
        score = 0
        policy_actions: list[str] = []
        for signal_name, pattern, weight in PROMPT_RISK_PATTERNS:
            if re.search(pattern, lowered):
                signals.append(signal_name)
                score += weight
        if "secret_exfiltration" in signals:
            policy_actions.append("secret_exfiltration")
        if "policy_override" in signals:
            policy_actions.append("policy_override")
        if "external_send" in signals:
            policy_actions.append("external_messaging")
        if "browser_control" in signals:
            policy_actions.append("browser_navigation")
        if "shell_execution" in signals:
            policy_actions.append("shell_execution")
        if "filesystem_damage" in signals:
            policy_actions.append("destructive_filesystem_actions")

        if score >= 70:
            band = "critical"
        elif score >= 40:
            band = "high"
        elif score >= 15:
            band = "moderate"
        else:
            band = "low"
        return {
            "score": min(score, 100),
            "band": band,
            "signals": signals,
            "policy_actions": sorted(set(policy_actions)),
            "redacted_excerpt": self._redact_sensitive_terms(prompt)[:220],
        }

    def _redact_sensitive_terms(self, value: str) -> str:
        redacted = value
        for pattern in [r"(?i)\b(password|token|secret|credential|api key)\b", r"(?i)\b(ignore previous|jailbreak|bypass)\b"]:
            redacted = re.sub(pattern, "[redacted]", redacted)
        return redacted

    def _sign_record(self, payload: dict[str, Any], *, exclude: set[str] | None = None) -> str:
        cleaned = {key: value for key, value in payload.items() if not exclude or key not in exclude}
        canonical = json.dumps(cleaned, sort_keys=True, separators=(",", ":"))
        return hmac.new(self.security_secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    def _verify_chain(self, records: list[dict[str, Any]]) -> bool:
        expected_prev = ""
        for record in reversed(records):
            if str(record.get("prev_hash") or "") != expected_prev:
                return False
            expected_hash = self._sign_record(record, exclude={"entry_hash"})
            if not hmac.compare_digest(str(record.get("entry_hash") or ""), expected_hash):
                return False
            expected_prev = expected_hash
        return True

    def _rebuild_chain(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rebuilt: list[dict[str, Any]] = []
        prev_hash = ""
        for record in reversed(records):
            updated = dict(record)
            updated["prev_hash"] = prev_hash
            updated["entry_hash"] = self._sign_record(updated, exclude={"entry_hash"})
            prev_hash = updated["entry_hash"]
            rebuilt.insert(0, updated)
        return rebuilt

    def _extract_material_text(self, path: Path, content: bytes, content_type: str) -> tuple[str, str]:
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md", ".csv", ".json"} or content_type.startswith("text/"):
            return self._decode_text(content), "text"
        if suffix == ".pdf" or content_type == "application/pdf":
            try:
                reader = PdfReader(str(path))
                return "\n".join(page.extract_text() or "" for page in reader.pages).strip(), "pdf"
            except Exception:
                return "", "pdf-fallback"
        return "", "binary"

    def _summarize_text(self, text: str) -> str:
        cleaned = " ".join(text.split())
        if not cleaned:
            return "Binary classroom material uploaded. Open the project workspace to inspect the original file."
        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        return " ".join(sentences[:2])[:280]

    def _safe_filename(self, filename: str) -> str:
        sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", filename.strip())
        return sanitized or "upload.bin"

    def _title_from_filename(self, filename: str) -> str:
        stem = Path(filename).stem.replace("-", " ").replace("_", " ").strip()
        return stem.title() or "Untitled Material"

    def _decode_text(self, content: bytes) -> str:
        for encoding in ("utf-8", "latin-1"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return content.decode("utf-8", errors="ignore")

    def _load_json(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, payload: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _timestamp(self) -> str:
        return datetime.now(UTC).isoformat()
