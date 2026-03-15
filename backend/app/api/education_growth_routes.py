from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.api.education_growth_schemas import (
    AssessmentPackRequest,
    AssessmentPackResponse,
    AssignmentStatusBoardResponse,
    AssignmentAutopilotRequest,
    AssignmentAutopilotResponse,
    CitationVerificationResponse,
    CitationVerifyRequest,
    ClassroomLibraryResponse,
    ClassroomRosterResponse,
    ClassroomReplayResponse,
    EducationGrowthOverviewResponse,
    FamilyShareLinkResponse,
    FamilyViewResponse,
    InterventionDashboardResponse,
    LessonToProjectRequest,
    LessonToProjectResponse,
    LibraryPromoteRequest,
    MarketplaceResponse,
    OfflineSchoolEditionResponse,
    PeerReviewCreateRequest,
    PeerReviewPairingsResponse,
    PeerReviewResolveRequest,
    PeerReviewResponse,
    RevisionCoachRequest,
    RevisionCoachResponse,
    RubricTrainRequest,
    RubricTrainResponse,
    SchoolPackInstallResponse,
    StandardsMapResponse,
)


router = APIRouter()


@router.get("/api/v1/edu/growth/overview", response_model=EducationGrowthOverviewResponse)
def growth_overview(request: Request) -> EducationGrowthOverviewResponse:
    service = request.app.state.education_growth_service
    return EducationGrowthOverviewResponse(**service.get_overview())


@router.post("/api/v1/edu/growth/autopilot", response_model=AssignmentAutopilotResponse, status_code=status.HTTP_201_CREATED)
def assignment_autopilot(payload: AssignmentAutopilotRequest, request: Request) -> AssignmentAutopilotResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.run_assignment_autopilot(payload.model_dump(exclude_none=True))
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return AssignmentAutopilotResponse(**result)


@router.post("/api/v1/edu/growth/revision-coach", response_model=RevisionCoachResponse)
def revision_coach(payload: RevisionCoachRequest, request: Request) -> RevisionCoachResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.run_revision_coach(payload.model_dump(exclude_none=True))
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return RevisionCoachResponse(**result)


@router.get("/api/v1/edu/growth/library/{classroom_id}", response_model=ClassroomLibraryResponse)
def classroom_library(
    classroom_id: str,
    request: Request,
    access_key: str = Query(..., min_length=8),
) -> ClassroomLibraryResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.get_classroom_library(classroom_id, access_key)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ClassroomLibraryResponse(**result)


@router.post("/api/v1/edu/growth/library/{classroom_id}/promote", response_model=ClassroomLibraryResponse)
def promote_library(
    classroom_id: str,
    payload: LibraryPromoteRequest,
    request: Request,
) -> ClassroomLibraryResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.promote_classroom_library(
            {
                "classroom_id": classroom_id,
                **payload.model_dump(exclude_none=True),
            }
        )
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ClassroomLibraryResponse(**result)


@router.post("/api/v1/edu/growth/peer-review", response_model=PeerReviewResponse, status_code=status.HTTP_201_CREATED)
def create_peer_review(payload: PeerReviewCreateRequest, request: Request) -> PeerReviewResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.create_peer_review(payload.model_dump(exclude_none=True))
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return PeerReviewResponse(**result)


@router.get("/api/v1/edu/growth/peer-review", response_model=list[PeerReviewResponse])
def list_peer_reviews(
    request: Request,
    classroom_id: str = Query(..., min_length=3),
    access_key: str = Query(..., min_length=8),
) -> list[PeerReviewResponse]:
    service = request.app.state.education_growth_service
    try:
        result = service.list_peer_reviews(classroom_id, access_key)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return [PeerReviewResponse(**item) for item in result]


@router.get("/api/v1/edu/growth/peer-review/pairs", response_model=PeerReviewPairingsResponse)
def peer_review_pairs(
    request: Request,
    classroom_id: str = Query(..., min_length=3),
    assignment_id: str = Query(..., min_length=3),
    access_key: str = Query(..., min_length=8),
) -> PeerReviewPairingsResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.suggest_peer_review_pairs(classroom_id, assignment_id, access_key)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return PeerReviewPairingsResponse(**result)


@router.post("/api/v1/edu/growth/peer-review/{review_id}/resolve", response_model=PeerReviewResponse)
def resolve_peer_review(review_id: str, payload: PeerReviewResolveRequest, request: Request) -> PeerReviewResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.resolve_peer_review(review_id, payload.model_dump(exclude_none=True))
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Peer review not found.") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return PeerReviewResponse(**result)


@router.get("/api/v1/edu/growth/family-view", response_model=FamilyViewResponse)
def family_view(
    request: Request,
    classroom_id: str = Query(..., min_length=3),
    project_slug: str = Query(..., min_length=3),
    access_key: str = Query(..., min_length=8),
) -> FamilyViewResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.get_family_view(classroom_id, project_slug, access_key)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return FamilyViewResponse(**result)


