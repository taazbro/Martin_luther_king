export type SchedulerStatus = {
  enabled: boolean
  etl_interval_seconds: number
  retrain_interval_seconds: number
  benchmark_interval_seconds: number
  active_tasks: number
}

export type HealthStatus = {
  status: string
  app: string
  trained: boolean
  trained_at: string
  database_backend: string
  scheduler: SchedulerStatus
}

export type AuthTokenResponse = {
  access_token: string
  token_type: string
  expires_at: string
  username: string
  role: string
}

export type AdminStatusResponse = {
  database_backend: string
  database_url: string
  latest_snapshot: Record<string, unknown> | null
  scheduler: SchedulerStatus
  model_summary: Record<string, unknown>
  current_user: {
    username: string
    role: string
  }
}

export type BenchmarkScore = {
  benchmark_name: string
  score: number
  status: 'pass' | 'warn' | 'fail'
  summary: string
}

export type BenchmarkReportResponse = {
  generated_at: string
  overall_score: number
  benchmarks: BenchmarkScore[]
  recommendations: string[]
}

export type StudioTemplate = {
  id: string
  label: string
  description: string
  project_type: string
  category: string
  supports_simulation: boolean
  layout_direction: string
  export_targets: string[]
  starter_prompts: string[]
  theme_tokens: Record<string, string>
  sections: Array<{
    section_id: string
    title: string
    objective: string
  }>
  workflow: WorkflowStage[]
}

export type StudioPlugin = {
  id: string
  label: string
  version: string
  description: string
  capabilities: string[]
}

export type DesktopContext = {
  isDesktop: boolean
  backendUrl: string
  workspaceRoot: string
  lastProjectSlug: string
  pendingProjectSlug: string
  recentProjects: Array<{
    slug: string
    title: string
    manifestPath: string
    bundlePath: string
    updatedAt: string
  }>
  recovery: {
    unclean_exit: boolean
    imported_path: string
    imported_project_slug: string
  }
  updater: {
    status: string
    currentVersion: string
    availableVersion: string
    downloadedVersion: string
    lastCheckedAt: string
    message: string
    error: string
  }
  preferences: {
    launchAtLogin: boolean
  }
  canInstallToApplications: boolean
  installTargetPath: string
}

export type StudioSampleProject = {
  title: string
  slug: string
  template_id: string
  summary: string
}

export type RevisionEntry = {
  revision_id: string
  action: string
  summary: string
  actor: string
  created_at: string
}

export type TeacherComment = {
  comment_id: string
  author: string
  criterion: string
  body: string
  created_at: string
}

export type StandardsAlignmentEntry = {
  standard_id: string
  label: string
  reason: string
}

export type StudioSystemStatus = {
  workspace_root: string
  frontend_dist: string
  startup: Record<string, unknown>
  tools: {
    tesseract_available: boolean
    tesseract_path?: string | null
  }
  local_ai: {
    configured_model: string
    base_url: string
    configured: boolean
    ollama_reachable: boolean
    available_models: string[]
  }
  portability: {
    backup_export_type: string
    import_supported: boolean
    duplicate_supported: boolean
  }
  provider_ai: {
    configured_profiles: number
    managed_profiles: number
    providers_available: string[]
  }
  release: {
    desktop_version: string
    release_notes_path: string
    packaged_app_path: string
  }
}

export type AIProviderId =
  | 'openai'
  | 'anthropic'
  | 'google'
  | 'groq'
  | 'mistral'
  | 'cohere'
  | 'xai'

export type AIAuthMode = 'user-key' | 'managed-subscription'
export type AIRedactionMode = 'off' | 'metadata-only' | 'pii-lite'

export type AITaskCapability =
  | 'research'
  | 'assignments'
  | 'feedback'
  | 'planning'
  | 'review'
  | 'export'
  | 'classroom'

export type AIProviderCatalogEntry = {
  provider_id: AIProviderId
  label: string
  sdk_package: string
  docs_url: string
  default_model: string
  recommended_models: string[]
  supports_custom_base_url: boolean
  supports_managed_subscription: boolean
  notes: string
  sdk_installed: boolean
  supported_tasks: AITaskCapability[]
}

