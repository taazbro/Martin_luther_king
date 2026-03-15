from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.api.education_schemas import EducationAssignment, EducationClassroomResponse, EducationMaterial
from app.api.studio_schemas import ProjectExportResponse, StudioPluginSummary, StudioProjectResponse, StudioSampleProject, StudioTemplateSummary


RuntimeMode = Literal["no-llm", "local-llm", "provider-ai"]
ReviewDecision = Literal["approved", "rejected"]


class GrowthRouteProvider(BaseModel):
    provider_id: str
    provider_label: str
    profile_id: str
    profile_label: str
    auth_mode: str
    model: str


class GrowthRouteDecision(BaseModel):
    task_kind: str
    execution_mode: RuntimeMode
    required_capability: str
    reason: str
    selected_provider: GrowthRouteProvider | None = None
    local_available: bool
    provider_available: bool


class AssignmentAutopilotRequest(BaseModel):
    classroom_id: str = Field(min_length=3, max_length=120)
    access_key: str = Field(min_length=8, max_length=200)
    topic: str = Field(min_length=3, max_length=200)
    title: str = Field(default="", max_length=160)
    summary: str = Field(default="", max_length=500)
    audience: str = Field(default="", max_length=120)
    template_id: str = Field(default="", max_length=120)
    goals: list[str] = Field(default_factory=list)
    rubric: list[str] = Field(default_factory=list)
    standards: list[str] = Field(default_factory=list)
    lesson_seed: str = Field(default="", max_length=2400)
    due_date: str = Field(default="", max_length=80)
    local_mode: RuntimeMode | None = None
    ai_profile_id: str = Field(default="", max_length=120)


class AssessmentPackResponse(BaseModel):
    assignment_id: str
    assignment_title: str
    route: GrowthRouteDecision
    quiz_questions: list[dict[str, Any]]
    discussion_prompts: list[str]
    exit_tickets: list[str]
    differentiated_supports: list[dict[str, Any]]
    teacher_note: str


class StandardsMapResponse(BaseModel):
    classroom_id: str
    assignment_id: str
    assignment_title: str
    standards_alignment: list[dict[str, Any]]
    district_rubric_map: list[dict[str, Any]]
    teacher_moves: list[str]


class AssignmentAutopilotResponse(BaseModel):
    classroom: EducationClassroomResponse
    assignment: EducationAssignment
    route: GrowthRouteDecision
    evidence_pack: list[EducationMaterial]
    checkpoints: list[dict[str, Any]]
    export_targets: list[str]
    assessment_pack: AssessmentPackResponse
    standards_map: StandardsMapResponse
    lesson_to_project_scaffold: dict[str, Any]
    teacher_summary: str


class AssessmentPackRequest(BaseModel):
    classroom_id: str = Field(min_length=3, max_length=120)
    assignment_id: str = Field(min_length=3, max_length=120)
    access_key: str = Field(min_length=8, max_length=200)
    ai_profile_id: str = Field(default="", max_length=120)


class RevisionCoachRequest(BaseModel):
    classroom_id: str = Field(min_length=3, max_length=120)
    assignment_id: str = Field(min_length=3, max_length=120)
    access_key: str = Field(min_length=8, max_length=200)
    draft_text: str = Field(min_length=20, max_length=12000)
    rubric: list[str] = Field(default_factory=list)
    teacher_feedback: list[str] = Field(default_factory=list)
    project_slug: str = Field(default="", max_length=160)
    ai_profile_id: str = Field(default="", max_length=120)


class CitationVerificationResponse(BaseModel):
    ready_for_export: bool
    overall_score: float
    verified_claims: list[dict[str, Any]]
    blocked_claims: list[dict[str, Any]]


class RevisionCoachResponse(BaseModel):
    route: GrowthRouteDecision
    rubric_breakdown: list[dict[str, Any]]
    citation_verification: CitationVerificationResponse
    revision_tasks: list[str]
    student_summary: str
    family_summary: str


class LibraryPromoteRequest(BaseModel):
    access_key: str = Field(min_length=8, max_length=200)
    material_ids: list[str] = Field(default_factory=list)


class ClassroomLibraryResponse(BaseModel):
    classroom_id: str
    teacher_name: str
    item_count: int
    collections: list[dict[str, Any]]
    reusable_items: list[dict[str, Any]]
    recommended_reuse: list[dict[str, Any]]


class PeerReviewCreateRequest(BaseModel):
    classroom_id: str = Field(min_length=3, max_length=120)
    assignment_id: str = Field(min_length=3, max_length=120)
    reviewer_student_id: str = Field(min_length=3, max_length=120)
    target_student_id: str = Field(min_length=3, max_length=120)
    access_key: str = Field(min_length=8, max_length=200)
    draft_text: str = Field(min_length=20, max_length=8000)
    rubric: list[str] = Field(default_factory=list)
    project_slug: str = Field(default="", max_length=160)


