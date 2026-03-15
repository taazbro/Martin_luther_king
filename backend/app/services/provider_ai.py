from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import Settings


SUPPORTED_PROVIDER_TASKS: tuple[str, ...] = (
    "research",
    "assignments",
    "feedback",
    "planning",
    "review",
    "export",
    "classroom",
)

SUPPORTED_REDACTION_MODES: tuple[str, ...] = ("off", "metadata-only", "pii-lite")

PROVIDER_COST_HINTS_USD_PER_1K_TOKENS: dict[str, float] = {
    "openai": 0.012,
    "anthropic": 0.015,
    "google": 0.006,
    "groq": 0.003,
    "mistral": 0.007,
    "cohere": 0.008,
    "xai": 0.01,
}

PROVIDER_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "provider_id": "openai",
        "label": "OpenAI",
        "sdk_package": "openai",
        "docs_url": "https://platform.openai.com/docs/libraries/python",
        "default_model": "gpt-5-mini",
        "recommended_models": ["gpt-5-mini", "gpt-5"],
        "supports_custom_base_url": True,
        "supports_managed_subscription": True,
        "notes": "Best for general research, writing, planning, and structured educational workflows.",
    },
    {
        "provider_id": "anthropic",
        "label": "Anthropic",
        "sdk_package": "anthropic",
        "docs_url": "https://docs.anthropic.com/en/api/client-sdks#python",
        "default_model": "claude-sonnet-4-5",
        "recommended_models": ["claude-sonnet-4-5", "claude-opus-4-1"],
        "supports_custom_base_url": True,
        "supports_managed_subscription": True,
        "notes": "Strong for analysis, long-form reasoning, feedback, and classroom-safe drafting.",
    },
    {
        "provider_id": "google",
        "label": "Google Gemini",
        "sdk_package": "google-genai",
        "docs_url": "https://ai.google.dev/gemini-api/docs/quickstart?lang=python",
        "default_model": "gemini-2.5-flash",
        "recommended_models": ["gemini-2.5-flash", "gemini-2.5-pro"],
        "supports_custom_base_url": False,
        "supports_managed_subscription": True,
        "notes": "Useful for multimodal classroom work and general content generation.",
    },
    {
        "provider_id": "groq",
        "label": "Groq",
        "sdk_package": "groq",
        "docs_url": "https://console.groq.com/docs/libraries#python-library",
        "default_model": "llama-3.3-70b-versatile",
        "recommended_models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
        "supports_custom_base_url": True,
        "supports_managed_subscription": True,
        "notes": "Fast inference path for classroom tooling, drafting, and quick research assistance.",
    },
    {
        "provider_id": "mistral",
        "label": "Mistral",
        "sdk_package": "mistralai",
        "docs_url": "https://docs.mistral.ai/getting-started/clients/#python",
        "default_model": "mistral-medium-latest",
        "recommended_models": ["mistral-medium-latest", "mistral-large-latest"],
        "supports_custom_base_url": False,
        "supports_managed_subscription": True,
        "notes": "Good for multilingual drafting, summaries, and educational writing support.",
    },
    {
        "provider_id": "cohere",
        "label": "Cohere",
        "sdk_package": "cohere",
        "docs_url": "https://docs.cohere.com/docs/chat-api",
        "default_model": "command-a-03-2025",
        "recommended_models": ["command-a-03-2025", "command-r-plus-08-2024"],
        "supports_custom_base_url": False,
        "supports_managed_subscription": True,
        "notes": "Useful for retrieval-grounded assistance, summarization, and report generation.",
    },
    {
        "provider_id": "xai",
        "label": "xAI",
        "sdk_package": "xai-sdk",
        "docs_url": "https://docs.x.ai/docs/sdk",
        "default_model": "grok-3-mini",
        "recommended_models": ["grok-3-mini", "grok-3"],
        "supports_custom_base_url": False,
        "supports_managed_subscription": True,
        "notes": "Useful for Grok-backed research assistance and planning flows.",
    },
)


