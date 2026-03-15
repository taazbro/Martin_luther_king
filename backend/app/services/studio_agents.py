from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from typing import Any
from urllib import error, request

if TYPE_CHECKING:
    from app.services.provider_ai import ProviderAIService


STUDIO_AGENT_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "name": "research",
        "display_name": "Research Agent",
        "role": "Evidence organizer",
        "description": "Builds a research brief, key questions, and evidence board from uploaded documents.",
    },
    {
        "name": "planner",
        "display_name": "Planner Agent",
        "role": "Project compiler planner",
        "description": "Creates the mission graph, section plan, and workflow sequencing for the project.",
    },
    {
        "name": "writer",
        "display_name": "Writer Agent",
        "role": "Structured draft author",
        "description": "Produces editable draft sections tied to exact evidence chunks.",
    },
    {
        "name": "historian",
        "display_name": "Historian Agent",
        "role": "Context and timeline guide",
        "description": "Extracts historical context, chronology, and continuity from uploaded evidence.",
    },
    {
        "name": "citation",
        "display_name": "Citation Agent",
        "role": "Provenance mapper",
        "description": "Maps every section and artifact back to supporting document chunks.",
    },
    {
        "name": "design",
        "display_name": "Design Agent",
        "role": "Theme and layout system designer",
        "description": "Produces theme tokens, layout direction, and presentation choices for the chosen template.",
    },
    {
        "name": "qa",
        "display_name": "QA Agent",
        "role": "Quality and regression checker",
        "description": "Flags missing evidence, incomplete sections, and weak coverage before export.",
    },
    {
        "name": "teacher",
        "display_name": "Teacher Agent",
        "role": "Rubric reviewer",
        "description": "Scores the project against the rubric and produces reviewer guidance.",
    },
    {
        "name": "export",
        "display_name": "Export Agent",
        "role": "Build and delivery planner",
        "description": "Prepares the local export bundle for static, report, and React outputs.",
    },
)


