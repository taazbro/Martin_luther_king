from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_education_growth_end_to_end(tmp_path):
    settings = Settings(
        db_path=tmp_path / "education-growth.sqlite3",
        workflow_scheduler_enabled=False,
        admin_password="mlk-admin-demo",
        studio_root_dir=tmp_path / "studio_workspace",
        studio_template_dir=tmp_path / "templates",
        community_root_dir=tmp_path / "community",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        classroom_response = client.post(
            "/api/v1/edu/classrooms",
            json={
                "title": "Civics Period 5",
                "subject": "Civics",
                "grade_band": "Grades 9-10",
                "teacher_name": "Ms. Rivera",
                "description": "A civic inquiry classroom for local evidence projects.",
                "default_template_id": "lesson-module",
                "standards_focus": ["C3 Inquiry", "Source Analysis"],
            },
        )
        assert classroom_response.status_code == 201
        classroom = classroom_response.json()
        classroom_id = classroom["classroom_id"]
        teacher_access_key = classroom["security_bootstrap"]["teacher_access_key"]
        student_access_key = classroom["security_bootstrap"]["student_access_key"]
        reviewer_access_key = classroom["security_bootstrap"]["reviewer_access_key"]

        student_response = client.post(
            f"/api/v1/edu/classrooms/{classroom_id}/students",
            json={
                "name": "Jordan Lee",
                "grade_level": "Grade 9",
                "learning_goals": ["Use stronger evidence", "Practice revisions"],
                "notes": "Interested in local history and policy.",
                "access_key": teacher_access_key,
            },
        )
        assert student_response.status_code == 200
        student_id = student_response.json()["students"][0]["student_id"]

        material_response = client.post(
            f"/api/v1/edu/classrooms/{classroom_id}/materials",
            data={"access_key": teacher_access_key},
            files={
                "file": (
                    "transit-notes.txt",
                    b"Students compared transit access maps, resident interviews, and policy memos about neighborhood mobility in 2025.",
                    "text/plain",
                )
            },
        )
        assert material_response.status_code == 200

        overview = client.get("/api/v1/edu/growth/overview")
        assert overview.status_code == 200
        assert overview.json()["counts"]["classrooms"] == 1

        autopilot = client.post(
            "/api/v1/edu/growth/autopilot",
            json={
                "classroom_id": classroom_id,
                "access_key": teacher_access_key,
                "topic": "Neighborhood transit access and mobility justice",
                "audience": "Grade 9 students",
                "rubric": ["Evidence Quality", "Citation Accuracy", "Clarity"],
                "goals": ["Compare approved sources", "Build a cited local argument"],
                "due_date": "2026-05-01",
            },
        )
        assert autopilot.status_code == 201
        autopilot_payload = autopilot.json()
        assignment_id = autopilot_payload["assignment"]["assignment_id"]
        assert autopilot_payload["evidence_pack"][0]["file_name"] == "transit-notes.txt"
        assert autopilot_payload["assessment_pack"]["quiz_questions"]
        assert autopilot_payload["standards_map"]["standards_alignment"]

        library_promote = client.post(
            f"/api/v1/edu/growth/library/{classroom_id}/promote",
            json={
                "access_key": teacher_access_key,
                "material_ids": [],
            },
        )
        assert library_promote.status_code == 200
        assert library_promote.json()["item_count"] >= 1

        library_get = client.get(
            f"/api/v1/edu/growth/library/{classroom_id}",
            params={"access_key": reviewer_access_key},
        )
        assert library_get.status_code == 200
        assert library_get.json()["collections"]

        launch = client.post(
            f"/api/v1/edu/classrooms/{classroom_id}/launch",
            json={
                "assignment_id": assignment_id,
                "student_id": student_id,
                "access_key": teacher_access_key,
            },
        )
        assert launch.status_code == 200
        launch_payload = launch.json()
        project_slug = launch_payload["project"]["slug"]

        compiled = client.post(f"/api/v1/studio/projects/{project_slug}/compile", json={})
        assert compiled.status_code == 200
        assert compiled.json()["exports"]

        revision_coach = client.post(
            "/api/v1/edu/growth/revision-coach",
            json={
                "classroom_id": classroom_id,
                "assignment_id": assignment_id,
                "access_key": student_access_key,
                "project_slug": project_slug,
                "draft_text": (
                    "Neighborhood transit access is unequal because some families wait longer and walk farther for buses. "
                    "Policy memos and resident interviews show that neighborhoods with fewer route investments have slower service."
                ),
                "rubric": ["Evidence Quality", "Citation Accuracy", "Clarity"],
                "teacher_feedback": ["Add one stronger source comparison.", "Make the main claim more explicit."],
            },
        )
        assert revision_coach.status_code == 200
        revision_payload = revision_coach.json()
        assert revision_payload["revision_tasks"]
        assert "student_summary" in revision_payload

        citation_verify = client.post(
            "/api/v1/edu/growth/citation-verify",
            json={
                "project_slug": project_slug,
                "claims": [
                    "Neighborhood transit access is unequal because some families wait longer and walk farther for buses.",
                    "The project should also mention a source that was never uploaded anywhere.",
                ],
            },
        )
        assert citation_verify.status_code == 200
        citation_payload = citation_verify.json()
        assert citation_payload["verified_claims"]
        assert citation_payload["blocked_claims"]

        family_view = client.get(
            "/api/v1/edu/growth/family-view",
            params={
                "classroom_id": classroom_id,
                "project_slug": project_slug,
                "access_key": teacher_access_key,
            },
        )
        assert family_view.status_code == 200
        family_payload = family_view.json()
        assert family_payload["downloads"]
        assert family_payload["summary"].startswith(launch_payload["project"]["title"])

        family_share = client.post(
            "/api/v1/edu/growth/family-view/share",
            params={
                "classroom_id": classroom_id,
                "project_slug": project_slug,
                "access_key": teacher_access_key,
            },
        )
        assert family_share.status_code == 201
        shared_family = client.get(f"/api/v1/edu/growth/family-view/shared/{family_share.json()['share_token']}")
        assert shared_family.status_code == 200
        assert shared_family.json()["share_link"]

        peer_review = client.post(
            "/api/v1/edu/growth/peer-review",
            json={
                "classroom_id": classroom_id,
                "assignment_id": assignment_id,
                "reviewer_student_id": student_id,
                "target_student_id": student_id,
                "access_key": student_access_key,
                "project_slug": project_slug,
                "draft_text": "The draft uses local transit evidence, but it needs one clearer citation and a stronger conclusion.",
                "rubric": ["Evidence Quality", "Citation Accuracy", "Clarity"],
            },
        )
        assert peer_review.status_code == 201
        review_id = peer_review.json()["review_id"]

        listed_reviews = client.get(
            "/api/v1/edu/growth/peer-review",
            params={"classroom_id": classroom_id, "access_key": reviewer_access_key},
        )
        assert listed_reviews.status_code == 200
        assert listed_reviews.json()[0]["review_id"] == review_id

        review_pairs = client.get(
            "/api/v1/edu/growth/peer-review/pairs",
            params={
                "classroom_id": classroom_id,
                "assignment_id": assignment_id,
                "access_key": reviewer_access_key,
            },
        )
        assert review_pairs.status_code == 200
        assert review_pairs.json()["assignment_id"] == assignment_id

        resolved_review = client.post(
            f"/api/v1/edu/growth/peer-review/{review_id}/resolve",
            json={
                "decision": "approved",
                "reviewer": "Ms. Rivera",
                "note": "Peer feedback is safe and helpful.",
                "access_key": reviewer_access_key,
            },
        )
        assert resolved_review.status_code == 200
        assert resolved_review.json()["status"] == "approved"

        standards_map = client.get(
            "/api/v1/edu/growth/standards-map",
            params={
                "classroom_id": classroom_id,
                "assignment_id": assignment_id,
                "access_key": teacher_access_key,
            },
        )
        assert standards_map.status_code == 200
        assert standards_map.json()["district_rubric_map"]

        interventions = client.get(
            "/api/v1/edu/growth/interventions",
            params={"classroom_id": classroom_id, "access_key": teacher_access_key},
        )
        assert interventions.status_code == 200
        assert interventions.json()["student_signals"]

        roster = client.get(
            "/api/v1/edu/growth/roster",
            params={"classroom_id": classroom_id, "access_key": reviewer_access_key},
        )
        assert roster.status_code == 200
        assert roster.json()["students"][0]["progress_state"]

        assignment_status = client.get(
            "/api/v1/edu/growth/assignment-status",
            params={"classroom_id": classroom_id, "access_key": reviewer_access_key},
        )
        assert assignment_status.status_code == 200
        assert assignment_status.json()["assignments"][0]["assignment_id"] == assignment_id

        replay = client.get(
            "/api/v1/edu/growth/replay",
            params={"classroom_id": classroom_id, "access_key": reviewer_access_key},
        )
        assert replay.status_code == 200
        replay_payload = replay.json()
        assert replay_payload["counts"]["timeline_events"] > 0
        assert any(item["event_type"] == "project_export" for item in replay_payload["timeline"])

        lesson_to_project = client.post(
            "/api/v1/edu/growth/lesson-to-project",
            json={
                "lesson_plan": (
                    "Community Transit Lesson\n"
                    "- Analyze approved maps and testimony\n"
                    "- Build a short evidence-backed recommendation\n"
                    "- Close with an exit ticket"
                ),
                "classroom_id": classroom_id,
                "access_key": teacher_access_key,
                "seed_from_classroom": True,
            },
        )
        assert lesson_to_project.status_code == 201
        assert lesson_to_project.json()["project"]["documents"]

        rubric_train = client.post(
            "/api/v1/edu/growth/rubric-train",
            json={
                "classroom_id": classroom_id,
                "access_key": teacher_access_key,
                "project_slugs": [project_slug],
            },
        )
        assert rubric_train.status_code == 200
        assert rubric_train.json()["criterion_patterns"]

        assessment_pack = client.post(
            "/api/v1/edu/growth/assessment-pack",
            json={
                "classroom_id": classroom_id,
                "assignment_id": assignment_id,
                "access_key": teacher_access_key,
            },
        )
        assert assessment_pack.status_code == 200
        assert assessment_pack.json()["discussion_prompts"]

        marketplace = client.get("/api/v1/edu/growth/marketplace")
        assert marketplace.status_code == 200
        marketplace_payload = marketplace.json()
        assert marketplace_payload["templates"]
        assert marketplace_payload["school_packs"]
        assert marketplace_payload["plugin_sdk"]["plugin_sdk_path"]

        install_pack = client.post("/api/v1/edu/growth/school-packs/teacher-research-writing-kit/install")
        assert install_pack.status_code == 201
        assert install_pack.json()["recommended_templates"]

        offline = client.get("/api/v1/edu/growth/offline-school-edition")
        assert offline.status_code == 200
        assert offline.json()["supported_modes"]


def test_education_growth_provider_routing(tmp_path, monkeypatch):
    settings = Settings(
        db_path=tmp_path / "education-growth-provider.sqlite3",
        workflow_scheduler_enabled=False,
        admin_password="mlk-admin-demo",
        studio_root_dir=tmp_path / "studio_workspace",
        studio_template_dir=tmp_path / "templates",
        community_root_dir=tmp_path / "community",
    )
    app = create_app(settings)

    def fake_invoke_provider(**kwargs: object) -> str:
        provider_id = str(kwargs["provider_id"])
        return f"{provider_id} response for {str(kwargs['prompt'])[:48]}"

    with TestClient(app) as client:
        monkeypatch.setattr(app.state.ai_provider_service, "_invoke_provider", fake_invoke_provider)
        for payload in (
            {
                "label": "OpenAI Writing",
                "provider_id": "openai",
                "auth_mode": "managed-subscription",
                "api_key": "sk-openai-test-key",
                "default_model": "gpt-5-mini",
                "base_url": "",
                "capabilities": ["assignments", "research"],
            },
            {
                "label": "Anthropic Feedback",
                "provider_id": "anthropic",
                "auth_mode": "managed-subscription",
                "api_key": "anthropic-feedback-key",
                "default_model": "claude-sonnet-4-5",
                "base_url": "",
                "capabilities": ["feedback", "review"],
            },
            {
                "label": "Groq Planning",
                "provider_id": "groq",
                "auth_mode": "managed-subscription",
                "api_key": "groq-planning-key",
                "default_model": "llama-3.3-70b-versatile",
                "base_url": "",
                "capabilities": ["planning"],
            },
        ):
            response = client.post("/api/v1/ai/profiles", json=payload)
            assert response.status_code == 201

        classroom_response = client.post(
            "/api/v1/edu/classrooms",
            json={
                "title": "Provider Civics",
                "subject": "Civics",
                "grade_band": "Grades 9-10",
                "teacher_name": "Ms. Rivera",
                "description": "Provider-routed classroom.",
                "default_template_id": "lesson-module",
                "standards_focus": ["C3 Inquiry"],
            },
        )
        assert classroom_response.status_code == 201
        classroom = classroom_response.json()
        classroom_id = classroom["classroom_id"]
        teacher_access_key = classroom["security_bootstrap"]["teacher_access_key"]

        assignment = client.post(
            "/api/v1/edu/growth/autopilot",
            json={
                "classroom_id": classroom_id,
                "access_key": teacher_access_key,
                "topic": "Local housing policy",
                "rubric": ["Evidence Quality", "Citation Accuracy"],
            },
        )
        assert assignment.status_code == 201
        assert assignment.json()["route"]["execution_mode"] == "provider-ai"
        assert assignment.json()["route"]["selected_provider"]["provider_id"] == "openai"

        assignment_id = assignment.json()["assignment"]["assignment_id"]
        revision = client.post(
            "/api/v1/edu/growth/revision-coach",
            json={
                "classroom_id": classroom_id,
                "assignment_id": assignment_id,
                "access_key": teacher_access_key,
                "draft_text": (
                    "Local housing policy affects rent levels and neighborhood stability. "
                    "The draft needs stronger evidence and a clearer explanation of what the sources prove."
                ),
                "rubric": ["Evidence Quality", "Citation Accuracy", "Clarity"],
            },
        )
        assert revision.status_code == 200
        assert revision.json()["route"]["selected_provider"]["provider_id"] == "anthropic"

        lesson = client.post(
            "/api/v1/edu/growth/lesson-to-project",
            json={
                "lesson_plan": (
                    "Housing Policy Strategy Lesson\n"
                    "- Compare policy memos\n"
                    "- Build a recommendation\n"
                    "- Prepare for discussion"
                ),
                "classroom_id": classroom_id,
                "access_key": teacher_access_key,
            },
        )
        assert lesson.status_code == 201
        assert lesson.json()["route"]["selected_provider"]["provider_id"] == "groq"
