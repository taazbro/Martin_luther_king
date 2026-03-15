import type {
  AdminStatusResponse,
  AIClassroomPolicy,
  AIProviderCatalogEntry,
  AIProviderProfile,
  AIProviderTestResponse,
  AIUsageEntry,
  AssignmentStatusBoard,
  AuthTokenResponse,
  BenchmarkReportResponse,
  ClassroomLibrary,
  ClassroomRoster,
  ClassroomReplay,
  EducationAgentCatalogEntry,
  EducationAgentRunResponse,
  EducationApproval,
  EducationAuditResponse,
  EducationClassroom,
  EducationGrowthOverview,
  EducationLaunchResponse,
  EducationMaterial,
  EducationOverview,
  EducationSafetyStatus,
  EduClawnBootstrapResponse,
  EduClawnOverview,
  FamilyShareLink,
  FamilyView,
  EduClawnSourceSummary,
  HealthStatus,
  InterventionDashboard,
  LessonToProjectResponse,
  MarketplaceResponse,
  OfflineSchoolEdition,
  PeerReview,
  PeerReviewPairings,
  ProjectDocument,
  ProjectSummary,
  RevisionCoachResponse,
  RubricTrainResponse,
  SchoolPackInstallResponse,
  StudioSystemStatus,
  StandardsMap,
  StudioAgentCatalogEntry,
  StudioArtifactBundle,
  StudioCompileResponse,
  StudioGraph,
  StudioOverview,
  StudioProject,
  StudioSearchResult,
  StudioTemplate,
  AssignmentAutopilotResponse,
  AssessmentPack,
  CitationVerification,
} from './types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type RequestOptions = RequestInit & {
  token?: string
}