export type AIProviderProfile = {
  profile_id: string
  label: string
  provider_id: AIProviderId
  provider_label: string
  auth_mode: AIAuthMode
  default_model: string
  base_url: string
  capabilities: AITaskCapability[]
  enabled: boolean
  daily_request_limit: number
  monthly_budget_usd: number
  fallback_profile_ids: string[]
  redaction_mode: AIRedactionMode
  usage_cap_per_classroom_daily: number
  managed_subscription_note: string
  usage_summary: {
    requests_today: number
    spend_this_month_usd: number
  }
  api_key_hint: string
  sdk_installed: boolean
  last_tested_at: string
  last_test_status: string
  last_error: string
  created_at: string
  updated_at: string
}

export type AIProviderTestResponse = {
  used: boolean
  generated_at: string
  provider_id: AIProviderId
  provider_label: string
  profile_id: string
  profile_label: string
  auth_mode: AIAuthMode
  model: string
  output_text: string
  error: string
  effective_profile_id: string
  effective_profile_label: string
  classroom_id: string
  fallback_used: boolean
  estimated_cost_usd: number
  redaction: Record<string, unknown>
}

export type AIClassroomPolicy = {
  classroom_id: string
  daily_request_limit: number
  monthly_budget_usd: number
  managed_subscription_allowed: boolean
  allowed_profile_ids: string[]
  redact_student_pii: boolean
  notes: string
  created_at: string
  updated_at: string
}

export type AIUsageEntry = {
  usage_id: string
  source: string
  task: string
  provider_id: AIProviderId
  provider_label: string
  profile_id: string
  profile_label: string
  auth_mode: AIAuthMode
  model: string
  success: boolean
  error: string
  prompt_preview: string
  metadata: Record<string, unknown>
  created_at: string
  classroom_id: string
  estimated_cost_usd: number
  redaction: Record<string, unknown>
  fallback_used: boolean
}

export type StudioOverview = {
  studio_name: string
  local_modes: Array<Record<string, unknown>>
  install_modes: Array<Record<string, unknown>>
  counts: {
    templates: number
    projects: number
    documents: number
    exports: number
    plugins: number
  }
  templates: StudioTemplate[]
  sample_projects: StudioSampleProject[]
  plugins: StudioPlugin[]
}

export type WorkflowStage = {
  stage_id: string
  label: string
  description: string
  enabled: boolean
}

export type StudioSection = {
  section_id: string
  title: string
  objective: string
  content: string
  citations: unknown[]
}

export type ProjectDocument = {
  document_id: string
  title: string
  file_name: string
  content_type: string
  source_path: string
  citation_label: string
  summary: string
  word_count: number
  reading_level: string
  entities: string[]
  years: string[]
  chunk_count: number
  duplicate_similarity: number
  extraction_method: string
  ocr_status: string
  uploaded_at: string
  knowledge_graph_nodes?: number | null
}

export type ProjectExport = {
  export_type: string
  path: string
  created_at: string
}

export type ProjectSummary = {
  project_id: string
  slug: string
  title: string
  summary: string
  topic: string
  audience: string
  template_id: string
  template_label: string
  project_type: string
  local_mode: string
  status: string
  document_count: number
  export_count: number
  documents: ProjectDocument[]
  exports: ProjectExport[]
  submission_readiness: Record<string, unknown>
  updated_at: string
}

export type StudioProject = {
  version: string
  project_id: string
  slug: string
  title: string
  summary: string
  topic: string
  audience: string
  goals: string[]
  rubric: string[]
  template_id: string
  template_label: string
  project_type: string
  local_mode: 'no-llm' | 'local-llm' | 'provider-ai'
  ai_profile_id: string
  status: string
  created_at: string
  updated_at: string
  theme_tokens: Record<string, string>
  workflow: {
    stages: WorkflowStage[]
  }
  sections: StudioSection[]
  documents: ProjectDocument[]
  artifacts: Record<string, unknown>
  exports: ProjectExport[]
  teacher_review: Record<string, unknown> | null
  teacher_comments: TeacherComment[]
  provenance: Record<string, unknown>
  simulation: Record<string, unknown>
  standards_alignment: StandardsAlignmentEntry[]
  revision_history: RevisionEntry[]
  plugin_ids: string[]
  template: Record<string, unknown>
  plugins: Array<Record<string, unknown>>
  classroom_context: Record<string, unknown>
  quality_gates: Record<string, unknown>
  submission_readiness: Record<string, unknown>
}

export type StudioSearchResult = {
  chunk_id: string
  document_id: string
  citation_label: string
  excerpt: string
  score: number
  match_reason: string
}