class ProviderAIService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.root_dir = settings.studio_root_dir / "ai_control_plane"
        self.profiles_path = self.root_dir / "profiles.json"
        self.usage_path = self.root_dir / "usage_log.json"
        self.classroom_policies_path = self.root_dir / "classroom_policies.json"
        self.root_dir.mkdir(parents=True, exist_ok=True)
        if not self.profiles_path.exists():
            self._write_json(self.profiles_path, [])
        if not self.usage_path.exists():
            self._write_json(self.usage_path, [])
        if not self.classroom_policies_path.exists():
            self._write_json(self.classroom_policies_path, [])
        self._aes = AESGCM(self._derive_encryption_key(settings.educlawn_security_secret))

    def provider_catalog(self) -> list[dict[str, Any]]:
        entries = []
        for provider in PROVIDER_CATALOG:
            entry = dict(provider)
            entry["sdk_installed"] = self._sdk_installed(provider["provider_id"])
            entry["supported_tasks"] = list(SUPPORTED_PROVIDER_TASKS)
            entries.append(entry)
        return entries

    def list_profiles(self) -> list[dict[str, Any]]:
        profiles = [self._sanitize_profile(profile) for profile in self._load_profiles()]
        return sorted(profiles, key=lambda item: item["updated_at"], reverse=True)

    def list_classroom_policies(self) -> list[dict[str, Any]]:
        return sorted(self._load_json(self.classroom_policies_path), key=lambda item: item["updated_at"], reverse=True)

    def get_classroom_policy(self, classroom_id: str) -> dict[str, Any]:
        for policy in self.list_classroom_policies():
            if policy["classroom_id"] == classroom_id:
                return policy
        return self._default_classroom_policy(classroom_id)

    def upsert_classroom_policy(self, classroom_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        policies = self._load_json(self.classroom_policies_path)
        existing = next((policy for policy in policies if policy["classroom_id"] == classroom_id), None)
        now = self._timestamp()
        if existing is None:
            existing = self._default_classroom_policy(classroom_id)
            existing["created_at"] = now
            policies.insert(0, existing)
        if "daily_request_limit" in payload:
            existing["daily_request_limit"] = self._normalize_positive_int(payload["daily_request_limit"], "Daily request limit")
        if "monthly_budget_usd" in payload:
            existing["monthly_budget_usd"] = self._normalize_budget(payload["monthly_budget_usd"], "Monthly classroom budget")
        if "managed_subscription_allowed" in payload:
            existing["managed_subscription_allowed"] = bool(payload["managed_subscription_allowed"])
        if "allowed_profile_ids" in payload:
            existing["allowed_profile_ids"] = self._normalize_profile_ids(payload.get("allowed_profile_ids"))
        if "redact_student_pii" in payload:
            existing["redact_student_pii"] = bool(payload["redact_student_pii"])
        if "notes" in payload:
            existing["notes"] = str(payload.get("notes") or "").strip()[:280]
        existing["updated_at"] = now
        self._write_json(self.classroom_policies_path, policies)
        return existing

    def create_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        provider = self._catalog_by_id(str(payload["provider_id"]))
        api_key = str(payload.get("api_key") or "").strip()
        if len(api_key) < 8:
            raise ValueError("API key is required.")
        now = self._timestamp()
        profile = {
            "profile_id": f"ai-profile-{uuid4().hex[:10]}",
            "label": str(payload["label"]).strip(),
            "provider_id": provider["provider_id"],
            "auth_mode": self._normalize_auth_mode(str(payload.get("auth_mode") or "user-key")),
            "default_model": str(payload.get("default_model") or provider["default_model"]).strip(),
            "base_url": str(payload.get("base_url") or "").strip(),
            "capabilities": self._normalize_capabilities(payload.get("capabilities")),
            "enabled": bool(payload.get("enabled", True)),
            "daily_request_limit": self._normalize_positive_int(payload.get("daily_request_limit", 120), "Daily request limit"),
            "monthly_budget_usd": self._normalize_budget(payload.get("monthly_budget_usd", 20.0), "Monthly provider budget"),
            "fallback_profile_ids": self._normalize_profile_ids(payload.get("fallback_profile_ids")),
            "redaction_mode": self._normalize_redaction_mode(str(payload.get("redaction_mode") or "pii-lite")),
            "usage_cap_per_classroom_daily": self._normalize_positive_int(
                payload.get("usage_cap_per_classroom_daily", 40),
                "Per-classroom daily usage cap",
            ),
            "managed_subscription_note": str(payload.get("managed_subscription_note") or "").strip()[:240],
            "api_key_ciphertext": self._encrypt_secret(api_key),
            "api_key_hint": self._mask_secret(api_key),
            "created_at": now,
            "updated_at": now,
            "last_tested_at": "",
            "last_test_status": "never",
            "last_error": "",
        }
        profiles = self._load_profiles()
        profiles.insert(0, profile)
        self._write_json(self.profiles_path, profiles)
        return self._sanitize_profile(profile)

    def update_profile(self, profile_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        profiles = self._load_profiles()
        for profile in profiles:
            if profile["profile_id"] != profile_id:
                continue
            if "label" in payload:
                profile["label"] = str(payload["label"]).strip()
            if "auth_mode" in payload:
                profile["auth_mode"] = self._normalize_auth_mode(str(payload["auth_mode"]))
            if "default_model" in payload and str(payload["default_model"]).strip():
                profile["default_model"] = str(payload["default_model"]).strip()
            if "base_url" in payload:
                profile["base_url"] = str(payload.get("base_url") or "").strip()
            if "capabilities" in payload:
                profile["capabilities"] = self._normalize_capabilities(payload.get("capabilities"))
            if "enabled" in payload:
                profile["enabled"] = bool(payload["enabled"])
            if "daily_request_limit" in payload:
                profile["daily_request_limit"] = self._normalize_positive_int(payload["daily_request_limit"], "Daily request limit")
            if "monthly_budget_usd" in payload:
                profile["monthly_budget_usd"] = self._normalize_budget(payload["monthly_budget_usd"], "Monthly provider budget")
            if "fallback_profile_ids" in payload:
                profile["fallback_profile_ids"] = self._normalize_profile_ids(payload.get("fallback_profile_ids"), current_profile_id=profile_id)
            if "redaction_mode" in payload:
                profile["redaction_mode"] = self._normalize_redaction_mode(str(payload["redaction_mode"]))
            if "usage_cap_per_classroom_daily" in payload:
                profile["usage_cap_per_classroom_daily"] = self._normalize_positive_int(
                    payload["usage_cap_per_classroom_daily"],
                    "Per-classroom daily usage cap",
                )
            if "managed_subscription_note" in payload:
                profile["managed_subscription_note"] = str(payload.get("managed_subscription_note") or "").strip()[:240]
            if payload.get("api_key"):
                api_key = str(payload["api_key"]).strip()
                profile["api_key_ciphertext"] = self._encrypt_secret(api_key)
                profile["api_key_hint"] = self._mask_secret(api_key)
            profile["updated_at"] = self._timestamp()
            self._write_json(self.profiles_path, profiles)
            return self._sanitize_profile(profile)
        raise FileNotFoundError(profile_id)

    def delete_profile(self, profile_id: str) -> None:
        profiles = self._load_profiles()
        remaining = [profile for profile in profiles if profile["profile_id"] != profile_id]
        if len(remaining) == len(profiles):
            raise FileNotFoundError(profile_id)
        self._write_json(self.profiles_path, remaining)

    def test_profile(self, profile_id: str) -> dict[str, Any]:
        result = self.generate_with_profile(
            profile_id,
            task="research",
            prompt="Reply with READY and a one-sentence description of what this provider is good at for classrooms.",
            system_prompt="You are validating an educational workspace AI connection.",
            source="profile_test",
        )
        self._update_test_status(profile_id, result)
        return result

    def recent_usage(self, limit: int = 25) -> list[dict[str, Any]]:
        entries = self._load_json(self.usage_path)
        return entries[:limit]

    def get_profile_summary(self, profile_id: str) -> dict[str, Any]:
        for profile in self._load_profiles():
            if profile["profile_id"] == profile_id:
                return self._sanitize_profile(profile)
        raise FileNotFoundError(profile_id)

    def generate_with_profile(
        self,
        profile_id: str,
        *,
        task: str,
        prompt: str,
        system_prompt: str = "",
        source: str = "workspace",
        metadata: dict[str, Any] | None = None,
        classroom_id: str = "",
    ) -> dict[str, Any]:
        primary_profile = self._load_profile(profile_id)
        classroom_policy = self.get_classroom_policy(classroom_id) if classroom_id else None
        candidate_ids = self._candidate_profile_ids(primary_profile, classroom_policy)
        last_result = self._blocked_result(primary_profile, "No provider could be used.", classroom_id=classroom_id)

        for index, candidate_id in enumerate(candidate_ids):
            profile = self._load_profile(candidate_id)
            provider = self._catalog_by_id(profile["provider_id"])
            generated_at = self._timestamp()
            preflight_error = self._preflight_policy_error(
                profile=profile,
                task=task,
                prompt=prompt,
                classroom_policy=classroom_policy,
                classroom_id=classroom_id,
            )
            if preflight_error:
                last_result = self._blocked_result(
                    profile,
                    preflight_error,
                    classroom_id=classroom_id,
                    fallback_used=index > 0,
                )
                self._append_usage(
                    self._usage_entry(
                        profile=profile,
                        provider=provider,
                        source=source,
                        task=task,
                        prompt_preview=prompt[:180],
                        metadata=metadata or {},
                        created_at=generated_at,
                        classroom_id=classroom_id,
                        success=False,
                        error=preflight_error,
                        estimated_cost_usd=0.0,
                        redaction={"mode": profile.get("redaction_mode", "pii-lite"), "applied": False, "flags": []},
                        fallback_used=index > 0,
                    )
                )
                continue

            sanitized_prompt, sanitized_system_prompt, sanitized_metadata, redaction = self._redact_payload(
                prompt=prompt,
                system_prompt=system_prompt,
                metadata=metadata or {},
                redaction_mode=str(profile.get("redaction_mode") or "pii-lite"),
                redact_student_pii=bool((classroom_policy or {}).get("redact_student_pii", True)),
            )
            try:
                output_text = self._invoke_provider(
                    provider_id=profile["provider_id"],
                    api_key=self._decrypt_secret(profile["api_key_ciphertext"]),
                    model=profile["default_model"],
                    prompt=sanitized_prompt,
                    system_prompt=sanitized_system_prompt,
                    base_url=str(profile.get("base_url") or ""),
                ).strip()
                if not output_text:
                    raise RuntimeError("Provider returned an empty response.")
                estimated_cost = self._estimate_cost_usd(profile["provider_id"], profile["default_model"], sanitized_prompt, output_text)
                result = {
                    "used": True,
                    "generated_at": generated_at,
                    "provider_id": profile["provider_id"],
                    "provider_label": provider["label"],
                    "profile_id": profile["profile_id"],
                    "profile_label": profile["label"],
                    "auth_mode": profile["auth_mode"],
                    "model": profile["default_model"],
                    "output_text": output_text,
                    "error": "",
                    "effective_profile_id": profile["profile_id"],
                    "effective_profile_label": profile["label"],
                    "classroom_id": classroom_id,
                    "fallback_used": index > 0,
                    "estimated_cost_usd": estimated_cost,
                    "redaction": redaction,
                }
                self._append_usage(
                    self._usage_entry(
                        profile=profile,
                        provider=provider,
                        source=source,
                        task=task,
                        prompt_preview=sanitized_prompt[:180],
                        metadata=sanitized_metadata,
                        created_at=generated_at,
                        classroom_id=classroom_id,
                        success=True,
                        error="",
                        estimated_cost_usd=estimated_cost,
                        redaction=redaction,
                        fallback_used=index > 0,
                    )
                )
                return result
            except Exception as error:  # pragma: no cover - exercised through higher-level flows
                estimated_cost = self._estimate_cost_usd(profile["provider_id"], profile["default_model"], sanitized_prompt, "")
                last_result = {
                    "used": False,
                    "generated_at": generated_at,
                    "provider_id": profile["provider_id"],
                    "provider_label": provider["label"],
                    "profile_id": primary_profile["profile_id"],
                    "profile_label": primary_profile["label"],
                    "auth_mode": profile["auth_mode"],
                    "model": profile["default_model"],
                    "output_text": "",
                    "error": str(error),
                    "effective_profile_id": profile["profile_id"],
                    "effective_profile_label": profile["label"],
                    "classroom_id": classroom_id,
                    "fallback_used": index > 0,
                    "estimated_cost_usd": estimated_cost,
                    "redaction": redaction,
                }
                self._append_usage(
                    self._usage_entry(
                        profile=profile,
                        provider=provider,
                        source=source,
                        task=task,
                        prompt_preview=sanitized_prompt[:180],
                        metadata=sanitized_metadata,
                        created_at=generated_at,
                        classroom_id=classroom_id,
                        success=False,
                        error=str(error),
                        estimated_cost_usd=estimated_cost,
                        redaction=redaction,
                        fallback_used=index > 0,
                    )
                )
        return last_result

    def _invoke_provider(
        self,
        *,
        provider_id: str,
        api_key: str,
        model: str,
        prompt: str,
        system_prompt: str,
        base_url: str = "",
    ) -> str:
        if provider_id == "openai":
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url=base_url or None)
            response = client.responses.create(
                model=model,
                input=self._openai_input(system_prompt, prompt),
                max_output_tokens=900,
            )
            text = str(getattr(response, "output_text", "") or "").strip()
            if text:
                return text
            return json.dumps(response.model_dump(), indent=2)[:1200]

        if provider_id == "anthropic":
            from anthropic import Anthropic

            client = Anthropic(api_key=api_key, base_url=base_url or None)
            message = client.messages.create(
                model=model,
                max_tokens=900,
                system=system_prompt or None,
                messages=[{"role": "user", "content": prompt}],
            )
            return "\n".join(
                block.text for block in getattr(message, "content", []) if getattr(block, "type", "") == "text"
            ).strip()

        if provider_id == "google":
            from google import genai

            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model,
                contents=self._joined_prompt(system_prompt, prompt),
            )
            text = str(getattr(response, "text", "") or "").strip()
            if text:
                return text
            return json.dumps(getattr(response, "model_dump", lambda: {})(), indent=2)[:1200]

        if provider_id == "groq":
            from groq import Groq

            client = Groq(api_key=api_key, base_url=base_url or None)
            response = client.chat.completions.create(
                model=model,
                messages=self._chat_messages(system_prompt, prompt),
                temperature=0.2,
                max_tokens=900,
            )
            return str(response.choices[0].message.content or "").strip()

        if provider_id == "mistral":
            from mistralai import Mistral

            client = Mistral(api_key=api_key)
            response = client.chat.complete(
                model=model,
                messages=self._chat_messages(system_prompt, prompt),
            )
            content = response.choices[0].message.content
            if isinstance(content, list):
                return "\n".join(
                    str(part.get("text") or "")
                    for part in content
                    if isinstance(part, dict)
                ).strip()
            return str(content or "").strip()

        if provider_id == "cohere":
            import cohere

            client = cohere.ClientV2(api_key=api_key)
            response = client.chat(
                model=model,
                messages=self._chat_messages(system_prompt, prompt),
            )
            message = getattr(response, "message", None)
            content = getattr(message, "content", []) if message is not None else []
            collected = []
            for part in content:
                text = getattr(part, "text", "")
                if text:
                    collected.append(str(text))
            return "\n".join(collected).strip()

        if provider_id == "xai":
            from xai_sdk import Client
            from xai_sdk.chat import system as xai_system
            from xai_sdk.chat import user as xai_user

            client = Client(api_key=api_key)
            messages = []
            if system_prompt.strip():
                messages.append(xai_system(system_prompt.strip()))
            messages.append(xai_user(prompt))
            chat = client.chat.create(model=model, messages=messages)
            response = chat.sample()
            return str(getattr(response, "content", "") or "").strip()

        raise ValueError(f"Unsupported provider: {provider_id}")

    def _update_test_status(self, profile_id: str, result: dict[str, Any]) -> None:
        profiles = self._load_profiles()
        for profile in profiles:
            if profile["profile_id"] != profile_id:
                continue
            profile["last_tested_at"] = result["generated_at"]
            profile["last_test_status"] = "passed" if result["used"] else "failed"
            profile["last_error"] = str(result.get("error") or "")
            profile["updated_at"] = self._timestamp()
            self._write_json(self.profiles_path, profiles)
            return

    def _load_profile(self, profile_id: str) -> dict[str, Any]:
        for profile in self._load_profiles():
            if profile["profile_id"] == profile_id:
                return profile
        raise FileNotFoundError(profile_id)

    def _load_profiles(self) -> list[dict[str, Any]]:
        return self._load_json(self.profiles_path)

    def _sanitize_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        provider = self._catalog_by_id(profile["provider_id"])
        usage = self._profile_usage_summary(profile["profile_id"])
        return {
            "profile_id": profile["profile_id"],
            "label": profile["label"],
            "provider_id": profile["provider_id"],
            "provider_label": provider["label"],
            "auth_mode": profile["auth_mode"],
            "default_model": profile["default_model"],
            "base_url": profile.get("base_url") or "",
            "capabilities": list(profile.get("capabilities", [])),
            "enabled": bool(profile.get("enabled", True)),
            "daily_request_limit": int(profile.get("daily_request_limit", 120) or 0),
            "monthly_budget_usd": float(profile.get("monthly_budget_usd", 20.0) or 0.0),
            "fallback_profile_ids": list(profile.get("fallback_profile_ids", [])),
            "redaction_mode": str(profile.get("redaction_mode") or "pii-lite"),
            "usage_cap_per_classroom_daily": int(profile.get("usage_cap_per_classroom_daily", 40) or 0),
            "managed_subscription_note": str(profile.get("managed_subscription_note") or ""),
            "usage_summary": usage,
            "api_key_hint": profile.get("api_key_hint") or "",
            "sdk_installed": self._sdk_installed(profile["provider_id"]),
            "last_tested_at": profile.get("last_tested_at") or "",
            "last_test_status": profile.get("last_test_status") or "never",
            "last_error": profile.get("last_error") or "",
            "created_at": profile["created_at"],
            "updated_at": profile["updated_at"],
        }

    def _catalog_by_id(self, provider_id: str) -> dict[str, Any]:
        for provider in PROVIDER_CATALOG:
            if provider["provider_id"] == provider_id:
                return dict(provider)
        raise KeyError(provider_id)

    def _sdk_installed(self, provider_id: str) -> bool:
        module_name = {
            "openai": "openai",
            "anthropic": "anthropic",
            "google": "google.genai",
            "groq": "groq",
            "mistral": "mistralai",
            "cohere": "cohere",
            "xai": "xai_sdk",
        }[provider_id]
        return importlib.util.find_spec(module_name) is not None

    def _normalize_capabilities(self, raw_value: Any) -> list[str]:
        items = raw_value if isinstance(raw_value, list) else []
        normalized = []
        for item in items:
            value = str(item).strip().lower().replace("_", "-")
            if value in SUPPORTED_PROVIDER_TASKS and value not in normalized:
                normalized.append(value)
        return normalized or ["research", "assignments", "feedback"]

    def _normalize_profile_ids(self, raw_value: Any, *, current_profile_id: str = "") -> list[str]:
        items = raw_value if isinstance(raw_value, list) else []
        known = {profile["profile_id"] for profile in self._load_profiles()}
        normalized: list[str] = []
        for item in items:
            value = str(item).strip()
            if not value or value == current_profile_id:
                continue
            if value not in known:
                raise ValueError(f"Unknown fallback profile: {value}")
            if value not in normalized:
                normalized.append(value)
        return normalized

    def _normalize_redaction_mode(self, redaction_mode: str) -> str:
        if redaction_mode not in SUPPORTED_REDACTION_MODES:
            raise ValueError("Unsupported redaction mode.")
        return redaction_mode

    def _normalize_positive_int(self, value: Any, label: str) -> int:
        number = int(value)
        if number < 1:
            raise ValueError(f"{label} must be at least 1.")
        return number

    def _normalize_budget(self, value: Any, label: str) -> float:
        number = round(float(value), 2)
        if number <= 0:
            raise ValueError(f"{label} must be greater than 0.")
        return number

    def _normalize_auth_mode(self, auth_mode: str) -> str:
        if auth_mode not in {"user-key", "managed-subscription"}:
            raise ValueError("Unsupported auth mode.")
        return auth_mode

    def _derive_encryption_key(self, secret: str) -> bytes:
        seed = f"{secret}|educlawn-provider-ai".encode("utf-8")
        return hashlib.sha256(seed).digest()

    def _encrypt_secret(self, value: str) -> str:
        nonce = os.urandom(12)
        ciphertext = self._aes.encrypt(nonce, value.encode("utf-8"), None)
        return base64.b64encode(nonce + ciphertext).decode("utf-8")

    def _decrypt_secret(self, value: str) -> str:
        raw = base64.b64decode(value.encode("utf-8"))
        nonce, ciphertext = raw[:12], raw[12:]
        return self._aes.decrypt(nonce, ciphertext, None).decode("utf-8")

    def _mask_secret(self, value: str) -> str:
        trimmed = value.strip()
        if len(trimmed) <= 8:
            return "*" * len(trimmed)
        return f"{trimmed[:4]}...{trimmed[-4:]}"

    def _append_usage(self, entry: dict[str, Any]) -> None:
        entries = self._load_json(self.usage_path)
        entries.insert(0, entry)
        self._write_json(self.usage_path, entries[:240])

    def _usage_entry(
        self,
        *,
        profile: dict[str, Any],
        provider: dict[str, Any],
        source: str,
        task: str,
        prompt_preview: str,
        metadata: dict[str, Any],
        created_at: str,
        classroom_id: str,
        success: bool,
        error: str,
        estimated_cost_usd: float,
        redaction: dict[str, Any],
        fallback_used: bool,
    ) -> dict[str, Any]:
        return {
            "usage_id": f"ai-usage-{uuid4().hex[:10]}",
            "source": source,
            "task": task,
            "provider_id": profile["provider_id"],
            "provider_label": provider["label"],
            "profile_id": profile["profile_id"],
            "profile_label": profile["label"],
            "auth_mode": profile["auth_mode"],
            "model": profile["default_model"],
            "success": success,
            "error": error,
            "prompt_preview": prompt_preview,
            "metadata": metadata,
            "created_at": created_at,
            "classroom_id": classroom_id,
            "estimated_cost_usd": estimated_cost_usd,
            "redaction": redaction,
            "fallback_used": fallback_used,
        }

    def _candidate_profile_ids(self, profile: dict[str, Any], classroom_policy: dict[str, Any] | None) -> list[str]:
        candidates = [profile["profile_id"], *profile.get("fallback_profile_ids", [])]
        allowed = set((classroom_policy or {}).get("allowed_profile_ids", []))
        if allowed:
            candidates = [candidate for candidate in candidates if candidate in allowed]
        ordered: list[str] = []
        for candidate in candidates:
            if candidate not in ordered:
                ordered.append(candidate)
        return ordered

    def _preflight_policy_error(
        self,
        *,
        profile: dict[str, Any],
        task: str,
        prompt: str,
        classroom_policy: dict[str, Any] | None,
        classroom_id: str,
    ) -> str:
        if not bool(profile.get("enabled", True)):
            return "Provider profile is disabled."
        if task not in profile.get("capabilities", []):
            return f"Provider profile does not allow task '{task}'."
        if profile["auth_mode"] == "managed-subscription" and classroom_policy and not classroom_policy.get("managed_subscription_allowed", True):
            return "Managed subscriptions are disabled for this classroom."

        entries = self._load_json(self.usage_path)
        now = datetime.now(UTC)
        profile_daily_count = self._usage_count(entries, now, profile_id=profile["profile_id"])
        if profile_daily_count >= int(profile.get("daily_request_limit", 120) or 0):
            return "Provider profile daily request limit reached."

        classroom_daily_limit = int(profile.get("usage_cap_per_classroom_daily", 40) or 0)
        if classroom_id and self._usage_count(entries, now, classroom_id=classroom_id) >= classroom_daily_limit:
            return "Per-classroom daily usage cap reached for this profile."

        if classroom_policy and classroom_id:
            if self._usage_count(entries, now, classroom_id=classroom_id) >= int(classroom_policy["daily_request_limit"]):
                return "Classroom daily request limit reached."

        estimated_prompt_cost = self._estimate_cost_usd(profile["provider_id"], profile["default_model"], prompt, "")
        monthly_spend = self._usage_spend(entries, now, profile_id=profile["profile_id"])
        if monthly_spend + estimated_prompt_cost > float(profile.get("monthly_budget_usd", 20.0) or 0.0):
            return "Provider monthly budget reached."

        if classroom_policy and classroom_id:
            classroom_spend = self._usage_spend(entries, now, classroom_id=classroom_id)
            if classroom_spend + estimated_prompt_cost > float(classroom_policy["monthly_budget_usd"]):
                return "Classroom monthly AI budget reached."
        return ""

    def _usage_count(
        self,
        entries: list[dict[str, Any]],
        now: datetime,
        *,
        profile_id: str = "",
        classroom_id: str = "",
    ) -> int:
        return sum(
            1
            for entry in entries
            if self._matches_day(entry.get("created_at", ""), now)
            and (not profile_id or entry.get("profile_id") == profile_id)
            and (not classroom_id or entry.get("classroom_id") == classroom_id)
        )

    def _usage_spend(
        self,
        entries: list[dict[str, Any]],
        now: datetime,
        *,
        profile_id: str = "",
        classroom_id: str = "",
    ) -> float:
        return round(
            sum(
                float(entry.get("estimated_cost_usd") or 0.0)
                for entry in entries
                if self._matches_month(entry.get("created_at", ""), now)
                and (not profile_id or entry.get("profile_id") == profile_id)
                and (not classroom_id or entry.get("classroom_id") == classroom_id)
            ),
            4,
        )

    def _matches_day(self, raw_timestamp: str, now: datetime) -> bool:
        try:
            timestamp = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
        except ValueError:
            return False
        return timestamp.astimezone(UTC).date() == now.date()

    def _matches_month(self, raw_timestamp: str, now: datetime) -> bool:
        try:
            timestamp = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
        except ValueError:
            return False
        timestamp = timestamp.astimezone(UTC)
        return timestamp.year == now.year and timestamp.month == now.month

    def _estimate_cost_usd(self, provider_id: str, model: str, prompt: str, output_text: str) -> float:
        estimated_tokens = max(1, (len(prompt) + len(output_text) + len(model)) // 4)
        rate = PROVIDER_COST_HINTS_USD_PER_1K_TOKENS.get(provider_id, 0.01)
        return round((estimated_tokens / 1000.0) * rate, 4)

    def _redact_payload(
        self,
        *,
        prompt: str,
        system_prompt: str,
        metadata: dict[str, Any],
        redaction_mode: str,
        redact_student_pii: bool,
    ) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
        sanitized_metadata = dict(metadata)
        flags: list[str] = []
        sanitized_prompt = prompt
        sanitized_system_prompt = system_prompt

        if redaction_mode in {"metadata-only", "pii-lite"}:
            for key in ("student_name", "teacher_name", "family_name", "reviewer_name", "email", "phone"):
                if key in sanitized_metadata and sanitized_metadata[key]:
                    sanitized_metadata[key] = "[redacted]"
                    flags.append(f"metadata:{key}")

        if redaction_mode == "pii-lite" and redact_student_pii:
            sanitized_prompt, prompt_flags = self._redact_text(prompt)
            sanitized_system_prompt, system_flags = self._redact_text(system_prompt)
            flags.extend(prompt_flags)
            flags.extend(system_flags)

        return (
            sanitized_prompt,
            sanitized_system_prompt,
            sanitized_metadata,
            {
                "mode": redaction_mode,
                "applied": bool(flags),
                "flags": sorted(set(flags)),
            },
        )

    def _redact_text(self, text: str) -> tuple[str, list[str]]:
        updated = text
        flags: list[str] = []
        substitutions = [
            (r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[redacted_email]", "email"),
            (r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){2}\d{4}\b", "[redacted_phone]", "phone"),
            (r"\b\d{6,}\b", "[redacted_number]", "long-number"),
            (r"\b(student|teacher|family|reviewer)\s*[:\-]\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}", r"\1: [redacted_name]", "role-name"),
        ]
        for pattern, replacement, label in substitutions:
            next_text, count = re.subn(pattern, replacement, updated, flags=re.IGNORECASE)
            if count:
                flags.append(label)
                updated = next_text
        return updated, flags

    def _blocked_result(
        self,
        profile: dict[str, Any],
        error: str,
        *,
        classroom_id: str = "",
        fallback_used: bool = False,
    ) -> dict[str, Any]:
        provider = self._catalog_by_id(profile["provider_id"])
        generated_at = self._timestamp()
        return {
            "used": False,
            "generated_at": generated_at,
            "provider_id": profile["provider_id"],
            "provider_label": provider["label"],
            "profile_id": profile["profile_id"],
            "profile_label": profile["label"],
            "auth_mode": profile["auth_mode"],
            "model": profile["default_model"],
            "output_text": "",
            "error": error,
            "effective_profile_id": profile["profile_id"],
            "effective_profile_label": profile["label"],
            "classroom_id": classroom_id,
            "fallback_used": fallback_used,
            "estimated_cost_usd": 0.0,
            "redaction": {"mode": str(profile.get("redaction_mode") or "pii-lite"), "applied": False, "flags": []},
        }

    def _default_classroom_policy(self, classroom_id: str) -> dict[str, Any]:
        now = self._timestamp()
        return {
            "classroom_id": classroom_id,
            "daily_request_limit": 60,
            "monthly_budget_usd": 35.0,
            "managed_subscription_allowed": True,
            "allowed_profile_ids": [],
            "redact_student_pii": True,
            "notes": "",
            "created_at": now,
            "updated_at": now,
        }

    def _profile_usage_summary(self, profile_id: str) -> dict[str, Any]:
        entries = self._load_json(self.usage_path)
        now = datetime.now(UTC)
        return {
            "requests_today": self._usage_count(entries, now, profile_id=profile_id),
            "spend_this_month_usd": self._usage_spend(entries, now, profile_id=profile_id),
        }

    def _openai_input(self, system_prompt: str, prompt: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if system_prompt.strip():
            items.append(
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt.strip()}],
                }
            )
        items.append(
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        )
        return items

    def _chat_messages(self, system_prompt: str, prompt: str) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _joined_prompt(self, system_prompt: str, prompt: str) -> str:
        if not system_prompt.strip():
            return prompt
        return f"{system_prompt.strip()}\n\n{prompt}"

    def _timestamp(self) -> str:
        return datetime.now(UTC).isoformat()

    def _load_json(self, path: Path) -> list[dict[str, Any]]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_json(self, path: Path, payload: list[dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