async function request<T>(path: string, init?: RequestOptions): Promise<T> {
  const headers = new Headers(init?.headers)
  const isFormData = init?.body instanceof FormData

  if (!isFormData && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  if (init?.token) {
    headers.set('Authorization', `Bearer ${init.token}`)
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    throw new ApiError(response.status, await readError(response))
  }

  if (response.status === 204) {
    return undefined as T
  }

  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

async function readError(response: Response): Promise<string> {
  const contentType = response.headers.get('content-type') ?? ''

  if (contentType.includes('application/json')) {
    const payload = await response.json() as { detail?: string }
    return payload.detail ?? `Request failed: ${response.status}`
  }

  const message = await response.text()
  return message || `Request failed: ${response.status}`
}

export const api = {
  health: () => request<HealthStatus>('/health'),
  aiProviderCatalog: () => request<AIProviderCatalogEntry[]>('/api/v1/ai/catalog'),
  aiProfiles: () => request<AIProviderProfile[]>('/api/v1/ai/profiles'),
  createAiProfile: (payload: {
    label: string
    provider_id: AIProviderCatalogEntry['provider_id']
    auth_mode: 'user-key' | 'managed-subscription'
    api_key: string
    default_model: string
    base_url: string
    capabilities: string[]
    enabled?: boolean
    daily_request_limit?: number
    monthly_budget_usd?: number
    fallback_profile_ids?: string[]
    redaction_mode?: 'off' | 'metadata-only' | 'pii-lite'
    usage_cap_per_classroom_daily?: number
    managed_subscription_note?: string
  }) =>
    request<AIProviderProfile>('/api/v1/ai/profiles', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateAiProfile: (profileId: string, payload: {
    label?: string
    auth_mode?: 'user-key' | 'managed-subscription'
    api_key?: string
    default_model?: string
    base_url?: string
    capabilities?: string[]
    enabled?: boolean
    daily_request_limit?: number
    monthly_budget_usd?: number
    fallback_profile_ids?: string[]
    redaction_mode?: 'off' | 'metadata-only' | 'pii-lite'
    usage_cap_per_classroom_daily?: number
    managed_subscription_note?: string
  }) =>
    request<AIProviderProfile>(`/api/v1/ai/profiles/${encodeURIComponent(profileId)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  deleteAiProfile: (profileId: string) =>
    request<void>(`/api/v1/ai/profiles/${encodeURIComponent(profileId)}`, {
      method: 'DELETE',
    }),
  testAiProfile: (profileId: string) =>
    request<AIProviderTestResponse>(`/api/v1/ai/profiles/${encodeURIComponent(profileId)}/test`, {
      method: 'POST',
    }),
  aiUsage: () => request<AIUsageEntry[]>('/api/v1/ai/usage'),
  aiClassroomPolicies: () => request<AIClassroomPolicy[]>('/api/v1/ai/classroom-policies'),
  aiClassroomPolicy: (classroomId: string) =>
    request<AIClassroomPolicy>(`/api/v1/ai/classroom-policies/${encodeURIComponent(classroomId)}`),
  updateAiClassroomPolicy: (
    classroomId: string,
    payload: {
      daily_request_limit: number
      monthly_budget_usd: number
      managed_subscription_allowed: boolean
      allowed_profile_ids: string[]
      redact_student_pii: boolean
      notes: string
    },
  ) =>
    request<AIClassroomPolicy>(`/api/v1/ai/classroom-policies/${encodeURIComponent(classroomId)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  login: (payload: { username: string; password: string }) =>
    request<AuthTokenResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  adminStatus: (token: string) =>
    request<AdminStatusResponse>('/api/v1/admin/status', {
      token,
    }),
  latestBenchmark: (token: string) =>
    request<BenchmarkReportResponse>('/api/v1/admin/benchmarks/latest', {
      token,
    }),
  studioOverview: () => request<StudioOverview>('/api/v1/studio/overview'),
  studioSystemStatus: () => request<StudioSystemStatus>('/api/v1/studio/system/status'),
  studioTemplates: () => request<StudioTemplate[]>('/api/v1/studio/templates'),
  studioAgentCatalog: () => request<StudioAgentCatalogEntry[]>('/api/v1/studio/agents/catalog'),
  studioProjects: () => request<ProjectSummary[]>('/api/v1/studio/projects'),
  educationOverview: () => request<EducationOverview>('/api/v1/edu/overview'),
  educationClassrooms: () => request<EducationClassroom[]>('/api/v1/edu/classrooms'),
  educationAgentCatalog: () => request<EducationAgentCatalogEntry[]>('/api/v1/edu/agents/catalog'),
  educationApprovals: (classroomId: string, accessKey: string) =>
    request<EducationApproval[]>(
      `/api/v1/edu/approvals?classroom_id=${encodeURIComponent(classroomId)}&access_key=${encodeURIComponent(accessKey)}`,
    ),
  educationAudit: (classroomId: string, accessKey: string) =>
    request<EducationAuditResponse>(
      `/api/v1/edu/audit?classroom_id=${encodeURIComponent(classroomId)}&access_key=${encodeURIComponent(accessKey)}`,
    ),
  educationSafety: () => request<EducationSafetyStatus>('/api/v1/edu/safety'),
  educationGrowthOverview: () => request<EducationGrowthOverview>('/api/v1/edu/growth/overview'),
  assignmentAutopilot: (payload: {
    classroom_id: string
    access_key: string
    topic: string
    title?: string
    summary?: string
    audience?: string
    template_id?: string
    goals?: string[]
    rubric?: string[]
    standards?: string[]
    lesson_seed?: string
    due_date?: string
    local_mode?: 'no-llm' | 'local-llm' | 'provider-ai'
    ai_profile_id?: string
  }) =>
    request<AssignmentAutopilotResponse>('/api/v1/edu/growth/autopilot', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  revisionCoach: (payload: {
    classroom_id: string
    assignment_id: string
    access_key: string
    draft_text: string
    rubric?: string[]
    teacher_feedback?: string[]
    project_slug?: string
    ai_profile_id?: string
  }) =>
    request<RevisionCoachResponse>('/api/v1/edu/growth/revision-coach', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  classroomLibrary: (classroomId: string, accessKey: string) =>
    request<ClassroomLibrary>(
      `/api/v1/edu/growth/library/${encodeURIComponent(classroomId)}?access_key=${encodeURIComponent(accessKey)}`,
    ),
  promoteClassroomLibrary: (classroomId: string, payload: { access_key: string; material_ids: string[] }) =>
    request<ClassroomLibrary>(`/api/v1/edu/growth/library/${encodeURIComponent(classroomId)}/promote`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  createPeerReview: (payload: {
    classroom_id: string
    assignment_id: string
    reviewer_student_id: string
    target_student_id: string
    access_key: string
    draft_text: string
    rubric?: string[]
    project_slug?: string
  }) =>
    request<PeerReview>('/api/v1/edu/growth/peer-review', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listPeerReviews: (classroomId: string, accessKey: string) =>
    request<PeerReview[]>(
      `/api/v1/edu/growth/peer-review?classroom_id=${encodeURIComponent(classroomId)}&access_key=${encodeURIComponent(accessKey)}`,
    ),
  peerReviewPairs: (classroomId: string, assignmentId: string, accessKey: string) =>
    request<PeerReviewPairings>(
      `/api/v1/edu/growth/peer-review/pairs?classroom_id=${encodeURIComponent(classroomId)}&assignment_id=${encodeURIComponent(assignmentId)}&access_key=${encodeURIComponent(accessKey)}`,
    ),
  resolvePeerReview: (
    reviewId: string,
    payload: { decision: 'approved' | 'rejected'; reviewer: string; note: string; access_key: string },
  ) =>
    request<PeerReview>(`/api/v1/edu/growth/peer-review/${encodeURIComponent(reviewId)}/resolve`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  familyView: (classroomId: string, projectSlug: string, accessKey: string) =>
    request<FamilyView>(
      `/api/v1/edu/growth/family-view?classroom_id=${encodeURIComponent(classroomId)}&project_slug=${encodeURIComponent(projectSlug)}&access_key=${encodeURIComponent(accessKey)}`,
    ),
  createFamilyShareLink: (classroomId: string, projectSlug: string, accessKey: string) =>
    request<FamilyShareLink>(
      `/api/v1/edu/growth/family-view/share?classroom_id=${encodeURIComponent(classroomId)}&project_slug=${encodeURIComponent(projectSlug)}&access_key=${encodeURIComponent(accessKey)}`,
      { method: 'POST' },
    ),
  sharedFamilyView: (shareToken: string) =>
    request<FamilyView>(`/api/v1/edu/growth/family-view/shared/${encodeURIComponent(shareToken)}`),
  citationVerify: (payload: { project_slug?: string; claims: string[] }) =>
    request<CitationVerification>('/api/v1/edu/growth/citation-verify', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  lessonToProject: (payload: {
    lesson_plan: string
    title?: string
    topic?: string
    audience?: string
    goals?: string[]
    rubric?: string[]
    template_id?: string
    local_mode?: 'no-llm' | 'local-llm' | 'provider-ai'
    ai_profile_id?: string
    classroom_id?: string
    access_key?: string
    seed_from_classroom?: boolean
  }) =>
    request<LessonToProjectResponse>('/api/v1/edu/growth/lesson-to-project', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  rubricTrain: (payload: { classroom_id: string; access_key: string; project_slugs?: string[] }) =>
    request<RubricTrainResponse>('/api/v1/edu/growth/rubric-train', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  standardsMap: (classroomId: string, assignmentId: string, accessKey: string) =>
    request<StandardsMap>(
      `/api/v1/edu/growth/standards-map?classroom_id=${encodeURIComponent(classroomId)}&assignment_id=${encodeURIComponent(assignmentId)}&access_key=${encodeURIComponent(accessKey)}`,
    ),
  interventionDashboard: (classroomId: string, accessKey: string) =>
    request<InterventionDashboard>(
      `/api/v1/edu/growth/interventions?classroom_id=${encodeURIComponent(classroomId)}&access_key=${encodeURIComponent(accessKey)}`,
    ),
  classroomRoster: (classroomId: string, accessKey: string) =>
    request<ClassroomRoster>(
      `/api/v1/edu/growth/roster?classroom_id=${encodeURIComponent(classroomId)}&access_key=${encodeURIComponent(accessKey)}`,
    ),
  assignmentStatusBoard: (classroomId: string, accessKey: string) =>
    request<AssignmentStatusBoard>(
      `/api/v1/edu/growth/assignment-status?classroom_id=${encodeURIComponent(classroomId)}&access_key=${encodeURIComponent(accessKey)}`,
    ),
  classroomReplay: (classroomId: string, accessKey: string) =>
    request<ClassroomReplay>(
      `/api/v1/edu/growth/replay?classroom_id=${encodeURIComponent(classroomId)}&access_key=${encodeURIComponent(accessKey)}`,
    ),
  assessmentPack: (payload: { classroom_id: string; assignment_id: string; access_key: string; ai_profile_id?: string }) =>
    request<AssessmentPack>('/api/v1/edu/growth/assessment-pack', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  marketplace: () => request<MarketplaceResponse>('/api/v1/edu/growth/marketplace'),
  installSchoolPack: (packId: string) =>
    request<SchoolPackInstallResponse>(`/api/v1/edu/growth/school-packs/${encodeURIComponent(packId)}/install`, {
      method: 'POST',
    }),
  offlineSchoolEdition: () => request<OfflineSchoolEdition>('/api/v1/edu/growth/offline-school-edition'),
  educlawnOverview: () => request<EduClawnOverview>('/api/v1/educlawn/overview'),
  educlawnSource: () => request<EduClawnSourceSummary>('/api/v1/educlawn/source'),
  educlawnBootstrap: (payload: {
    school_name: string
    classroom_title: string
    teacher_name: string
    subject: string
    grade_band: string
    description: string
    default_template_id: string
    template_id: string
    assignment_title: string
    assignment_summary: string
    topic: string
    audience: string
    goals: string[]
    rubric: string[]
    standards_focus: string[]
    due_date: string
    local_mode: 'no-llm' | 'local-llm' | 'provider-ai'
    ai_profile_id: string
  }) =>
    request<EduClawnBootstrapResponse>('/api/v1/educlawn/bootstrap', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  createClassroom: (payload: {
    title: string
    subject: string
    grade_band: string
    teacher_name: string
    description: string
    default_template_id: string
    standards_focus: string[]
  }) =>
    request<EducationClassroom>('/api/v1/edu/classrooms', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  enrollStudent: (classroomId: string, payload: {
    name: string
    grade_level: string
    learning_goals: string[]
    notes: string
    access_key: string
  }) =>
    request<EducationClassroom>(`/api/v1/edu/classrooms/${encodeURIComponent(classroomId)}/students`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  createAssignment: (classroomId: string, payload: {
    title: string
    summary: string
    topic: string
    audience: string
    template_id: string
    goals: string[]
    rubric: string[]
    standards: string[]
    due_date: string
    local_mode: 'no-llm' | 'local-llm' | 'provider-ai'
    ai_profile_id: string
    access_key: string
  }) =>
    request<EducationClassroom>(`/api/v1/edu/classrooms/${encodeURIComponent(classroomId)}/assignments`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  uploadClassroomMaterial: (classroomId: string, file: File, accessKey: string, assignmentId = '') => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('access_key', accessKey)
    if (assignmentId) {
      formData.append('assignment_id', assignmentId)
    }
    return request<EducationMaterial>(`/api/v1/edu/classrooms/${encodeURIComponent(classroomId)}/materials`, {
      method: 'POST',
      body: formData,
    })
  },
  launchStudentProject: (classroomId: string, payload: { assignment_id: string; student_id: string; access_key: string }) =>
    request<EducationLaunchResponse>(`/api/v1/edu/classrooms/${encodeURIComponent(classroomId)}/launch`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  runEducationAgent: (payload: {
    role: 'teacher' | 'student' | 'shared'
    agent_name: string
    classroom_id?: string
    assignment_id?: string
    student_id?: string
    project_slug?: string
    ai_profile_id?: string
    access_key: string
    prompt: string
  }) =>
    request<EducationAgentRunResponse>('/api/v1/edu/agents/run', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  resolveEducationApproval: (
    approvalId: string,
    payload: { decision: 'approved' | 'rejected'; reviewer: string; note: string; access_key: string },
  ) =>
    request<EducationApproval>(`/api/v1/edu/approvals/${encodeURIComponent(approvalId)}/resolve`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  createProject: (payload: {
    title: string
    summary: string
    topic: string
    audience: string
    goals: string[]
    rubric: string[]
    template_id: string
    local_mode: 'no-llm' | 'local-llm' | 'provider-ai'
    ai_profile_id: string
  }) =>
    request<StudioProject>('/api/v1/studio/projects', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  importProject: (file: File, title = '') => {
    const formData = new FormData()
    formData.append('file', file)
    if (title) {
      formData.append('title', title)
    }
    return request<StudioProject>('/api/v1/studio/projects/import', {
      method: 'POST',
      body: formData,
    })
  },
  getProject: (slug: string) =>
    request<StudioProject>(`/api/v1/studio/projects/${encodeURIComponent(slug)}`),
  updateProject: (slug: string, payload: Record<string, unknown>) =>
    request<StudioProject>(`/api/v1/studio/projects/${encodeURIComponent(slug)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  cloneProject: (slug: string, title: string) =>
    request<StudioProject>(`/api/v1/studio/projects/${encodeURIComponent(slug)}/clone`, {
      method: 'POST',
      body: JSON.stringify({ title }),
    }),
  addTeacherComment: (slug: string, payload: { author: string; body: string; criterion?: string }) =>
    request<StudioProject>(`/api/v1/studio/projects/${encodeURIComponent(slug)}/comments`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listDocuments: (slug: string) =>
    request<ProjectDocument[]>(`/api/v1/studio/projects/${encodeURIComponent(slug)}/documents`),
  uploadDocument: (slug: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request<ProjectDocument>(`/api/v1/studio/projects/${encodeURIComponent(slug)}/documents`, {
      method: 'POST',
      body: formData,
    })
  },
  searchProject: (slug: string, query: string, limit = 6) =>
    request<StudioSearchResult[]>(`/api/v1/studio/projects/${encodeURIComponent(slug)}/search`, {
      method: 'POST',
      body: JSON.stringify({ query, limit }),
    }),
  projectGraph: (slug: string) =>
    request<StudioGraph>(`/api/v1/studio/projects/${encodeURIComponent(slug)}/graph`),
  compileProject: (slug: string, stages?: Array<Record<string, unknown>>) =>
    request<StudioCompileResponse>(`/api/v1/studio/projects/${encodeURIComponent(slug)}/compile`, {
      method: 'POST',
      body: JSON.stringify(stages ? { stages } : {}),
    }),
  projectArtifacts: (slug: string) =>
    request<StudioArtifactBundle>(`/api/v1/studio/projects/${encodeURIComponent(slug)}/artifacts`),
  downloadUrl: (slug: string, exportType: string) =>
    `${API_BASE}/api/v1/studio/projects/${encodeURIComponent(slug)}/download/${encodeURIComponent(exportType)}`,
  legacyUrl: () => `${API_BASE}/legacy`,
}
