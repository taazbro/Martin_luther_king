from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request
from uuid import uuid4

import yaml

from app.core.config import Settings
from app.services.education_os import EducationOperatingSystemService
from app.services.provider_ai import ProviderAIService
from app.services.studio_engine import ProjectStudioService, TemplateRegistryService


SCHOOL_PACKS: tuple[dict[str, Any], ...] = (
    {
        "pack_id": "urban-civics-district",
        "label": "Urban Civics District Pack",
        "audience": "district",
        "description": "A civics-forward starter bundle for districts running inquiry, evidence, and community-action projects.",
        "recommended_template_ids": ["research-portfolio", "lesson-module", "civic-campaign-simulator"],
        "sample_project_slug": "urban-civics-district-starter",
        "plugin_ids": ["standards-mapper"],
        "offline_ready": True,
    },
    {
        "pack_id": "community-history-nonprofit",
        "label": "Community History Nonprofit Pack",
        "audience": "nonprofit",
        "description": "A local-history and public-memory starter kit for archives, museums, and neighborhood groups.",
        "recommended_template_ids": ["museum-exhibit-site", "documentary-story", "mlk-legacy-lab"],
        "sample_project_slug": "community-history-nonprofit-starter",
        "plugin_ids": ["oral-history-pack"],
        "offline_ready": True,
    },
    {
        "pack_id": "teacher-research-writing-kit",
        "label": "Teacher Research and Writing Kit",
        "audience": "teacher",
        "description": "A one-click starter for classroom research portfolios, revision coaching, and assessment packs.",
        "recommended_template_ids": ["research-portfolio", "lesson-module", "debate-prep-kit"],
        "sample_project_slug": "teacher-research-writing-starter",
        "plugin_ids": ["standards-mapper"],
        "offline_ready": True,
    },
)

ROUTING_PROFILES: dict[str, dict[str, Any]] = {
    "writing": {
        "provider_order": ["openai", "mistral", "cohere", "anthropic"],
        "required_capability": "assignments",
        "prefer_local": True,
    },
    "feedback": {
        "provider_order": ["anthropic", "openai", "cohere", "mistral"],
        "required_capability": "feedback",
        "prefer_local": True,
    },
    "multimodal": {
        "provider_order": ["google", "openai", "anthropic"],
        "required_capability": "research",
        "prefer_local": False,
    },
    "speed": {
        "provider_order": ["groq", "openai", "xai"],
        "required_capability": "planning",
        "prefer_local": False,
    },
    "research": {
        "provider_order": ["openai", "anthropic", "cohere", "xai", "google"],
        "required_capability": "research",
        "prefer_local": True,
    },
    "assessment": {
        "provider_order": ["openai", "anthropic", "groq", "cohere"],
        "required_capability": "assignments",
        "prefer_local": True,
    },
    "planning": {
        "provider_order": ["openai", "anthropic", "groq", "mistral"],
        "required_capability": "planning",
        "prefer_local": True,
    },
    "review": {
        "provider_order": ["anthropic", "openai", "cohere"],
        "required_capability": "review",
        "prefer_local": True,
    },
}