export type StudioGraph = {
  nodes: Array<Record<string, unknown>>
  edges: Array<Record<string, unknown>>
  highlights: string[]
}

export type StudioAgentName =
  | 'research'
  | 'planner'
  | 'writer'
  | 'historian'
  | 'citation'
  | 'design'
  | 'qa'
  | 'teacher'
  | 'export'

export type StudioAgentCatalogEntry = {
  name: StudioAgentName
  display_name: string
  role: string
  description: string
}

export type StudioAgentInsight = {
  agent_name: StudioAgentName
  display_name: string
  role: string
  summary: string
  confidence: number
  priority: 'low' | 'medium' | 'high'
  signals: string[]
  actions: string[]
}

export type StudioArtifactBundle = {
  generated_at: string
  runtime_mode: Record<string, unknown>
  agents: StudioAgentInsight[]
  artifacts: Record<string, unknown>
}

export type StudioCompileResponse = {
  project: StudioProject
  workflow_results: Array<Record<string, unknown>>
  retrieval_results: StudioSearchResult[]
  knowledge_graph: StudioGraph
  artifacts: StudioArtifactBundle | null
  exports: ProjectExport[]
}

export type ProjectDraft = {
  title: string
  summary: string
  topic: string
  audience: string
  goalsText: string
  rubricText: string
  template_id: string
  local_mode: 'no-llm' | 'local-llm' | 'provider-ai'
  ai_profile_id: string
}

export type EducationRole = 'teacher' | 'student' | 'shared'

export type EducationRoleModel = {
  role: EducationRole
  label: string
  description: string
  agent_names: string[]
}

export type EducationTemplateTrack = {
  id: string
  label: string
  project_type: string
  category: string
}

export type EducationOverview = {
  product_name: string
  positioning: string
  difference_statement: string
  role_models: EducationRoleModel[]
  safety_model: Record<string, unknown>
  counts: {
    classrooms: number
    students: number
    assignments: number
    pending_approvals: number
    audit_entries: number
  }
  agent_catalog: EducationAgentCatalogEntry[]
  template_tracks: EducationTemplateTrack[]
}

export type EducationStudent = {
  student_id: string
  name: string
  grade_level: string
  learning_goals: string[]
  notes: string
  project_slugs: string[]
  created_at: string
  updated_at: string
}

export type EducationLaunchedProject = {
  student_id: string
  student_name: string
  project_slug: string
  project_title: string
  created_at: string
}

export type EducationAssignment = {
  assignment_id: string
  title: string
  summary: string
  topic: string
  audience: string
  template_id: string
  template_label: string
  goals: string[]
  rubric: string[]
  standards: string[]
  due_date: string
  local_mode: 'no-llm' | 'local-llm' | 'provider-ai'
  ai_profile_id: string
  status: string
  created_at: string
  updated_at: string
  evidence_material_ids: string[]
  launched_projects: EducationLaunchedProject[]
}

export type EducationMaterial = {
  material_id: string
  title: string
  file_name: string
  content_type: string
  source_path: string
  summary: string
  word_count: number
  assignment_id?: string | null
  scope: 'shared' | 'assignment'
  extraction_method: string
  uploaded_at: string
}

export type EducationSecurityBootstrap = {
  teacher_access_key: string
  student_access_key: string
  reviewer_access_key: string
  issued_at: string
  rotation_note: string
}

export type EducationSecurityPosture = {
  policy_version: string
  protected: boolean
  max_material_bytes: number
  allowed_content_types: string[]
  audit_chain_valid: boolean
  approval_chain_valid: boolean
}

export type EducationClassroom = {
  version: string
  classroom_id: string
  title: string
  subject: string
  grade_band: string
  teacher_name: string
  description: string
  default_template_id: string
  standards_focus: string[]
  safety_mode: string
  created_at: string
  updated_at: string
  students: EducationStudent[]
  assignments: EducationAssignment[]
  evidence_library: EducationMaterial[]
  shared_layer: Record<string, unknown>
  security_posture?: EducationSecurityPosture | null
  security_bootstrap?: EducationSecurityBootstrap | null
  student_count: number
  assignment_count: number
  evidence_count: number
  project_count: number
}

export type EducationAgentCatalogEntry = {
  name: string
  display_name: string
  role: EducationRole
  description: string
  allowed_tool_scopes: string[]
  artifact_types: string[]
}