@router.post("/api/v1/edu/growth/family-view/share", response_model=FamilyShareLinkResponse, status_code=status.HTTP_201_CREATED)
def create_family_share_link(
    request: Request,
    classroom_id: str = Query(..., min_length=3),
    project_slug: str = Query(..., min_length=3),
    access_key: str = Query(..., min_length=8),
) -> FamilyShareLinkResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.create_family_share_link(classroom_id, project_slug, access_key)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return FamilyShareLinkResponse(**result)


@router.get("/api/v1/edu/growth/family-view/shared/{share_token}", response_model=FamilyViewResponse)
def shared_family_view(share_token: str, request: Request) -> FamilyViewResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.get_family_view_by_share_token(share_token)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Shared family view not found.") from error
    return FamilyViewResponse(**result)


@router.post("/api/v1/edu/growth/citation-verify", response_model=CitationVerificationResponse)
def citation_verify(payload: CitationVerifyRequest, request: Request) -> CitationVerificationResponse:
    service = request.app.state.education_growth_service
    return CitationVerificationResponse(**service.verify_citations(payload.model_dump(exclude_none=True)))


@router.post("/api/v1/edu/growth/lesson-to-project", response_model=LessonToProjectResponse, status_code=status.HTTP_201_CREATED)
def lesson_to_project(payload: LessonToProjectRequest, request: Request) -> LessonToProjectResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.lesson_to_project(payload.model_dump(exclude_none=True))
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return LessonToProjectResponse(**result)


@router.post("/api/v1/edu/growth/rubric-train", response_model=RubricTrainResponse)
def rubric_train(payload: RubricTrainRequest, request: Request) -> RubricTrainResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.train_rubric_model(payload.model_dump(exclude_none=True))
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return RubricTrainResponse(**result)


@router.get("/api/v1/edu/growth/standards-map", response_model=StandardsMapResponse)
def standards_map(
    request: Request,
    classroom_id: str = Query(..., min_length=3),
    assignment_id: str = Query(..., min_length=3),
    access_key: str = Query(..., min_length=8),
) -> StandardsMapResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.map_standards(
            {
                "classroom_id": classroom_id,
                "assignment_id": assignment_id,
                "access_key": access_key,
            }
        )
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return StandardsMapResponse(**result)


@router.get("/api/v1/edu/growth/interventions", response_model=InterventionDashboardResponse)
def intervention_dashboard(
    request: Request,
    classroom_id: str = Query(..., min_length=3),
    access_key: str = Query(..., min_length=8),
) -> InterventionDashboardResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.intervention_dashboard(classroom_id, access_key)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return InterventionDashboardResponse(**result)


@router.get("/api/v1/edu/growth/roster", response_model=ClassroomRosterResponse)
def classroom_roster(
    request: Request,
    classroom_id: str = Query(..., min_length=3),
    access_key: str = Query(..., min_length=8),
) -> ClassroomRosterResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.classroom_roster(classroom_id, access_key)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ClassroomRosterResponse(**result)


@router.get("/api/v1/edu/growth/assignment-status", response_model=AssignmentStatusBoardResponse)
def assignment_status_board(
    request: Request,
    classroom_id: str = Query(..., min_length=3),
    access_key: str = Query(..., min_length=8),
) -> AssignmentStatusBoardResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.assignment_status_board(classroom_id, access_key)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return AssignmentStatusBoardResponse(**result)


@router.get("/api/v1/edu/growth/replay", response_model=ClassroomReplayResponse)
def classroom_replay(
    request: Request,
    classroom_id: str = Query(..., min_length=3),
    access_key: str = Query(..., min_length=8),
) -> ClassroomReplayResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.classroom_replay(classroom_id, access_key)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ClassroomReplayResponse(**result)


@router.post("/api/v1/edu/growth/assessment-pack", response_model=AssessmentPackResponse)
def assessment_pack(payload: AssessmentPackRequest, request: Request) -> AssessmentPackResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.generate_assessment_pack(payload.model_dump(exclude_none=True))
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return AssessmentPackResponse(**result)


@router.get("/api/v1/edu/growth/marketplace", response_model=MarketplaceResponse)
def marketplace(request: Request) -> MarketplaceResponse:
    service = request.app.state.education_growth_service
    return MarketplaceResponse(**service.get_marketplace())


@router.post("/api/v1/edu/growth/school-packs/{pack_id}/install", response_model=SchoolPackInstallResponse, status_code=status.HTTP_201_CREATED)
def install_school_pack(pack_id: str, request: Request) -> SchoolPackInstallResponse:
    service = request.app.state.education_growth_service
    try:
        result = service.install_school_pack(pack_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="School pack not found.") from error
    return SchoolPackInstallResponse(**result)


@router.get("/api/v1/edu/growth/offline-school-edition", response_model=OfflineSchoolEditionResponse)
def offline_school_edition(request: Request) -> OfflineSchoolEditionResponse:
    service = request.app.state.education_growth_service
    return OfflineSchoolEditionResponse(**service.get_offline_school_edition())
