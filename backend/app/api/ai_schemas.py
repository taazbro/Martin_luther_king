from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


AIProviderId = Literal["openai", "anthropic", "google", "groq", "mistral", "cohere", "xai"]
AIAuthMode = Literal["user-key", "managed-subscription"]
AITaskCapability = Literal["research", "assignments", "feedback", "planning", "review", "export", "classroom"]
AIRedactionMode = Literal["off", "metadata-only", "pii-lite"]


class AIProviderCatalogEntry(BaseModel):
    provider_id: AIProviderId
    label: str
    sdk_package: str
    docs_url: str
    default_model: str
    recommended_models: list[str]
    supports_custom_base_url: bool
    supports_managed_subscription: bool
    notes: str
    sdk_installed: bool
    supported_tasks: list[AITaskCapability]


class AIProviderProfileCreateRequest(BaseModel):
    label: str = Field(min_length=2, max_length=120)
    provider_id: AIProviderId
    auth_mode: AIAuthMode = "user-key"
    api_key: str = Field(min_length=8, max_length=500)
    default_model: str = Field(min_length=2, max_length=120)
    base_url: str = Field(default="", max_length=300)
    capabilities: list[AITaskCapability] = Field(default_factory=list)
    enabled: bool = True
    daily_request_limit: int = Field(default=120, ge=1, le=5000)
    monthly_budget_usd: float = Field(default=20.0, gt=0, le=10000)
    fallback_profile_ids: list[str] = Field(default_factory=list)
    redaction_mode: AIRedactionMode = "pii-lite"
    usage_cap_per_classroom_daily: int = Field(default=40, ge=1, le=5000)
    managed_subscription_note: str = Field(default="", max_length=240)


class AIProviderProfileUpdateRequest(BaseModel):
    label: str | None = Field(default=None, min_length=2, max_length=120)
    auth_mode: AIAuthMode | None = None
    api_key: str | None = Field(default=None, min_length=8, max_length=500)
    default_model: str | None = Field(default=None, min_length=2, max_length=120)
    base_url: str | None = Field(default=None, max_length=300)
    capabilities: list[AITaskCapability] | None = None
    enabled: bool | None = None
    daily_request_limit: int | None = Field(default=None, ge=1, le=5000)
    monthly_budget_usd: float | None = Field(default=None, gt=0, le=10000)
    fallback_profile_ids: list[str] | None = None
    redaction_mode: AIRedactionMode | None = None
    usage_cap_per_classroom_daily: int | None = Field(default=None, ge=1, le=5000)
    managed_subscription_note: str | None = Field(default=None, max_length=240)


class AIProviderUsageSummary(BaseModel):
    requests_today: int
    spend_this_month_usd: float


class AIProviderProfileResponse(BaseModel):
    profile_id: str
    label: str
    provider_id: AIProviderId
    provider_label: str
    auth_mode: AIAuthMode
    default_model: str
    base_url: str
    capabilities: list[AITaskCapability]
    enabled: bool
    daily_request_limit: int
    monthly_budget_usd: float
    fallback_profile_ids: list[str]
    redaction_mode: AIRedactionMode
    usage_cap_per_classroom_daily: int
    managed_subscription_note: str
    usage_summary: AIProviderUsageSummary
    api_key_hint: str
    sdk_installed: bool
    last_tested_at: str
    last_test_status: str
    last_error: str
    created_at: str
    updated_at: str


class AIProviderTestResponse(BaseModel):
    used: bool
    generated_at: str
    provider_id: AIProviderId
    provider_label: str
    profile_id: str
    profile_label: str
    auth_mode: AIAuthMode
    model: str
    output_text: str
    error: str
    effective_profile_id: str
    effective_profile_label: str
    classroom_id: str
    fallback_used: bool
    estimated_cost_usd: float
    redaction: dict[str, object]


class AIClassroomPolicyRequest(BaseModel):
    daily_request_limit: int = Field(default=60, ge=1, le=5000)
    monthly_budget_usd: float = Field(default=35.0, gt=0, le=10000)
    managed_subscription_allowed: bool = True
    allowed_profile_ids: list[str] = Field(default_factory=list)
    redact_student_pii: bool = True
    notes: str = Field(default="", max_length=280)


class AIClassroomPolicyResponse(BaseModel):
    classroom_id: str
    daily_request_limit: int
    monthly_budget_usd: float
    managed_subscription_allowed: bool
    allowed_profile_ids: list[str]
    redact_student_pii: bool
    notes: str
    created_at: str
    updated_at: str


class AIUsageEntry(BaseModel):
    usage_id: str
    source: str
    task: str
    provider_id: AIProviderId
    provider_label: str
    profile_id: str
    profile_label: str
    auth_mode: AIAuthMode
    model: str
    success: bool
    error: str
    prompt_preview: str
    metadata: dict[str, object]
    created_at: str
    classroom_id: str
    estimated_cost_usd: float
    redaction: dict[str, object]
    fallback_used: bool