export type EducationApproval = {
  approval_id: string
  status: 'pending' | 'approved' | 'rejected'
  requested_at: string
  reviewed_at?: string | null
  reviewer: string
  note: string
  agent_name: string
  role: string
  classroom_id?: string | null
  assignment_id?: string | null
  student_id?: string | null
  project_slug?: string | null
  requested_actions: string[]
  prompt_excerpt: string
  rationale: string
  risk_assessment?: EducationRiskAssessment | null
  prev_hash?: string | null
  entry_hash?: string | null
}

export type EducationAuditEntry = {
  audit_id: string
  created_at: string
  actor_role: string
  agent_name: string
  action: string
  summary: string
  classroom_id?: string | null
  assignment_id?: string | null
  student_id?: string | null
  project_slug?: string | null
  allowed_actions: string[]
  sensitive_actions_requested: string[]
  status: string
  prompt_excerpt?: string | null
  risk_assessment?: EducationRiskAssessment | null
  ai_usage?: Record<string, unknown> | null
  prev_hash?: string | null
  entry_hash?: string | null
}

export type EducationRiskAssessment = {
  score: number
  band: 'low' | 'moderate' | 'high' | 'critical'
  signals: string[]
  policy_actions: string[]
  redacted_excerpt: string
}

export type EducationSafetyStatus = {
  policy_name: string
  mode: string
  approval_required_for: string[]
  blocked_capabilities: string[]
  role_policies: EducationRoleModel[]
  allowed_tool_scopes: string[]
  pending_approvals: number
  audit_entries: number
  last_audit_entries: EducationAuditEntry[]
  audit_chain_valid: boolean
  approval_chain_valid: boolean
  material_policy: Record<string, unknown>
  provider_ai_profiles: number
}

export type EducationAgentRunResponse = {
  run_id: string
  agent_name: string
  display_name: string
  role: string
  summary: string
  allowed_actions: string[]
  blocked_capabilities: string[]
  requires_approval: boolean
  sensitive_actions_requested: string[]
  risk_assessment: EducationRiskAssessment
  approval_request: EducationApproval | null
  artifacts: Record<string, unknown>
  provider_ai?: Record<string, unknown> | null
  audit_entry: EducationAuditEntry
}

export type EducationAuditResponse = {
  entries: EducationAuditEntry[]
}

export type EducationLaunchResponse = {
  classroom: EducationClassroom
  project: StudioProject
  seeded_material_count: number
}

export type GrowthRouteDecision = {
  task_kind: string
  execution_mode: 'no-llm' | 'local-llm' | 'provider-ai'
  required_capability: string
  reason: string
  selected_provider?: {
    provider_id: string
    provider_label: string
    profile_id: string
    profile_label: string
    auth_mode: string
    model: string
  } | null
  local_available: boolean
  provider_available: boolean
}

export type CitationVerification = {
  ready_for_export: boolean
  overall_score: number
  verified_claims: Array<Record<string, unknown>>
  blocked_claims: Array<Record<string, unknown>>
}

export type AssessmentPack = {
  assignment_id: string
  assignment_title: string
  route: GrowthRouteDecision
  quiz_questions: Array<Record<string, unknown>>
  discussion_prompts: string[]
  exit_tickets: string[]
  differentiated_supports: Array<Record<string, unknown>>
  teacher_note: string
}

export type StandardsMap = {
  classroom_id: string
  assignment_id: string
  assignment_title: string
  standards_alignment: Array<Record<string, unknown>>
  district_rubric_map: Array<Record<string, unknown>>
  teacher_moves: string[]
}

export type AssignmentAutopilotResponse = {
  classroom: EducationClassroom
  assignment: EducationAssignment
  route: GrowthRouteDecision
  evidence_pack: EducationMaterial[]
  checkpoints: Array<Record<string, unknown>>
  export_targets: string[]
  assessment_pack: AssessmentPack
  standards_map: StandardsMap
  lesson_to_project_scaffold: Record<string, unknown>
  teacher_summary: string
}

export type RevisionCoachResponse = {
  route: GrowthRouteDecision
  rubric_breakdown: Array<Record<string, unknown>>
  citation_verification: CitationVerification
  revision_tasks: string[]
  student_summary: string
  family_summary: string
}

export type ClassroomLibrary = {
  classroom_id: string
  teacher_name: string
  item_count: number
  collections: Array<Record<string, unknown>>
  reusable_items: Array<Record<string, unknown>>
  recommended_reuse: Array<Record<string, unknown>>
}

