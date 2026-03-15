from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_studio_project_flow(tmp_path):
    settings = Settings(
        db_path=tmp_path / "studio.sqlite3",
        workflow_scheduler_enabled=False,
        admin_password="mlk-admin-demo",
        studio_root_dir=tmp_path / "studio_workspace",
        studio_template_dir=tmp_path / "templates",
        community_root_dir=tmp_path / "community",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        overview = client.get("/api/v1/studio/overview")
        assert overview.status_code == 200
        overview_payload = overview.json()
        assert overview_payload["counts"]["templates"] >= 6
        assert overview_payload["counts"]["plugins"] >= 2
        assert len(overview_payload["sample_projects"]) >= 3

        system_status = client.get("/api/v1/studio/system/status")
        assert system_status.status_code == 200
        system_payload = system_status.json()
        assert system_payload["portability"]["import_supported"] is True
        assert "desktop_version" in system_payload["release"]

        templates = client.get("/api/v1/studio/templates")
        assert templates.status_code == 200
        assert any(template["project_type"] == "interactive_history_app" for template in templates.json())

        create = client.post(
            "/api/v1/studio/projects",
            json={
                "title": "Local Water Justice Exhibit",
                "summary": "A local-first project built from uploaded sources.",
                "topic": "Water justice in the local community",
                "audience": "High school students",
                "goals": ["Explain the issue", "Compare evidence", "Present a civic response"],
                "rubric": ["Evidence", "Clarity", "Audience Fit"],
                "template_id": "research-portfolio",
                "local_mode": "no-llm",
            },
        )
        assert create.status_code == 201
        project = create.json()
        slug = project["slug"]
        assert project["template_id"] == "research-portfolio"
        assert project["workflow"]["stages"][0]["stage_id"] == "ingest"

        projects = client.get("/api/v1/studio/projects")
        assert projects.status_code == 200
        assert any(item["slug"] == slug for item in projects.json())

        upload = client.post(
            f"/api/v1/studio/projects/{slug}/documents",
            files={"file": ("water-notes.txt", b"Water Justice Coalition met in 2024 to discuss clean water access in Detroit. Community leaders and students compared maps, policy memos, and oral histories.", "text/plain")},
        )
        assert upload.status_code == 200
        document_payload = upload.json()
        assert document_payload["chunk_count"] >= 1
        assert document_payload["reading_level"]

        documents = client.get(f"/api/v1/studio/projects/{slug}/documents")
        assert documents.status_code == 200
        assert len(documents.json()) == 1

        search = client.post(
            f"/api/v1/studio/projects/{slug}/search",
            json={"query": "clean water access coalition policy", "limit": 4},
        )
        assert search.status_code == 200
        search_payload = search.json()
        assert len(search_payload) >= 1
        assert search_payload[0]["chunk_id"]

        graph = client.get(f"/api/v1/studio/projects/{slug}/graph")
        assert graph.status_code == 200
        graph_payload = graph.json()
        assert len(graph_payload["nodes"]) >= 3

        compiled = client.post(f"/api/v1/studio/projects/{slug}/compile", json={})
        assert compiled.status_code == 200
        compiled_payload = compiled.json()
        assert len(compiled_payload["workflow_results"]) >= 6
        assert compiled_payload["artifacts"]["runtime_mode"]["effective_mode"] == "no-llm"
        assert len(compiled_payload["artifacts"]["agents"]) == 9
        assert len(compiled_payload["exports"]) == 5
        assert compiled_payload["project"]["submission_readiness"]["ready_for_export"] is True

        local_llm_request = client.put(
            f"/api/v1/studio/projects/{slug}",
            json={"local_mode": "local-llm"},
        )
        assert local_llm_request.status_code == 200

        local_llm_compile = client.post(f"/api/v1/studio/projects/{slug}/compile", json={})
        assert local_llm_compile.status_code == 200
        local_llm_payload = local_llm_compile.json()
        assert local_llm_payload["artifacts"]["runtime_mode"]["requested_mode"] == "local-llm"
        assert local_llm_payload["artifacts"]["runtime_mode"]["effective_mode"] == "no-llm"

        artifacts = client.get(f"/api/v1/studio/projects/{slug}/artifacts")
        assert artifacts.status_code == 200
        artifact_payload = artifacts.json()
        assert artifact_payload["artifacts"]["research_brief"]["evidence_board"]
        assert artifact_payload["artifacts"]["written_sections"]["sections"]

        rubric_report = client.get(f"/api/v1/studio/projects/{slug}/download/rubric_report")
        assert rubric_report.status_code == 200

        teacher_comment = client.post(
            f"/api/v1/studio/projects/{slug}/comments",
            json={"author": "Ms. Rivera", "criterion": "Evidence", "body": "Strengthen the source comparison in section two."},
        )
        assert teacher_comment.status_code == 200
        teacher_comment_payload = teacher_comment.json()
        assert teacher_comment_payload["teacher_comments"][0]["author"] == "Ms. Rivera"
        assert teacher_comment_payload["revision_history"][0]["action"] == "teacher_comment"
        assert teacher_comment_payload["standards_alignment"]

        static_site = client.get(f"/api/v1/studio/projects/{slug}/download/static_site")
        assert static_site.status_code == 200
        assert "text/html" in static_site.headers["content-type"]

        project_bundle = client.get(f"/api/v1/studio/projects/{slug}/download/project_bundle")
        assert project_bundle.status_code == 200
        assert ".cpsbundle" in project_bundle.headers.get("content-disposition", "")

        clone = client.post(
            f"/api/v1/studio/projects/{slug}/clone",
            json={"title": "Local Water Justice Exhibit Clone"},
        )
        assert clone.status_code == 200
        assert clone.json()["slug"] != slug

        imported = client.post(
            "/api/v1/studio/projects/import",
            files={"file": ("import-bundle.cpsbundle", project_bundle.content, "application/octet-stream")},
            data={"title": "Imported Water Justice Exhibit"},
        )
        assert imported.status_code == 201
        assert imported.json()["title"] == "Imported Water Justice Exhibit"


def test_studio_export_quality_gates_block_final_exports(tmp_path):
    settings = Settings(
        db_path=tmp_path / "studio-gates.sqlite3",
        workflow_scheduler_enabled=False,
        admin_password="mlk-admin-demo",
        studio_root_dir=tmp_path / "studio_workspace",
        studio_template_dir=tmp_path / "templates",
        community_root_dir=tmp_path / "community",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        create = client.post(
            "/api/v1/studio/projects",
            json={
                "title": "Blocked Export Project",
                "summary": "A project used to verify quality gates.",
                "topic": "Local archive research",
                "audience": "High school students",
                "goals": ["Compare sources"],
                "rubric": ["Evidence", "Clarity"],
                "template_id": "research-portfolio",
                "local_mode": "no-llm",
            },
        )
        assert create.status_code == 201
        slug = create.json()["slug"]

        upload = client.post(
            f"/api/v1/studio/projects/{slug}/documents",
            files={"file": ("archive-notes.txt", b"Students compared archival notes, letters, and local meeting records from 2024.", "text/plain")},
        )
        assert upload.status_code == 200

        app.state.studio_service.update_project(
            slug,
            {
                "quality_gates": {
                    "min_citation_coverage": 100.0,
                    "min_overall_score": 99.0,
                    "min_rubric_score": 99.0,
                    "min_documents": 1,
                    "require_no_pending_approvals": True,
                }
            },
        )

        compiled = client.post(f"/api/v1/studio/projects/{slug}/compile", json={})
        assert compiled.status_code == 200
        payload = compiled.json()
        assert payload["project"]["submission_readiness"]["ready_for_export"] is False
        assert payload["workflow_results"][-1]["status"] == "blocked"
        assert [item["export_type"] for item in payload["exports"]] == ["rubric_report"]

        static_site = client.get(f"/api/v1/studio/projects/{slug}/download/static_site")
        assert static_site.status_code == 403

        rubric_report = client.get(f"/api/v1/studio/projects/{slug}/download/rubric_report")
        assert rubric_report.status_code == 200


def test_studio_provider_ai_flow(tmp_path, monkeypatch):
    settings = Settings(
        db_path=tmp_path / "studio-provider.sqlite3",
        workflow_scheduler_enabled=False,
        admin_password="mlk-admin-demo",
        studio_root_dir=tmp_path / "studio_workspace",
        studio_template_dir=tmp_path / "templates",
        community_root_dir=tmp_path / "community",
    )
    app = create_app(settings)

    def fake_invoke_provider(**_: object) -> str:
        return "Provider AI generated a sharper evidence-backed classroom draft."

    with TestClient(app) as client:
        monkeypatch.setattr(app.state.ai_provider_service, "_invoke_provider", fake_invoke_provider)
        profile_response = client.post(
            "/api/v1/ai/profiles",
            json={
                "label": "OpenAI Managed Seat",
                "provider_id": "openai",
                "auth_mode": "managed-subscription",
                "api_key": "sk-managed-provider-key",
                "default_model": "gpt-5-mini",
                "base_url": "",
                "capabilities": ["research", "assignments", "planning", "review"],
            },
        )
        assert profile_response.status_code == 201
        profile_id = profile_response.json()["profile_id"]

        create = client.post(
            "/api/v1/studio/projects",
            json={
                "title": "Provider AI Water Justice Exhibit",
                "summary": "A local-first project with provider-backed drafting.",
                "topic": "Water justice in the local community",
                "audience": "High school students",
                "goals": ["Explain the issue", "Compare evidence", "Present a civic response"],
                "rubric": ["Evidence", "Clarity", "Audience Fit"],
                "template_id": "research-portfolio",
                "local_mode": "provider-ai",
                "ai_profile_id": profile_id,
            },
        )
        assert create.status_code == 201
        slug = create.json()["slug"]
        assert create.json()["ai_profile_id"] == profile_id

        upload = client.post(
            f"/api/v1/studio/projects/{slug}/documents",
            files={"file": ("water-notes.txt", b"Residents compared clean water maps, testimony, and infrastructure records in 2024.", "text/plain")},
        )
        assert upload.status_code == 200

        compiled = client.post(f"/api/v1/studio/projects/{slug}/compile", json={})
        assert compiled.status_code == 200
        payload = compiled.json()
        assert payload["artifacts"]["runtime_mode"]["requested_mode"] == "provider-ai"
        assert payload["artifacts"]["runtime_mode"]["effective_mode"] == "provider-ai"
        assert payload["artifacts"]["artifacts"]["provider_ai_trace"]["profile_id"] == profile_id
        assert payload["project"]["ai_profile_id"] == profile_id