class PeerReviewResolveRequest(BaseModel):
    decision: ReviewDecision
    reviewer: str = Field(min_length=2, max_length=120)
    note: str = Field(default="", max_length=500)
    access_key: str = Field(min_length=8, max_length=200)


class PeerReviewResponse(BaseModel):
    review_id: str
    classroom_id: str
    assignment_id: str
    project_slug: str
    reviewer_student_id: str
    reviewer_name: str
    target_student_id: str
    target_student_name: str
    status: str
    summary: str
    rubric_guided_comments: list[dict[str, Any]]
    created_at: str
    resolved_at: str
    moderator: str
    note: str
    approval_id: str


class PeerReviewPairingsResponse(BaseModel):
    classroom_id: str
    assignment_id: str
    assignment_title: str
    pair_count: int
    pairs: list[dict[str, Any]]


class FamilyViewResponse(BaseModel):
    classroom_id: str
    classroom_title: str
    project_slug: str
    project_title: str
    student_name: str
    assignment_title: str
    summary: str
    progress: dict[str, Any]
    teacher_comments: list[dict[str, Any]]
    next_steps: list[str]
    downloads: list[ProjectExportResponse]
    share_link: str


class FamilyShareLinkResponse(BaseModel):
    share_token: str
    classroom_id: str
    project_slug: str
    project_title: str
    created_at: str
    share_url: str


class CitationVerifyRequest(BaseModel):
    project_slug: str = Field(default="", max_length=160)
    claims: list[str] = Field(default_factory=list)


class LessonToProjectRequest(BaseModel):
    lesson_plan: str = Field(min_length=20, max_length=12000)
    title: str = Field(default="", max_length=160)
    topic: str = Field(default="", max_length=200)
    audience: str = Field(default="", max_length=120)
    goals: list[str] = Field(default_factory=list)
    rubric: list[str] = Field(default_factory=list)
    template_id: str = Field(default="", max_length=120)
    local_mode: RuntimeMode = "no-llm"
    ai_profile_id: str = Field(default="", max_length=120)
    classroom_id: str = Field(default="", max_length=120)
    access_key: str = Field(default="", max_length=200)
    seed_from_classroom: bool = True


class LessonToProjectResponse(BaseModel):
    project: StudioProjectResponse
    route: GrowthRouteDecision
    scaffold: dict[str, Any]


class RubricTrainRequest(BaseModel):
    classroom_id: str = Field(min_length=3, max_length=120)
    access_key: str = Field(min_length=8, max_length=200)
    project_slugs: list[str] = Field(default_factory=list)


class RubricTrainResponse(BaseModel):
    model_id: str
    classroom_id: str
    created_at: str
    trained_on_projects: list[str]
    criterion_patterns: list[dict[str, Any]]
    quality_signals: list[str]


class InterventionDashboardResponse(BaseModel):
    classroom_id: str
    classroom_title: str
    summary: dict[str, Any]
    student_signals: list[dict[str, Any]]
    interventions: list[str]


class ClassroomRosterResponse(BaseModel):
    classroom_id: str
    classroom_title: str
    students: list[dict[str, Any]]
    summary: dict[str, int]


class ClassroomReplayResponse(BaseModel):
    classroom_id: str
    classroom_title: str
    counts: dict[str, int]
    timeline: list[dict[str, Any]]


class AssignmentStatusBoardResponse(BaseModel):
    classroom_id: str
    classroom_title: str
    assignments: list[dict[str, Any]]


class MarketplaceSchoolPack(BaseModel):
    pack_id: str
    label: str
    audience: str
    description: str
    recommended_template_ids: list[str]
    sample_project_slug: str
    plugin_ids: list[str]
    offline_ready: bool
    installed: bool
    installed_at: str
    manifest_path: str


class MarketplaceResponse(BaseModel):
    templates: list[StudioTemplateSummary]
    sample_projects: list[StudioSampleProject]
    plugins: list[StudioPluginSummary]
    school_packs: list[MarketplaceSchoolPack]
    plugin_sdk: dict[str, Any]
    offline_school_edition: dict[str, Any]


class SchoolPackInstallResponse(BaseModel):
    pack_id: str
    label: str
    installed_at: str
    manifest_path: str
    created_samples: list[str]
    recommended_templates: list[str]


class OfflineSchoolEditionResponse(BaseModel):
    edition_name: str
    readiness_score: float
    supported_modes: list[str]
    local_capabilities: dict[str, bool]
    recommended_rollout: list[str]
    installed_assets: list[str]


class EducationGrowthOverviewResponse(BaseModel):
    counts: dict[str, int]
    routing_matrix: list[dict[str, Any]]
    offline_school_edition: OfflineSchoolEditionResponse