class EducationGrowthService:
    def __init__(
        self,
        settings: Settings,
        studio_service: ProjectStudioService,
        education_service: EducationOperatingSystemService,
        template_registry: TemplateRegistryService,
        ai_provider_service: ProviderAIService,
    ) -> None:
        self.settings = settings
        self.studio_service = studio_service
        self.education_service = education_service
        self.template_registry = template_registry
        self.ai_provider_service = ai_provider_service
        self.root_dir = settings.studio_root_dir / "education_growth"
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.library_path = self.root_dir / "classroom_library.json"
        self.peer_reviews_path = self.root_dir / "peer_reviews.json"
        self.rubric_models_path = self.root_dir / "rubric_models.json"
        self.family_links_path = self.root_dir / "family_links.json"
        self.school_pack_dir = settings.community_root_dir / "school_packs"
        self.school_pack_dir.mkdir(parents=True, exist_ok=True)
        for path in (self.library_path, self.peer_reviews_path, self.rubric_models_path, self.family_links_path):
            if not path.exists():
                self._write_json(path, [])

    def get_overview(self) -> dict[str, Any]:
        classrooms = self.education_service.list_classrooms()
        library_items = self._load_json(self.library_path)
        peer_reviews = self._load_json(self.peer_reviews_path)
        rubric_models = self._load_json(self.rubric_models_path)
        marketplace = self.get_marketplace()
        return {
            "counts": {
                "classrooms": len(classrooms),
                "library_items": len(library_items),
                "peer_reviews": len(peer_reviews),
                "rubric_models": len(rubric_models),
                "school_packs": len(marketplace["school_packs"]),
                "family_links": len(self._load_json(self.family_links_path)),
            },
            "routing_matrix": [
                {
                    "task_kind": task_kind,
                    "provider_order": list(config["provider_order"]),
                    "required_capability": config["required_capability"],
                    "prefer_local": bool(config["prefer_local"]),
                }
                for task_kind, config in ROUTING_PROFILES.items()
            ],
            "offline_school_edition": self.get_offline_school_edition(),
        }

    def run_assignment_autopilot(self, payload: dict[str, Any]) -> dict[str, Any]:
        classroom = self._authorized_classroom(
            str(payload["classroom_id"]),
            str(payload["access_key"]),
            {"teacher"},
        )
        topic = str(payload["topic"]).strip()
        template = self._pick_template(
            explicit_template_id=str(payload.get("template_id") or "").strip(),
            topic=topic,
            lesson_seed=str(payload.get("lesson_seed") or "").strip(),
            default_template_id=str(classroom.get("default_template_id") or "lesson-module"),
        )
        goals = self._string_list(payload.get("goals")) or self._default_goals(topic, template)
        rubric = self._string_list(payload.get("rubric")) or [
            "Evidence Quality",
            "Citation Accuracy",
            "Clarity",
            "Revision Quality",
        ]
        standards = self._string_list(payload.get("standards")) or list(classroom.get("standards_focus", []))
        route = self._run_hybrid_brain(
            task_kind="writing",
            prompt=(
                f"Build a classroom-safe assignment autopilot package for topic '{topic}' "
                f"using template '{template['label']}' and rubric {', '.join(rubric)}."
            ),
            system_prompt="You help teachers create bounded, evidence-backed assignment packages for EduClawn.",
            preferred_profile_id=str(payload.get("ai_profile_id") or "").strip(),
            metadata={"feature": "assignment_autopilot", "classroom_id": classroom["classroom_id"]},
            classroom_id=classroom["classroom_id"],
        )
        assignment_title = str(payload.get("title") or "").strip() or self._assignment_title(topic, template["label"])
        assignment_summary = str(payload.get("summary") or "").strip() or (
            f"Students will investigate {topic} using approved evidence and a {template['label']} workflow."
        )
        requested_mode = str(payload.get("local_mode") or "").strip()
        if requested_mode:
            local_mode = requested_mode
        elif route["decision"]["execution_mode"] == "provider-ai":
            local_mode = "provider-ai"
        elif route["decision"]["execution_mode"] == "local-llm":
            local_mode = "local-llm"
        else:
            local_mode = "no-llm"
        created_classroom = self.education_service.create_assignment(
            classroom["classroom_id"],
            {
                "title": assignment_title,
                "summary": assignment_summary,
                "topic": topic,
                "audience": str(payload.get("audience") or classroom.get("grade_band") or "students").strip(),
                "template_id": template["id"],
                "goals": goals,
                "rubric": rubric,
                "standards": standards,
                "due_date": str(payload.get("due_date") or "").strip(),
                "local_mode": local_mode,
                "ai_profile_id": str(payload.get("ai_profile_id") or "").strip(),
                "access_key": str(payload["access_key"]),
            },
        )
        assignment = created_classroom["assignments"][-1]
        evidence_pack = self._rank_classroom_materials(classroom, topic, assignment_id=assignment["assignment_id"])
        self._attach_assignment_evidence(classroom["classroom_id"], assignment["assignment_id"], evidence_pack)
        refreshed_classroom = self.education_service.get_classroom(classroom["classroom_id"])
        refreshed_assignment = self.education_service._find_assignment(  # noqa: SLF001
            self.education_service._load_classroom(classroom["classroom_id"]),  # noqa: SLF001
            assignment["assignment_id"],
        )
        checkpoints = self._checkpoint_plan(topic, refreshed_assignment)
        standards_map = self.map_standards(
            {
                "classroom_id": classroom["classroom_id"],
                "assignment_id": assignment["assignment_id"],
                "access_key": str(payload["access_key"]),
            }
        )
        assessment_pack = self.generate_assessment_pack(
            {
                "classroom_id": classroom["classroom_id"],
                "assignment_id": assignment["assignment_id"],
                "access_key": str(payload["access_key"]),
                "ai_profile_id": str(payload.get("ai_profile_id") or "").strip(),
            }
        )
        lesson_scaffold = self._lesson_to_project_scaffold(
            topic=topic,
            template=template,
            goals=goals,
            rubric=rubric,
            evidence_pack=evidence_pack,
            ai_output=route["output_text"],
        )
        self.education_service._append_audit(  # noqa: SLF001
            {
                "actor_role": "teacher",
                "agent_name": "assignment-autopilot",
                "action": "assignment_autopilot_run",
                "summary": f"Autopilot built {assignment_title} with {len(evidence_pack)} suggested evidence items.",
                "classroom_id": classroom["classroom_id"],
                "assignment_id": assignment["assignment_id"],
                "allowed_actions": ["draft_lesson_artifacts", "align_rubrics_and_standards", "inspect_evidence_library"],
                "sensitive_actions_requested": [],
                "status": "completed",
                "ai_usage": route["decision"].get("selected_provider"),
            }
        )
        return {
            "classroom": refreshed_classroom,
            "assignment": self.education_service.get_classroom(classroom["classroom_id"])["assignments"][-1],
            "route": route["decision"],
            "evidence_pack": evidence_pack,
            "checkpoints": checkpoints,
            "export_targets": list(template.get("export_targets", [])),
            "assessment_pack": assessment_pack,
            "standards_map": standards_map,
            "lesson_to_project_scaffold": lesson_scaffold,
            "teacher_summary": (
                route["output_text"]
                or f"Autopilot prepared {assignment_title} with rubric-aligned checkpoints and reusable evidence."
            ),
        }

    def run_revision_coach(self, payload: dict[str, Any]) -> dict[str, Any]:
        classroom = self._authorized_classroom(
            str(payload["classroom_id"]),
            str(payload["access_key"]),
            {"student", "teacher", "reviewer"},
        )
        assignment = self.education_service._find_assignment(  # noqa: SLF001
            self.education_service._load_classroom(classroom["classroom_id"]),  # noqa: SLF001
            str(payload["assignment_id"]),
        )
        draft_text = str(payload.get("draft_text") or "").strip()
        rubric = self._string_list(payload.get("rubric")) or list(assignment.get("rubric", []))
        teacher_feedback = self._string_list(payload.get("teacher_feedback"))
        claims = self._extract_claims(draft_text)
        citation_verification = self.verify_citations(
            {
                "project_slug": str(payload.get("project_slug") or "").strip(),
                "claims": claims,
            }
        )
        rubric_breakdown = self._rubric_breakdown(
            draft_text=draft_text,
            rubric=rubric,
            citation_verification=citation_verification,
            teacher_feedback=teacher_feedback,
        )
        route = self._run_hybrid_brain(
            task_kind="feedback",
            prompt=(
                f"Compare this student draft against rubric {', '.join(rubric)} and return concrete revision steps.\n\n"
                f"Draft:\n{draft_text}\n\nTeacher feedback:\n{'; '.join(teacher_feedback) or 'None yet.'}"
            ),
            system_prompt="You are a revision coach inside EduClawn. Return concrete, classroom-safe revision advice only.",
            preferred_profile_id=str(payload.get("ai_profile_id") or "").strip(),
            metadata={
                "feature": "revision_coach",
                "classroom_id": classroom["classroom_id"],
                "assignment_id": assignment["assignment_id"],
                "project_slug": str(payload.get("project_slug") or "").strip(),
            },
            classroom_id=classroom["classroom_id"],
        )
        revision_tasks = self._revision_tasks(rubric_breakdown, citation_verification, teacher_feedback)
        self.education_service._append_audit(  # noqa: SLF001
            {
                "actor_role": "student",
                "agent_name": "student-revision-coach",
                "action": "revision_coach_run",
                "summary": f"Revision coach generated {len(revision_tasks)} tasks for {assignment['title']}.",
                "classroom_id": classroom["classroom_id"],
                "assignment_id": assignment["assignment_id"],
                "project_slug": str(payload.get("project_slug") or "").strip() or None,
                "allowed_actions": ["review_student_projects", "propose_revisions", "map_citations"],
                "sensitive_actions_requested": [],
                "status": "completed",
                "ai_usage": route["decision"].get("selected_provider"),
            }
        )
        return {
            "route": route["decision"],
            "rubric_breakdown": rubric_breakdown,
            "citation_verification": citation_verification,
            "revision_tasks": revision_tasks,
            "student_summary": route["output_text"] or self._student_revision_summary(rubric_breakdown, revision_tasks),
            "family_summary": self._family_revision_summary(rubric_breakdown, revision_tasks),
        }

    def get_classroom_library(self, classroom_id: str, access_key: str) -> dict[str, Any]:
        classroom = self._authorized_classroom(classroom_id, access_key, {"teacher", "reviewer"})
        teacher_key = self._teacher_key(classroom["teacher_name"])
        library_items = self._load_json(self.library_path)
        teacher_items = [item for item in library_items if item["teacher_key"] == teacher_key]
        collections = []
        seen_collection_ids: set[str] = set()
        for item in teacher_items:
            collection_id = item["collection_id"]
            if collection_id in seen_collection_ids:
                continue
            seen_collection_ids.add(collection_id)
            related = [entry for entry in teacher_items if entry["collection_id"] == collection_id]
            collections.append(
                {
                    "collection_id": collection_id,
                    "label": related[0]["collection_label"],
                    "classroom_ids": sorted({entry["origin_classroom_id"] for entry in related}),
                    "item_count": len(related),
                    "latest_topic": related[0]["topic_hint"],
                }
            )
        reusable_items = sorted(
            teacher_items,
            key=lambda item: item["promoted_at"],
            reverse=True,
        )[:12]
        recommended = []
        current_topics = " ".join(
            [classroom["subject"], classroom["description"], *classroom.get("standards_focus", [])]
        )
        for item in teacher_items:
            if item["origin_classroom_id"] == classroom["classroom_id"]:
                continue
            score = self._keyword_score(current_topics, f"{item['title']} {item['summary']} {item['topic_hint']}")
            if score <= 0:
                continue
            recommended.append({**item, "reuse_score": score})
        recommended.sort(key=lambda item: (-int(item["reuse_score"]), item["title"]))
        return {
            "classroom_id": classroom["classroom_id"],
            "teacher_name": classroom["teacher_name"],
            "item_count": len(teacher_items),
            "collections": collections,
            "reusable_items": reusable_items,
            "recommended_reuse": recommended[:8],
        }

    def promote_classroom_library(self, payload: dict[str, Any]) -> dict[str, Any]:
        classroom = self._authorized_classroom(
            str(payload["classroom_id"]),
            str(payload["access_key"]),
            {"teacher"},
        )
        requested_ids = set(self._string_list(payload.get("material_ids")))
        library_items = self._load_json(self.library_path)
        existing_fingerprints = {item["fingerprint"] for item in library_items}
        collection_id = f"collection-{self._teacher_key(classroom['teacher_name'])}-{self._slugify(classroom['title'])}"
        inserted = 0
        for material in classroom.get("evidence_library", []):
            if requested_ids and material["material_id"] not in requested_ids:
                continue
            fingerprint = self._library_fingerprint(classroom, material)
            if fingerprint in existing_fingerprints:
                continue
            entry = {
                "library_item_id": f"lib-{uuid4().hex[:10]}",
                "teacher_key": self._teacher_key(classroom["teacher_name"]),
                "teacher_name": classroom["teacher_name"],
                "origin_classroom_id": classroom["classroom_id"],
                "collection_id": collection_id,
                "collection_label": f"{classroom['title']} shared evidence",
                "topic_hint": classroom["description"] or classroom["subject"],
                "title": material["title"],
                "summary": material["summary"],
                "source_material_id": material["material_id"],
                "file_name": material["file_name"],
                "content_type": material["content_type"],
                "word_count": material["word_count"],
                "scope": material["scope"],
                "promoted_at": self._timestamp(),
                "fingerprint": fingerprint,
            }
            library_items.insert(0, entry)
            existing_fingerprints.add(fingerprint)
            inserted += 1
        self._write_json(self.library_path, library_items[:600])
        self.education_service._append_audit(  # noqa: SLF001
            {
                "actor_role": "teacher",
                "agent_name": "classroom-library",
                "action": "library_promoted",
                "summary": f"Promoted {inserted} materials into the reusable classroom library.",
                "classroom_id": classroom["classroom_id"],
                "allowed_actions": ["inspect_evidence_library", "read_classroom_materials"],
                "sensitive_actions_requested": [],
                "status": "completed",
            }
        )
        return self.get_classroom_library(classroom["classroom_id"], str(payload["access_key"]))

    def create_peer_review(self, payload: dict[str, Any]) -> dict[str, Any]:
        classroom = self._authorized_classroom(
            str(payload["classroom_id"]),
            str(payload["access_key"]),
            {"student", "teacher"},
        )
        raw_classroom = self.education_service._load_classroom(classroom["classroom_id"])  # noqa: SLF001
        assignment = self.education_service._find_assignment(raw_classroom, str(payload["assignment_id"]))  # noqa: SLF001
        reviewer = self.education_service._find_student(raw_classroom, str(payload["reviewer_student_id"]))  # noqa: SLF001
        target = self.education_service._find_student(raw_classroom, str(payload["target_student_id"]))  # noqa: SLF001
        rubric = self._string_list(payload.get("rubric")) or list(assignment.get("rubric", []))
        draft_text = str(payload.get("draft_text") or "").strip()
        comments = self._peer_review_comments(draft_text, rubric)
        approval = self.education_service._create_approval(  # noqa: SLF001
            {
                "agent_name": "approval-guard",
                "role": "shared",
                "classroom_id": classroom["classroom_id"],
                "assignment_id": assignment["assignment_id"],
                "student_id": target["student_id"],
                "project_slug": str(payload.get("project_slug") or "").strip() or None,
                "requested_actions": ["peer_review_release"],
                "prompt": f"Release peer review from {reviewer['name']} to {target['name']}: {draft_text[:180]}",
                "risk_assessment": {
                    "score": 42,
                    "band": "moderate",
                    "signals": ["peer_review_requires_teacher_gate"],
                    "policy_actions": ["peer_review_release"],
                    "redacted_excerpt": draft_text[:180],
                },
            }
        )
        review = {
            "review_id": f"peer-{uuid4().hex[:10]}",
            "classroom_id": classroom["classroom_id"],
            "assignment_id": assignment["assignment_id"],
            "project_slug": str(payload.get("project_slug") or "").strip(),
            "reviewer_student_id": reviewer["student_id"],
            "reviewer_name": reviewer["name"],
            "target_student_id": target["student_id"],
            "target_student_name": target["name"],
            "status": "pending_teacher_approval",
            "summary": f"Peer review from {reviewer['name']} is waiting for teacher approval.",
            "rubric_guided_comments": comments,
            "created_at": self._timestamp(),
            "resolved_at": "",
            "moderator": "",
            "note": "",
            "approval_id": approval["approval_id"],
        }
        reviews = self._load_json(self.peer_reviews_path)
        reviews.insert(0, review)
        self._write_json(self.peer_reviews_path, reviews[:300])
        self.education_service._append_audit(  # noqa: SLF001
            {
                "actor_role": "student",
                "agent_name": "peer-review-mode",
                "action": "peer_review_submitted",
                "summary": f"{reviewer['name']} submitted a peer review for {target['name']}.",
                "classroom_id": classroom["classroom_id"],
                "assignment_id": assignment["assignment_id"],
                "student_id": target["student_id"],
                "project_slug": review["project_slug"] or None,
                "allowed_actions": ["review_student_projects", "queue_teacher_approval"],
                "sensitive_actions_requested": ["peer_review_release"],
                "status": "approval_required",
            }
        )
        return review

    def list_peer_reviews(self, classroom_id: str, access_key: str) -> list[dict[str, Any]]:
        classroom = self._authorized_classroom(classroom_id, access_key, {"teacher", "reviewer"})
        reviews = self._load_json(self.peer_reviews_path)
        return [review for review in reviews if review["classroom_id"] == classroom["classroom_id"]]

    def suggest_peer_review_pairs(self, classroom_id: str, assignment_id: str, access_key: str) -> dict[str, Any]:
        classroom = self._authorized_classroom(classroom_id, access_key, {"teacher", "reviewer"})
        raw_classroom = self.education_service._load_classroom(classroom["classroom_id"])  # noqa: SLF001
        assignment = self.education_service._find_assignment(raw_classroom, assignment_id)  # noqa: SLF001
        launched = sorted(assignment.get("launched_projects", []), key=lambda item: item["student_name"])
        pairs = []
        if len(launched) >= 2:
            for index, reviewer in enumerate(launched):
                target = launched[(index + 1) % len(launched)]
                if reviewer["student_id"] == target["student_id"]:
                    continue
                pairs.append(
                    {
                        "reviewer_student_id": reviewer["student_id"],
                        "reviewer_name": reviewer["student_name"],
                        "target_student_id": target["student_id"],
                        "target_student_name": target["student_name"],
                        "reviewer_project_slug": reviewer["project_slug"],
                        "target_project_slug": target["project_slug"],
                    }
                )
        return {
            "classroom_id": classroom["classroom_id"],
            "assignment_id": assignment["assignment_id"],
            "assignment_title": assignment["title"],
            "pair_count": len(pairs),
            "pairs": pairs,
        }

    def resolve_peer_review(self, review_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        reviews = self._load_json(self.peer_reviews_path)
        for review in reviews:
            if review["review_id"] != review_id:
                continue
            classroom = self._authorized_classroom(
                str(review["classroom_id"]),
                str(payload["access_key"]),
                {"teacher", "reviewer"},
            )
            decision = str(payload["decision"]).strip()
            if decision not in {"approved", "rejected"}:
                raise ValueError("Decision must be approved or rejected.")
            review["status"] = decision
            review["resolved_at"] = self._timestamp()
            review["moderator"] = str(payload.get("reviewer") or "").strip() or classroom["teacher_name"]
            review["note"] = str(payload.get("note") or "").strip()
            if review.get("approval_id"):
                self.education_service.resolve_approval(  # noqa: SLF001
                    str(review["approval_id"]),
                    {
                        "decision": decision,
                        "reviewer": review["moderator"],
                        "note": review["note"],
                        "access_key": str(payload["access_key"]),
                    },
                )
            self._write_json(self.peer_reviews_path, reviews)
            self.education_service._append_audit(  # noqa: SLF001
                {
                    "actor_role": "teacher",
                    "agent_name": "peer-review-mode",
                    "action": "peer_review_resolved",
                    "summary": f"{decision.title()} peer review {review_id}.",
                    "classroom_id": classroom["classroom_id"],
                    "assignment_id": review["assignment_id"],
                    "student_id": review["target_student_id"],
                    "project_slug": review["project_slug"] or None,
                    "allowed_actions": ["queue_teacher_approval", "review_student_projects"],
                    "sensitive_actions_requested": [],
                    "status": decision,
                }
            )
            return review
        raise FileNotFoundError(review_id)

    def get_family_view(self, classroom_id: str, project_slug: str, access_key: str) -> dict[str, Any]:
        classroom = self._authorized_classroom(classroom_id, access_key, {"teacher", "reviewer", "student"})
        project = self.studio_service.get_project(project_slug)
        launched = self._find_project_context(classroom, project_slug)
        readiness = self.studio_service.get_submission_readiness(project_slug)
        progress = {
            "status": project["status"],
            "documents": len(project.get("documents", [])),
            "exports": len(project.get("exports", [])),
            "teacher_comments": len(project.get("teacher_comments", [])),
            "revision_steps": len(project.get("revision_history", [])),
            "progress_state": readiness["progress_state"],
            "ready_for_export": readiness["ready_for_export"],
        }
        simple_language_summary = (
            f"{project['title']} is a local project about {project['topic']}. "
            f"It currently includes {progress['documents']} source documents and {progress['exports']} downloadable exports."
        )
        next_steps = []
        if progress["documents"] < 2:
            next_steps.append("Add one more source so the project has stronger evidence.")
        if progress["teacher_comments"] > 0:
            next_steps.append("Review the latest teacher feedback before exporting the final version.")
        if progress["exports"] == 0:
            next_steps.append("Run the project workflow so the family can download the finished project.")
        if not progress["ready_for_export"]:
            next_steps.append("Finish the citation and review checkpoints before the final export is shared.")
        if not next_steps:
            next_steps.append("The project is in good shape. Review the downloads together and celebrate the work.")
        share_link = self._find_family_share_link(classroom["classroom_id"], project_slug)
        return {
            "classroom_id": classroom["classroom_id"],
            "classroom_title": classroom["title"],
            "project_slug": project["slug"],
            "project_title": project["title"],
            "student_name": launched.get("student_name") if launched else "",
            "assignment_title": launched.get("assignment_title") if launched else "",
            "summary": simple_language_summary,
            "progress": progress,
            "teacher_comments": [
                {
                    "criterion": comment["criterion"] or "General support",
                    "plain_language": comment["body"],
                    "created_at": comment["created_at"],
                }
                for comment in project.get("teacher_comments", [])[:6]
            ],
            "next_steps": next_steps,
            "downloads": [
                {
                    "export_type": export["export_type"],
                    "path": export["path"],
                    "created_at": export["created_at"],
                }
                for export in project.get("exports", [])
            ],
            "share_link": share_link.get("share_url", ""),
        }

    def create_family_share_link(self, classroom_id: str, project_slug: str, access_key: str) -> dict[str, Any]:
        classroom = self._authorized_classroom(classroom_id, access_key, {"teacher", "reviewer"})
        project = self.studio_service.get_project(project_slug)
        token = f"family-{uuid4().hex[:18]}"
        link = {
            "share_token": token,
            "classroom_id": classroom["classroom_id"],
            "project_slug": project["slug"],
            "project_title": project["title"],
            "created_at": self._timestamp(),
            "share_url": f"/api/v1/edu/growth/family-view/shared/{token}",
        }
        links = self._load_json(self.family_links_path)
        links = [
            existing
            for existing in links
            if not (existing["classroom_id"] == classroom["classroom_id"] and existing["project_slug"] == project_slug)
        ]
        links.insert(0, link)
        self._write_json(self.family_links_path, links[:300])
        self.education_service._append_audit(  # noqa: SLF001
            {
                "actor_role": "teacher",
                "agent_name": "family-share",
                "action": "family_share_link_created",
                "summary": f"Created a family-safe share link for {project['title']}.",
                "classroom_id": classroom["classroom_id"],
                "project_slug": project_slug,
                "allowed_actions": ["share_family_safe_view"],
                "sensitive_actions_requested": [],
                "status": "completed",
            }
        )
        return link

    def get_family_view_by_share_token(self, share_token: str) -> dict[str, Any]:
        link = next((entry for entry in self._load_json(self.family_links_path) if entry["share_token"] == share_token), None)
        if not link:
            raise FileNotFoundError(share_token)
        classroom = self.education_service.get_classroom(str(link["classroom_id"]))
        project = self.studio_service.get_project(str(link["project_slug"]))
        launched = self._find_project_context(classroom, str(link["project_slug"]))
        readiness = self.studio_service.get_submission_readiness(str(link["project_slug"]))
        return {
            "classroom_id": classroom["classroom_id"],
            "classroom_title": classroom["title"],
            "project_slug": project["slug"],
            "project_title": project["title"],
            "student_name": launched.get("student_name") if launched else "",
            "assignment_title": launched.get("assignment_title") if launched else "",
            "summary": f"{project['title']} is ready to review with family-safe details and read-only downloads.",
            "progress": {
                "status": project["status"],
                "documents": len(project.get("documents", [])),
                "exports": len(project.get("exports", [])),
                "teacher_comments": len(project.get("teacher_comments", [])),
                "revision_steps": len(project.get("revision_history", [])),
                "progress_state": readiness["progress_state"],
                "ready_for_export": readiness["ready_for_export"],
            },
            "teacher_comments": [
                {
                    "criterion": comment["criterion"] or "General support",
                    "plain_language": comment["body"],
                    "created_at": comment["created_at"],
                }
                for comment in project.get("teacher_comments", [])[:6]
            ],
            "next_steps": list(readiness["recommendations"]),
            "downloads": [
                {
                    "export_type": export["export_type"],
                    "path": export["path"],
                    "created_at": export["created_at"],
                }
                for export in project.get("exports", [])
            ],
            "share_link": str(link["share_url"]),
        }

    def verify_citations(self, payload: dict[str, Any]) -> dict[str, Any]:
        project_slug = str(payload.get("project_slug") or "").strip()
        claims = [claim for claim in self._string_list(payload.get("claims")) if claim]
        if not claims:
            return {
                "ready_for_export": False,
                "overall_score": 0.0,
                "verified_claims": [],
                "blocked_claims": [],
            }
        verified_claims: list[dict[str, Any]] = []
        blocked_claims: list[dict[str, Any]] = []
        for claim in claims:
            result = {}
            if project_slug:
                query = " ".join(self._keywords(claim)[:8]) or claim
                matches = self.studio_service.search_project(project_slug, query, limit=2)
                result = matches[0] if matches else {}
            score = float(result.get("score") or 0.0)
            entry = {
                "claim": claim,
                "verified": score >= 20.0,
                "score": round(score, 1),
                "citation_label": str(result.get("citation_label") or ""),
                "excerpt": str(result.get("excerpt") or ""),
                "chunk_id": str(result.get("chunk_id") or ""),
            }
            if entry["verified"]:
                verified_claims.append(entry)
            else:
                blocked_claims.append(entry)
        overall_score = round((len(verified_claims) / max(len(claims), 1)) * 100.0, 1)
        return {
            "ready_for_export": len(blocked_claims) == 0,
            "overall_score": overall_score,
            "verified_claims": verified_claims,
            "blocked_claims": blocked_claims,
        }

    def lesson_to_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        classroom = None
        if payload.get("classroom_id") and payload.get("access_key"):
            classroom = self._authorized_classroom(
                str(payload["classroom_id"]),
                str(payload["access_key"]),
                {"teacher"},
            )
        lesson_plan = str(payload.get("lesson_plan") or "").strip()
        template = self._pick_template(
            explicit_template_id=str(payload.get("template_id") or "").strip(),
            topic=str(payload.get("topic") or lesson_plan[:120]).strip(),
            lesson_seed=lesson_plan,
            default_template_id=str((classroom or {}).get("default_template_id") or "lesson-module"),
        )
        topic = str(payload.get("topic") or self._lesson_topic(lesson_plan)).strip()
        goals = self._string_list(payload.get("goals")) or self._lesson_goals(lesson_plan, topic)
        rubric = self._string_list(payload.get("rubric")) or ["Evidence Quality", "Clarity", "Revision Quality"]
        title = str(payload.get("title") or "").strip() or self._assignment_title(topic, template["label"])
        audience = str(payload.get("audience") or (classroom or {}).get("grade_band") or "students").strip()
        route = self._run_hybrid_brain(
            task_kind="planning",
            prompt=f"Convert this lesson plan into a project scaffold: {lesson_plan}",
            system_prompt="You help teachers convert lessons into student project scaffolds inside EduClawn.",
            preferred_profile_id=str(payload.get("ai_profile_id") or "").strip(),
            metadata={"feature": "lesson_to_project", "template_id": template["id"]},
            classroom_id=str((classroom or {}).get("classroom_id") or ""),
        )
        project = self.studio_service.create_project(
            {
                "title": title,
                "summary": route["output_text"] or f"Project scaffold generated from lesson plan: {topic}.",
                "topic": topic,
                "audience": audience,
                "goals": goals,
                "rubric": rubric,
                "template_id": template["id"],
                "local_mode": str(payload.get("local_mode") or "no-llm"),
                "ai_profile_id": str(payload.get("ai_profile_id") or "").strip(),
            }
        )
        if classroom and payload.get("seed_from_classroom", True):
            for material in classroom.get("evidence_library", [])[:6]:
                source_path = self.education_service.root_dir / material["source_path"]
                if source_path.exists():
                    self.studio_service.ingest_document(
                        project["slug"],
                        material["file_name"],
                        source_path.read_bytes(),
                        material["content_type"],
                    )
        scaffold = self._lesson_to_project_scaffold(
            topic=topic,
            template=template,
            goals=goals,
            rubric=rubric,
            evidence_pack=self._rank_classroom_materials(classroom, topic) if classroom else [],
            ai_output=route["output_text"],
        )
        return {
            "project": self.studio_service.get_project(project["slug"]),
            "route": route["decision"],
            "scaffold": scaffold,
        }

    def train_rubric_model(self, payload: dict[str, Any]) -> dict[str, Any]:
        classroom = self._authorized_classroom(
            str(payload["classroom_id"]),
            str(payload["access_key"]),
            {"teacher", "reviewer"},
        )
        requested_slugs = self._string_list(payload.get("project_slugs"))
        if not requested_slugs:
            requested_slugs = self._classroom_project_slugs(classroom)
        projects = [self.studio_service.get_project(slug) for slug in requested_slugs if slug]
        if not projects:
            raise ValueError("No projects were available to train the rubric model.")
        criterion_patterns = []
        quality_signals = Counter[str]()
        for criterion in self._classroom_criteria(projects):
            comment_bodies = [
                comment["body"]
                for project in projects
                for comment in project.get("teacher_comments", [])
                if not comment.get("criterion") or comment["criterion"].lower() == criterion.lower()
            ]
            token_counts = Counter(self._keywords(" ".join(comment_bodies)))
            pattern = {
                "criterion": criterion,
                "exemplar_signals": [token for token, _ in token_counts.most_common(4)] or self._criterion_defaults(criterion),
                "look_fors": self._criterion_defaults(criterion),
                "project_count": len(projects),
            }
            criterion_patterns.append(pattern)
            quality_signals.update(pattern["exemplar_signals"])
        model = {
            "model_id": f"rubric-model-{uuid4().hex[:10]}",
            "classroom_id": classroom["classroom_id"],
            "created_at": self._timestamp(),
            "trained_on_projects": [project["slug"] for project in projects],
            "criterion_patterns": criterion_patterns,
            "quality_signals": [token for token, _ in quality_signals.most_common(8)],
        }
        models = self._load_json(self.rubric_models_path)
        models.insert(0, model)
        self._write_json(self.rubric_models_path, models[:100])
        self.education_service._append_audit(  # noqa: SLF001
            {
                "actor_role": "teacher",
                "agent_name": "rubric-trainer",
                "action": "rubric_model_trained",
                "summary": f"Trained rubric model on {len(projects)} projects for {classroom['title']}.",
                "classroom_id": classroom["classroom_id"],
                "allowed_actions": ["review_student_projects", "align_rubrics_and_standards"],
                "sensitive_actions_requested": [],
                "status": "completed",
            }
        )
        return model

    def map_standards(self, payload: dict[str, Any]) -> dict[str, Any]:
        classroom = self._authorized_classroom(
            str(payload["classroom_id"]),
            str(payload["access_key"]),
            {"teacher", "reviewer"},
        )
        raw_classroom = self.education_service._load_classroom(classroom["classroom_id"])  # noqa: SLF001
        assignment = self.education_service._find_assignment(raw_classroom, str(payload["assignment_id"]))  # noqa: SLF001
        template = self.template_registry.get_template(assignment["template_id"])
        standards_alignment = self.studio_service._build_standards_alignment(  # noqa: SLF001
            template=template,
            topic=assignment["topic"],
            goals=assignment.get("goals", []),
            rubric=assignment.get("rubric", []),
        )
        district_rubric_map = [
            {
                "criterion": criterion,
                "district_signal": "C3 Inquiry" if "evidence" in criterion.lower() else "Communication and reasoning",
                "why_it_matches": (
                    f"{criterion} aligns with {standards_alignment[index % len(standards_alignment)]['label']}"
                    if standards_alignment
                    else f"{criterion} aligns with classroom standards focus."
                ),
            }
            for index, criterion in enumerate(assignment.get("rubric", []))
        ]
        teacher_moves = [
            "Use the mapped standards as the language for mini-lessons and feedback.",
            "Connect each checkpoint to one rubric criterion and one standard label.",
            "Reuse the same alignment in parent/family updates and exported reports.",
        ]
        return {
            "classroom_id": classroom["classroom_id"],
            "assignment_id": assignment["assignment_id"],
            "assignment_title": assignment["title"],
            "standards_alignment": standards_alignment,
            "district_rubric_map": district_rubric_map,
            "teacher_moves": teacher_moves,
        }

    def intervention_dashboard(self, classroom_id: str, access_key: str) -> dict[str, Any]:
        classroom = self._authorized_classroom(classroom_id, access_key, {"teacher", "reviewer"})
        student_signals = []
        counters = Counter[str]()
        for student in classroom.get("students", []):
            latest_project = self._latest_student_project(student)
            signals: list[str] = []
            recommended = []
            citation_gaps = 0
            revision_gap = False
            project_summary = None
            progress_state = "not_started"
            if latest_project:
                project_summary = self.studio_service.get_project(latest_project)
                readiness = self.studio_service.get_submission_readiness(latest_project)
                progress_state = readiness["progress_state"]
                citation_gaps = sum(len(section.get("citations", [])) == 0 for section in project_summary.get("sections", []))
                revision_gap = (
                    len(project_summary.get("teacher_comments", [])) > 0
                    and len(project_summary.get("revision_history", [])) < 3
                )
            if not student.get("project_slugs"):
                signals.append("stuck_at_launch")
                recommended.append("Launch the first project and seed it with approved evidence.")
            if citation_gaps:
                signals.append("under_citing")
                recommended.append("Run the citation verifier and revise the weakest evidence-backed section first.")
            if revision_gap:
                signals.append("weak_revision_loop")
                recommended.append("Schedule a feedback conference and require one concrete revision task per criterion.")
            if not signals:
                signals.append("on_track")
                recommended.append("Keep the current momentum and move toward export readiness.")
            for signal in signals:
                counters.update([signal])
            student_signals.append(
                {
                    "student_id": student["student_id"],
                    "student_name": student["name"],
                    "project_count": len(student.get("project_slugs", [])),
                    "signals": signals,
                    "recommended_interventions": recommended,
                    "latest_project_slug": latest_project or "",
                    "teacher_comments": len(project_summary.get("teacher_comments", [])) if project_summary else 0,
                    "progress_state": progress_state,
                }
            )
        interventions = [
            "Prioritize students who have not launched a project yet.",
            "Target under-citing students with the citation verifier and shared evidence mini-lessons.",
            "Use the classroom replay to inspect whether feedback is leading to real revision.",
        ]
        return {
            "classroom_id": classroom["classroom_id"],
            "classroom_title": classroom["title"],
            "summary": {
                "students": len(classroom.get("students", [])),
                "stuck_at_launch": counters["stuck_at_launch"],
                "under_citing": counters["under_citing"],
                "weak_revision_loop": counters["weak_revision_loop"],
                "on_track": counters["on_track"],
            },
            "student_signals": student_signals,
            "interventions": interventions,
        }

    def classroom_replay(self, classroom_id: str, access_key: str) -> dict[str, Any]:
        classroom = self._authorized_classroom(classroom_id, access_key, {"teacher", "reviewer"})
        timeline = []
        for entry in self.education_service.list_audit_entries(classroom_id=classroom["classroom_id"], access_key=access_key, limit=250):
            timeline.append(
                {
                    "event_id": entry["audit_id"],
                    "created_at": entry["created_at"],
                    "event_type": "audit",
                    "headline": entry["action"],
                    "summary": entry["summary"],
                    "status": entry["status"],
                }
            )
        for review in self.list_peer_reviews(classroom["classroom_id"], access_key):
            timeline.append(
                {
                    "event_id": review["review_id"],
                    "created_at": review["created_at"],
                    "event_type": "peer_review",
                    "headline": review["status"],
                    "summary": review["summary"],
                    "status": review["status"],
                }
            )
        for slug in self._classroom_project_slugs(classroom):
            project = self.studio_service.get_project(slug)
            for revision in project.get("revision_history", [])[:20]:
                timeline.append(
                    {
                        "event_id": revision["revision_id"],
                        "created_at": revision["created_at"],
                        "event_type": "project_revision",
                        "headline": revision["action"],
                        "summary": revision["summary"],
                        "status": "completed",
                    }
                )
            for export in project.get("exports", []):
                timeline.append(
                    {
                        "event_id": f"{slug}-{export['export_type']}",
                        "created_at": export["created_at"],
                        "event_type": "project_export",
                        "headline": export["export_type"],
                        "summary": f"Exported {export['export_type']} for {project['title']}.",
                        "status": "completed",
                    }
                )
        timeline.sort(key=lambda item: item["created_at"], reverse=True)
        return {
            "classroom_id": classroom["classroom_id"],
            "classroom_title": classroom["title"],
            "counts": {
                "timeline_events": len(timeline),
                "audit_entries": len([item for item in timeline if item["event_type"] == "audit"]),
                "peer_reviews": len([item for item in timeline if item["event_type"] == "peer_review"]),
                "project_events": len([item for item in timeline if item["event_type"].startswith("project_")]),
            },
            "timeline": timeline[:200],
        }

    def classroom_roster(self, classroom_id: str, access_key: str) -> dict[str, Any]:
        classroom = self._authorized_classroom(classroom_id, access_key, {"teacher", "reviewer"})
        students = []
        summary = Counter[str]()
        for student in classroom.get("students", []):
            latest_project_slug = self._latest_student_project(student)
            latest_project = self.studio_service.get_project(latest_project_slug) if latest_project_slug else None
            readiness = (
                self.studio_service.get_submission_readiness(latest_project_slug)
                if latest_project_slug
                else self.studio_service._empty_submission_readiness()  # noqa: SLF001
            )
            assignment_title = next(
                (
                    assignment["title"]
                    for assignment in classroom.get("assignments", [])
                    for launched in assignment.get("launched_projects", [])
                    if launched["student_id"] == student["student_id"] and launched["project_slug"] == latest_project_slug
                ),
                "",
            )
            summary.update([readiness["progress_state"]])
            students.append(
                {
                    "student_id": student["student_id"],
                    "student_name": student["name"],
                    "grade_level": student["grade_level"],
                    "project_count": len(student.get("project_slugs", [])),
                    "latest_project_slug": latest_project_slug or "",
                    "assignment_title": assignment_title,
                    "progress_state": readiness["progress_state"],
                    "ready_for_export": readiness["ready_for_export"],
                    "teacher_comments": len((latest_project or {}).get("teacher_comments", [])),
                    "revision_steps": len((latest_project or {}).get("revision_history", [])),
                }
            )
        return {
            "classroom_id": classroom["classroom_id"],
            "classroom_title": classroom["title"],
            "students": students,
            "summary": {
                "students": len(students),
                "not_started": summary["not_started"],
                "researching": summary["researching"],
                "drafting": summary["drafting"],
                "under_review": summary["under_review"],
                "ready_for_export": summary["ready_for_export"],
                "exported": summary["exported"],
            },
        }

    def assignment_status_board(self, classroom_id: str, access_key: str) -> dict[str, Any]:
        classroom = self._authorized_classroom(classroom_id, access_key, {"teacher", "reviewer"})
        assignments = []
        for assignment in classroom.get("assignments", []):
            launched = assignment.get("launched_projects", [])
            progress_counter = Counter[str]()
            ready_count = 0
            for project_ref in launched:
                readiness = self.studio_service.get_submission_readiness(project_ref["project_slug"])
                progress_counter.update([readiness["progress_state"]])
                if readiness["ready_for_export"]:
                    ready_count += 1
            assignments.append(
                {
                    "assignment_id": assignment["assignment_id"],
                    "assignment_title": assignment["title"],
                    "status": assignment["status"],
                    "student_count": len(classroom.get("students", [])),
                    "launched_count": len(launched),
                    "ready_count": ready_count,
                    "progress_states": dict(progress_counter),
                    "due_date": assignment.get("due_date", ""),
                }
            )
        return {
            "classroom_id": classroom["classroom_id"],
            "classroom_title": classroom["title"],
            "assignments": assignments,
        }

    def generate_assessment_pack(self, payload: dict[str, Any]) -> dict[str, Any]:
        classroom = self._authorized_classroom(
            str(payload["classroom_id"]),
            str(payload["access_key"]),
            {"teacher", "reviewer"},
        )
        raw_classroom = self.education_service._load_classroom(classroom["classroom_id"])  # noqa: SLF001
        assignment = self.education_service._find_assignment(raw_classroom, str(payload["assignment_id"]))  # noqa: SLF001
        evidence_pack = self._rank_classroom_materials(classroom, assignment["topic"], assignment["assignment_id"])
        route = self._run_hybrid_brain(
            task_kind="assessment",
            prompt=(
                f"Generate quizzes, discussion prompts, exit tickets, and differentiated supports for "
                f"{assignment['title']} using evidence about {assignment['topic']}."
            ),
            system_prompt="You create concise classroom assessment packs for teachers inside EduClawn.",
            preferred_profile_id=str(payload.get("ai_profile_id") or assignment.get("ai_profile_id") or "").strip(),
            metadata={"feature": "assessment_pack", "assignment_id": assignment["assignment_id"]},
            classroom_id=classroom["classroom_id"],
        )
        key_sources = [item["title"] for item in evidence_pack[:3]] or ["approved classroom evidence"]
        quiz_questions = [
            {
                "question": f"Which source best supports the central claim about {assignment['topic']}?",
                "answer_type": "short_response",
                "source_hint": key_sources[0],
            },
            {
                "question": "What evidence would weaken a weak or unsupported claim?",
                "answer_type": "discussion_check",
                "source_hint": key_sources[0],
            },
            {
                "question": "How does the strongest source connect to the selected audience and rubric?",
                "answer_type": "written_response",
                "source_hint": key_sources[min(1, len(key_sources) - 1)],
            },
        ]
        discussion_prompts = [
            f"Which approved source changes how you understand {assignment['topic']}?",
            "What would happen to the argument if the strongest source were removed?",
            "How should the audience affect the way the evidence is explained?",
        ]
        exit_tickets = [
            "Name one claim you can support with approved evidence today.",
            "Which rubric criterion still needs attention before the next checkpoint?",
        ]
        differentiated_supports = [
            {
                "learner_group": "students needing scaffolds",
                "support": "Use sentence stems and one preselected source chunk from the evidence pack.",
            },
            {
                "learner_group": "students ready to extend",
                "support": "Add a counterargument and verify it with an additional source.",
            },
        ]
        return {
            "assignment_id": assignment["assignment_id"],
            "assignment_title": assignment["title"],
            "route": route["decision"],
            "quiz_questions": quiz_questions,
            "discussion_prompts": discussion_prompts,
            "exit_tickets": exit_tickets,
            "differentiated_supports": differentiated_supports,
            "teacher_note": route["output_text"] or "Assessment pack generated from the same classroom evidence and rubric.",
        }

    def get_marketplace(self) -> dict[str, Any]:
        installed_packs = {pack["pack_id"]: pack for pack in self._installed_school_packs()}
        plugin_sdk = {
            "template_sdk_path": str(self.settings.root_dir / "docs" / "TEMPLATE_SDK.md"),
            "plugin_sdk_path": str(self.settings.root_dir / "docs" / "PLUGIN_SDK.md"),
            "template_starter_dir": str(self.settings.community_root_dir / "template_starters"),
            "school_pack_readme": str(self.settings.community_root_dir / "README.md"),
            "extension_points": ["document_parsers", "exporters", "rubric_packs", "subject_agents"],
            "installed_plugins": len(self.template_registry.list_plugins()),
            "install_flow": [
                "Choose a school pack.",
                "Install the pack locally.",
                "Open the starter sample project or template starter.",
                "Customize the classroom and export workflow.",
            ],
        }
        return {
            "templates": self.template_registry.list_templates(),
            "sample_projects": self.template_registry.list_sample_projects(),
            "plugins": self.template_registry.list_plugins(),
            "school_packs": [
                {
                    **pack,
                    "installed": pack["pack_id"] in installed_packs,
                    "installed_at": installed_packs.get(pack["pack_id"], {}).get("installed_at", ""),
                    "manifest_path": installed_packs.get(pack["pack_id"], {}).get("manifest_path", ""),
                }
                for pack in SCHOOL_PACKS
            ],
            "plugin_sdk": plugin_sdk,
            "offline_school_edition": self.get_offline_school_edition(),
        }

    def install_school_pack(self, pack_id: str) -> dict[str, Any]:
        pack = self._school_pack(pack_id)
        manifest_path = self.school_pack_dir / f"{pack_id}.yaml"
        installed_at = self._timestamp()
        sample_slug = str(pack["sample_project_slug"])
        blueprint_path = self.settings.community_root_dir / "school_packs" / f"{pack_id}.yaml"
        if blueprint_path.exists():
            sample_manifest = yaml.safe_load(blueprint_path.read_text(encoding="utf-8")) or {}
        else:
            sample_manifest = {
                "title": pack["label"],
                "slug": sample_slug,
                "template_id": pack["recommended_template_ids"][0],
                "summary": pack["description"],
            }
        sample_manifest.setdefault("title", pack["label"])
        sample_manifest["slug"] = sample_slug
        sample_manifest.setdefault("template_id", pack["recommended_template_ids"][0])
        sample_manifest.setdefault("summary", pack["description"])
        sample_path = self.settings.community_root_dir / "sample_projects" / f"{sample_slug}.yaml"
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        if not sample_path.exists():
            sample_path.write_text(yaml.safe_dump(sample_manifest, sort_keys=False), encoding="utf-8")
        manifest = {
            "pack_id": pack["pack_id"],
            "label": pack["label"],
            "installed_at": installed_at,
            "recommended_template_ids": pack["recommended_template_ids"],
            "plugin_ids": pack["plugin_ids"],
            "sample_project_slug": sample_slug,
            "manifest_path": str(manifest_path),
        }
        manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
        return {
            "pack_id": pack["pack_id"],
            "label": pack["label"],
            "installed_at": installed_at,
            "manifest_path": str(manifest_path),
            "created_samples": [sample_slug],
            "recommended_templates": list(pack["recommended_template_ids"]),
        }

    def get_offline_school_edition(self) -> dict[str, Any]:
        docker_compose_path = self.settings.root_dir / "docker-compose.yml"
        packaged_app = self.settings.root_dir / "desktop" / "release" / "mac-arm64" / "EduClawn.app"
        tesseract_available = bool(self.studio_service.get_system_status().get("tools", {}).get("tesseract_available"))
        local_ai_configured = bool(self.settings.local_llm_model)
        readiness_components = {
            "desktop_app": packaged_app.exists(),
            "docker_compose": docker_compose_path.exists(),
            "local_workspace": self.settings.studio_root_dir.exists(),
            "provider_optional": True,
            "network_not_required": True,
            "ocr_optional": tesseract_available,
            "local_ai_optional": local_ai_configured or True,
        }
        readiness_score = round(
            (sum(1 for value in readiness_components.values() if value) / len(readiness_components)) * 100.0,
            1,
        )
        return {
            "edition_name": "EduClawn Offline School Edition",
            "readiness_score": readiness_score,
            "supported_modes": ["desktop_app", "docker_compose", "developer_mode", "offline_school_edition"],
            "local_capabilities": readiness_components,
            "recommended_rollout": [
                "Install the packaged desktop app or use docker compose for lab machines.",
                "Keep provider AI optional and rely on no-llm or local-llm by default.",
                "Preinstall school packs and plugin packs before imaging student devices.",
            ],
            "installed_assets": [
                str(path)
                for path in [docker_compose_path, packaged_app]
                if path.exists()
            ],
        }

    def _run_hybrid_brain(
        self,
        *,
        task_kind: str,
        prompt: str,
        system_prompt: str,
        preferred_profile_id: str = "",
        metadata: dict[str, Any] | None = None,
        classroom_id: str = "",
    ) -> dict[str, Any]:
        config = ROUTING_PROFILES.get(task_kind, ROUTING_PROFILES["research"])
        local_available = bool(self.settings.local_llm_model)
        if local_available and config["prefer_local"] and task_kind != "multimodal" and not preferred_profile_id:
            output = self._local_llm_completion(prompt, system_prompt)
            if output:
                return {
                    "output_text": output,
                    "decision": {
                        "task_kind": task_kind,
                        "execution_mode": "local-llm",
                        "required_capability": config["required_capability"],
                        "reason": f"Local model {self.settings.local_llm_model} handled the task first under hybrid routing.",
                        "selected_provider": None,
                        "local_available": True,
                        "provider_available": bool(self.ai_provider_service.list_profiles()),
                    },
                }

        profile = self._route_provider_profile(task_kind, preferred_profile_id)
        if profile:
            provider_result = self.ai_provider_service.generate_with_profile(
                profile["profile_id"],
                task=config["required_capability"],
                prompt=prompt,
                system_prompt=system_prompt,
                source="education_growth",
                metadata=metadata or {"task_kind": task_kind},
                classroom_id=classroom_id,
            )
            if provider_result["used"]:
                return {
                    "output_text": provider_result["output_text"],
                    "decision": {
                        "task_kind": task_kind,
                        "execution_mode": "provider-ai",
                        "required_capability": config["required_capability"],
                        "reason": f"Routed to {provider_result['provider_label']} for {task_kind}.",
                        "selected_provider": {
                            "provider_id": provider_result["provider_id"],
                            "provider_label": provider_result["provider_label"],
                            "profile_id": provider_result["profile_id"],
                            "profile_label": provider_result["profile_label"],
                            "auth_mode": provider_result["auth_mode"],
                            "model": provider_result["model"],
                        },
                        "local_available": local_available,
                        "provider_available": True,
                    },
                }
            error_message = str(provider_result.get("error") or "Provider AI failed.")
        else:
            error_message = "No provider profile matched the requested task."

        output = ""
        if local_available and task_kind != "multimodal":
            output = self._local_llm_completion(prompt, system_prompt)
        if output:
            return {
                "output_text": output,
                "decision": {
                    "task_kind": task_kind,
                    "execution_mode": "local-llm",
                    "required_capability": config["required_capability"],
                    "reason": f"Provider routing fell back to local mode: {error_message}",
                    "selected_provider": None,
                    "local_available": local_available,
                    "provider_available": bool(profile),
                },
            }
        return {
            "output_text": "",
            "decision": {
                "task_kind": task_kind,
                "execution_mode": "no-llm",
                "required_capability": config["required_capability"],
                "reason": error_message or "Deterministic fallback remained active.",
                "selected_provider": None,
                "local_available": local_available,
                "provider_available": bool(profile),
            },
        }

    def _route_provider_profile(self, task_kind: str, preferred_profile_id: str = "") -> dict[str, Any] | None:
        profiles = self.ai_provider_service.list_profiles()
        if preferred_profile_id:
            for profile in profiles:
                if profile["profile_id"] == preferred_profile_id:
                    return profile
        config = ROUTING_PROFILES.get(task_kind, ROUTING_PROFILES["research"])
        required_capability = str(config["required_capability"])
        capable = [
            profile
            for profile in profiles
            if required_capability in profile.get("capabilities", [])
        ]
        if not capable:
            capable = profiles
        for provider_id in config["provider_order"]:
            for profile in capable:
                if profile["provider_id"] == provider_id:
                    return profile
        return capable[0] if capable else None

    def _authorized_classroom(self, classroom_id: str, access_key: str, allowed_roles: set[str]) -> dict[str, Any]:
        raw_classroom = self.education_service._load_classroom(classroom_id)  # noqa: SLF001
        self.education_service._authorize_classroom_action(raw_classroom, access_key, allowed_roles)  # noqa: SLF001
        return self.education_service.get_classroom(classroom_id)

    def _pick_template(
        self,
        *,
        explicit_template_id: str,
        topic: str,
        lesson_seed: str,
        default_template_id: str,
    ) -> dict[str, Any]:
        if explicit_template_id:
            return self.template_registry.get_template(explicit_template_id)
        combined = f"{topic} {lesson_seed}".lower()
        if any(word in combined for word in ("experiment", "hypothesis", "lab", "science")):
            return self.template_registry.get_template("science-fair-lab")
        if any(word in combined for word in ("debate", "argument", "counterclaim")):
            return self.template_registry.get_template("debate-prep-kit")
        if any(word in combined for word in ("museum", "artifact", "gallery", "exhibit")):
            return self.template_registry.get_template("museum-exhibit-site")
        if any(word in combined for word in ("campaign", "simulation", "policy", "stakeholder")):
            return self.template_registry.get_template("civic-campaign-simulator")
        if any(word in combined for word in ("family", "story", "oral history", "documentary")):
            return self.template_registry.get_template("documentary-story")
        if any(word in combined for word in ("lesson", "objective", "exit ticket")):
            return self.template_registry.get_template("lesson-module")
        return self.template_registry.get_template(default_template_id)

    def _attach_assignment_evidence(self, classroom_id: str, assignment_id: str, evidence_pack: list[dict[str, Any]]) -> None:
        raw_classroom = self.education_service._load_classroom(classroom_id)  # noqa: SLF001
        assignment = self.education_service._find_assignment(raw_classroom, assignment_id)  # noqa: SLF001
        assignment["evidence_material_ids"] = sorted(
            {
                *assignment.get("evidence_material_ids", []),
                *[item["material_id"] for item in evidence_pack],
            }
        )
        assignment["updated_at"] = self._timestamp()
        raw_classroom["updated_at"] = self._timestamp()
        self.education_service._save_classroom(raw_classroom)  # noqa: SLF001

    def _rank_classroom_materials(
        self,
        classroom: dict[str, Any] | None,
        topic: str,
        assignment_id: str | None = None,
        limit: int = 6,
    ) -> list[dict[str, Any]]:
        if not classroom:
            return []
        scored = []
        for material in classroom.get("evidence_library", []):
            if assignment_id and material.get("assignment_id") not in {None, "", assignment_id} and material["scope"] != "shared":
                continue
            score = self._keyword_score(topic, f"{material['title']} {material['summary']}")
            scored.append((score, material))
        scored.sort(key=lambda item: (-item[0], item[1]["title"]))
        return [dict(material) for _, material in scored[:limit]]

    def _checkpoint_plan(self, topic: str, assignment: dict[str, Any]) -> list[dict[str, Any]]:
        due_date = assignment.get("due_date") or "Set due date"
        return [
            {"checkpoint": "Question framing", "detail": f"Define the inquiry around {topic}.", "target": "Day 1"},
            {"checkpoint": "Evidence shortlist", "detail": "Choose the strongest approved sources.", "target": "Day 2"},
            {"checkpoint": "Draft section", "detail": "Write one section with citations.", "target": "Day 4"},
            {"checkpoint": "Revision conference", "detail": "Compare the draft against the rubric.", "target": due_date},
        ]

    def _lesson_to_project_scaffold(
        self,
        *,
        topic: str,
        template: dict[str, Any],
        goals: list[str],
        rubric: list[str],
        evidence_pack: list[dict[str, Any]],
        ai_output: str,
    ) -> dict[str, Any]:
        return {
            "project_title_hint": self._assignment_title(topic, template["label"]),
            "template_id": template["id"],
            "sections": [section["title"] for section in template.get("sections", [])],
            "goals": goals,
            "rubric": rubric,
            "evidence_titles": [item["title"] for item in evidence_pack[:4]],
            "planner_note": ai_output or f"Use {template['label']} to turn the lesson into a project with cited, editable sections.",
        }

    def _rubric_breakdown(
        self,
        *,
        draft_text: str,
        rubric: list[str],
        citation_verification: dict[str, Any],
        teacher_feedback: list[str],
    ) -> list[dict[str, Any]]:
        word_count = len(draft_text.split())
        average_sentence_length = max(1, word_count // max(len(self._extract_claims(draft_text)), 1))
        breakdown = []
        verified_count = len(citation_verification.get("verified_claims", []))
        blocked_count = len(citation_verification.get("blocked_claims", []))
        for criterion in rubric:
            lowered = criterion.lower()
            if "evidence" in lowered:
                score = 82 if verified_count >= 2 else 58 if verified_count else 42
                note = "Strong evidence is present." if score >= 80 else "Add more explicit evidence links."
            elif "citation" in lowered:
                score = 88 if blocked_count == 0 and verified_count else 46
                note = "Claims are grounded in approved sources." if score >= 80 else "Some claims still need exact source matches."
            elif "clarity" in lowered:
                score = 84 if average_sentence_length <= 24 else 61
                note = "The draft is readable." if score >= 80 else "Break long sections into clearer sentences."
            elif "revision" in lowered:
                score = 79 if teacher_feedback else 55
                note = "Revision targets are visible." if teacher_feedback else "Use teacher comments to drive the next revision."
            else:
                score = 74 if word_count >= 120 else 57
                note = "The draft is moving in the right direction." if score >= 70 else "Build the section further before export."
            breakdown.append(
                {
                    "criterion": criterion,
                    "score": score,
                    "status": "strong" if score >= 80 else "watch" if score >= 60 else "needs_work",
                    "note": note,
                }
            )
        return breakdown

    def _revision_tasks(
        self,
        rubric_breakdown: list[dict[str, Any]],
        citation_verification: dict[str, Any],
        teacher_feedback: list[str],
    ) -> list[str]:
        tasks = [
            f"Improve {entry['criterion'].lower()}: {entry['note']}"
            for entry in rubric_breakdown
            if entry["status"] != "strong"
        ]
        for blocked in citation_verification.get("blocked_claims", [])[:3]:
            tasks.append(f"Find an approved source for: {blocked['claim']}")
        for feedback in teacher_feedback[:3]:
            tasks.append(f"Teacher feedback action: {feedback}")
        return tasks[:8] or ["Revise one paragraph so it cites a stronger approved source."]

    def _student_revision_summary(self, rubric_breakdown: list[dict[str, Any]], tasks: list[str]) -> str:
        weakest = next((entry for entry in rubric_breakdown if entry["status"] != "strong"), None)
        if weakest:
            return f"Start with {weakest['criterion'].lower()}, then work through the next {min(len(tasks), 3)} revision tasks."
        return "Your draft is in good shape. Do a final citation check before exporting."

    def _family_revision_summary(self, rubric_breakdown: list[dict[str, Any]], tasks: list[str]) -> str:
        weakest = next((entry for entry in rubric_breakdown if entry["status"] == "needs_work"), None)
        if weakest:
            return f"The main next step is improving {weakest['criterion'].lower()}. There are {len(tasks)} clear revision tasks ready."
        return "The project has clear progress and mainly needs a final review."

    def _peer_review_comments(self, draft_text: str, rubric: list[str]) -> list[dict[str, Any]]:
        claims = self._extract_claims(draft_text)
        comments = []
        for criterion in rubric[:4]:
            comments.append(
                {
                    "criterion": criterion,
                    "comment": (
                        f"One thing working well is the focus on {criterion.lower()}. "
                        f"One next step is to strengthen it with a more exact example or citation."
                    ),
                }
            )
        if claims:
            comments.append(
                {
                    "criterion": "Claim strength",
                    "comment": f"The clearest claim right now is: '{claims[0]}'. Keep that claim and add one stronger source.",
                }
            )
        return comments

    def _find_project_context(self, classroom: dict[str, Any], project_slug: str) -> dict[str, Any]:
        for assignment in classroom.get("assignments", []):
            for launched in assignment.get("launched_projects", []):
                if launched["project_slug"] == project_slug:
                    return {
                        **launched,
                        "assignment_title": assignment["title"],
                    }
        return {}

    def _lesson_topic(self, lesson_plan: str) -> str:
        first_line = next((line.strip() for line in lesson_plan.splitlines() if line.strip()), "Classroom inquiry project")
        cleaned = re.sub(r"^[#\-*\d.\s]+", "", first_line).strip()
        return cleaned[:120] or "Classroom inquiry project"

    def _lesson_goals(self, lesson_plan: str, topic: str) -> list[str]:
        bullet_like = []
        for line in lesson_plan.splitlines():
            stripped = line.strip()
            if stripped.startswith(("-", "*")):
                bullet_like.append(stripped.lstrip("-* ").strip())
        if bullet_like:
            return bullet_like[:5]
        return [
            f"Explain the core issue in {topic}.",
            "Use approved evidence in every major section.",
            "Revise the work after feedback and citation checks.",
        ]

    def _classroom_project_slugs(self, classroom: dict[str, Any]) -> list[str]:
        project_slugs = []
        for assignment in classroom.get("assignments", []):
            for launched in assignment.get("launched_projects", []):
                project_slugs.append(launched["project_slug"])
        return list(dict.fromkeys(project_slugs))

    def _classroom_criteria(self, projects: list[dict[str, Any]]) -> list[str]:
        criteria = []
        for project in projects:
            criteria.extend(project.get("rubric", []))
        return list(dict.fromkeys(criteria)) or ["Evidence Quality", "Clarity", "Revision Quality"]

    def _criterion_defaults(self, criterion: str) -> list[str]:
        lowered = criterion.lower()
        if "evidence" in lowered:
            return ["cited sources", "source comparison", "document grounding"]
        if "citation" in lowered:
            return ["claim-source match", "citation label", "approved evidence"]
        if "clarity" in lowered:
            return ["clear explanation", "plain language", "strong organization"]
        if "revision" in lowered:
            return ["responds to feedback", "improves weak sections", "checks rubric"]
        return ["clear purpose", "audience fit", "project coherence"]

    def _latest_student_project(self, student: dict[str, Any]) -> str | None:
        if not student.get("project_slugs"):
            return None
        return student["project_slugs"][-1]

    def _find_family_share_link(self, classroom_id: str, project_slug: str) -> dict[str, Any]:
        for link in self._load_json(self.family_links_path):
            if link["classroom_id"] == classroom_id and link["project_slug"] == project_slug:
                return link
        return {}

    def _installed_school_packs(self) -> list[dict[str, Any]]:
        packs = []
        for path in sorted(self.school_pack_dir.glob("*.yaml")):
            with path.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle) or {}
            packs.append({**payload, "manifest_path": str(path)})
        return packs

    def _school_pack(self, pack_id: str) -> dict[str, Any]:
        for pack in SCHOOL_PACKS:
            if pack["pack_id"] == pack_id:
                return dict(pack)
        raise FileNotFoundError(pack_id)

    def _default_goals(self, topic: str, template: dict[str, Any]) -> list[str]:
        return [
            f"Investigate {topic} using approved evidence.",
            f"Build a {template['label']} that fits the selected audience.",
            "Revise the work using rubric-aligned checkpoints.",
        ]

    def _assignment_title(self, topic: str, template_label: str) -> str:
        base = re.sub(r"\s+", " ", topic).strip().title()[:80]
        if "Lesson" in template_label:
            return f"{base} Lesson Module"
        if "Simulator" in template_label:
            return f"{base} Strategy Lab"
        return f"{base} Inquiry Project"

    def _local_llm_completion(self, prompt: str, system_prompt: str) -> str:
        if not self.settings.local_llm_model:
            return ""
        payload = json.dumps(
            {
                "model": self.settings.local_llm_model,
                "prompt": f"{system_prompt}\n\n{prompt}".strip(),
                "stream": False,
            }
        ).encode("utf-8")
        endpoint = f"{self.settings.local_llm_base_url.rstrip('/')}/api/generate"
        try:
            response = urllib_request.urlopen(
                urllib_request.Request(
                    endpoint,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                ),
                timeout=8,
            )
            body = json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError, ValueError, urllib_error.HTTPError, urllib_error.URLError):
            return ""
        return str(body.get("response") or "").strip()

    def _library_fingerprint(self, classroom: dict[str, Any], material: dict[str, Any]) -> str:
        seed = "|".join(
            [
                classroom["teacher_name"],
                material["title"],
                material["summary"],
                material["file_name"],
            ]
        )
        return hashlib.sha1(seed.encode("utf-8")).hexdigest()

    def _teacher_key(self, teacher_name: str) -> str:
        return self._slugify(teacher_name or "teacher")

    def _extract_claims(self, draft_text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", draft_text)
        claims = [sentence.strip() for sentence in sentences if len(sentence.strip()) >= 35]
        return claims[:6]

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def _keywords(self, text: str) -> list[str]:
        stop_words = {
            "the",
            "and",
            "for",
            "with",
            "that",
            "this",
            "from",
            "into",
            "using",
            "about",
            "students",
            "their",
            "they",
            "them",
            "have",
            "will",
            "after",
            "before",
        }
        return [
            token
            for token in re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", text.lower())
            if token not in stop_words
        ]

    def _keyword_score(self, topic: str, text: str) -> int:
        topic_terms = set(self._keywords(topic))
        text_terms = set(self._keywords(text))
        return len(topic_terms & text_terms)

    def _slugify(self, value: str) -> str:
        value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
        return value or "item"

    def _timestamp(self) -> str:
        return datetime.now(UTC).isoformat()

    def _load_json(self, path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_json(self, path: Path, payload: list[dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
