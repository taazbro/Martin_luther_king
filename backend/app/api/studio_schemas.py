from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


StudioAgentName = Literal["research", "planner", "writer", "historian", "citation", "design", "qa", "teacher", "export"]


class StudioTemplateSummary(BaseModel):
    id: str
    label: str
    description: str
    project_type: str
    category: str
    supports_simulation: bool
    layout_direction: str
    export_targets: list[str]
    starter_prompts: list[str]
    theme_tokens: dict[str, str]
    sections: list[dict[str, str]]
    workflow: list[dict[str, object]]


class StudioPluginSummary(BaseModel):
    id: str
    label: str
    version: str
    description: str
    capabilities: list[str]


class StudioSampleProject(BaseModel):
    title: str
    slug: str
    template_id: str
    summary: str


class StudioOverviewResponse(BaseModel):
    studio_name: str
    local_modes: list[dict[str, object]]
    install_modes: list[dict[str, object]]
    counts: dict[str, int]
    templates: list[StudioTemplateSummary]
    sample_projects: list[StudioSampleProject]
    plugins: list[StudioPluginSummary]


class StudioProjectCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=140)
    summary: str = Field(default="", max_length=400)
    topic: str = Field(min_length=3, max_length=200)
    audience: str = Field(min_length=3, max_length=120)
    goals: list[str] = Field(default_factory=list)
    rubric: list[str] = Field(default_factory=list)
    template_id: str = Field(min_length=3, max_length=120)
    local_mode: Literal["no-llm", "local-llm", "provider-ai"] = "no-llm"
    ai_profile_id: str = Field(default="", max_length=120)
    slug: str | None = None


class StudioProjectCloneRequest(BaseModel):
    title: str = Field(min_length=3, max_length=140)


class WorkflowStage(BaseModel):
    stage_id: str
    label: str
    description: str
    enabled: bool


class StudioProjectUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=140)
    summary: str | None = Field(default=None, max_length=400)
    topic: str | None = Field(default=None, min_length=3, max_length=200)
    audience: str | None = Field(default=None, min_length=3, max_length=120)
    goals: list[str] | None = None
    rubric: list[str] | None = None
    local_mode: Literal["no-llm", "local-llm", "provider-ai"] | None = None
    ai_profile_id: str | None = Field(default=None, max_length=120)
    theme_tokens: dict[str, str] | None = None
    sections: list[dict[str, object]] | None = None
    workflow: dict[str, list[WorkflowStage]] | None = None


class ProjectDocumentResponse(BaseModel):
    document_id: str
    title: str
    file_name: str
    content_type: str
    source_path: str
    citation_label: str
    summary: str
    word_count: int
    reading_level: str
    entities: list[str]
    years: list[str]
    chunk_count: int
    duplicate_similarity: float
    extraction_method: str
    ocr_status: str
    uploaded_at: str
    knowledge_graph_nodes: int | None = None


class ProjectExportResponse(BaseModel):
    export_type: str
    path: str
    created_at: str


class RevisionEntry(BaseModel):
    revision_id: str
    action: str
    summary: str
    actor: str
    created_at: str


class TeacherComment(BaseModel):
    comment_id: str
    author: str
    criterion: str
    body: str
    created_at: str


class StandardsAlignmentEntry(BaseModel):
    standard_id: str
    label: str
    reason: str


class StudioProjectSummaryResponse(BaseModel):
    project_id: str
    slug: str
    title: str
    summary: str
    topic: str
    audience: str
    template_id: str
    template_label: str
    project_type: str
    local_mode: str
    ai_profile_id: str = ""
    status: str
    document_count: int
    export_count: int
    documents: list[ProjectDocumentResponse]
    exports: list[ProjectExportResponse]
    submission_readiness: dict[str, object]
    updated_at: str


class StudioProjectResponse(BaseModel):
    version: str
    project_id: str
    slug: str
    title: str
    summary: str
    topic: str
    audience: str
    goals: list[str]
    rubric: list[str]
    template_id: str
    template_label: str
    project_type: str
    local_mode: str
    ai_profile_id: str = ""
    status: str
    created_at: str
    updated_at: str
    theme_tokens: dict[str, str]
    workflow: dict[str, list[WorkflowStage]]
    sections: list[dict[str, object]]
    documents: list[ProjectDocumentResponse]
    artifacts: dict[str, object]
    exports: list[ProjectExportResponse]
    teacher_review: dict[str, object] | None = None
    teacher_comments: list[TeacherComment]
    provenance: dict[str, object]
    simulation: dict[str, object]
    standards_alignment: list[StandardsAlignmentEntry]
    revision_history: list[RevisionEntry]
    plugin_ids: list[str]
    template: dict[str, object]
    plugins: list[dict[str, object]]
    classroom_context: dict[str, object]
    quality_gates: dict[str, object]
    submission_readiness: dict[str, object]


class StudioSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=240)
    limit: int = Field(default=6, ge=1, le=20)


class StudioSearchResult(BaseModel):
    chunk_id: str
    document_id: str
    citation_label: str
    excerpt: str
    score: float
    match_reason: str


class StudioGraphResponse(BaseModel):
    nodes: list[dict[str, object]]
    edges: list[dict[str, object]]
    highlights: list[str]


class StudioAgentCatalogEntry(BaseModel):
    name: StudioAgentName
    display_name: str
    role: str
    description: str


class StudioAgentInsight(BaseModel):
    agent_name: StudioAgentName
    display_name: str
    role: str
    summary: str
    confidence: float
    priority: Literal["low", "medium", "high"]
    signals: list[str]
    actions: list[str]


class StudioArtifactBundleResponse(BaseModel):
    generated_at: str
    runtime_mode: dict[str, object]
    agents: list[StudioAgentInsight]
    artifacts: dict[str, object]


class StudioCompileRequest(BaseModel):
    stages: list[WorkflowStage] | None = None


class StudioTeacherCommentRequest(BaseModel):
    author: str = Field(default="teacher", min_length=2, max_length=80)
    body: str = Field(min_length=3, max_length=1200)
    criterion: str = Field(default="", max_length=120)


class StudioSystemStatusResponse(BaseModel):
    workspace_root: str
    frontend_dist: str
    startup: dict[str, object]
    tools: dict[str, object]
    local_ai: dict[str, object]
    provider_ai: dict[str, object]
    portability: dict[str, object]
    release: dict[str, object]


class StudioCompileResponse(BaseModel):
    project: StudioProjectResponse
    workflow_results: list[dict[str, object]]
    retrieval_results: list[StudioSearchResult]
    knowledge_graph: StudioGraphResponse
    artifacts: StudioArtifactBundleResponse | None = None
    exports: list[ProjectExportResponse]