export type PeerReview = {
  review_id: string
  classroom_id: string
  assignment_id: string
  project_slug: string
  reviewer_student_id: string
  reviewer_name: string
  target_student_id: string
  target_student_name: string
  status: string
  summary: string
  rubric_guided_comments: Array<Record<string, unknown>>
  created_at: string
  resolved_at: string
  moderator: string
  note: string
  approval_id: string
}

export type PeerReviewPairings = {
  classroom_id: string
  assignment_id: string
  assignment_title: string
  pair_count: number
  pairs: Array<Record<string, unknown>>
}

export type FamilyView = {
  classroom_id: string
  classroom_title: string
  project_slug: string
  project_title: string
  student_name: string
  assignment_title: string
  summary: string
  progress: Record<string, unknown>
  teacher_comments: Array<Record<string, unknown>>
  next_steps: string[]
  downloads: ProjectExport[]
  share_link: string
}

export type FamilyShareLink = {
  share_token: string
  classroom_id: string
  project_slug: string
  project_title: string
  created_at: string
  share_url: string
}

export type LessonToProjectResponse = {
  project: StudioProject
  route: GrowthRouteDecision
  scaffold: Record<string, unknown>
}

export type RubricTrainResponse = {
  model_id: string
  classroom_id: string
  created_at: string
  trained_on_projects: string[]
  criterion_patterns: Array<Record<string, unknown>>
  quality_signals: string[]
}

export type InterventionDashboard = {
  classroom_id: string
  classroom_title: string
  summary: Record<string, unknown>
  student_signals: Array<Record<string, unknown>>
  interventions: string[]
}

export type ClassroomRoster = {
  classroom_id: string
  classroom_title: string
  students: Array<Record<string, unknown>>
  summary: Record<string, number>
}

export type ClassroomReplay = {
  classroom_id: string
  classroom_title: string
  counts: Record<string, number>
  timeline: Array<Record<string, unknown>>
}

export type AssignmentStatusBoard = {
  classroom_id: string
  classroom_title: string
  assignments: Array<Record<string, unknown>>
}

export type MarketplaceSchoolPack = {
  pack_id: string
  label: string
  audience: string
  description: string
  recommended_template_ids: string[]
  sample_project_slug: string
  plugin_ids: string[]
  offline_ready: boolean
  installed: boolean
  installed_at: string
  manifest_path: string
}

export type MarketplaceResponse = {
  templates: StudioTemplate[]
  sample_projects: StudioSampleProject[]
  plugins: StudioPlugin[]
  school_packs: MarketplaceSchoolPack[]
  plugin_sdk: Record<string, unknown>
  offline_school_edition: Record<string, unknown>
}

export type SchoolPackInstallResponse = {
  pack_id: string
  label: string
  installed_at: string
  manifest_path: string
  created_samples: string[]
  recommended_templates: string[]
}

export type OfflineSchoolEdition = {
  edition_name: string
  readiness_score: number
  supported_modes: string[]
  local_capabilities: Record<string, boolean>
  recommended_rollout: string[]
  installed_assets: string[]
}

export type EducationGrowthOverview = {
  counts: Record<string, number>
  routing_matrix: Array<Record<string, unknown>>
  offline_school_edition: OfflineSchoolEdition
}

export type EduClawnSourceSummary = {
  available: boolean
  path: string
  package_name: string
  version: string
  license: string
  node_requirement: string
  counts: {
    extensions: number
    skills: number
    apps: number
    channels: number
  }
  channels: string[]
  skills: string[]
  dangerous_tools: string[]
  key_paths?: Record<string, string> | null
}

export type EduClawnOverview = {
  product_name: string
  tagline: string
  source_summary: EduClawnSourceSummary
  product_shape: Record<string, string>
  derived_control_plane: Record<string, unknown>
  education_templates: Array<Record<string, string>>
  implementation_status: Record<string, boolean>
}

export type EduClawnControlPlane = {
  version: string
  product: Record<string, unknown>
  school: Record<string, unknown>
  gateway: Record<string, unknown>
  roles: Record<string, unknown>
  tools: Record<string, unknown>
  skills: Record<string, unknown>
  templates: Record<string, unknown>
  security: Record<string, unknown>
}

export type EduClawnBootstrapResponse = {
  classroom: EducationClassroom
  assignment: EducationAssignment
  control_plane: EduClawnControlPlane
  control_plane_path: string
  attestation_path: string
  source_summary: EduClawnSourceSummary
}
