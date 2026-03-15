from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.api.studio_schemas import (
    ProjectDocumentResponse,
    ProjectExportResponse,
    StudioAgentCatalogEntry,
    StudioArtifactBundleResponse,
    StudioCompileRequest,
    StudioCompileResponse,
    StudioGraphResponse,
    StudioOverviewResponse,
    StudioProjectCloneRequest,
    StudioProjectCreateRequest,
    StudioProjectResponse,
    StudioProjectSummaryResponse,
    StudioSystemStatusResponse,
    StudioTeacherCommentRequest,
    StudioProjectUpdateRequest,
    StudioSearchRequest,
    StudioSearchResult,
    StudioTemplateSummary,
)


router = APIRouter()


@router.get("/api/v1/studio/overview", response_model=StudioOverviewResponse)
def studio_overview(request: Request) -> StudioOverviewResponse:
    studio_service = request.app.state.studio_service
    return StudioOverviewResponse(**studio_service.get_overview())


@router.get("/api/v1/studio/system/status", response_model=StudioSystemStatusResponse)
def studio_system_status(request: Request) -> StudioSystemStatusResponse:
    studio_service = request.app.state.studio_service
    return StudioSystemStatusResponse(**studio_service.get_system_status(request.app.state.startup_status))


@router.get("/api/v1/studio/templates", response_model=list[StudioTemplateSummary])
def studio_templates(request: Request) -> list[StudioTemplateSummary]:
    templates = request.app.state.template_registry.list_templates()
    return [StudioTemplateSummary(**template) for template in templates]


@router.get("/api/v1/studio/agents/catalog", response_model=list[StudioAgentCatalogEntry])
def studio_agent_catalog(request: Request) -> list[StudioAgentCatalogEntry]:
    catalog = request.app.state.studio_agent_runtime.catalog()
    return [StudioAgentCatalogEntry(**entry) for entry in catalog]


@router.get("/api/v1/studio/projects", response_model=list[StudioProjectSummaryResponse])
def list_projects(request: Request) -> list[StudioProjectSummaryResponse]:
    studio_service = request.app.state.studio_service
    return [StudioProjectSummaryResponse(**project) for project in studio_service.list_projects()]


@router.post("/api/v1/studio/projects", response_model=StudioProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: StudioProjectCreateRequest, request: Request) -> StudioProjectResponse:
    studio_service = request.app.state.studio_service
    try:
        project = studio_service.create_project(payload.model_dump())
    except KeyError as error:
        raise HTTPException(status_code=404, detail=f"Template not found: {error.args[0]}") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return StudioProjectResponse(**project)


@router.post("/api/v1/studio/projects/import", response_model=StudioProjectResponse, status_code=status.HTTP_201_CREATED)
async def import_project_bundle(
    request: Request,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
) -> StudioProjectResponse:
    studio_service = request.app.state.studio_service
    try:
        project = studio_service.import_project_bundle(
            filename=file.filename or "project-bundle.zip",
            content=await file.read(),
            title=title,
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=400, detail=f"Invalid project bundle: {error.args[0]}") from error
    return StudioProjectResponse(**project)


@router.get("/api/v1/studio/projects/{slug}", response_model=StudioProjectResponse)
def get_project(slug: str, request: Request) -> StudioProjectResponse:
    studio_service = request.app.state.studio_service
    try:
        project = studio_service.get_project(slug)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found.") from error
    return StudioProjectResponse(**project)


@router.put("/api/v1/studio/projects/{slug}", response_model=StudioProjectResponse)
def update_project(slug: str, payload: StudioProjectUpdateRequest, request: Request) -> StudioProjectResponse:
    studio_service = request.app.state.studio_service
    try:
        project = studio_service.update_project(slug, payload.model_dump(exclude_none=True))
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found.") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return StudioProjectResponse(**project)


