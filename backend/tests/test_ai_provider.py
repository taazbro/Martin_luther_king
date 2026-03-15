from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_ai_provider_profile_lifecycle(tmp_path, monkeypatch):
    settings = Settings(
        db_path=tmp_path / "ai.sqlite3",
        workflow_scheduler_enabled=False,
        admin_password="mlk-admin-demo",
        studio_root_dir=tmp_path / "studio_workspace",
        studio_template_dir=tmp_path / "templates",
        community_root_dir=tmp_path / "community",
    )
    app = create_app(settings)

    def fake_invoke_provider(**_: object) -> str:
        return "READY classroom-safe provider connection."

    with TestClient(app) as client:
        monkeypatch.setattr(app.state.ai_provider_service, "_invoke_provider", fake_invoke_provider)
        catalog = client.get("/api/v1/ai/catalog")
        assert catalog.status_code == 200
        catalog_payload = catalog.json()
        assert any(entry["provider_id"] == "openai" for entry in catalog_payload)
        assert any(entry["provider_id"] == "anthropic" for entry in catalog_payload)

        create = client.post(
            "/api/v1/ai/profiles",
            json={
                "label": "Teacher OpenAI",
                "provider_id": "openai",
                "auth_mode": "user-key",
                "api_key": "sk-test-provider-key",
                "default_model": "gpt-5-mini",
                "base_url": "",
                "capabilities": ["research", "assignments", "feedback"],
                "daily_request_limit": 25,
                "monthly_budget_usd": 18.5,
                "redaction_mode": "pii-lite",
            },
        )
        assert create.status_code == 201
        profile = create.json()
        profile_id = profile["profile_id"]
        assert profile["api_key_hint"].startswith("sk-t")
        assert profile["daily_request_limit"] == 25
        assert profile["redaction_mode"] == "pii-lite"

        listed = client.get("/api/v1/ai/profiles")
        assert listed.status_code == 200
        assert listed.json()[0]["profile_id"] == profile_id

        updated = client.put(
            f"/api/v1/ai/profiles/{profile_id}",
            json={
                "label": "Managed OpenAI Seat",
                "auth_mode": "managed-subscription",
                "capabilities": ["research", "planning", "review"],
                "managed_subscription_note": "Reserved for trusted classroom flows.",
            },
        )
        assert updated.status_code == 200
        assert updated.json()["auth_mode"] == "managed-subscription"
        assert updated.json()["managed_subscription_note"]

        tested = client.post(f"/api/v1/ai/profiles/{profile_id}/test")
        assert tested.status_code == 200
        assert tested.json()["used"] is True
        assert "READY" in tested.json()["output_text"]
        assert tested.json()["redaction"]["mode"] == "pii-lite"

        usage = client.get("/api/v1/ai/usage")
        assert usage.status_code == 200
        usage_payload = usage.json()
        assert usage_payload[0]["profile_id"] == profile_id
        assert usage_payload[0]["success"] is True
        assert "estimated_cost_usd" in usage_payload[0]

        deleted = client.delete(f"/api/v1/ai/profiles/{profile_id}")
        assert deleted.status_code == 204

        listed_after_delete = client.get("/api/v1/ai/profiles")
        assert listed_after_delete.status_code == 200
        assert listed_after_delete.json() == []


def test_ai_provider_classroom_policy_and_fallback(tmp_path, monkeypatch):
    settings = Settings(
        db_path=tmp_path / "ai-policy.sqlite3",
        workflow_scheduler_enabled=False,
        admin_password="mlk-admin-demo",
        studio_root_dir=tmp_path / "studio_workspace",
        studio_template_dir=tmp_path / "templates",
        community_root_dir=tmp_path / "community",
    )
    app = create_app(settings)

    calls: list[str] = []

    def fake_invoke_provider(**kwargs: object) -> str:
        provider_id = str(kwargs["provider_id"])
        calls.append(str(kwargs["prompt"]))
        if provider_id == "openai":
            raise RuntimeError("primary provider unavailable")
        return "Anthropic fallback completed the classroom-safe response."

    with TestClient(app) as client:
        monkeypatch.setattr(app.state.ai_provider_service, "_invoke_provider", fake_invoke_provider)
        primary = client.post(
            "/api/v1/ai/profiles",
            json={
                "label": "Primary OpenAI",
                "provider_id": "openai",
                "auth_mode": "managed-subscription",
                "api_key": "sk-primary-provider-key",
                "default_model": "gpt-5-mini",
                "base_url": "",
                "capabilities": ["research", "assignments"],
                "daily_request_limit": 10,
                "monthly_budget_usd": 15.0,
                "usage_cap_per_classroom_daily": 5,
            },
        )
        assert primary.status_code == 201
        primary_id = primary.json()["profile_id"]

        fallback = client.post(
            "/api/v1/ai/profiles",
            json={
                "label": "Fallback Anthropic",
                "provider_id": "anthropic",
                "auth_mode": "managed-subscription",
                "api_key": "anthropic-fallback-provider-key",
                "default_model": "claude-sonnet-4-5",
                "base_url": "",
                "capabilities": ["research", "assignments", "feedback"],
                "daily_request_limit": 10,
                "monthly_budget_usd": 15.0,
            },
        )
        assert fallback.status_code == 201
        fallback_id = fallback.json()["profile_id"]

        patched = client.put(
            f"/api/v1/ai/profiles/{primary_id}",
            json={"fallback_profile_ids": [fallback_id]},
        )
        assert patched.status_code == 200
        assert patched.json()["fallback_profile_ids"] == [fallback_id]

        policy = client.put(
            "/api/v1/ai/classroom-policies/classroom-demo",
            json={
                "daily_request_limit": 8,
                "monthly_budget_usd": 12.0,
                "managed_subscription_allowed": True,
                "allowed_profile_ids": [primary_id, fallback_id],
                "redact_student_pii": True,
                "notes": "Only approved managed seats may run in this classroom.",
            },
        )
        assert policy.status_code == 200
        assert policy.json()["allowed_profile_ids"] == [primary_id, fallback_id]

        result = app.state.ai_provider_service.generate_with_profile(
            primary_id,
            task="research",
            prompt="Student: Jordan Lee\nEmail: jordan@example.com\nSummarize the project evidence safely.",
            system_prompt="You are a classroom-safe assistant.",
            source="test",
            metadata={"student_name": "Jordan Lee"},
            classroom_id="classroom-demo",
        )
        assert result["used"] is True
        assert result["effective_profile_id"] == fallback_id
        assert result["fallback_used"] is True
        assert result["redaction"]["applied"] is True
        assert any("[redacted_email]" in prompt for prompt in calls)

        listed_policy = client.get("/api/v1/ai/classroom-policies/classroom-demo")
        assert listed_policy.status_code == 200
        assert listed_policy.json()["managed_subscription_allowed"] is True

        usage = client.get("/api/v1/ai/usage")
        assert usage.status_code == 200
        usage_payload = usage.json()
        assert usage_payload[0]["fallback_used"] is True
        assert usage_payload[0]["classroom_id"] == "classroom-demo"