class ProjectAgentRuntime:
    def __init__(
        self,
        local_llm_model: str = "",
        local_llm_base_url: str = "http://127.0.0.1:11434",
        ai_provider_service: ProviderAIService | None = None,
    ) -> None:
        self.local_llm_model = local_llm_model.strip()
        self.local_llm_base_url = local_llm_base_url.rstrip("/")
        self.ai_provider_service = ai_provider_service

    def catalog(self) -> list[dict[str, Any]]:
        return [dict(entry) for entry in STUDIO_AGENT_CATALOG]

    def run(
        self,
        manifest: dict[str, Any],
        template: dict[str, Any],
        documents: list[dict[str, Any]],
        retrieval_results: list[dict[str, Any]],
        knowledge_graph: dict[str, Any],
    ) -> dict[str, Any]:
        generated_at = datetime.now(UTC).isoformat()
        evidence_board = self._build_evidence_board(documents, retrieval_results)
        research = self._research_artifact(manifest, template, documents, evidence_board)
        planner = self._planner_artifact(manifest, template, evidence_board, knowledge_graph)
        historian = self._historian_artifact(manifest, documents, knowledge_graph)
        citation = self._citation_artifact(manifest, template, evidence_board)
        writer = self._writer_artifact(manifest, template, evidence_board, citation)
        design = self._design_artifact(manifest, template)
        simulation = self._simulation_artifact(manifest, template, evidence_board)
        qa = self._qa_artifact(manifest, documents, writer, citation, simulation)
        teacher = self._teacher_artifact(manifest, writer, citation, qa)
        export = self._export_artifact(manifest, template, design, qa)
        provider_context = self._maybe_apply_provider_ai(
            manifest=manifest,
            template=template,
            research=research["artifact"],
            writer=writer["artifact"],
            teacher=teacher["artifact"],
        )
        llm_context = self._maybe_apply_local_llm(
            manifest=manifest,
            template=template,
            research=research["artifact"],
            writer=writer["artifact"],
        )

        artifacts = {
            "research_brief": research["artifact"],
            "mission_graph": planner["artifact"],
            "historical_context": historian["artifact"],
            "citation_map": citation["artifact"],
            "written_sections": writer["artifact"],
            "design_system": design["artifact"],
            "qa_report": qa["artifact"],
            "teacher_review": teacher["artifact"],
            "export_plan": export["artifact"],
            "simulation_blueprint": simulation,
        }
        if provider_context["used"]:
            artifacts["provider_ai_trace"] = {
                "provider_id": provider_context["provider_id"],
                "provider_label": provider_context["provider_label"],
                "profile_id": provider_context["profile_id"],
                "profile_label": provider_context["profile_label"],
                "auth_mode": provider_context["auth_mode"],
                "model": provider_context["model"],
            }
        if llm_context["used"]:
            artifacts["local_llm_trace"] = {
                "model": self.local_llm_model,
                "provider": "ollama-compatible",
                "base_url": self.local_llm_base_url,
            }

        return {
            "generated_at": generated_at,
            "runtime_mode": self._runtime_mode(manifest, llm_context, provider_context),
            "agents": [
                research["agent"],
                planner["agent"],
                writer["agent"],
                historian["agent"],
                citation["agent"],
                design["agent"],
                qa["agent"],
                teacher["agent"],
                export["agent"],
            ],
            "artifacts": artifacts,
        }

    def _runtime_mode(
        self,
        manifest: dict[str, Any],
        llm_context: dict[str, Any],
        provider_context: dict[str, Any],
    ) -> dict[str, Any]:
        requested_mode = str(manifest.get("local_mode", "no-llm"))
        configured = bool(self.local_llm_model)
        if requested_mode == "provider-ai" and provider_context["used"]:
            note = (
                f"Provider AI used {provider_context['provider_label']} "
                f"through profile {provider_context['profile_label']}."
            )
        elif requested_mode == "provider-ai" and provider_context["error"]:
            note = f"Provider AI fallback engaged: {provider_context['error']}"
        elif requested_mode == "provider-ai":
            note = "Provider AI mode was requested, but no provider profile is configured."
        elif requested_mode != "local-llm":
            note = "Deterministic local generation is active."
        elif llm_context["used"]:
            note = f"Local model {self.local_llm_model} refined the generated artifacts."
        elif configured and llm_context["error"]:
            note = f"Local model fallback engaged: {llm_context['error']}"
        elif configured:
            note = f"Local model {self.local_llm_model} is configured, but deterministic fallback was used."
        else:
            note = "Deterministic local generation is active because no local model is configured."
        return {
            "requested_mode": requested_mode,
            "local_llm_configured": configured,
            "provider_ai_configured": bool(manifest.get("ai_profile_id")),
            "effective_mode": (
                "provider-ai"
                if provider_context["used"]
                else "local-llm"
                if llm_context["used"]
                else "no-llm"
            ),
            "note": note,
        }

    def _maybe_apply_provider_ai(
        self,
        manifest: dict[str, Any],
        template: dict[str, Any],
        research: dict[str, Any],
        writer: dict[str, Any],
        teacher: dict[str, Any],
    ) -> dict[str, Any]:
        requested_mode = str(manifest.get("local_mode", "no-llm"))
        profile_id = str(manifest.get("ai_profile_id") or "").strip()
        classroom_id = str((manifest.get("classroom_context") or {}).get("classroom_id") or "")
        if requested_mode != "provider-ai":
            return {"used": False, "error": ""}
        if not profile_id:
            return {"used": False, "error": "No provider AI profile is selected for this project."}
        if self.ai_provider_service is None:
            return {"used": False, "error": "Provider AI service is not available."}

        context = (
            f"Project title: {manifest['title']}. Topic: {manifest['topic']}. "
            f"Audience: {manifest['audience']}. Template: {template['label']}."
        )

        research_result = self.ai_provider_service.generate_with_profile(
            profile_id,
            task="research",
            source="studio_project",
            metadata={"project_slug": manifest["slug"], "artifact": "research_brief"},
            system_prompt="You are an evidence-grounded research assistant inside EduClawn.",
            prompt=(
                f"{context} Rewrite this project brief into a concise, cited-ready research brief for students. "
                f"Draft brief: {research['executive_summary']}"
            ),
            classroom_id=classroom_id,
        )
        if not research_result["used"]:
            return research_result
        research["executive_summary"] = research_result["output_text"]

        revised_sections = 0
        for section in writer["sections"][:4]:
            section_result = self.ai_provider_service.generate_with_profile(
                profile_id,
                task="assignments",
                source="studio_project",
                metadata={
                    "project_slug": manifest["slug"],
                    "artifact": "written_sections",
                    "section_id": section["section_id"],
                },
                system_prompt="You are a classroom-safe writing assistant inside EduClawn.",
                prompt=(
                    f"{context} Rewrite this section for clarity, evidence-grounding, and student readability. "
                    f"Keep it under 140 words. Section: {section['title']}. Draft: {section['body']}"
                ),
                classroom_id=classroom_id,
            )
            if section_result["used"]:
                section["body"] = section_result["output_text"]
                revised_sections += 1

        review_result = self.ai_provider_service.generate_with_profile(
            profile_id,
            task="review",
            source="studio_project",
            metadata={"project_slug": manifest["slug"], "artifact": "teacher_review"},
            system_prompt="You are a rubric-focused teacher coach inside EduClawn.",
            prompt=(
                f"{context} Produce one concise teacher coaching note for this draft. "
                f"Current teacher note seed: {teacher['teacher_notes'][0]}"
            ),
            classroom_id=classroom_id,
        )
        if review_result["used"]:
            teacher["teacher_notes"][0] = review_result["output_text"]

        return {
            "used": True,
            "error": "",
            "provider_id": research_result["provider_id"],
            "provider_label": research_result["provider_label"],
            "profile_id": research_result["profile_id"],
            "profile_label": research_result["profile_label"],
            "auth_mode": research_result["auth_mode"],
            "model": research_result["model"],
            "revised_sections": revised_sections,
        }

    def _maybe_apply_local_llm(
        self,
        manifest: dict[str, Any],
        template: dict[str, Any],
        research: dict[str, Any],
        writer: dict[str, Any],
    ) -> dict[str, Any]:
        requested_mode = str(manifest.get("local_mode", "no-llm"))
        if requested_mode != "local-llm" or not self.local_llm_model:
            return {"used": False, "error": ""}

        goal_text = "; ".join(manifest.get("goals", [])) or manifest["topic"]
        project_context = (
            f"Project title: {manifest['title']}. Topic: {manifest['topic']}. "
            f"Audience: {manifest['audience']}. Template: {template['label']}. Goals: {goal_text}."
        )

        research_prompt = (
            "Rewrite this project brief for a local-first educational studio. "
            "Keep it concise, specific, and grounded in evidence. "
            f"{project_context} Draft brief: {research['executive_summary']}"
        )
        improved_research = self._local_llm_completion(research_prompt)
        if not improved_research:
            return {"used": False, "error": "Local model server did not return a usable response."}
        research["executive_summary"] = improved_research

        for section in writer["sections"]:
            section_prompt = (
                "Rewrite this section into a sharper educational draft. "
                "Keep it under 120 words, retain the evidence reference, and keep the tone suitable for students. "
                f"{project_context} Section title: {section['title']}. Draft: {section['body']}"
            )
            improved_body = self._local_llm_completion(section_prompt)
            if improved_body:
                section["body"] = improved_body

        return {"used": True, "error": ""}

    def _local_llm_completion(self, prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self.local_llm_model,
                "prompt": prompt,
                "stream": False,
            }
        ).encode("utf-8")
        endpoint = f"{self.local_llm_base_url}/api/generate"
        try:
            response = request.urlopen(
                request.Request(
                    endpoint,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                ),
                timeout=8,
            )
            body = json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError, ValueError, error.HTTPError, error.URLError):
            return ""
        return str(body.get("response") or "").strip()

    def _build_evidence_board(
        self,
        documents: list[dict[str, Any]],
        retrieval_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        board = []
        seen_chunk_ids: set[str] = set()

        for result in retrieval_results[:8]:
            chunk_id = str(result["chunk_id"])
            if chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk_id)
            board.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": result["document_id"],
                    "citation_label": result["citation_label"],
                    "score": round(float(result["score"]), 1),
                    "excerpt": result["excerpt"],
                    "why_it_matters": f"Supports the project's {result['match_reason']} requirement.",
                }
            )

        if board:
            return board

        for document in documents[:4]:
            board.append(
                {
                    "chunk_id": f"{document['document_id']}-summary",
                    "document_id": document["document_id"],
                    "citation_label": document["citation_label"],
                    "score": 55.0,
                    "excerpt": document["summary"],
                    "why_it_matters": "Baseline evidence extracted from the uploaded source summary.",
                }
            )
        return board

    def _research_artifact(
        self,
        manifest: dict[str, Any],
        template: dict[str, Any],
        documents: list[dict[str, Any]],
        evidence_board: list[dict[str, Any]],
    ) -> dict[str, Any]:
        key_questions = [
            f"What is the strongest local evidence for {manifest['topic']}?",
            f"How should the project address the needs of {manifest['audience']}?",
            f"Which uploaded sources best support the {template['label']} format?",
        ]
        artifact = {
            "executive_summary": (
                f"{manifest['title']} is being compiled as a {template['label']} using "
                f"{len(documents)} uploaded sources and {len(evidence_board)} highlighted evidence chunks."
            ),
            "key_questions": key_questions,
            "evidence_board": evidence_board,
            "document_coverage": [document["title"] for document in documents[:6]],
        }
        return {
            "agent": self._agent_payload(
                "research",
                "Research Agent",
                "Evidence organizer",
                artifact["executive_summary"],
                88.0 if documents else 62.0,
                "high" if len(documents) < 2 else "medium",
                [
                    f"Uploaded sources: {len(documents)}",
                    f"Evidence chunks selected: {len(evidence_board)}",
                    f"Project topic: {manifest['topic']}",
                ],
                [
                    "Use the evidence board as the canonical source list.",
                    "Upload at least one more source if coverage is narrow.",
                    "Keep key questions visible during drafting and review.",
                ],
            ),
            "artifact": artifact,
        }

    def _planner_artifact(
        self,
        manifest: dict[str, Any],
        template: dict[str, Any],
        evidence_board: list[dict[str, Any]],
        knowledge_graph: dict[str, Any],
    ) -> dict[str, Any]:
        workflow = manifest["workflow"]["stages"]
        sections = manifest["sections"]
        nodes = [
            {"id": stage["stage_id"], "label": stage["label"], "stage_type": "workflow"}
            for stage in workflow
        ] + [
            {"id": section["section_id"], "label": section["title"], "stage_type": "section"}
            for section in sections
        ]
        edges = []
        for left, right in zip(workflow, workflow[1:], strict=False):
            edges.append({"source": left["stage_id"], "target": right["stage_id"], "relationship": "next"})
        for section in sections:
            edges.append({"source": "plan", "target": section["section_id"], "relationship": "builds"})

        artifact = {
            "objective": f"Compile a local-first {template['label']} for {manifest['audience']}.",
            "workflow_graph": {"nodes": nodes, "edges": edges},
            "knowledge_graph_summary": {
                "nodes": len(knowledge_graph["nodes"]),
                "edges": len(knowledge_graph["edges"]),
                "highlights": knowledge_graph["highlights"][:3],
            },
            "section_plan": [
                {
                    "section_id": section["section_id"],
                    "title": section["title"],
                    "objective": section["objective"],
                    "primary_evidence": [item["citation_label"] for item in evidence_board[:2]],
                }
                for section in sections
            ],
        }
        return {
            "agent": self._agent_payload(
                "planner",
                "Planner Agent",
                "Project compiler planner",
                "Structured workflow and section graph generated for the local project compiler.",
                91.0,
                "medium",
                [
                    f"Workflow stages: {len(workflow)}",
                    f"Sections: {len(sections)}",
                    f"Knowledge graph nodes: {len(knowledge_graph['nodes'])}",
                ],
                [
                    "Run the stages in order unless the student disables one in the workflow builder.",
                    "Use section objectives as the minimum artifact contract.",
                    "Keep knowledge-graph highlights visible during editing.",
                ],
            ),
            "artifact": artifact,
        }

    def _historian_artifact(
        self,
        manifest: dict[str, Any],
        documents: list[dict[str, Any]],
        knowledge_graph: dict[str, Any],
    ) -> dict[str, Any]:
        timeline_points = []
        for document in documents[:5]:
            for year in document.get("years", [])[:2]:
                timeline_points.append(
                    {
                        "year": year,
                        "event": f"{document['title']} contains evidence relevant to {manifest['topic']}.",
                        "source": document["citation_label"],
                    }
                )
        artifact = {
            "context_summary": (
                f"The uploaded source base frames {manifest['topic']} through "
                f"{len(knowledge_graph['nodes'])} graph nodes and {len(timeline_points)} timeline anchors."
            ),
            "timeline_points": timeline_points[:8],
            "continuity_notes": knowledge_graph["highlights"][:4],
        }
        return {
            "agent": self._agent_payload(
                "historian",
                "Historian Agent",
                "Context and timeline guide",
                artifact["context_summary"],
                84.0 if timeline_points else 70.0,
                "medium",
                [
                    f"Timeline anchors: {len(timeline_points)}",
                    f"Graph highlights: {len(knowledge_graph['highlights'])}",
                    f"Documents with years: {sum(1 for document in documents if document.get('years'))}",
                ],
                [
                    "Use timeline points to ground chronology-sensitive sections.",
                    "Add more date-bearing evidence if the project needs stronger historical sequencing.",
                    "Tie continuity notes into captions, exhibits, or simulation branches.",
                ],
            ),
            "artifact": artifact,
        }

    def _citation_artifact(
        self,
        manifest: dict[str, Any],
        template: dict[str, Any],
        evidence_board: list[dict[str, Any]],
    ) -> dict[str, Any]:
        citation_map = []
        for index, section in enumerate(manifest["sections"]):
            section_evidence = evidence_board[index:index + 2] or evidence_board[:1]
            citation_map.append(
                {
                    "section_id": section["section_id"],
                    "section_title": section["title"],
                    "citations": [
                        {
                            "chunk_id": item["chunk_id"],
                            "citation_label": item["citation_label"],
                            "excerpt": item["excerpt"],
                        }
                        for item in section_evidence
                    ],
                }
            )
        artifact = {
            "project_type": template["project_type"],
            "citation_map": citation_map,
            "provenance_rule": "Every generated section must cite at least one evidence chunk.",
        }
        return {
            "agent": self._agent_payload(
                "citation",
                "Citation Agent",
                "Provenance mapper",
                "Section-to-evidence provenance map generated from uploaded chunks.",
                93.0 if evidence_board else 60.0,
                "high" if len(evidence_board) < len(manifest["sections"]) else "medium",
                [
                    f"Sections mapped: {len(citation_map)}",
                    f"Evidence entries: {len(evidence_board)}",
                    f"Project type: {template['project_type']}",
                ],
                [
                    "Do not export sections without provenance.",
                    "Use chunk IDs as stable references during editing and review.",
                    "Keep citation labels visible in student-facing previews.",
                ],
            ),
            "artifact": artifact,
        }

    def _writer_artifact(
        self,
        manifest: dict[str, Any],
        template: dict[str, Any],
        evidence_board: list[dict[str, Any]],
        citation_artifact: dict[str, Any],
    ) -> dict[str, Any]:
        sections = []
        citation_lookup = {
            item["section_id"]: item["citations"]
            for item in citation_artifact["artifact"]["citation_map"]
        }
        for section in manifest["sections"]:
            citations = citation_lookup.get(section["section_id"], [])
            lead = citations[0] if citations else None
            body = (
                f"{section['title']} addresses {section['objective']} for {manifest['audience']}. "
                f"The section is grounded in uploaded evidence and shaped for the {template['label']} format."
            )
            if lead:
                body += f" Anchor evidence: {lead['excerpt']} ({lead['citation_label']})."
            sections.append(
                {
                    "section_id": section["section_id"],
                    "title": section["title"],
                    "body": body,
                    "citations": citations,
                }
            )
        artifact = {"sections": sections}
        return {
            "agent": self._agent_payload(
                "writer",
                "Writer Agent",
                "Structured draft author",
                f"Generated {len(sections)} editable draft sections with inline provenance.",
                86.0 if evidence_board else 58.0,
                "medium",
                [
                    f"Draft sections: {len(sections)}",
                    f"Evidence-linked sections: {sum(1 for section in sections if section['citations'])}",
                    f"Template: {template['label']}",
                ],
                [
                    "Use the drafts as editable starting points, not locked output.",
                    "Revise section tone for the target audience before final export.",
                    "If a section lacks citations, upload more evidence or rerun retrieval.",
                ],
            ),
            "artifact": artifact,
        }

    def _design_artifact(
        self,
        manifest: dict[str, Any],
        template: dict[str, Any],
    ) -> dict[str, Any]:
        theme_tokens = template["theme_tokens"] | {
            "project_title": manifest["title"],
            "audience": manifest["audience"],
        }
        artifact = {
            "theme_tokens": theme_tokens,
            "layout_direction": template["layout_direction"],
            "presentation_notes": [
                "Keep evidence labels visible near claims.",
                "Preserve the project's local-first identity in the copy and footer.",
                "Use the template's motion style sparingly for readability.",
            ],
        }
        return {
            "agent": self._agent_payload(
                "design",
                "Design Agent",
                "Theme and layout system designer",
                "Theme tokens and layout rules prepared for local export targets.",
                82.0,
                "medium",
                [
                    f"Color family: {theme_tokens['accent']}",
                    f"Layout: {template['layout_direction']}",
                    f"Project type: {template['project_type']}",
                ],
                [
                    "Keep typography expressive but readable on student devices.",
                    "Use color to separate evidence, narration, and teacher feedback.",
                    "Respect the template layout contract during export compilation.",
                ],
            ),
            "artifact": artifact,
        }

    def _simulation_artifact(
        self,
        manifest: dict[str, Any],
        template: dict[str, Any],
        evidence_board: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not template.get("supports_simulation", False):
            return {
                "enabled": False,
                "nodes": [],
                "branches": [],
            }

        nodes = [
            {
                "node_id": "entry",
                "label": f"Start {manifest['title']}",
                "prompt": f"Choose how to introduce {manifest['topic']} to {manifest['audience']}.",
            }
        ]
        branches = []
        for index, evidence in enumerate(evidence_board[:3], start=1):
            node_id = f"choice-{index}"
            nodes.append(
                {
                    "node_id": node_id,
                    "label": evidence["citation_label"],
                    "prompt": f"Use this evidence to advance the project narrative: {evidence['excerpt']}",
                }
            )
            branches.append(
                {
                    "source": "entry",
                    "target": node_id,
                    "condition": f"Student chooses evidence route {index}",
                }
            )
        return {
            "enabled": True,
            "nodes": nodes,
            "branches": branches,
        }

    def _qa_artifact(
        self,
        manifest: dict[str, Any],
        documents: list[dict[str, Any]],
        writer: dict[str, Any],
        citation: dict[str, Any],
        simulation: dict[str, Any],
    ) -> dict[str, Any]:
        warnings = []
        if len(documents) < 2:
            warnings.append("Project has fewer than two uploaded sources.")
        if any(not section["citations"] for section in writer["artifact"]["sections"]):
            warnings.append("At least one section lacks supporting citations.")
        if manifest["project_type"] == "civic_campaign_simulator" and not simulation["enabled"]:
            warnings.append("Simulation template selected without a simulation blueprint.")

        artifact = {
            "status": "ready" if not warnings else "attention_needed",
            "warnings": warnings,
            "checks": {
                "document_count": len(documents),
                "section_count": len(writer["artifact"]["sections"]),
                "citation_coverage": sum(
                    1 for item in citation["artifact"]["citation_map"] if item["citations"]
                ),
            },
        }
        return {
            "agent": self._agent_payload(
                "qa",
                "QA Agent",
                "Quality and regression checker",
                f"QA completed with status {artifact['status']}.",
                89.0 if not warnings else 74.0,
                "high" if warnings else "low",
                [
                    f"Warnings: {len(warnings)}",
                    f"Documents: {len(documents)}",
                    f"Sections: {len(writer['artifact']['sections'])}",
                ],
                warnings or [
                    "Proceed to export after one final human review.",
                    "Preserve citations during any manual editing.",
                    "Keep the project manifest in sync with section changes.",
                ],
            ),
            "artifact": artifact,
        }

    def _teacher_artifact(
        self,
        manifest: dict[str, Any],
        writer: dict[str, Any],
        citation: dict[str, Any],
        qa: dict[str, Any],
    ) -> dict[str, Any]:
        rubric = manifest.get("rubric") or [
            "Evidence Quality",
            "Clarity",
            "Historical Accuracy",
            "Design",
            "Audience Fit",
        ]
        evidence_coverage = sum(1 for item in citation["artifact"]["citation_map"] if item["citations"])
        section_count = len(writer["artifact"]["sections"])
        base_score = 72 + evidence_coverage * 4 + max(0, section_count - 3) * 2
        if qa["artifact"]["warnings"]:
            base_score -= len(qa["artifact"]["warnings"]) * 6

        rubric_scores = [
            {
                "criterion": criterion,
                "score": max(55, min(100, base_score - index * 2)),
                "feedback": f"{criterion} is supported by the current artifact set.",
            }
            for index, criterion in enumerate(rubric)
        ]
        artifact = {
            "overall_score": round(sum(item["score"] for item in rubric_scores) / len(rubric_scores), 1),
            "rubric_scores": rubric_scores,
            "teacher_notes": [
                "Ask the student to explain why each citation was chosen.",
                "Encourage one revision pass focused on audience clarity.",
                "Use the workflow graph to discuss process, not only output.",
            ],
        }
        return {
            "agent": self._agent_payload(
                "teacher",
                "Teacher Agent",
                "Rubric reviewer",
                f"Rubric scoring completed with overall score {artifact['overall_score']}.",
                87.0,
                "medium",
                [
                    f"Rubric dimensions: {len(rubric_scores)}",
                    f"Overall score: {artifact['overall_score']}",
                    f"QA status: {qa['artifact']['status']}",
                ],
                [
                    "Use rubric scores as coaching signals, not final grades.",
                    "Re-run review after major evidence or section changes.",
                    "Keep teacher notes attached to the project manifest.",
                ],
            ),
            "artifact": artifact,
        }

    def _export_artifact(
        self,
        manifest: dict[str, Any],
        template: dict[str, Any],
        design: dict[str, Any],
        qa: dict[str, Any],
    ) -> dict[str, Any]:
        artifact = {
            "targets": template["export_targets"],
            "ready_for_export": qa["artifact"]["status"] == "ready",
            "build_notes": [
                "Generate a static site for the easiest local sharing path.",
                "Package a React scaffold for students who want to extend the project.",
                "Emit a printable report for classroom review.",
            ],
            "theme_tokens": design["artifact"]["theme_tokens"],
        }
        return {
            "agent": self._agent_payload(
                "export",
                "Export Agent",
                "Build and delivery planner",
                f"Prepared export targets: {', '.join(template['export_targets'])}.",
                85.0 if artifact["ready_for_export"] else 71.0,
                "medium" if artifact["ready_for_export"] else "high",
                [
                    f"Targets: {len(template['export_targets'])}",
                    f"Ready: {artifact['ready_for_export']}",
                    f"Project: {manifest['title']}",
                ],
                [
                    "Prefer the static-site bundle for the first student handoff.",
                    "Use the React scaffold if further customization is needed.",
                    "Keep the printable report aligned with the same citations and sections.",
                ],
            ),
            "artifact": artifact,
        }

    def _agent_payload(
        self,
        agent_name: str,
        display_name: str,
        role: str,
        summary: str,
        confidence: float,
        priority: str,
        signals: list[str],
        actions: list[str],
    ) -> dict[str, Any]:
        return {
            "agent_name": agent_name,
            "display_name": display_name,
            "role": role,
            "summary": summary,
            "confidence": round(confidence, 1),
            "priority": priority,
            "signals": signals,
            "actions": actions,
        }