@router.post("/api/v1/studio/projects/{slug}/clone", response_model=StudioProjectResponse)
def clone_project(slug: str, payload: StudioProjectCloneRequest, request: Request) -> StudioProjectResponse:
    studio_service = request.app.state.studio_service
    try:
        project = studio_service.clone_project(slug, payload.title)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found.") from error
    return StudioProjectResponse(**project)


@router.post("/api/v1/studio/projects/{slug}/comments", response_model=StudioProjectResponse)
def add_teacher_comment(slug: str, payload: StudioTeacherCommentRequest, request: Request) -> StudioProjectResponse:
    studio_service = request.app.state.studio_service
    try:
        project = studio_service.add_teacher_comment(slug, payload.author, payload.body, payload.criterion)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found.") from error
    return StudioProjectResponse(**project)


@router.get("/api/v1/studio/projects/{slug}/documents", response_model=list[ProjectDocumentResponse])
def list_project_documents(slug: str, request: Request) -> list[ProjectDocumentResponse]:
    studio_service = request.app.state.studio_service
    try:
        documents = studio_service.list_documents(slug)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found.") from error
    return [ProjectDocumentResponse(**document) for document in documents]


@router.post("/api/v1/studio/projects/{slug}/documents", response_model=ProjectDocumentResponse)
async def upload_document(
    slug: str,
    request: Request,
    file: UploadFile = File(...),
    content_type: str | None = Form(default=None),
) -> ProjectDocumentResponse:
    studio_service = request.app.state.studio_service
    try:
        payload = studio_service.ingest_document(
            slug=slug,
            filename=file.filename or "upload.txt",
            content=await file.read(),
            content_type=content_type or file.content_type,
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found.") from error
    return ProjectDocumentResponse(**payload)


@router.post("/api/v1/studio/projects/{slug}/search", response_model=list[StudioSearchResult])
def search_project(slug: str, payload: StudioSearchRequest, request: Request) -> list[StudioSearchResult]:
    studio_service = request.app.state.studio_service
    try:
        results = studio_service.search_project(slug, payload.query, payload.limit)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found.") from error
    return [StudioSearchResult(**item) for item in results]


@router.get("/api/v1/studio/projects/{slug}/graph", response_model=StudioGraphResponse)
def project_graph(slug: str, request: Request) -> StudioGraphResponse:
    studio_service = request.app.state.studio_service
    try:
        graph = studio_service.compile_knowledge_graph(slug)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found.") from error
    return StudioGraphResponse(**graph)


@router.post("/api/v1/studio/projects/{slug}/compile", response_model=StudioCompileResponse)
def compile_project(slug: str, payload: StudioCompileRequest, request: Request) -> StudioCompileResponse:
    studio_service = request.app.state.studio_service
    try:
        compiled = studio_service.run_workflow(
            slug,
            stages=[stage.model_dump() for stage in payload.stages] if payload.stages else None,
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found.") from error
    return StudioCompileResponse(**compiled)


@router.get("/api/v1/studio/projects/{slug}/artifacts", response_model=StudioArtifactBundleResponse)
def get_artifacts(slug: str, request: Request) -> StudioArtifactBundleResponse:
    studio_service = request.app.state.studio_service
    try:
        artifact_bundle = studio_service.get_artifact_bundle(slug)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found.") from error

    if artifact_bundle is None:
        raise HTTPException(status_code=404, detail="Artifacts not found.")
    return StudioArtifactBundleResponse(**artifact_bundle)


@router.get("/api/v1/studio/projects/{slug}/download/{export_type}")
def download_export(slug: str, export_type: str, request: Request) -> FileResponse:
    studio_service = request.app.state.studio_service
    try:
        export_path = studio_service.get_export_path(slug, export_type)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Export not found.") from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error) or "Export blocked by quality gates.") from error
    if export_path.is_dir():
        raise HTTPException(status_code=400, detail="Directory exports are packaged through the project bundle.")
    return FileResponse(export_path, filename=export_path.name)
