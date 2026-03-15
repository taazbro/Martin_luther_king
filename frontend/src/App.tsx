import {
  useDeferredValue,
  useEffect,
  useEffectEvent,
  useState,
  useTransition,
  type ChangeEvent,
  type FormEvent,
  type ReactNode,
} from 'react'
import './App.css'
import { ApiError, api } from './api'
import type {
  AdminStatusResponse,
  AIAuthMode,
  AIProviderCatalogEntry,
  AIProviderId,
  AIProviderProfile,
  AIUsageEntry,
  AssignmentAutopilotResponse,
  AssignmentStatusBoard,
  BenchmarkReportResponse,
  ClassroomLibrary,
  ClassroomRoster,
  ClassroomReplay,
  DesktopContext,
  EducationAgentCatalogEntry,
  EducationAgentRunResponse,
  EducationApproval,
  EducationAuditEntry,
  EducationClassroom,
  EducationGrowthOverview,
  EducationOverview,
  EducationSafetyStatus,
  EduClawnBootstrapResponse,
  EduClawnOverview,
  FamilyShareLink,
  FamilyView,
  HealthStatus,
  InterventionDashboard,
  LessonToProjectResponse,
  MarketplaceResponse,
  OfflineSchoolEdition,
  PeerReview,
  PeerReviewPairings,
  ProjectDraft,
  ProjectSummary,
  RevisionCoachResponse,
  RubricTrainResponse,
  SchoolPackInstallResponse,
  StudioAgentCatalogEntry,
  StudioArtifactBundle,
  StudioCompileResponse,
  StudioGraph,
  StudioOverview,
  StudioProject,
  StudioSampleProject,
  StudioSearchResult,
  StudioSystemStatus,
  StudioTemplate,
  StandardsMap,
  AssessmentPack,
  CitationVerification,
} from './types'

const DRAFT_STORAGE_KEY = 'educlawn-draft'
const ADMIN_TOKEN_STORAGE_KEY = 'educlawn-admin-token'
const ONBOARDING_STORAGE_KEY = 'educlawn-onboarding-complete'
const CLASSROOM_ACCESS_STORAGE_KEY = 'educlawn-classroom-access'
const EXPERIENCE_SETTINGS_STORAGE_KEY = 'educlawn-experience-settings'

const defaultDraft: ProjectDraft = {
  title: 'Neighborhood Memory Archive',
  summary: 'A local-first civic project assembled from uploaded documents and community evidence.',
  topic: 'Neighborhood memory, public history, and local civic action',
  audience: 'Middle and high school students',
  goalsText: 'Explain the issue\nCurate source evidence\nBuild an interactive local project',
  rubricText: 'Evidence Quality\nClarity\nAudience Fit\nDesign\nRevision Quality',
  template_id: 'mlk-legacy-lab',
  local_mode: 'no-llm',
  ai_profile_id: '',
}

const defaultCredentials = {
  username: 'admin',
  password: 'mlk-admin-demo',
}

const defaultClassroomDraft = {
  title: 'Civics Period 3',
  subject: 'Civics',
  grade_band: 'Grades 8-10',
  teacher_name: 'Ms. Rivera',
  description: 'A bounded classroom workspace for local-first research, projects, and teacher review.',
  default_template_id: 'lesson-module',
  standardsText: 'C3 Inquiry\nSource Analysis',
}

const defaultStudentDraft = {
  name: 'Jordan Lee',
  grade_level: 'Grade 9',
  learningGoalsText: 'Use stronger evidence\nPractice citations',
  notes: 'Interested in local policy and community history.',
}

const defaultAssignmentDraft = {
  title: 'Water Justice Brief',
  summary: 'Investigate a civic issue with approved evidence and build a cited student project.',
  topic: 'Clean water access and local infrastructure',
  audience: 'Grade 9 students',
  template_id: 'research-portfolio',
  goalsText: 'Compare local evidence\nDraft an evidence-backed claim',
  rubricText: 'Evidence Quality\nCitation Accuracy\nClarity',
  standardsText: 'C3 Inquiry\nArgument Writing',
  due_date: '2026-04-15',
  local_mode: 'no-llm' as 'no-llm' | 'local-llm' | 'provider-ai',
  ai_profile_id: '',
}

const defaultEducationAgentDraft = {
  role: 'teacher' as const,
  agent_name: 'lesson-planner',
  prompt: 'Build a bounded classroom plan using only approved materials and teacher-reviewed steps.',
  ai_profile_id: '',
}

const defaultAutopilotDraft = {
  topic: 'Neighborhood transit access and mobility justice',
  title: '',
  summary: '',
  audience: 'Grade 9 students',
  template_id: '',
  goalsText: 'Compare approved sources\nBuild a cited local argument',
  rubricText: 'Evidence Quality\nCitation Accuracy\nClarity',
  standardsText: 'C3 Inquiry\nSource Analysis',
  lessonSeed: 'Use approved maps, resident testimony, and policy memos to build a classroom-safe inquiry workflow.',
  due_date: '2026-05-01',
  local_mode: 'no-llm' as 'no-llm' | 'local-llm' | 'provider-ai',
  ai_profile_id: '',
}

const defaultRevisionCoachDraft = {
  draftText: (
    'Neighborhood transit access is unequal because some families wait longer and walk farther for buses. '
    + 'Policy memos and resident interviews show that neighborhoods with fewer route investments have slower service.'
  ),
  teacherFeedbackText: 'Add one stronger source comparison.\nMake the main claim more explicit.',
  ai_profile_id: '',
}

const defaultLessonProjectDraft = {
  lessonPlan: (
    'Community Transit Lesson\n'
    + '- Analyze approved maps and testimony\n'
    + '- Build a short evidence-backed recommendation\n'
    + '- Close with an exit ticket'
  ),
  title: '',
  topic: '',
  audience: '',
  goalsText: '',
  rubricText: '',
  template_id: '',
  local_mode: 'no-llm' as 'no-llm' | 'local-llm' | 'provider-ai',
  ai_profile_id: '',
  seed_from_classroom: true,
}

const defaultPeerReviewDraft = {
  draftText: 'The draft uses local evidence, but it needs one clearer citation and a stronger conclusion.',
  rubricText: 'Evidence Quality\nCitation Accuracy\nClarity',
}

const defaultPeerReviewResolution = {
  reviewer: 'Ms. Rivera',
  note: 'Peer feedback is safe and useful for revision.',
}

const defaultApprovalReview = {
  reviewer: 'Ms. Rivera',
  note: 'Teacher reviewed. Sensitive external actions still require manual handling.',
}

const defaultEduClawnDraft = {
  school_name: 'Roosevelt High',
  classroom_title: 'Civics 2A',
  teacher_name: 'Ms. Rivera',
  subject: 'Civics',
  grade_band: 'Grades 9-10',
  description: 'EduClawn control plane for a bounded classroom runtime.',
  default_template_id: 'lesson-module',
  template_id: 'research-portfolio',
  assignment_title: 'Community Archive Brief',
  assignment_summary: 'Create a cited classroom-safe project from approved evidence.',
  topic: 'Community archives and local history',
  audience: 'Grade 10 students',
  goalsText: 'Use approved evidence\nBuild a cited brief',
  rubricText: 'Evidence Quality\nCitation Accuracy',
  standardsText: 'Source Analysis\nCivic Inquiry',
  due_date: '2026-04-20',
  local_mode: 'no-llm' as 'no-llm' | 'local-llm' | 'provider-ai',
  ai_profile_id: '',
}

const defaultAiProfileDraft = {
  label: 'Teacher OpenAI Workspace',
  provider_id: 'openai' as AIProviderId,
  auth_mode: 'user-key' as AIAuthMode,
  api_key: '',
  default_model: 'gpt-5-mini',
  base_url: '',
  capabilitiesText: 'research\nassignments\nfeedback',
}

type ClassroomAccessKeys = {
  teacher_access_key: string
  student_access_key: string
  reviewer_access_key: string
  issued_at: string
}

type ExperienceProfile = 'teacher' | 'student' | 'family' | 'builder'
type ExperienceLevel = 'guided' | 'standard' | 'advanced'

type ExperienceSettings = {
  profile: ExperienceProfile
  level: ExperienceLevel
  simplifiedDashboard: boolean
  largeText: boolean
  reducedMotion: boolean
}

type PageId = 'home' | 'projects' | 'classroom' | 'autopilot' | 'ops' | 'family' | 'marketplace' | 'ai' | 'desktop' | 'advanced'
type ProjectView = 'create' | 'build' | 'review'
type ClassroomView = 'setup' | 'launch' | 'safety'

const defaultExperienceSettings: ExperienceSettings = {
  profile: 'teacher',
  level: 'guided',
  simplifiedDashboard: true,
  largeText: false,
  reducedMotion: false,
}

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [overview, setOverview] = useState<StudioOverview | null>(null)
  const [systemStatus, setSystemStatus] = useState<StudioSystemStatus | null>(null)
  const [desktopContext, setDesktopContext] = useState<DesktopContext | null>(null)
  const [aiCatalog, setAiCatalog] = useState<AIProviderCatalogEntry[]>([])
  const [aiProfiles, setAiProfiles] = useState<AIProviderProfile[]>([])
  const [aiUsage, setAiUsage] = useState<AIUsageEntry[]>([])
  const [aiProfileDraft, setAiProfileDraft] = useState(defaultAiProfileDraft)
  const [selectedAiProfileId, setSelectedAiProfileId] = useState('')
  const [templates, setTemplates] = useState<StudioTemplate[]>([])
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [agentCatalog, setAgentCatalog] = useState<StudioAgentCatalogEntry[]>([])
  const [educationOverview, setEducationOverview] = useState<EducationOverview | null>(null)
  const [educationClassrooms, setEducationClassrooms] = useState<EducationClassroom[]>([])
  const [educationAgentCatalog, setEducationAgentCatalog] = useState<EducationAgentCatalogEntry[]>([])
  const [educationApprovals, setEducationApprovals] = useState<EducationApproval[]>([])
  const [educationAudit, setEducationAudit] = useState<EducationAuditEntry[]>([])
  const [educationSafety, setEducationSafety] = useState<EducationSafetyStatus | null>(null)
  const [growthOverview, setGrowthOverview] = useState<EducationGrowthOverview | null>(null)
  const [classroomLibrary, setClassroomLibrary] = useState<ClassroomLibrary | null>(null)
  const [peerReviews, setPeerReviews] = useState<PeerReview[]>([])
  const [peerReviewPairs, setPeerReviewPairs] = useState<PeerReviewPairings | null>(null)
  const [familyView, setFamilyView] = useState<FamilyView | null>(null)
  const [familyShareLink, setFamilyShareLink] = useState<FamilyShareLink | null>(null)
  const [interventionDashboard, setInterventionDashboard] = useState<InterventionDashboard | null>(null)
  const [classroomRoster, setClassroomRoster] = useState<ClassroomRoster | null>(null)
  const [assignmentStatusBoard, setAssignmentStatusBoard] = useState<AssignmentStatusBoard | null>(null)
  const [classroomReplay, setClassroomReplay] = useState<ClassroomReplay | null>(null)
  const [marketplace, setMarketplace] = useState<MarketplaceResponse | null>(null)
  const [offlineSchoolEdition, setOfflineSchoolEdition] = useState<OfflineSchoolEdition | null>(null)
  const [autopilotDraft, setAutopilotDraft] = useState(defaultAutopilotDraft)
  const [revisionCoachDraft, setRevisionCoachDraft] = useState(defaultRevisionCoachDraft)
  const [lessonProjectDraft, setLessonProjectDraft] = useState(defaultLessonProjectDraft)
  const [peerReviewDraft, setPeerReviewDraft] = useState(defaultPeerReviewDraft)
  const [peerReviewResolution, setPeerReviewResolution] = useState(defaultPeerReviewResolution)
  const [autopilotResult, setAutopilotResult] = useState<AssignmentAutopilotResponse | null>(null)
  const [revisionCoachResult, setRevisionCoachResult] = useState<RevisionCoachResponse | null>(null)
  const [citationVerification, setCitationVerification] = useState<CitationVerification | null>(null)
  const [lessonProjectResult, setLessonProjectResult] = useState<LessonToProjectResponse | null>(null)
  const [rubricModel, setRubricModel] = useState<RubricTrainResponse | null>(null)
  const [standardsMap, setStandardsMap] = useState<StandardsMap | null>(null)
  const [assessmentPack, setAssessmentPack] = useState<AssessmentPack | null>(null)
  const [lastInstalledPack, setLastInstalledPack] = useState<SchoolPackInstallResponse | null>(null)
  const [educlawnOverview, setEduclawnOverview] = useState<EduClawnOverview | null>(null)
  const [educlawnDraft, setEduclawnDraft] = useState(defaultEduClawnDraft)
  const [educlawnBootstrapResult, setEduclawnBootstrapResult] = useState<EduClawnBootstrapResponse | null>(null)
  const [selectedClassroomId, setSelectedClassroomId] = useState<string>('')
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<string>('')
  const [selectedStudentId, setSelectedStudentId] = useState<string>('')
  const [classroomAccessVault, setClassroomAccessVault] = useState<Record<string, ClassroomAccessKeys>>(() => {
    const saved = window.localStorage.getItem(CLASSROOM_ACCESS_STORAGE_KEY)
    if (!saved) {
      return {}
    }
    try {
      return JSON.parse(saved) as Record<string, ClassroomAccessKeys>
    } catch {
      return {}
    }
  })
  const [experienceSettings, setExperienceSettings] = useState<ExperienceSettings>(() => {
    const saved = window.localStorage.getItem(EXPERIENCE_SETTINGS_STORAGE_KEY)
    if (!saved) {
      return defaultExperienceSettings
    }
    try {
      return { ...defaultExperienceSettings, ...(JSON.parse(saved) as Partial<ExperienceSettings>) }
    } catch {
      return defaultExperienceSettings
    }
  })
  const [classroomDraft, setClassroomDraft] = useState(defaultClassroomDraft)
  const [studentDraft, setStudentDraft] = useState(defaultStudentDraft)
  const [assignmentDraft, setAssignmentDraft] = useState(defaultAssignmentDraft)
  const [educationAgentDraft, setEducationAgentDraft] = useState<{
    role: 'teacher' | 'student' | 'shared'
    agent_name: string
    prompt: string
    ai_profile_id: string
  }>(defaultEducationAgentDraft)
  const [educationAgentResult, setEducationAgentResult] = useState<EducationAgentRunResponse | null>(null)
  const [approvalReview, setApprovalReview] = useState(defaultApprovalReview)
  const [selectedProjectSlug, setSelectedProjectSlug] = useState<string>('')
  const [project, setProject] = useState<StudioProject | null>(null)
  const [artifactBundle, setArtifactBundle] = useState<StudioArtifactBundle | null>(null)
  const [compileResult, setCompileResult] = useState<StudioCompileResponse | null>(null)
  const [graph, setGraph] = useState<StudioGraph | null>(null)
  const [searchResults, setSearchResults] = useState<StudioSearchResult[]>([])
  const [searchQuery, setSearchQuery] = useState('local evidence civic strategy')
  const [draft, setDraft] = useState<ProjectDraft>(() => {
    const saved = window.localStorage.getItem(DRAFT_STORAGE_KEY)
    if (!saved) {
      return defaultDraft
    }
    try {
      return JSON.parse(saved) as ProjectDraft
    } catch {
      return defaultDraft
    }
  })
  const [credentials, setCredentials] = useState(defaultCredentials)
  const [token, setToken] = useState(() => window.localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY) ?? '')
  const [adminStatus, setAdminStatus] = useState<AdminStatusResponse | null>(null)
  const [benchmark, setBenchmark] = useState<BenchmarkReportResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [authError, setAuthError] = useState<string | null>(null)
  const [activePage, setActivePage] = useState<PageId>('home')
  const [projectView, setProjectView] = useState<ProjectView>('create')
  const [classroomView, setClassroomView] = useState<ClassroomView>('setup')
  const [isBooting, setIsBooting] = useState(true)
  const [isWorking, setIsWorking] = useState(false)
  const [isOnboardingComplete, setIsOnboardingComplete] = useState(
    () => window.localStorage.getItem(ONBOARDING_STORAGE_KEY) === 'true',
  )
  const [importTitle, setImportTitle] = useState('')
  const [teacherComment, setTeacherComment] = useState({
    author: 'Teacher',
    criterion: '',
    body: '',
  })
  const [isPending, startTransition] = useTransition()

  const deferredHealth = useDeferredValue(health)
  const deferredOverview = useDeferredValue(overview)
  const deferredSystemStatus = useDeferredValue(systemStatus)
  const deferredDesktopContext = useDeferredValue(desktopContext)
  const deferredAiCatalog = useDeferredValue(aiCatalog)
  const deferredAiProfiles = useDeferredValue(aiProfiles)
  const deferredAiUsage = useDeferredValue(aiUsage)
  const deferredTemplates = useDeferredValue(templates)
  const deferredProjects = useDeferredValue(projects)
  const deferredEducationOverview = useDeferredValue(educationOverview)
  const deferredEducationClassrooms = useDeferredValue(educationClassrooms)
  const deferredEducationApprovals = useDeferredValue(educationApprovals)
  const deferredEducationAudit = useDeferredValue(educationAudit)
  const deferredEducationSafety = useDeferredValue(educationSafety)
  const deferredGrowthOverview = useDeferredValue(growthOverview)
  const deferredClassroomLibrary = useDeferredValue(classroomLibrary)
  const deferredPeerReviews = useDeferredValue(peerReviews)
  const deferredPeerReviewPairs = useDeferredValue(peerReviewPairs)
  const deferredFamilyView = useDeferredValue(familyView)
  const deferredFamilyShareLink = useDeferredValue(familyShareLink)
  const deferredInterventionDashboard = useDeferredValue(interventionDashboard)
  const deferredClassroomRoster = useDeferredValue(classroomRoster)
  const deferredAssignmentStatusBoard = useDeferredValue(assignmentStatusBoard)
  const deferredClassroomReplay = useDeferredValue(classroomReplay)
  const deferredMarketplace = useDeferredValue(marketplace)
  const deferredOfflineSchoolEdition = useDeferredValue(offlineSchoolEdition)
  const deferredAutopilotResult = useDeferredValue(autopilotResult)
  const deferredRevisionCoachResult = useDeferredValue(revisionCoachResult)
  const deferredCitationVerification = useDeferredValue(citationVerification)
  const deferredLessonProjectResult = useDeferredValue(lessonProjectResult)
  const deferredRubricModel = useDeferredValue(rubricModel)
  const deferredStandardsMap = useDeferredValue(standardsMap)
  const deferredAssessmentPack = useDeferredValue(assessmentPack)
  const deferredLastInstalledPack = useDeferredValue(lastInstalledPack)
  const deferredEduclawnOverview = useDeferredValue(educlawnOverview)
  const deferredEduclawnBootstrapResult = useDeferredValue(educlawnBootstrapResult)
  const deferredProject = useDeferredValue(project)
  const deferredArtifacts = useDeferredValue(artifactBundle)
  const deferredGraph = useDeferredValue(graph)
  const deferredSearchResults = useDeferredValue(searchResults)
  const deferredBenchmark = useDeferredValue(benchmark)
  const deferredAdminStatus = useDeferredValue(adminStatus)

  const refreshStudio = useEffectEvent(async (showBootRibbon = false) => {
    if (showBootRibbon) {
      setIsBooting(true)
    }

    setError(null)

    try {
      const [healthResponse, overviewResponse, systemStatusResponse, templateResponse, projectResponse, catalogResponse] = await Promise.all([
        api.health(),
        api.studioOverview(),
        api.studioSystemStatus(),
        api.studioTemplates(),
        api.studioProjects(),
        api.studioAgentCatalog(),
      ])

      startTransition(() => {
        setHealth(healthResponse)
        setOverview(overviewResponse)
        setSystemStatus(systemStatusResponse)
        setTemplates(templateResponse)
        setProjects(projectResponse)
        setAgentCatalog(catalogResponse)
      })

      if (!selectedProjectSlug && projectResponse.length > 0) {
        setSelectedProjectSlug(projectResponse[0].slug)
      }
    } catch (refreshError) {
      setError(getErrorMessage(refreshError, 'Failed to load EduClawn.'))
    } finally {
      if (showBootRibbon) {
        setIsBooting(false)
      }
    }
  })

  const refreshAi = useEffectEvent(async () => {
    try {
      const [catalogResponse, profilesResponse, usageResponse] = await Promise.all([
        api.aiProviderCatalog(),
        api.aiProfiles(),
        api.aiUsage(),
      ])
      startTransition(() => {
        setAiCatalog(catalogResponse)
        setAiProfiles(profilesResponse)
        setAiUsage(usageResponse)
      })
    } catch (aiError) {
      setError(getErrorMessage(aiError, 'Failed to load AI providers.'))
    }
  })

  const refreshEducation = useEffectEvent(async () => {
    try {
      const [overviewResponse, classroomResponse, agentResponse, safetyResponse] = await Promise.all([
        api.educationOverview(),
        api.educationClassrooms(),
        api.educationAgentCatalog(),
        api.educationSafety(),
      ])
      const activeClassroomId = selectedClassroomId || classroomResponse[0]?.classroom_id || ''
      const activeKeys = activeClassroomId ? classroomAccessVault[activeClassroomId] : undefined
      let approvalResponse: EducationApproval[] = []
      let auditEntries: EducationAuditEntry[] = []

      if (activeClassroomId && activeKeys) {
        const [approvalsResponse, auditResponse] = await Promise.all([
          api.educationApprovals(activeClassroomId, activeKeys.reviewer_access_key || activeKeys.teacher_access_key),
          api.educationAudit(activeClassroomId, activeKeys.teacher_access_key || activeKeys.reviewer_access_key),
        ])
        approvalResponse = approvalsResponse
        auditEntries = auditResponse.entries
      }

      startTransition(() => {
        setEducationOverview(overviewResponse)
        setEducationClassrooms(classroomResponse)
        setEducationAgentCatalog(agentResponse)
        setEducationApprovals(approvalResponse)
        setEducationAudit(auditEntries)
        setEducationSafety(safetyResponse)
      })

      if (!selectedClassroomId && classroomResponse.length > 0) {
        setSelectedClassroomId(classroomResponse[0].classroom_id)
      }
    } catch (educationError) {
      setError(getErrorMessage(educationError, 'Failed to load Education OS.'))
    }
  })

  const refreshGrowth = useEffectEvent(async () => {
    try {
      const [overviewResponse, marketplaceResponse, offlineResponse] = await Promise.all([
        api.educationGrowthOverview(),
        api.marketplace(),
        api.offlineSchoolEdition(),
      ])

      let libraryResponse: ClassroomLibrary | null = null
      let reviewResponse: PeerReview[] = []
      let reviewPairsResponse: PeerReviewPairings | null = null
      let interventionResponse: InterventionDashboard | null = null
      let rosterResponse: ClassroomRoster | null = null
      let assignmentStatusResponse: AssignmentStatusBoard | null = null
      let replayResponse: ClassroomReplay | null = null
      let standardsResponse: StandardsMap | null = null
      let familyResponse: FamilyView | null = null

      const teacherOrReviewerKey = selectedClassroomId
        ? classroomAccessVault[selectedClassroomId]?.teacher_access_key || classroomAccessVault[selectedClassroomId]?.reviewer_access_key || ''
        : ''
      const anyAccessKey = selectedClassroomId
        ? classroomAccessVault[selectedClassroomId]?.teacher_access_key
            || classroomAccessVault[selectedClassroomId]?.reviewer_access_key
            || classroomAccessVault[selectedClassroomId]?.student_access_key
            || ''
        : ''

      if (selectedClassroomId && teacherOrReviewerKey) {
        const requests: Array<Promise<unknown>> = [
          api.classroomLibrary(selectedClassroomId, teacherOrReviewerKey),
          api.listPeerReviews(selectedClassroomId, teacherOrReviewerKey),
          api.interventionDashboard(selectedClassroomId, teacherOrReviewerKey),
          api.classroomRoster(selectedClassroomId, teacherOrReviewerKey),
          api.assignmentStatusBoard(selectedClassroomId, teacherOrReviewerKey),
          api.classroomReplay(selectedClassroomId, teacherOrReviewerKey),
        ]

        if (selectedAssignmentId) {
          requests.push(api.peerReviewPairs(selectedClassroomId, selectedAssignmentId, teacherOrReviewerKey))
        }

        if (selectedAssignmentId) {
          requests.push(api.standardsMap(selectedClassroomId, selectedAssignmentId, teacherOrReviewerKey))
        }

        if (selectedProjectSlug && anyAccessKey) {
          requests.push(api.familyView(selectedClassroomId, selectedProjectSlug, anyAccessKey))
        }

        const results = await Promise.all(requests)
        libraryResponse = results[0] as ClassroomLibrary
        reviewResponse = results[1] as PeerReview[]
        interventionResponse = results[2] as InterventionDashboard
        rosterResponse = results[3] as ClassroomRoster
        assignmentStatusResponse = results[4] as AssignmentStatusBoard
        replayResponse = results[5] as ClassroomReplay
        reviewPairsResponse = selectedAssignmentId ? (results[6] as PeerReviewPairings) : null
        standardsResponse = selectedAssignmentId ? (results[selectedAssignmentId ? 7 : 6] as StandardsMap) : null
        familyResponse = selectedProjectSlug && anyAccessKey
          ? (results[selectedAssignmentId ? 8 : 6] as FamilyView)
          : null
      }

      startTransition(() => {
        setGrowthOverview(overviewResponse)
        setMarketplace(marketplaceResponse)
        setOfflineSchoolEdition(offlineResponse)
        setClassroomLibrary(libraryResponse)
        setPeerReviews(reviewResponse)
        setPeerReviewPairs(reviewPairsResponse)
        setInterventionDashboard(interventionResponse)
        setClassroomRoster(rosterResponse)
        setAssignmentStatusBoard(assignmentStatusResponse)
        setClassroomReplay(replayResponse)
        setStandardsMap(standardsResponse)
        setFamilyView(familyResponse)
        setFamilyShareLink(
          familyResponse?.share_link
            ? {
                share_token: '',
                classroom_id: familyResponse.classroom_id,
                project_slug: familyResponse.project_slug,
                project_title: familyResponse.project_title,
                created_at: '',
                share_url: familyResponse.share_link,
              }
            : null,
        )
      })
    } catch (growthError) {
      setError(getErrorMessage(growthError, 'Failed to load EduClawn growth features.'))
    }
  })

  const refreshEduClawn = useEffectEvent(async () => {
    try {
      const overviewResponse = await api.educlawnOverview()
      startTransition(() => {
        setEduclawnOverview(overviewResponse)
      })
    } catch (educlawnError) {
      setError(getErrorMessage(educlawnError, 'Failed to load EduClawn.'))
    }
  })

  const loadDesktopContext = useEffectEvent(async () => {
    if (!window.educlawnDesktop?.getContext) {
      return
    }
    try {
      const context = await window.educlawnDesktop.getContext()
      startTransition(() => {
        setDesktopContext(context)
      })
    } catch {}
  })

  const loadProject = useEffectEvent(async (slug: string) => {
    if (!slug) {
      return
    }

    setError(null)

    try {
      const [projectResponse, graphResponse] = await Promise.all([
        api.getProject(slug),
        api.projectGraph(slug),
      ])

      let artifactResponse: StudioArtifactBundle | null = null
      try {
        artifactResponse = await api.projectArtifacts(slug)
      } catch (artifactError) {
        if (!(artifactError instanceof ApiError && artifactError.status === 404)) {
          throw artifactError
        }
      }

      startTransition(() => {
        setProject(projectResponse)
        setGraph(graphResponse)
        setArtifactBundle(artifactResponse)
      })
    } catch (projectError) {
      setError(getErrorMessage(projectError, 'Failed to load the selected project.'))
    }
  })

  const refreshAdmin = useEffectEvent(async (activeToken: string) => {
    if (!activeToken) {
      return
    }

    setAuthError(null)

    try {
      const [statusResponse, benchmarkResponse] = await Promise.all([
        api.adminStatus(activeToken),
        api.latestBenchmark(activeToken),
      ])

      startTransition(() => {
        setAdminStatus(statusResponse)
        setBenchmark(benchmarkResponse)
      })
    } catch (adminError) {
      if (isUnauthorized(adminError)) {
        window.localStorage.removeItem(ADMIN_TOKEN_STORAGE_KEY)
        startTransition(() => {
          setToken('')
          setAdminStatus(null)
          setBenchmark(null)
        })
        setAuthError('Admin session expired. Log in again.')
        return
      }

      if (!(adminError instanceof ApiError && adminError.status === 404)) {
        setAuthError(getErrorMessage(adminError, 'Failed to load admin operations.'))
      }
    }
  })

  useEffect(() => {
    void refreshStudio(true)
  }, [])

  useEffect(() => {
    void refreshEducation()
  }, [])

  useEffect(() => {
    void refreshGrowth()
  }, [])

  useEffect(() => {
    void refreshEduClawn()
  }, [])

  useEffect(() => {
    void refreshAi()
  }, [])

  useEffect(() => {
    void loadDesktopContext()
  }, [])

  useEffect(() => {
    if (!window.educlawnDesktop?.onStateChanged) {
      return undefined
    }
    return window.educlawnDesktop.onStateChanged((context) => {
      startTransition(() => {
        setDesktopContext(context)
      })
    })
  }, [])

  useEffect(() => {
    window.localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft))
  }, [draft])

  useEffect(() => {
    window.localStorage.setItem(ONBOARDING_STORAGE_KEY, String(isOnboardingComplete))
  }, [isOnboardingComplete])

  useEffect(() => {
    window.localStorage.setItem(CLASSROOM_ACCESS_STORAGE_KEY, JSON.stringify(classroomAccessVault))
  }, [classroomAccessVault])

  useEffect(() => {
    window.localStorage.setItem(EXPERIENCE_SETTINGS_STORAGE_KEY, JSON.stringify(experienceSettings))
  }, [experienceSettings])

  useEffect(() => {
    if (!selectedProjectSlug) {
      return
    }
    void loadProject(selectedProjectSlug)
  }, [selectedProjectSlug])

  useEffect(() => {
    if (!desktopContext?.pendingProjectSlug) {
      return
    }
    setSelectedProjectSlug(desktopContext.pendingProjectSlug)
    void window.educlawnDesktop?.consumePendingProject?.(desktopContext.pendingProjectSlug)
  }, [desktopContext?.pendingProjectSlug])

  useEffect(() => {
    if (!desktopContext?.recovery.unclean_exit) {
      return
    }
    setNotice('Recovered the desktop session after an unexpected shutdown.')
  }, [desktopContext?.recovery.unclean_exit])

  useEffect(() => {
    if (!desktopContext?.recovery.imported_project_slug || !desktopContext.recovery.imported_path) {
      return
    }
    setNotice(`Imported ${desktopContext.recovery.imported_path} and restored the project locally.`)
  }, [desktopContext?.recovery.imported_path, desktopContext?.recovery.imported_project_slug])

  useEffect(() => {
    if (!project?.slug || !window.educlawnDesktop?.trackProject) {
      return
    }
    void window.educlawnDesktop.trackProject({
      slug: project.slug,
      title: project.title,
    })
  }, [project?.slug, project?.title])

  useEffect(() => {
    if (!selectedClassroomId) {
      return
    }
    void refreshEducation()
  }, [classroomAccessVault, selectedClassroomId])

  useEffect(() => {
    void refreshGrowth()
  }, [classroomAccessVault, selectedAssignmentId, selectedClassroomId, selectedProjectSlug])

  useEffect(() => {
    if (!selectedAiProfileId) {
      return
    }
    if (!aiProfiles.some(profile => profile.profile_id === selectedAiProfileId)) {
      setSelectedAiProfileId('')
      setAiProfileDraft(defaultAiProfileDraft)
    }
  }, [aiProfiles, selectedAiProfileId])

  useEffect(() => {
    if (!token) {
      startTransition(() => {
        setAdminStatus(null)
        setBenchmark(null)
      })
      return
    }
    void refreshAdmin(token)
  }, [token])

  useEffect(() => {
    if (!selectedClassroomId) {
      return
    }

    const classroom = educationClassrooms.find(item => item.classroom_id === selectedClassroomId)
    if (!classroom) {
      return
    }

    if (!selectedAssignmentId || !classroom.assignments.some(item => item.assignment_id === selectedAssignmentId)) {
      setSelectedAssignmentId(classroom.assignments[0]?.assignment_id ?? '')
    }
    if (!selectedStudentId || !classroom.students.some(item => item.student_id === selectedStudentId)) {
      setSelectedStudentId(classroom.students[0]?.student_id ?? '')
    }
  }, [educationClassrooms, selectedAssignmentId, selectedClassroomId, selectedStudentId])

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const created = await api.createProject({
        title: draft.title.trim(),
        summary: draft.summary.trim(),
        topic: draft.topic.trim(),
        audience: draft.audience.trim(),
        goals: linesToArray(draft.goalsText),
        rubric: linesToArray(draft.rubricText),
        template_id: draft.template_id,
        local_mode: draft.local_mode,
        ai_profile_id: draft.ai_profile_id,
      })

      await refreshStudio(false)
      setProjectView('build')
      setActivePage('projects')
      setSelectedProjectSlug(created.slug)
      setNotice(`Created ${created.title}.`)
    } catch (createError) {
      setError(getErrorMessage(createError, 'Failed to create the project.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function saveProjectEdits() {
    if (!project) {
      return
    }

    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const updated = await api.updateProject(project.slug, {
        title: project.title,
        summary: project.summary,
        topic: project.topic,
        audience: project.audience,
        goals: project.goals,
        rubric: project.rubric,
        local_mode: project.local_mode,
        ai_profile_id: project.ai_profile_id,
        sections: project.sections,
        workflow: project.workflow,
        theme_tokens: project.theme_tokens,
      })
      await refreshStudio(false)
      startTransition(() => {
        setProject(updated)
      })
      setNotice(`Saved ${updated.title}.`)
    } catch (saveError) {
      setError(getErrorMessage(saveError, 'Failed to save the project manifest.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function compileProject() {
    if (!project) {
      return
    }

    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const compiled = await api.compileProject(project.slug, project.workflow.stages)
      await refreshStudio(false)
      startTransition(() => {
        setCompileResult(compiled)
        setProject(compiled.project)
        setArtifactBundle(compiled.artifacts)
        setGraph(compiled.knowledge_graph)
        setSearchResults(compiled.retrieval_results)
      })
      if (token) {
        await refreshAdmin(token)
      }
      setProjectView('review')
      setActivePage('projects')
      setNotice(`Compiled ${compiled.project.title} into ${compiled.exports.length} local exports.`)
    } catch (compileError) {
      setError(getErrorMessage(compileError, 'Failed to compile the project.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function runSearch() {
    if (!project) {
      return
    }

    setIsWorking(true)
    setError(null)

    try {
      const results = await api.searchProject(project.slug, searchQuery, 8)
      startTransition(() => {
        setSearchResults(results)
      })
    } catch (searchError) {
      setError(getErrorMessage(searchError, 'Failed to search project evidence.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function uploadDocuments(event: ChangeEvent<HTMLInputElement>) {
    if (!project || !event.target.files?.length) {
      return
    }

    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      for (const file of Array.from(event.target.files)) {
        await api.uploadDocument(project.slug, file)
      }
      await loadProject(project.slug)
      await refreshStudio(false)
      setNotice(`Uploaded ${event.target.files.length} document${event.target.files.length === 1 ? '' : 's'}.`)
      event.target.value = ''
    } catch (uploadError) {
      setError(getErrorMessage(uploadError, 'Failed to upload one or more documents.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function cloneProject() {
    if (!project) {
      return
    }

    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const cloned = await api.cloneProject(project.slug, `${project.title} Clone`)
      await refreshStudio(false)
      setSelectedProjectSlug(cloned.slug)
      setNotice(`Cloned project to ${cloned.title}.`)
    } catch (cloneError) {
      setError(getErrorMessage(cloneError, 'Failed to clone the project.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function importProjectBundle(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) {
      return
    }

    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const imported = await api.importProject(file, importTitle.trim())
      await refreshStudio(false)
      setSelectedProjectSlug(imported.slug)
      setNotice(`Imported backup as ${imported.title}.`)
      setImportTitle('')
      event.target.value = ''
    } catch (importError) {
      setError(getErrorMessage(importError, 'Failed to import the project bundle.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function submitTeacherComment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!project) {
      return
    }

    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const updated = await api.addTeacherComment(project.slug, teacherComment)
      startTransition(() => {
        setProject(updated)
      })
      await refreshStudio(false)
      setTeacherComment({ author: teacherComment.author, criterion: '', body: '' })
      setNotice('Teacher comment saved to the project timeline.')
    } catch (commentError) {
      setError(getErrorMessage(commentError, 'Failed to save the teacher comment.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function createClassroom(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const classroom = await api.createClassroom({
        ...classroomDraft,
        standards_focus: linesToArray(classroomDraft.standardsText),
      })
      storeClassroomAccess(classroom)
      await refreshEducation()
      setSelectedClassroomId(classroom.classroom_id)
      setClassroomView('setup')
      setActivePage('classroom')
      setNotice(`Created classroom ${classroom.title}. Local access keys were stored on this device.`)
    } catch (classroomError) {
      setError(getErrorMessage(classroomError, 'Failed to create the classroom.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function enrollStudent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedClassroomId) {
      return
    }
    const teacherAccessKey = requireClassroomAccess(selectedClassroomId, 'teacher')
    if (!teacherAccessKey) {
      return
    }

    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const classroom = await api.enrollStudent(selectedClassroomId, {
        name: studentDraft.name.trim(),
        grade_level: studentDraft.grade_level.trim(),
        learning_goals: linesToArray(studentDraft.learningGoalsText),
        notes: studentDraft.notes.trim(),
        access_key: teacherAccessKey,
      })
      await refreshEducation()
      setSelectedClassroomId(classroom.classroom_id)
      setSelectedStudentId(classroom.students[classroom.students.length - 1]?.student_id ?? selectedStudentId)
      setNotice(`Enrolled ${studentDraft.name}.`)
    } catch (studentError) {
      setError(getErrorMessage(studentError, 'Failed to enroll the student.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function createAssignment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedClassroomId) {
      return
    }
    const teacherAccessKey = requireClassroomAccess(selectedClassroomId, 'teacher')
    if (!teacherAccessKey) {
      return
    }

    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const classroom = await api.createAssignment(selectedClassroomId, {
        title: assignmentDraft.title.trim(),
        summary: assignmentDraft.summary.trim(),
        topic: assignmentDraft.topic.trim(),
        audience: assignmentDraft.audience.trim(),
        template_id: assignmentDraft.template_id,
        goals: linesToArray(assignmentDraft.goalsText),
        rubric: linesToArray(assignmentDraft.rubricText),
        standards: linesToArray(assignmentDraft.standardsText),
        due_date: assignmentDraft.due_date.trim(),
        local_mode: assignmentDraft.local_mode,
        ai_profile_id: assignmentDraft.ai_profile_id,
        access_key: teacherAccessKey,
      })
      await refreshEducation()
      setSelectedClassroomId(classroom.classroom_id)
      setSelectedAssignmentId(classroom.assignments[classroom.assignments.length - 1]?.assignment_id ?? selectedAssignmentId)
      setClassroomView('launch')
      setNotice(`Created assignment ${assignmentDraft.title}.`)
    } catch (assignmentError) {
      setError(getErrorMessage(assignmentError, 'Failed to create the assignment.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function uploadClassroomMaterials(event: ChangeEvent<HTMLInputElement>) {
    if (!selectedClassroomId || !event.target.files?.length) {
      return
    }
    const teacherAccessKey = requireClassroomAccess(selectedClassroomId, 'teacher')
    if (!teacherAccessKey) {
      return
    }

    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      for (const file of Array.from(event.target.files)) {
        await api.uploadClassroomMaterial(selectedClassroomId, file, teacherAccessKey, selectedAssignmentId)
      }
      await refreshEducation()
      setNotice(`Uploaded ${event.target.files.length} classroom material${event.target.files.length === 1 ? '' : 's'}.`)
      event.target.value = ''
    } catch (materialError) {
      setError(getErrorMessage(materialError, 'Failed to upload classroom material.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function launchStudentProject() {
    if (!selectedClassroomId || !selectedAssignmentId || !selectedStudentId) {
      return
    }
    const teacherAccessKey = requireClassroomAccess(selectedClassroomId, 'teacher')
    if (!teacherAccessKey) {
      return
    }

    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const launch = await api.launchStudentProject(selectedClassroomId, {
        assignment_id: selectedAssignmentId,
        student_id: selectedStudentId,
        access_key: teacherAccessKey,
      })
      await refreshEducation()
      await refreshStudio(false)
      setSelectedClassroomId(launch.classroom.classroom_id)
      setSelectedProjectSlug(launch.project.slug)
      setClassroomView('launch')
      setProjectView('build')
      setActivePage('classroom')
      startTransition(() => {
        setProject(launch.project)
      })
      setNotice(`Launched ${launch.project.title} with ${launch.seeded_material_count} approved classroom materials.`)
    } catch (launchError) {
      setError(getErrorMessage(launchError, 'Failed to launch the student project.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function runEducationAgent() {
    if (!selectedClassroomId) {
      return
    }
    const accessKey = requireRoleAccess(selectedClassroomId, educationAgentDraft.role)
    if (!accessKey) {
      return
    }

    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const result = await api.runEducationAgent({
        role: educationAgentDraft.role,
        agent_name: educationAgentDraft.agent_name,
        classroom_id: selectedClassroomId,
        assignment_id: selectedAssignmentId || undefined,
        student_id: selectedStudentId || undefined,
        project_slug: selectedProjectSlug || undefined,
        ai_profile_id: educationAgentDraft.ai_profile_id || undefined,
        access_key: accessKey,
        prompt: educationAgentDraft.prompt.trim(),
      })
      await refreshEducation()
      startTransition(() => {
        setEducationAgentResult(result)
      })
      if (result.requires_approval) {
        setClassroomView('safety')
      }
      setNotice(result.requires_approval ? 'Agent run completed and queued a sensitive action for approval.' : 'Education agent run completed.')
    } catch (agentError) {
      setError(getErrorMessage(agentError, 'Failed to run the education agent.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function runAssignmentAutopilot(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedClassroomId) {
      setError('Create or select a classroom before running Assignment Autopilot.')
      return
    }
    const teacherAccessKey = requireClassroomAccess(selectedClassroomId, 'teacher')
    if (!teacherAccessKey) {
      return
    }

    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const result = await api.assignmentAutopilot({
        classroom_id: selectedClassroomId,
        access_key: teacherAccessKey,
        topic: autopilotDraft.topic.trim(),
        title: autopilotDraft.title.trim(),
        summary: autopilotDraft.summary.trim(),
        audience: autopilotDraft.audience.trim(),
        template_id: autopilotDraft.template_id,
        goals: linesToArray(autopilotDraft.goalsText),
        rubric: linesToArray(autopilotDraft.rubricText),
        standards: linesToArray(autopilotDraft.standardsText),
        lesson_seed: autopilotDraft.lessonSeed.trim(),
        due_date: autopilotDraft.due_date.trim(),
        local_mode: autopilotDraft.local_mode,
        ai_profile_id: autopilotDraft.ai_profile_id,
      })
      await Promise.all([refreshEducation(), refreshGrowth(), refreshStudio(false)])
      setSelectedClassroomId(result.classroom.classroom_id)
      setSelectedAssignmentId(result.assignment.assignment_id)
      startTransition(() => {
        setAutopilotResult(result)
        setAssessmentPack(result.assessment_pack)
        setStandardsMap(result.standards_map)
      })
      setActivePage('autopilot')
      setNotice(`Assignment Autopilot created ${result.assignment.title}.`)
    } catch (autopilotError) {
      setError(getErrorMessage(autopilotError, 'Failed to run Assignment Autopilot.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function runRevisionCoach() {
    if (!selectedClassroomId || !selectedAssignmentId) {
      setError('Select a classroom and assignment before running the Revision Coach.')
      return
    }
    const accessKey = requireRoleAccess(selectedClassroomId, experienceSettings.profile === 'student' ? 'student' : 'teacher')
    if (!accessKey) {
      return
    }

    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const result = await api.revisionCoach({
        classroom_id: selectedClassroomId,
        assignment_id: selectedAssignmentId,
        access_key: accessKey,
        draft_text: revisionCoachDraft.draftText.trim(),
        rubric: selectedAssignment?.rubric ?? linesToArray(assignmentDraft.rubricText),
        teacher_feedback: linesToArray(revisionCoachDraft.teacherFeedbackText),
        project_slug: selectedProjectSlug || undefined,
        ai_profile_id: revisionCoachDraft.ai_profile_id || undefined,
      })
      startTransition(() => {
        setRevisionCoachResult(result)
        setCitationVerification(result.citation_verification)
      })
      await refreshGrowth()
      setNotice('Student Revision Coach produced concrete next steps.')
    } catch (revisionError) {
      setError(getErrorMessage(revisionError, 'Failed to run the Student Revision Coach.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function runCitationVerifier() {
    if (!selectedProjectSlug) {
      setError('Select or launch a project before verifying citations.')
      return
    }
    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const claims = linesToArray(revisionCoachDraft.draftText)
      const result = await api.citationVerify({
        project_slug: selectedProjectSlug,
        claims,
      })
      startTransition(() => {
        setCitationVerification(result)
      })
      setNotice(result.ready_for_export ? 'All claims are grounded in uploaded evidence.' : 'Some claims still need approved evidence before export.')
    } catch (verifyError) {
      setError(getErrorMessage(verifyError, 'Failed to verify citations.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function runLessonToProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const teacherAccessKey = selectedClassroomId ? requireClassroomAccess(selectedClassroomId, 'teacher') : null
    if (selectedClassroomId && !teacherAccessKey) {
      return
    }

    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const result = await api.lessonToProject({
        lesson_plan: lessonProjectDraft.lessonPlan.trim(),
        title: lessonProjectDraft.title.trim() || undefined,
        topic: lessonProjectDraft.topic.trim() || undefined,
        audience: lessonProjectDraft.audience.trim() || undefined,
        goals: linesToArray(lessonProjectDraft.goalsText),
        rubric: linesToArray(lessonProjectDraft.rubricText),
        template_id: lessonProjectDraft.template_id || undefined,
        local_mode: lessonProjectDraft.local_mode,
        ai_profile_id: lessonProjectDraft.ai_profile_id || undefined,
        classroom_id: selectedClassroomId || undefined,
        access_key: teacherAccessKey || undefined,
        seed_from_classroom: lessonProjectDraft.seed_from_classroom,
      })
      await Promise.all([refreshStudio(false), refreshGrowth()])
      setSelectedProjectSlug(result.project.slug)
      startTransition(() => {
        setLessonProjectResult(result)
      })
      setActivePage('projects')
      setProjectView('build')
      setNotice(`Converted the lesson plan into ${result.project.title}.`)
    } catch (lessonError) {
      setError(getErrorMessage(lessonError, 'Failed to convert the lesson into a project.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function promoteLibrary() {
    if (!selectedClassroomId) {
      return
    }
    const teacherAccessKey = requireClassroomAccess(selectedClassroomId, 'teacher')
    if (!teacherAccessKey) {
      return
    }
    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const result = await api.promoteClassroomLibrary(selectedClassroomId, {
        access_key: teacherAccessKey,
        material_ids: [],
      })
      startTransition(() => {
        setClassroomLibrary(result)
      })
      await refreshGrowth()
      setNotice('Promoted classroom evidence into the shared library.')
    } catch (libraryError) {
      setError(getErrorMessage(libraryError, 'Failed to promote classroom evidence.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function submitPeerReview() {
    if (!selectedClassroomId || !selectedAssignmentId || !selectedStudentId) {
      setError('Select a classroom, assignment, and student before creating a peer review.')
      return
    }
    const studentAccessKey = requireRoleAccess(selectedClassroomId, 'student')
    if (!studentAccessKey) {
      return
    }
    setIsWorking(true)
    setError(null)
    setNotice(null)
    try {
      const review = await api.createPeerReview({
        classroom_id: selectedClassroomId,
        assignment_id: selectedAssignmentId,
        reviewer_student_id: selectedStudentId,
        target_student_id: selectedStudentId,
        access_key: studentAccessKey,
        draft_text: peerReviewDraft.draftText.trim(),
        rubric: linesToArray(peerReviewDraft.rubricText),
        project_slug: selectedProjectSlug || undefined,
      })
      await refreshGrowth()
      startTransition(() => {
        setPeerReviews(current => [review, ...current])
      })
      setNotice('Peer review submitted and routed into the approval gate.')
    } catch (peerError) {
      setError(getErrorMessage(peerError, 'Failed to create the peer review.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function resolvePeerReview(reviewId: string, decision: 'approved' | 'rejected') {
    if (!selectedClassroomId) {
      return
    }
    const reviewerKey = requireRoleAccess(selectedClassroomId, 'shared')
    if (!reviewerKey) {
      return
    }
    setIsWorking(true)
    setError(null)
    setNotice(null)
    try {
      await api.resolvePeerReview(reviewId, {
        decision,
        reviewer: peerReviewResolution.reviewer.trim(),
        note: peerReviewResolution.note.trim(),
        access_key: reviewerKey,
      })
      await refreshGrowth()
      setNotice(`Peer review ${decision}.`)
    } catch (peerResolveError) {
      setError(getErrorMessage(peerResolveError, 'Failed to resolve the peer review.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function createFamilyShareLink() {
    if (!selectedClassroomId || !selectedProjectSlug) {
      setError('Select a classroom and project before creating a family share link.')
      return
    }
    const teacherAccessKey = requireRoleAccess(selectedClassroomId, 'shared')
    if (!teacherAccessKey) {
      return
    }
    setIsWorking(true)
    setError(null)
    setNotice(null)
    try {
      const result = await api.createFamilyShareLink(selectedClassroomId, selectedProjectSlug, teacherAccessKey)
      startTransition(() => {
        setFamilyShareLink(result)
      })
      await refreshGrowth()
      setNotice('Created a family-safe share link for the selected project.')
    } catch (familyShareError) {
      setError(getErrorMessage(familyShareError, 'Failed to create the family share link.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function trainRubricModel() {
    if (!selectedClassroomId) {
      return
    }
    const teacherAccessKey = requireClassroomAccess(selectedClassroomId, 'teacher')
    if (!teacherAccessKey) {
      return
    }
    setIsWorking(true)
    setError(null)
    setNotice(null)
    try {
      const result = await api.rubricTrain({
        classroom_id: selectedClassroomId,
        access_key: teacherAccessKey,
        project_slugs: selectedProjectSlug ? [selectedProjectSlug] : [],
      })
      startTransition(() => {
        setRubricModel(result)
      })
      await refreshGrowth()
      setNotice('Rubric Trainer learned local quality patterns from the selected projects.')
    } catch (rubricError) {
      setError(getErrorMessage(rubricError, 'Failed to train the rubric model.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function generateAssessmentPack() {
    if (!selectedClassroomId || !selectedAssignmentId) {
      return
    }
    const teacherAccessKey = requireClassroomAccess(selectedClassroomId, 'teacher')
    if (!teacherAccessKey) {
      return
    }
    setIsWorking(true)
    setError(null)
    setNotice(null)
    try {
      const result = await api.assessmentPack({
        classroom_id: selectedClassroomId,
        assignment_id: selectedAssignmentId,
        access_key: teacherAccessKey,
        ai_profile_id: assignmentDraft.ai_profile_id || undefined,
      })
      startTransition(() => {
        setAssessmentPack(result)
      })
      await refreshGrowth()
      setNotice('Assessment Pack Generator created classroom materials from the approved evidence.')
    } catch (assessmentError) {
      setError(getErrorMessage(assessmentError, 'Failed to generate the assessment pack.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function installSchoolPack(packId: string) {
    setIsWorking(true)
    setError(null)
    setNotice(null)
    try {
      const result = await api.installSchoolPack(packId)
      startTransition(() => {
        setLastInstalledPack(result)
      })
      await refreshGrowth()
      await refreshStudio(false)
      setNotice(`Installed school pack ${result.label}.`)
    } catch (packError) {
      setError(getErrorMessage(packError, 'Failed to install the school pack.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function resolveApproval(approvalId: string, decision: 'approved' | 'rejected') {
    if (!selectedClassroomId) {
      return
    }
    const accessKey = requireRoleAccess(selectedClassroomId, 'shared')
    if (!accessKey) {
      return
    }
    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      await api.resolveEducationApproval(approvalId, {
        decision,
        reviewer: approvalReview.reviewer.trim(),
        note: approvalReview.note.trim(),
        access_key: accessKey,
      })
      await refreshEducation()
      setNotice(`Approval ${decision}.`)
    } catch (approvalError) {
      setError(getErrorMessage(approvalError, 'Failed to resolve the approval request.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function bootstrapEduClawn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const result = await api.educlawnBootstrap({
        school_name: educlawnDraft.school_name.trim(),
        classroom_title: educlawnDraft.classroom_title.trim(),
        teacher_name: educlawnDraft.teacher_name.trim(),
        subject: educlawnDraft.subject.trim(),
        grade_band: educlawnDraft.grade_band.trim(),
        description: educlawnDraft.description.trim(),
        default_template_id: educlawnDraft.default_template_id,
        template_id: educlawnDraft.template_id,
        assignment_title: educlawnDraft.assignment_title.trim(),
        assignment_summary: educlawnDraft.assignment_summary.trim(),
        topic: educlawnDraft.topic.trim(),
        audience: educlawnDraft.audience.trim(),
        goals: linesToArray(educlawnDraft.goalsText),
        rubric: linesToArray(educlawnDraft.rubricText),
        standards_focus: linesToArray(educlawnDraft.standardsText),
        due_date: educlawnDraft.due_date.trim(),
        local_mode: educlawnDraft.local_mode,
        ai_profile_id: educlawnDraft.ai_profile_id,
      })
      storeClassroomAccess(result.classroom)
      await Promise.all([refreshEduClawn(), refreshEducation(), refreshStudio(false)])
      setSelectedClassroomId(result.classroom.classroom_id)
      setSelectedAssignmentId(result.assignment.assignment_id)
      startTransition(() => {
        setEduclawnBootstrapResult(result)
      })
      setNotice(`Bootstrapped EduClawn for ${result.classroom.title}. Signed control plane and local classroom keys are ready.`)
    } catch (bootstrapError) {
      setError(getErrorMessage(bootstrapError, 'Failed to bootstrap EduClawn.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsWorking(true)
    setAuthError(null)

    try {
      const session = await api.login(credentials)
      window.localStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, session.access_token)
      startTransition(() => {
        setToken(session.access_token)
      })
      setNotice(`Admin session active until ${formatTimestamp(session.expires_at)}.`)
    } catch (loginError) {
      setAuthError(getErrorMessage(loginError, 'Admin login failed.'))
    } finally {
      setIsWorking(false)
    }
  }

  function logout() {
    window.localStorage.removeItem(ADMIN_TOKEN_STORAGE_KEY)
    startTransition(() => {
      setToken('')
      setAdminStatus(null)
      setBenchmark(null)
    })
    setNotice('Admin session cleared.')
  }

  function updateDraftField<K extends keyof ProjectDraft>(field: K, value: ProjectDraft[K]) {
    setDraft(current => ({ ...current, [field]: value }))
  }

  function updateProjectField<K extends keyof StudioProject>(field: K, value: StudioProject[K]) {
    setProject(current => (current ? { ...current, [field]: value } : current))
  }

  function updateAiProviderDraft<K extends keyof typeof defaultAiProfileDraft>(field: K, value: typeof defaultAiProfileDraft[K]) {
    if (field === 'provider_id') {
      const provider = aiCatalog.find(item => item.provider_id === value)
      setAiProfileDraft(current => ({
        ...current,
        provider_id: value as AIProviderId,
        default_model: provider?.default_model ?? current.default_model,
        base_url: provider?.supports_custom_base_url ? current.base_url : '',
      }))
      return
    }
    setAiProfileDraft(current => ({ ...current, [field]: value }))
  }

  function updateEducationAgentRole(role: 'teacher' | 'student' | 'shared') {
    const firstAgent = educationAgentCatalog.find(agent => agent.role === role)
    setEducationAgentDraft(current => ({
      ...current,
      role,
      agent_name: firstAgent?.name ?? current.agent_name,
    }))
  }

  function updateProjectTextList(field: 'goals' | 'rubric', value: string) {
    setProject(current => (current ? { ...current, [field]: linesToArray(value) } : current))
  }

  function toggleWorkflowStage(stageId: string) {
    setProject(current => {
      if (!current) {
        return current
      }

      return {
        ...current,
        workflow: {
          stages: current.workflow.stages.map(stage =>
            stage.stage_id === stageId ? { ...stage, enabled: !stage.enabled } : stage,
          ),
        },
      }
    })
  }

  async function saveAiProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const payload = {
        label: aiProfileDraft.label.trim(),
        provider_id: aiProfileDraft.provider_id,
        auth_mode: aiProfileDraft.auth_mode,
        api_key: aiProfileDraft.api_key.trim(),
        default_model: aiProfileDraft.default_model.trim(),
        base_url: aiProfileDraft.base_url.trim(),
        capabilities: linesToArray(aiProfileDraft.capabilitiesText),
      }
      const saved = selectedAiProfileId
        ? await api.updateAiProfile(selectedAiProfileId, {
            label: payload.label,
            auth_mode: payload.auth_mode,
            api_key: payload.api_key || undefined,
            default_model: payload.default_model,
            base_url: payload.base_url,
            capabilities: payload.capabilities,
          })
        : await api.createAiProfile(payload)

      await refreshAi()
      setSelectedAiProfileId(saved.profile_id)
      setAiProfileDraft({
        label: saved.label,
        provider_id: saved.provider_id,
        auth_mode: saved.auth_mode,
        api_key: '',
        default_model: saved.default_model,
        base_url: saved.base_url,
        capabilitiesText: saved.capabilities.join('\n'),
      })
      setNotice(selectedAiProfileId ? `Updated AI profile ${saved.label}.` : `Added AI profile ${saved.label}.`)
    } catch (saveError) {
      setError(getErrorMessage(saveError, 'Failed to save the AI provider profile.'))
    } finally {
      setIsWorking(false)
    }
  }

  function loadAiProfile(profile: AIProviderProfile) {
    setSelectedAiProfileId(profile.profile_id)
    setAiProfileDraft({
      label: profile.label,
      provider_id: profile.provider_id,
      auth_mode: profile.auth_mode,
      api_key: '',
      default_model: profile.default_model,
      base_url: profile.base_url,
      capabilitiesText: profile.capabilities.join('\n'),
    })
    setActivePage('ai')
  }

  function resetAiProfileDraft() {
    setSelectedAiProfileId('')
    const provider = aiCatalog.find(item => item.provider_id === defaultAiProfileDraft.provider_id)
    setAiProfileDraft({
      ...defaultAiProfileDraft,
      default_model: provider?.default_model ?? defaultAiProfileDraft.default_model,
    })
  }

  async function testAiProfile(profileId: string) {
    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      const result = await api.testAiProfile(profileId)
      await refreshAi()
      setNotice(result.used ? `${result.provider_label} responded successfully.` : `${result.provider_label} test failed: ${result.error}`)
    } catch (testError) {
      setError(getErrorMessage(testError, 'Failed to test the AI provider profile.'))
    } finally {
      setIsWorking(false)
    }
  }

  async function deleteAiProfile(profileId: string) {
    const profile = aiProfiles.find(item => item.profile_id === profileId)
    if (!profile || !window.confirm(`Delete AI profile "${profile.label}"?`)) {
      return
    }

    setIsWorking(true)
    setError(null)
    setNotice(null)

    try {
      await api.deleteAiProfile(profileId)
      await refreshAi()
      setDraft(current => current.ai_profile_id === profileId ? { ...current, ai_profile_id: '' } : current)
      setAssignmentDraft(current => current.ai_profile_id === profileId ? { ...current, ai_profile_id: '' } : current)
      setEducationAgentDraft(current => current.ai_profile_id === profileId ? { ...current, ai_profile_id: '' } : current)
      setEduclawnDraft(current => current.ai_profile_id === profileId ? { ...current, ai_profile_id: '' } : current)
      setProject(current => current && current.ai_profile_id === profileId ? { ...current, ai_profile_id: '', local_mode: 'no-llm' } : current)
      if (selectedAiProfileId === profileId) {
        resetAiProfileDraft()
      }
      setNotice(`Deleted AI profile ${profile.label}.`)
    } catch (deleteError) {
      setError(getErrorMessage(deleteError, 'Failed to delete the AI provider profile.'))
    } finally {
      setIsWorking(false)
    }
  }

  const selectedTemplate = deferredTemplates.find(template => template.id === draft.template_id) ?? deferredTemplates[0] ?? null
  const adminReady = token.length > 0
  const isSimpleMode = experienceSettings.simplifiedDashboard && experienceSettings.level !== 'advanced'
  const showAdvancedSystems = !experienceSettings.simplifiedDashboard || experienceSettings.level === 'advanced'
  const visiblePages = getVisiblePages(experienceSettings.profile, showAdvancedSystems)
  const compileArtifacts = compileResult?.artifacts ?? deferredArtifacts
  const exports = deferredProject?.exports ?? []
  const bundleExport = exports.find(exportEntry => exportEntry.export_type === 'project_bundle')
  const rubricExport = exports.find(exportEntry => exportEntry.export_type === 'rubric_report')
  const teacherComments = deferredProject?.teacher_comments ?? []
  const standardsAlignment = deferredProject?.standards_alignment ?? []
  const revisionHistory = deferredProject?.revision_history ?? []
  const selectedClassroom = deferredEducationClassrooms.find(item => item.classroom_id === selectedClassroomId) ?? null
  const selectedAssignment = selectedClassroom?.assignments.find(item => item.assignment_id === selectedAssignmentId) ?? null
  const selectedStudent = selectedClassroom?.students.find(item => item.student_id === selectedStudentId) ?? null
  const selectedClassroomKeys = selectedClassroomId ? classroomAccessVault[selectedClassroomId] : undefined
  const filteredEducationAgents = educationAgentCatalog.filter(agent => agent.role === educationAgentDraft.role)
  const educlawnAllowedChannels = ((deferredEduclawnOverview?.derived_control_plane.allowed_channels as string[] | undefined) ?? [])
  const educlawnDeniedTools = ((deferredEduclawnOverview?.derived_control_plane.denied_tools as string[] | undefined) ?? [])
  const educlawnAttestation = (deferredEduclawnBootstrapResult?.control_plane.security as Record<string, unknown> | undefined) ?? undefined
  const recommendedSample = pickRecommendedSample(experienceSettings.profile, deferredOverview?.sample_projects ?? [])
  const selectedProviderProfile = deferredAiProfiles.find(item => item.profile_id === selectedAiProfileId) ?? null
  const draftProviderProfile = deferredAiProfiles.find(item => item.profile_id === draft.ai_profile_id) ?? null
  const projectProviderProfile = deferredAiProfiles.find(item => item.profile_id === deferredProject?.ai_profile_id) ?? null
  const educlawnProviderProfile = deferredAiProfiles.find(item => item.profile_id === educlawnDraft.ai_profile_id) ?? null
  const setupChecklist = [
    {
      label: 'Workspace selected',
      ready: Boolean(deferredDesktopContext?.workspaceRoot || deferredSystemStatus?.workspace_root),
    },
    {
      label: 'Local engine ready',
      ready: deferredHealth?.status === 'ok',
    },
    {
      label: 'Starter picked',
      ready: Boolean(draft.title.trim() && draft.template_id),
    },
    {
      label: 'Classroom keys ready',
      ready: Object.keys(classroomAccessVault).length > 0,
    },
  ]
  const readyChecklistCount = setupChecklist.filter(item => item.ready).length
  const activePageMeta = visiblePages.find(page => page.id === activePage) ?? visiblePages[0]
  const pageHeading =
    activePage === 'home'
      ? {
          title: 'Welcome to EduClawn',
          description: 'Choose a role, finish setup, and move into one focused part of the product at a time.',
        }
      : activePage === 'projects'
        ? {
            title: 'Projects',
            description: isSimpleMode
              ? 'Create, build, or review one project step at a time.'
              : 'Create, compile, review, and export local-first project work.',
          }
      : activePage === 'classroom'
          ? {
              title: experienceSettings.profile === 'student' ? 'Student Workspace' : 'Classroom',
              description: isSimpleMode
                ? 'Set up the classroom, launch student work, or review safety in separate steps.'
                : 'Assignments, approved materials, bounded agents, and safety workflows.',
            }
          : activePage === 'autopilot'
            ? {
                title: 'Autopilot',
                description: 'Turn teacher goals, lesson plans, and rubrics into assignments, revision tasks, citations, and project scaffolds.',
              }
            : activePage === 'ops'
              ? {
                  title: 'Teacher Ops',
                  description: 'Shared classroom library reuse, peer review moderation, standards mapping, interventions, replay, and assessment packs.',
                }
              : activePage === 'family'
                ? {
                    title: 'Family View',
                    description: 'A read-only, simpler explanation of student project progress and downloadable exports.',
                  }
                : activePage === 'marketplace'
                  ? {
                      title: 'Marketplace',
                      description: 'Templates, school packs, plugin SDK surfaces, and offline school deployment assets.',
                    }
          : activePage === 'ai'
            ? {
                title: 'AI Providers',
                description: 'Connect preferred model providers, store classroom-safe profiles locally, and route project or classroom work through them.',
              }
          : activePage === 'desktop'
            ? {
                title: 'Desktop Tools',
                description: 'Manage the workspace, recent projects, updates, and packaged-app behavior.',
              }
            : {
                title: 'Advanced Systems',
                description: 'EduClawn control plane, admin monitoring, and deeper orchestration surfaces.',
              }

  useEffect(() => {
    const pages = getVisiblePages(experienceSettings.profile, showAdvancedSystems)
    if (!pages.some(page => page.id === activePage)) {
      setActivePage('home')
    }
  }, [activePage, experienceSettings.profile, showAdvancedSystems])

  function applySampleProject(sample: StudioSampleProject) {
    setDraft(current => ({
      ...current,
      title: sample.title,
      summary: sample.summary,
      topic: sample.title,
      template_id: sample.template_id,
    }))
    setActivePage('projects')
    setProjectView('create')
    setNotice(`Loaded sample starter: ${sample.title}.`)
  }

  function updateExperienceSetting<K extends keyof ExperienceSettings>(field: K, value: ExperienceSettings[K]) {
    setExperienceSettings(current => ({ ...current, [field]: value }))
  }

  function applyExperienceProfile(profile: ExperienceProfile) {
    setExperienceSettings(current => ({
      ...current,
      profile,
      level: profile === 'builder' ? 'advanced' : profile === 'family' ? 'guided' : 'standard',
      simplifiedDashboard: profile === 'builder' ? false : true,
      largeText: profile === 'family' ? true : current.largeText,
    }))
    setActivePage(profile === 'teacher' ? 'classroom' : profile === 'student' ? 'projects' : profile === 'builder' ? 'projects' : 'home')
    setProjectView(profile === 'teacher' ? 'create' : 'build')
    setClassroomView(profile === 'teacher' ? 'setup' : profile === 'student' ? 'launch' : 'setup')

    if (profile === 'teacher') {
      setDraft({
        title: 'Classroom Inquiry Project',
        summary: 'A teacher-guided local project with approved sources, scaffolded sections, and rubric-aligned outputs.',
        topic: 'A local civic issue or community history topic',
        audience: 'Students, families, and classroom reviewers',
        goalsText: 'Build a classroom-ready project\nUse approved evidence\nSupport revision and teacher review',
        rubricText: 'Evidence Quality\nCitation Accuracy\nStudent Reflection\nRevision Quality',
        template_id: 'lesson-module',
        local_mode: 'no-llm',
        ai_profile_id: '',
      })
      setClassroomDraft({
        title: 'Civics Period 3',
        subject: 'Civics',
        grade_band: 'Grades 8-10',
        teacher_name: 'Ms. Rivera',
        description: 'A guided classroom workspace for assignments, approved evidence, and teacher review.',
        default_template_id: 'lesson-module',
        standardsText: 'C3 Inquiry\nSource Analysis',
      })
      setAssignmentDraft({
        title: 'Community Evidence Brief',
        summary: 'Students investigate an issue with teacher-approved evidence and produce a cited class project.',
        topic: 'A local civic challenge',
        audience: 'Middle and high school students',
        template_id: 'research-portfolio',
        goalsText: 'Use classroom-approved evidence\nDraft an argument with citations',
        rubricText: 'Evidence Quality\nCitation Accuracy\nClarity',
        standardsText: 'C3 Inquiry\nArgument Writing',
        due_date: '2026-04-15',
        local_mode: 'no-llm',
        ai_profile_id: '',
      })
      setEducationAgentDraft({
        role: 'teacher',
        agent_name: 'lesson-planner',
        prompt: 'Build a bounded lesson plan with approved evidence, teacher review points, and revision checkpoints.',
        ai_profile_id: '',
      })
      setNotice('Teacher quick-start loaded.')
      return
    }

    if (profile === 'student') {
      setDraft({
        title: 'Student Evidence Portfolio',
        summary: 'A simple student project built from local documents, guided writing, and teacher feedback.',
        topic: 'A classroom topic or community question',
        audience: 'Teacher and classmates',
        goalsText: 'Understand the topic\nAdd strong evidence\nRevise after feedback',
        rubricText: 'Evidence Quality\nClarity\nRevision Quality',
        template_id: 'research-portfolio',
        local_mode: 'no-llm',
        ai_profile_id: '',
      })
      setStudentDraft({
        name: 'Jordan Lee',
        grade_level: 'Grade 9',
        learningGoalsText: 'Use stronger evidence\nExplain ideas clearly',
        notes: 'Interested in local stories and community issues.',
      })
      setEducationAgentDraft({
        role: 'student',
        agent_name: 'research-coach',
        prompt: 'Coach me through finding evidence, drafting a claim, and revising safely inside the classroom rules.',
        ai_profile_id: '',
      })
      setNotice('Student quick-start loaded.')
      return
    }

    if (profile === 'family') {
      setDraft({
        title: 'Family Learning Story',
        summary: 'A simpler project space for guided uploads, easy reading, and local storytelling.',
        topic: 'Family history, neighborhood memory, or a local issue',
        audience: 'Family, teacher, and community visitors',
        goalsText: 'Collect a few sources\nExplain the story simply\nShare a clear final project',
        rubricText: 'Clarity\nEvidence Quality\nAccessibility',
        template_id: 'documentary-story',
        local_mode: 'no-llm',
        ai_profile_id: '',
      })
      setNotice('Family-friendly quick-start loaded.')
      return
    }

    setDraft({
      title: 'Advanced Project Build',
      summary: 'A more technical workspace for templates, workflows, provenance, and local compilation.',
      topic: 'A complex civic or educational problem',
      audience: 'Mixed classroom and public audiences',
      goalsText: 'Design a custom workflow\nUse advanced evidence retrieval\nCompile multiple exports',
      rubricText: 'System Design\nEvidence Quality\nOutput Quality',
      template_id: 'civic-campaign-simulator',
      local_mode: deferredSystemStatus?.local_ai.ollama_reachable ? 'local-llm' : 'no-llm',
      ai_profile_id: '',
    })
    setEducationAgentDraft({
      role: 'shared',
      agent_name: 'evidence-librarian',
      prompt: 'Coordinate the bounded workflow across planning, evidence, review, and export steps.',
      ai_profile_id: '',
    })
    setProjectView('create')
    setNotice('Advanced builder quick-start loaded.')
  }

  function jumpToPanel(panelId: string) {
    const pageId =
      panelId === 'starter-wizard' || panelId === 'workspace'
        ? 'projects'
        : panelId === 'teacher-os'
          ? 'classroom'
          : panelId === 'ai-hub'
            ? 'ai'
          : panelId === 'educlawn' || panelId === 'admin-ops'
            ? 'advanced'
            : panelId === 'desktop-tools'
              ? 'desktop'
              : 'home'
    setActivePage(pageId)
    window.setTimeout(() => {
      document.getElementById(panelId)?.scrollIntoView({
        behavior: experienceSettings.reducedMotion ? 'auto' : 'smooth',
        block: 'start',
      })
    }, 0)
  }

  function finishOnboarding() {
    setIsOnboardingComplete(true)
    setNotice('First-run setup saved. You can reopen the guided path at any time from the Easy Start Center.')
  }

  async function chooseWorkspace() {
    if (!window.educlawnDesktop?.chooseWorkspace) {
      return
    }
    const context = await window.educlawnDesktop.chooseWorkspace()
    startTransition(() => {
      setDesktopContext(context)
    })
    await refreshStudio(false)
    setNotice(`Workspace set to ${context.workspaceRoot}.`)
  }

  async function openWorkspace() {
    await window.educlawnDesktop?.openWorkspace?.()
  }

  async function openReleaseNotes() {
    await window.educlawnDesktop?.openReleaseNotes?.()
  }

  async function checkForUpdates() {
    if (!window.educlawnDesktop?.checkForUpdates) {
      return
    }
    const context = await window.educlawnDesktop.checkForUpdates()
    startTransition(() => {
      setDesktopContext(context)
    })
  }

  async function installDownloadedUpdate() {
    await window.educlawnDesktop?.installUpdate?.()
  }

  async function toggleLaunchAtLogin() {
    if (!window.educlawnDesktop?.setLaunchAtLogin || !desktopContext) {
      return
    }
    const context = await window.educlawnDesktop.setLaunchAtLogin(!desktopContext.preferences.launchAtLogin)
    startTransition(() => {
      setDesktopContext(context)
    })
  }

  async function installToApplications() {
    if (!window.educlawnDesktop?.installToApplications) {
      return
    }
    const context = await window.educlawnDesktop.installToApplications()
    startTransition(() => {
      setDesktopContext(context)
    })
  }

  function openRecentProject(slug: string) {
    setActivePage('projects')
    setProjectView('build')
    setSelectedProjectSlug(slug)
    setNotice(`Opened recent project ${slug}.`)
  }

  function storeClassroomAccess(classroom: EducationClassroom) {
    const bootstrap = classroom.security_bootstrap
    if (!bootstrap) {
      return
    }
    setClassroomAccessVault(current => ({
      ...current,
      [classroom.classroom_id]: {
        teacher_access_key: bootstrap.teacher_access_key,
        student_access_key: bootstrap.student_access_key,
        reviewer_access_key: bootstrap.reviewer_access_key,
        issued_at: bootstrap.issued_at,
      },
    }))
  }

  function requireClassroomAccess(classroomId: string, role: 'teacher' | 'student' | 'reviewer'): string | null {
    const keys = classroomAccessVault[classroomId]
    const accessKey =
      role === 'teacher'
        ? keys?.teacher_access_key
        : role === 'student'
          ? keys?.student_access_key
          : keys?.reviewer_access_key
    if (accessKey) {
      return accessKey
    }
    setError(`Missing local ${role} access key for this classroom. Re-bootstrap or recreate the classroom on this device.`)
    return null
  }

  function requireRoleAccess(classroomId: string, role: 'teacher' | 'student' | 'shared'): string | null {
    const keys = classroomAccessVault[classroomId]
    if (role === 'teacher') {
      return requireClassroomAccess(classroomId, 'teacher')
    }
    if (role === 'student') {
      return keys?.student_access_key || requireClassroomAccess(classroomId, 'teacher')
    }
    return keys?.reviewer_access_key || requireClassroomAccess(classroomId, 'teacher')
  }

  return (
    <div
      className={[
        'studio-shell',
        experienceSettings.largeText ? 'large-text' : '',
        experienceSettings.reducedMotion ? 'reduced-motion' : '',
      ].filter(Boolean).join(' ')}
    >
      <div className="glow glow-left" />
      <div className="glow glow-right" />

      <main className="studio-dashboard">
        <aside className="app-sidebar">
          <div className="sidebar-brand">
            <p className="eyebrow">EduClawn</p>
            <h1>EduClawn</h1>
            <p className="sidebar-copy">
              Local-first project building for students and teachers, with simple mode by default and advanced systems only when needed.
            </p>
            <div className="chip-row">
              {(deferredOverview?.install_modes ?? []).slice(0, 3).map(mode => (
                <span className="hero-tag" key={String(mode.mode)}>
                  {String(mode.mode).replaceAll('_', ' ')}
                </span>
              ))}
            </div>
          </div>

          <div className="sidebar-block">
            <span className="mini-label">Navigation</span>
            <div className="sidebar-nav">
              {visiblePages.map(page => (
                <button
                  className={`sidebar-link ${activePage === page.id ? 'active' : ''}`}
                  key={page.id}
                  type="button"
                  onClick={() => setActivePage(page.id)}
                >
                  <strong>{page.label}</strong>
                  <span>{page.detail}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="sidebar-block">
            <span className="mini-label">Status</span>
            <div className="sidebar-status">
              <div className={`status-pill ${deferredHealth?.trained ? 'trained' : 'neutral'}`}>
                <span className="status-dot" />
                {deferredHealth?.app ?? 'EduClawn'}
              </div>
              <div className="status-pill neutral">
                <span className="status-dot" />
                {formatProfileLabel(experienceSettings.profile)}
              </div>
              <div className="status-pill neutral">
                <span className="status-dot" />
                v{deferredSystemStatus?.release.desktop_version ?? '0.2.0'}
              </div>
              <div className="status-pill neutral">
                <span className="status-dot" />
                {deferredSystemStatus?.local_ai.ollama_reachable ? 'Local AI ready' : 'Fallback mode'}
              </div>
            </div>
          </div>

          <div className="sidebar-block">
            <span className="mini-label">Quick actions</span>
            <div className="sidebar-actions">
              <button className="action-button secondary" onClick={() => setActivePage(experienceSettings.profile === 'teacher' ? 'classroom' : 'projects')} disabled={isWorking}>
                {experienceSettings.profile === 'teacher' ? 'Open Classroom' : 'Open Projects'}
              </button>
              <button className="action-button" onClick={() => setActivePage('desktop')} disabled={isWorking}>
                Desktop Tools
              </button>
              <button className="text-button dark-on-light" type="button" onClick={() => setActivePage('ai')} disabled={isWorking}>
                AI Providers
              </button>
              {deferredProject ? (
                <button className="text-button dark-on-light" type="button" onClick={() => void compileProject()} disabled={isWorking}>
                  Compile Project
                </button>
              ) : null}
              <button className="text-button dark-on-light" type="button" onClick={() => void refreshStudio(false)}>
                Refresh Studio
              </button>
              <a className="text-button dark-on-light" href={api.legacyUrl()} target="_blank" rel="noreferrer">
                Legacy HTML
              </a>
            </div>
          </div>
        </aside>

        <section className="app-main">
          <section className="page-header">
            <div>
              <p className="eyebrow">{activePageMeta?.label ?? 'Home'}</p>
              <h2>{pageHeading.title}</h2>
              <p>{pageHeading.description}</p>
            </div>
            <div className="page-header-actions">
              <span className="pill">{formatProfileLabel(experienceSettings.profile)}</span>
              <span className="pill">{formatLevelLabel(experienceSettings.level)}</span>
              {showAdvancedSystems ? <span className="pill">Advanced on</span> : <span className="pill">Simple mode</span>}
              {activePage === 'desktop' ? (
                <button className="text-button dark-on-light" type="button" onClick={() => void openWorkspace()}>
                  Open Workspace
                </button>
              ) : null}
              {activePage === 'ai' ? (
                <button className="text-button dark-on-light" type="button" onClick={() => void refreshAi()}>
                  Refresh AI
                </button>
              ) : null}
              {activePage === 'advanced' && !showAdvancedSystems ? (
                <button className="text-button dark-on-light" type="button" onClick={() => updateExperienceSetting('simplifiedDashboard', false)}>
                  Reveal Advanced
                </button>
              ) : null}
            </div>
          </section>

          {activePage === 'home' && !isOnboardingComplete ? (
          <Panel
            panelId="first-run"
            title="First-Run Onboarding"
            subtitle="Pick who the app is for, confirm the local setup, and start with a guided path instead of the full system all at once."
          >
            <div className="stack-tight">
              <div className="preview-card embedded">
                <div className="preview-topline">
                  <div>
                    <span className="mini-label">Who is using EduClawn?</span>
                    <h3>{formatProfileLabel(experienceSettings.profile)}</h3>
                  </div>
                  <span className="pill">{formatLevelLabel(experienceSettings.level)}</span>
                </div>
                <div className="persona-grid">
                  {([
                    { id: 'teacher', title: 'Teacher', detail: 'Classrooms, assignments, evidence libraries, and review.' },
                    { id: 'student', title: 'Student', detail: 'Simpler research, drafting, and revision support.' },
                    { id: 'family', title: 'Family', detail: 'Larger text, simpler starters, and fewer advanced controls.' },
                    { id: 'builder', title: 'Advanced Builder', detail: 'Templates, workflows, provenance, and the full power surface.' },
                  ] as const).map(option => (
                    <button
                      className={`persona-card ${experienceSettings.profile === option.id ? 'selected' : ''}`}
                      key={option.id}
                      type="button"
                      onClick={() => applyExperienceProfile(option.id)}
                    >
                      <strong>{option.title}</strong>
                      <span>{option.detail}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="preview-card embedded">
                <div className="preview-topline">
                  <div>
                    <span className="mini-label">Workspace</span>
                    <h3>{deferredDesktopContext?.workspaceRoot ?? deferredSystemStatus?.workspace_root ?? 'Local workspace pending'}</h3>
                  </div>
                  <span className="pill">{String((deferredSystemStatus?.startup.state ?? 'pending')).replaceAll('_', ' ')}</span>
                </div>
                <div className="chip-row">
                  <span className="chip">Setup {readyChecklistCount}/{setupChecklist.length} ready</span>
                  {setupChecklist.map(item => (
                    <span className="chip" key={item.label}>
                      {item.ready ? 'Ready' : 'Next'} {item.label}
                    </span>
                  ))}
                </div>
                <div className="chip-row">
                  <span className="chip">Warmup {(deferredSystemStatus?.startup.state as string | undefined) ?? 'pending'}</span>
                  <span className="chip">OCR {deferredSystemStatus?.tools.tesseract_available ? 'ready' : 'not detected'}</span>
                  <span className="chip">Local AI {deferredSystemStatus?.local_ai.ollama_reachable ? 'reachable' : 'offline'}</span>
                  <span className="chip">Models {deferredSystemStatus?.local_ai.available_models.length ?? 0}</span>
                  <span className="chip">Updates {deferredDesktopContext?.updater.status ?? 'n/a'}</span>
                  <span className="chip">Launch at login {deferredDesktopContext?.preferences.launchAtLogin ? 'on' : 'off'}</span>
                </div>
                <div className="action-row">
                  {deferredDesktopContext ? (
                    <button className="action-button secondary" type="button" onClick={() => void chooseWorkspace()}>
                      Choose Desktop Workspace
                    </button>
                  ) : null}
                  {deferredDesktopContext ? (
                    <button className="text-button dark-on-light" type="button" onClick={() => void openWorkspace()}>
                      Open Workspace Folder
                    </button>
                  ) : null}
                  {deferredDesktopContext ? (
                    <button className="text-button dark-on-light" type="button" onClick={() => void openReleaseNotes()}>
                      Open Release Notes
                    </button>
                  ) : null}
                  {deferredDesktopContext ? (
                    <button className="text-button dark-on-light" type="button" onClick={() => void toggleLaunchAtLogin()}>
                      {deferredDesktopContext.preferences.launchAtLogin ? 'Disable Launch at Login' : 'Enable Launch at Login'}
                    </button>
                  ) : null}
                  {deferredDesktopContext?.canInstallToApplications ? (
                    <button className="text-button dark-on-light" type="button" onClick={() => void installToApplications()}>
                      Install to Applications
                    </button>
                  ) : null}
                </div>
                {deferredDesktopContext ? <p className="mini-label">{deferredDesktopContext.updater.message}</p> : null}
              </div>

              {deferredDesktopContext?.recentProjects.length ? (
                <div className="preview-card embedded">
                  <div className="preview-topline">
                    <div>
                      <span className="mini-label">Recent desktop work</span>
                      <h3>Open Recent Projects</h3>
                    </div>
                    <span className="pill">{deferredDesktopContext.recentProjects.length}</span>
                  </div>
                  <div className="card-grid compact">
                    {deferredDesktopContext.recentProjects.slice(0, 4).map((item) => (
                      <article className="mini-card" key={item.slug}>
                        <h3>{item.title}</h3>
                        <p>{item.slug}</p>
                        <button className="text-button dark-on-light" type="button" onClick={() => openRecentProject(item.slug)}>
                          Open
                        </button>
                      </article>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="card-grid compact">
                {(deferredOverview?.sample_projects ?? []).map(sample => (
                  <article className="mini-card" key={sample.slug}>
                    <h3>{sample.title}</h3>
                    <p>{sample.summary}</p>
                    <button className="text-button dark-on-light" type="button" onClick={() => applySampleProject(sample)}>
                      Use Sample Starter
                    </button>
                  </article>
                ))}
              </div>

              <div className="action-row">
                {recommendedSample ? (
                  <button className="action-button secondary" type="button" onClick={() => applySampleProject(recommendedSample)}>
                    Load Recommended Starter
                  </button>
                ) : null}
                <button className="action-button" type="button" onClick={finishOnboarding}>
                  Finish Onboarding
                </button>
              </div>
            </div>
          </Panel>
        ) : null}

          {activePage === 'home' && isOnboardingComplete ? (
          <Panel
            panelId="easy-start"
            title="Easy Start Center"
            subtitle="Keep the product comfortable for different kinds of users and move through the next steps with fewer decisions."
          >
          <div className="two-up">
            <div className="subpanel">
              <div className="preview-topline">
                <div>
                  <span className="mini-label">Current path</span>
                  <h3>{formatProfileLabel(experienceSettings.profile)}</h3>
                </div>
                <span className="pill">{formatLevelLabel(experienceSettings.level)}</span>
              </div>
              <div className="persona-grid">
                {([
                  { id: 'teacher', title: 'Teacher', detail: 'Assignments, evidence, and review.' },
                  { id: 'student', title: 'Student', detail: 'Research, drafting, and revision.' },
                  { id: 'family', title: 'Family', detail: 'A simpler and easier-to-read experience.' },
                  { id: 'builder', title: 'Advanced Builder', detail: 'Full templates, workflows, and system panels.' },
                ] as const).map(option => (
                  <button
                    className={`persona-card ${experienceSettings.profile === option.id ? 'selected' : ''}`}
                    key={option.id}
                    type="button"
                    onClick={() => applyExperienceProfile(option.id)}
                  >
                    <strong>{option.title}</strong>
                    <span>{option.detail}</span>
                  </button>
                ))}
              </div>
              <div className="action-row">
                <button className="text-button dark-on-light" type="button" onClick={() => setIsOnboardingComplete(false)}>
                  Reopen Guided Setup
                </button>
                {recommendedSample ? (
                  <button className="text-button dark-on-light" type="button" onClick={() => applySampleProject(recommendedSample)}>
                    Load Recommended Starter
                  </button>
                ) : null}
              </div>
            </div>

            <div className="subpanel">
              <div className="preview-topline">
                <div>
                  <span className="mini-label">Comfort and accessibility</span>
                  <h3>Use What Feels Easier</h3>
                </div>
                <span className="pill">{showAdvancedSystems ? 'full system' : 'simple mode'}</span>
              </div>
              <div className="setting-list">
                <button
                  className={`setting-toggle ${experienceSettings.simplifiedDashboard ? 'enabled' : ''}`}
                  type="button"
                  onClick={() => updateExperienceSetting('simplifiedDashboard', !experienceSettings.simplifiedDashboard)}
                >
                  <strong>Simple dashboard</strong>
                  <span>Hide advanced power-user panels until you need them.</span>
                </button>
                <button
                  className={`setting-toggle ${experienceSettings.largeText ? 'enabled' : ''}`}
                  type="button"
                  onClick={() => updateExperienceSetting('largeText', !experienceSettings.largeText)}
                >
                  <strong>Larger text</strong>
                  <span>Increase readability for classrooms, families, and presentations.</span>
                </button>
                <button
                  className={`setting-toggle ${experienceSettings.reducedMotion ? 'enabled' : ''}`}
                  type="button"
                  onClick={() => updateExperienceSetting('reducedMotion', !experienceSettings.reducedMotion)}
                >
                  <strong>Reduced motion</strong>
                  <span>Turn off extra animation and smooth scrolling.</span>
                </button>
              </div>
              <div className="chip-row">
                {setupChecklist.map(item => (
                  <span className="chip" key={item.label}>
                    {item.ready ? 'Ready' : 'Pending'} {item.label}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div className="card-grid compact">
            {experienceSettings.profile === 'teacher' ? (
              <>
                <article className="mini-card action-card">
                  <h3>Create a classroom</h3>
                  <p>Jump directly to the Teacher OS form and start a bounded classroom.</p>
                  <button className="text-button dark-on-light" type="button" onClick={() => jumpToPanel('teacher-os')}>
                    Open Teacher OS
                  </button>
                </article>
                <article className="mini-card action-card">
                  <h3>Prepare a starter project</h3>
                  <p>Use a guided template and create a project manifest first.</p>
                  <button className="text-button dark-on-light" type="button" onClick={() => jumpToPanel('starter-wizard')}>
                    Open Starter Wizard
                  </button>
                </article>
                <article className="mini-card action-card">
                  <h3>Open the workspace folder</h3>
                  <p>Review saved exports, bundles, and classroom materials outside the app.</p>
                  <button className="text-button dark-on-light" type="button" onClick={() => void openWorkspace()}>
                    Open Workspace
                  </button>
                </article>
              </>
            ) : null}

            {experienceSettings.profile === 'student' ? (
              <>
                <article className="mini-card action-card">
                  <h3>Start with a sample</h3>
                  <p>Load a recommended sample and edit it instead of starting from scratch.</p>
                  <button className="text-button dark-on-light" type="button" onClick={() => recommendedSample && applySampleProject(recommendedSample)}>
                    Load Sample
                  </button>
                </article>
                <article className="mini-card action-card">
                  <h3>Build your project</h3>
                  <p>Go straight to the starter form and create a first local project.</p>
                  <button className="text-button dark-on-light" type="button" onClick={() => jumpToPanel('starter-wizard')}>
                    Open Starter Wizard
                  </button>
                </article>
                <article className="mini-card action-card">
                  <h3>Upload sources</h3>
                  <p>Move into the workspace and add PDFs, notes, or images.</p>
                  <button className="text-button dark-on-light" type="button" onClick={() => jumpToPanel('workspace')}>
                    Open Workspace
                  </button>
                </article>
              </>
            ) : null}

            {experienceSettings.profile === 'family' ? (
              <>
                <article className="mini-card action-card">
                  <h3>Use the easiest starter</h3>
                  <p>Load a family-friendly project starter with simpler defaults.</p>
                  <button className="text-button dark-on-light" type="button" onClick={() => recommendedSample && applySampleProject(recommendedSample)}>
                    Load Starter
                  </button>
                </article>
                <article className="mini-card action-card">
                  <h3>Choose the workspace</h3>
                  <p>Pick a folder that is easy to find later.</p>
                  <button className="text-button dark-on-light" type="button" onClick={() => void chooseWorkspace()}>
                    Choose Workspace
                  </button>
                </article>
                <article className="mini-card action-card">
                  <h3>Turn on larger text</h3>
                  <p>Keep reading comfortable while reviewing sources and outputs.</p>
                  <button className="text-button dark-on-light" type="button" onClick={() => updateExperienceSetting('largeText', true)}>
                    Enable Larger Text
                  </button>
                </article>
              </>
            ) : null}

            {experienceSettings.profile === 'builder' ? (
              <>
                <article className="mini-card action-card">
                  <h3>Open advanced systems</h3>
                  <p>Jump into EduClawn, approvals, and the deeper orchestration surfaces.</p>
                  <button className="text-button dark-on-light" type="button" onClick={() => jumpToPanel('educlawn')}>
                    Open EduClawn
                  </button>
                </article>
                <article className="mini-card action-card">
                  <h3>Build a workflow</h3>
                  <p>Start in the starter wizard, then move into the workspace and compile exports.</p>
                  <button className="text-button dark-on-light" type="button" onClick={() => jumpToPanel('starter-wizard')}>
                    Open Starter Wizard
                  </button>
                </article>
                <article className="mini-card action-card">
                  <h3>Check update state</h3>
                  <p>Confirm build version and staged updates from the desktop shell.</p>
                  <button className="text-button dark-on-light" type="button" onClick={() => void checkForUpdates()}>
                    Check Updates
                  </button>
                </article>
              </>
            ) : null}
          </div>
          </Panel>
        ) : null}

        {error ? <section className="error-banner">{error}</section> : null}
        {authError ? <section className="error-banner">{authError}</section> : null}
        {notice ? <section className="notice-banner">{notice}</section> : null}

        {activePage === 'home' && isOnboardingComplete ? (
          <>
            <section className="metric-grid">
          <MetricCard label="Templates" value={deferredOverview?.counts.templates} />
          <MetricCard label="Projects" value={deferredOverview?.counts.projects} />
          <MetricCard label="Documents" value={deferredOverview?.counts.documents} />
          <MetricCard label="Exports" value={deferredOverview?.counts.exports} />
          <MetricCard label="Plugins" value={deferredOverview?.counts.plugins} />
          <MetricCard label="Benchmark Cadence" value={formatSeconds(deferredHealth?.scheduler.benchmark_interval_seconds)} />
            </section>

            <Panel title="Current Workspace" subtitle="Use the simpler page navigation instead of scrolling through every system at once.">
              <div className="card-grid compact">
                <article className="mini-card action-card">
                  <h3>Current project</h3>
                  <p>{deferredProject?.title ?? 'No active project selected yet.'}</p>
                  <button className="text-button dark-on-light" type="button" onClick={() => setActivePage('projects')}>
                    Open Projects
                  </button>
                </article>
                <article className="mini-card action-card">
                  <h3>Current classroom</h3>
                  <p>{selectedClassroom?.title ?? 'No classroom selected yet.'}</p>
                  <button
                    className="text-button dark-on-light"
                    type="button"
                    onClick={() => setActivePage(visiblePages.some(page => page.id === 'classroom') ? 'classroom' : 'projects')}
                  >
                    {visiblePages.some(page => page.id === 'classroom') ? 'Open Classroom' : 'Open Projects'}
                  </button>
                </article>
                <article className="mini-card action-card">
                  <h3>Desktop status</h3>
                  <p>{deferredDesktopContext?.workspaceRoot ?? deferredSystemStatus?.workspace_root ?? 'Workspace pending'}</p>
                  <button className="text-button dark-on-light" type="button" onClick={() => setActivePage('desktop')}>
                    Open Desktop Tools
                  </button>
                </article>
              </div>
            </Panel>
          </>
        ) : null}

        {activePage === 'advanced' && showAdvancedSystems ? (
          <Panel panelId="educlawn" title="EduClawn" subtitle="OpenClaw-derived control plane for bounded teacher and student orchestration.">
            <div className="two-up">
            <div className="subpanel">
              <div className="preview-topline">
                <div>
                  <span className="mini-label">Imported source</span>
                  <h3>{deferredEduclawnOverview?.source_summary.package_name || 'openclaw source pending'}</h3>
                </div>
                <span className="pill">
                  {deferredEduclawnOverview?.source_summary.available ? `v${deferredEduclawnOverview.source_summary.version}` : 'missing'}
                </span>
              </div>
              <p>{deferredEduclawnOverview?.tagline ?? 'EduClawn turns the OpenClaw product shape into a school-safe local-first system.'}</p>
              <div className="chip-row">
                <span className="chip">License {deferredEduclawnOverview?.source_summary.license || 'n/a'}</span>
                <span className="chip">Node {deferredEduclawnOverview?.source_summary.node_requirement || 'n/a'}</span>
                <span className="chip">Channels {deferredEduclawnOverview?.source_summary.counts.channels ?? 0}</span>
                <span className="chip">Skills {deferredEduclawnOverview?.source_summary.counts.skills ?? 0}</span>
                <span className="chip">Extensions {deferredEduclawnOverview?.source_summary.counts.extensions ?? 0}</span>
              </div>
              <div className="card-grid compact">
                <article className="mini-card">
                  <h3>Allowed channels</h3>
                  <div className="chip-row">
                    {educlawnAllowedChannels.map(channel => (
                      <span className="chip" key={channel}>{channel}</span>
                    ))}
                  </div>
                </article>
                <article className="mini-card">
                  <h3>Denied tools</h3>
                  <div className="chip-row">
                    {educlawnDeniedTools.slice(0, 8).map(tool => (
                      <span className="chip" key={tool}>{tool}</span>
                    ))}
                  </div>
                </article>
              </div>
              <div className="preview-card embedded">
                <p className="mini-label">Imported from</p>
                <p>{deferredEduclawnOverview?.source_summary.path || 'No local OpenClaw path detected.'}</p>
              </div>
            </div>

            <div className="subpanel">
              <div className="preview-topline">
                <div>
                  <span className="mini-label">Bootstrap</span>
                  <h3>Create EduClawn Control Plane</h3>
                </div>
                <span className="pill">{educlawnDraft.local_mode}</span>
              </div>
              <form className="form-grid" onSubmit={bootstrapEduClawn}>
                <div className="two-up">
                  <label className="field">
                    <span>School</span>
                    <input value={educlawnDraft.school_name} onChange={event => setEduclawnDraft(current => ({ ...current, school_name: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Teacher</span>
                    <input value={educlawnDraft.teacher_name} onChange={event => setEduclawnDraft(current => ({ ...current, teacher_name: event.target.value }))} />
                  </label>
                </div>
                <div className="two-up">
                  <label className="field">
                    <span>Classroom</span>
                    <input value={educlawnDraft.classroom_title} onChange={event => setEduclawnDraft(current => ({ ...current, classroom_title: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Subject</span>
                    <input value={educlawnDraft.subject} onChange={event => setEduclawnDraft(current => ({ ...current, subject: event.target.value }))} />
                  </label>
                </div>
                <div className="two-up">
                  <label className="field">
                    <span>Grade band</span>
                    <input value={educlawnDraft.grade_band} onChange={event => setEduclawnDraft(current => ({ ...current, grade_band: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Runtime mode</span>
                    <select value={educlawnDraft.local_mode} onChange={event => setEduclawnDraft(current => ({ ...current, local_mode: event.target.value as typeof defaultEduClawnDraft.local_mode }))}>
                      <option value="no-llm">No-LLM</option>
                      <option value="local-llm">Local-LLM</option>
                      <option value="provider-ai">Provider AI</option>
                    </select>
                  </label>
                </div>
                {educlawnDraft.local_mode === 'provider-ai' ? (
                  <label className="field">
                    <span>AI provider profile</span>
                    <select value={educlawnDraft.ai_profile_id} onChange={event => setEduclawnDraft(current => ({ ...current, ai_profile_id: event.target.value }))}>
                      <option value="">Choose a connected provider</option>
                      {deferredAiProfiles.map(profile => (
                        <option key={profile.profile_id} value={profile.profile_id}>
                          {profile.label} · {profile.provider_label}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : null}
                <label className="field">
                  <span>Description</span>
                  <textarea value={educlawnDraft.description} onChange={event => setEduclawnDraft(current => ({ ...current, description: event.target.value }))} />
                </label>
                <div className="two-up">
                  <label className="field">
                    <span>Default template</span>
                    <select value={educlawnDraft.default_template_id} onChange={event => setEduclawnDraft(current => ({ ...current, default_template_id: event.target.value }))}>
                      {deferredTemplates.map(template => (
                        <option key={template.id} value={template.id}>
                          {template.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>Assignment template</span>
                    <select value={educlawnDraft.template_id} onChange={event => setEduclawnDraft(current => ({ ...current, template_id: event.target.value }))}>
                      {deferredTemplates.map(template => (
                        <option key={template.id} value={template.id}>
                          {template.label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <label className="field">
                  <span>Assignment title</span>
                  <input value={educlawnDraft.assignment_title} onChange={event => setEduclawnDraft(current => ({ ...current, assignment_title: event.target.value }))} />
                </label>
                <label className="field">
                  <span>Assignment summary</span>
                  <textarea value={educlawnDraft.assignment_summary} onChange={event => setEduclawnDraft(current => ({ ...current, assignment_summary: event.target.value }))} />
                </label>
                <label className="field">
                  <span>Topic</span>
                  <input value={educlawnDraft.topic} onChange={event => setEduclawnDraft(current => ({ ...current, topic: event.target.value }))} />
                </label>
                <div className="two-up">
                  <label className="field">
                    <span>Goals</span>
                    <textarea value={educlawnDraft.goalsText} onChange={event => setEduclawnDraft(current => ({ ...current, goalsText: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Rubric</span>
                    <textarea value={educlawnDraft.rubricText} onChange={event => setEduclawnDraft(current => ({ ...current, rubricText: event.target.value }))} />
                  </label>
                </div>
                <div className="two-up">
                  <label className="field">
                    <span>Standards</span>
                    <textarea value={educlawnDraft.standardsText} onChange={event => setEduclawnDraft(current => ({ ...current, standardsText: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Due date</span>
                    <input value={educlawnDraft.due_date} onChange={event => setEduclawnDraft(current => ({ ...current, due_date: event.target.value }))} />
                  </label>
                </div>
                <button className="action-button full-width" disabled={isWorking || !deferredEduclawnOverview?.source_summary.available}>
                  {isWorking ? 'Bootstrapping EduClawn...' : 'Bootstrap EduClawn'}
                </button>
              </form>
              {educlawnProviderProfile ? (
                <div className="preview-card embedded">
                  <div className="preview-topline">
                    <div>
                      <span className="mini-label">Provider-backed bootstrap</span>
                      <h3>{educlawnProviderProfile.label}</h3>
                    </div>
                    <span className="pill">{educlawnProviderProfile.provider_label}</span>
                  </div>
                  <p>{educlawnProviderProfile.default_model}</p>
                </div>
              ) : null}
            </div>
          </div>

          {deferredEduclawnBootstrapResult ? (
            <div className="preview-card">
              <div className="preview-topline">
                <div>
                  <span className="mini-label">Generated control plane</span>
                  <h3>{deferredEduclawnBootstrapResult.classroom.title}</h3>
                </div>
                <span className="pill">{deferredEduclawnBootstrapResult.assignment.title}</span>
              </div>
              <p>{deferredEduclawnBootstrapResult.control_plane_path}</p>
              <p className="mini-label">Attestation: {deferredEduclawnBootstrapResult.attestation_path}</p>
              <div className="chip-row">
                {((((deferredEduclawnBootstrapResult.control_plane.gateway as Record<string, unknown> | undefined)?.allowed_channels) as string[] | undefined) ?? []).map(channel => (
                  <span className="chip" key={channel}>{channel}</span>
                ))}
              </div>
              <div className="chip-row">
                <span className="chip">Integrity {(educlawnAttestation?.config_sha256 as string | undefined)?.slice(0, 12) ?? 'n/a'}</span>
                <span className="chip">Signature {String(educlawnAttestation?.signature_algorithm ?? 'n/a')}</span>
                <span className="chip">Attestation {String(educlawnAttestation?.attestation_id ?? 'n/a')}</span>
              </div>
            </div>
          ) : null}
          </Panel>
        ) : activePage === 'advanced' ? (
          <Panel title="Advanced Systems Hidden" subtitle="Simple mode keeps expert controls out of the way until the core project and classroom flow are working.">
            <div className="preview-card embedded">
              <div className="preview-topline">
                <div>
                  <span className="mini-label">Currently hidden</span>
                  <h3>EduClawn, admin ops, and deeper orchestration panels</h3>
                </div>
                <span className="pill">simple mode</span>
              </div>
              <p>Use the Easy Start Center to keep the app calmer for beginners, then reveal the advanced systems when you need them.</p>
              <div className="action-row">
                <button className="action-button" type="button" onClick={() => updateExperienceSetting('simplifiedDashboard', false)}>
                  Reveal Advanced Systems
                </button>
              </div>
            </div>
          </Panel>
        ) : null}

        {activePage === 'projects' ? (
          <>
            {isSimpleMode ? (
              <section className="focus-strip">
                <div className="preview-topline">
                  <div>
                    <span className="mini-label">Projects flow</span>
                    <h3>One step at a time</h3>
                  </div>
                  <span className="pill">{projectView}</span>
                </div>
                <div className="focus-switch">
                  <button className={`focus-pill ${projectView === 'create' ? 'active' : ''}`} type="button" onClick={() => setProjectView('create')}>
                    Create
                  </button>
                  <button className={`focus-pill ${projectView === 'build' ? 'active' : ''}`} type="button" onClick={() => setProjectView('build')}>
                    Build
                  </button>
                  <button className={`focus-pill ${projectView === 'review' ? 'active' : ''}`} type="button" onClick={() => setProjectView('review')}>
                    Review
                  </button>
                </div>
              </section>
            ) : null}

            <section className={`studio-grid ${isSimpleMode ? 'single-column' : ''}`}>
          <div className="column">
            {!isSimpleMode || projectView === 'create' ? (
              <Panel panelId="starter-wizard" title="Starter Wizard" subtitle="Create a typed local project manifest and save it as project.yaml.">
              <form className="form-grid" onSubmit={createProject}>
                <label className="field">
                  <span>Project title</span>
                  <input value={draft.title} onChange={event => updateDraftField('title', event.target.value)} />
                </label>

                <label className="field">
                  <span>Summary</span>
                  <textarea value={draft.summary} onChange={event => updateDraftField('summary', event.target.value)} />
                </label>

                <label className="field">
                  <span>Topic</span>
                  <input value={draft.topic} onChange={event => updateDraftField('topic', event.target.value)} />
                </label>

                <label className="field">
                  <span>Audience</span>
                  <input value={draft.audience} onChange={event => updateDraftField('audience', event.target.value)} />
                </label>

                <label className="field">
                  <span>Goals</span>
                  <textarea value={draft.goalsText} onChange={event => updateDraftField('goalsText', event.target.value)} />
                </label>

                <label className="field">
                  <span>Rubric</span>
                  <textarea value={draft.rubricText} onChange={event => updateDraftField('rubricText', event.target.value)} />
                </label>

                <div className="two-up">
                  <label className="field">
                    <span>Template</span>
                    <select value={draft.template_id} onChange={event => updateDraftField('template_id', event.target.value)}>
                      {deferredTemplates.map(template => (
                        <option key={template.id} value={template.id}>
                          {template.label}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="field">
                    <span>Runtime mode</span>
                    <select value={draft.local_mode} onChange={event => updateDraftField('local_mode', event.target.value as ProjectDraft['local_mode'])}>
                      <option value="no-llm">No-LLM</option>
                      <option value="local-llm">Local-LLM</option>
                      <option value="provider-ai">Provider AI</option>
                    </select>
                  </label>
                </div>

                {draft.local_mode === 'provider-ai' ? (
                  <label className="field">
                    <span>AI provider profile</span>
                    <select value={draft.ai_profile_id} onChange={event => updateDraftField('ai_profile_id', event.target.value)}>
                      <option value="">Choose a connected provider</option>
                      {deferredAiProfiles.map(profile => (
                        <option key={profile.profile_id} value={profile.profile_id}>
                          {profile.label} · {profile.provider_label}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : null}

                {draft.local_mode === 'provider-ai' && !deferredAiProfiles.length ? (
                  <div className="empty-state">Add a provider profile on the AI page before using provider-ai mode.</div>
                ) : null}

                <button className="action-button full-width" disabled={isWorking || isBooting}>
                  {isWorking ? 'Creating project...' : 'Create Local Project'}
                </button>
              </form>

              {selectedTemplate ? (
                <div className="preview-card">
                  <div className="preview-topline">
                    <div>
                      <span className="mini-label">Selected template</span>
                      <h3>{selectedTemplate.label}</h3>
                    </div>
                    <span className="pill">{selectedTemplate.project_type.replaceAll('_', ' ')}</span>
                  </div>
                  <p>{selectedTemplate.description}</p>
                  <div className="chip-row">
                    {selectedTemplate.export_targets.map(target => (
                      <span className="chip" key={target}>{target}</span>
                    ))}
                    {draftProviderProfile ? <span className="chip">AI {draftProviderProfile.provider_label}</span> : null}
                  </div>
                </div>
              ) : null}
              </Panel>
            ) : null}

            {!isSimpleMode ? (
              <Panel title="Template Registry" subtitle="Built-in project blueprints for local-first open-source creation.">
              <div className="card-grid">
                {deferredTemplates.map(template => (
                  <article className={`template-card ${draft.template_id === template.id ? 'selected' : ''}`} key={template.id}>
                    <div className="preview-topline">
                      <div>
                        <span className="mini-label">{template.category}</span>
                        <h3>{template.label}</h3>
                      </div>
                      {template.supports_simulation ? <span className="pill">simulation</span> : null}
                    </div>
                    <p>{template.description}</p>
                    <div className="chip-row">
                      {template.sections.slice(0, 3).map(section => (
                        <span className="chip" key={section.section_id}>{section.title}</span>
                      ))}
                    </div>
                    <button className="text-button dark-on-light" type="button" onClick={() => updateDraftField('template_id', template.id)}>
                      Use Template
                    </button>
                  </article>
                ))}
              </div>
              </Panel>
            ) : null}

            {!isSimpleMode ? (
              <Panel title="Community Packs" subtitle="Sample projects and plugin packs included for open-source reuse.">
              <div className="stack-tight">
                <div>
                  <p className="mini-label">Sample projects</p>
                  <div className="card-grid compact">
                    {(deferredOverview?.sample_projects ?? []).map(sample => (
                      <article className="mini-card" key={sample.slug}>
                        <h3>{sample.title}</h3>
                        <p>{sample.summary}</p>
                      </article>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="mini-label">Plugin packs</p>
                  <div className="card-grid compact">
                    {(deferredOverview?.plugins ?? []).map(plugin => (
                      <article className="mini-card" key={plugin.id}>
                        <h3>{plugin.label}</h3>
                        <p>{plugin.description}</p>
                        <div className="chip-row">
                          {plugin.capabilities.map(capability => (
                            <span className="chip" key={capability}>{capability}</span>
                          ))}
                        </div>
                      </article>
                    ))}
                  </div>
                </div>
              </div>
              </Panel>
            ) : null}
          </div>

          <div className="column">
            {!isSimpleMode || projectView === 'build' ? (
              <Panel panelId="workspace" title="Workspace" subtitle="Select a project, edit the manifest, upload evidence, and compile locally.">
              <div className={`workspace-shell ${isSimpleMode ? 'single-column' : ''}`}>
                <div className="workspace-sidebar">
                  <p className="mini-label">Projects</p>
                  <div className="project-list">
                    {deferredProjects.map(item => (
                      <button
                        className={`project-list-item ${selectedProjectSlug === item.slug ? 'active' : ''}`}
                        key={item.slug}
                        type="button"
                        onClick={() => setSelectedProjectSlug(item.slug)}
                      >
                        <strong>{item.title}</strong>
                        <span>{item.template_label}</span>
                        <small>{formatTimestamp(item.updated_at)}</small>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="workspace-main">
                  {deferredProject ? (
                    <div className="stack-tight">
                      <div className="preview-card">
                        <div className="preview-topline">
                          <div>
                            <span className="mini-label">Project manifest</span>
                            <h3>{deferredProject.title}</h3>
                          </div>
                          <span className="pill">{deferredProject.local_mode}</span>
                        </div>
                        <p>{deferredProject.summary || deferredProject.topic}</p>
                        <div className="chip-row">
                          <span className="chip">{deferredProject.template_label}</span>
                          <span className="chip">{deferredProject.project_type.replaceAll('_', ' ')}</span>
                          <span className="chip">{deferredProject.documents.length} documents</span>
                          <span className="chip">{deferredProject.exports.length} exports</span>
                          {projectProviderProfile ? <span className="chip">AI {projectProviderProfile.provider_label}</span> : null}
                        </div>
                      </div>

                      <div className="preview-card embedded">
                        <div className="preview-topline">
                          <div>
                            <span className="mini-label">Submission readiness</span>
                            <h3>{String((deferredProject.submission_readiness.progress_state as string | undefined) ?? 'not_started').replaceAll('_', ' ')}</h3>
                          </div>
                          <span className="pill">
                            {(deferredProject.submission_readiness.ready_for_export as boolean | undefined) ? 'export unlocked' : 'quality gates active'}
                          </span>
                        </div>
                        <div className="chip-row">
                          <span className="chip">
                            Citations {String((deferredProject.submission_readiness.metrics as Record<string, unknown> | undefined)?.citation_coverage ?? 0)}%
                          </span>
                          <span className="chip">
                            Score {String((deferredProject.submission_readiness.metrics as Record<string, unknown> | undefined)?.overall_score ?? 0)}
                          </span>
                          <span className="chip">
                            Pending approvals {String((deferredProject.submission_readiness.metrics as Record<string, unknown> | undefined)?.pending_approvals ?? 0)}
                          </span>
                        </div>
                        {(((deferredProject.submission_readiness.blocking_reasons as string[] | undefined) ?? []).length > 0) ? (
                          <ul className="narrative-list">
                            {(((deferredProject.submission_readiness.blocking_reasons as string[] | undefined) ?? []).slice(0, 3)).map(reason => (
                              <li key={reason}>{reason}</li>
                            ))}
                          </ul>
                        ) : (
                          <p>Final exports are available. You can share the family-safe view and local bundles.</p>
                        )}
                      </div>

                      <div className="form-grid">
                        <label className="field">
                          <span>Title</span>
                          <input value={deferredProject.title} onChange={event => updateProjectField('title', event.target.value)} />
                        </label>
                        <label className="field">
                          <span>Summary</span>
                          <textarea value={deferredProject.summary} onChange={event => updateProjectField('summary', event.target.value)} />
                        </label>
                        <label className="field">
                          <span>Topic</span>
                          <input value={deferredProject.topic} onChange={event => updateProjectField('topic', event.target.value)} />
                        </label>
                        <label className="field">
                          <span>Audience</span>
                          <input value={deferredProject.audience} onChange={event => updateProjectField('audience', event.target.value)} />
                        </label>
                        <label className="field">
                          <span>Runtime mode</span>
                          <select
                            value={deferredProject.local_mode}
                            onChange={event => updateProjectField('local_mode', event.target.value as StudioProject['local_mode'])}
                          >
                            <option value="no-llm">No-LLM</option>
                            <option value="local-llm">Local-LLM</option>
                            <option value="provider-ai">Provider AI</option>
                          </select>
                        </label>
                        {deferredProject.local_mode === 'provider-ai' ? (
                          <label className="field">
                            <span>AI provider profile</span>
                            <select
                              value={deferredProject.ai_profile_id}
                              onChange={event => updateProjectField('ai_profile_id', event.target.value)}
                            >
                              <option value="">Choose a connected provider</option>
                              {deferredAiProfiles.map(profile => (
                                <option key={profile.profile_id} value={profile.profile_id}>
                                  {profile.label} · {profile.provider_label}
                                </option>
                              ))}
                            </select>
                          </label>
                        ) : null}
                        <label className="field">
                          <span>Goals</span>
                          <textarea value={deferredProject.goals.join('\n')} onChange={event => updateProjectTextList('goals', event.target.value)} />
                        </label>
                        <label className="field">
                          <span>Rubric</span>
                          <textarea value={deferredProject.rubric.join('\n')} onChange={event => updateProjectTextList('rubric', event.target.value)} />
                        </label>
                      </div>

                      <div className="action-row">
                        <button className="action-button" onClick={() => void saveProjectEdits()} disabled={isWorking}>
                          Save Manifest
                        </button>
                        <button className="action-button secondary" onClick={() => void compileProject()} disabled={isWorking}>
                          Run Workflow
                        </button>
                      </div>

                      <div className="two-up">
                        <div className="subpanel">
                          <div className="preview-topline">
                            <div>
                              <span className="mini-label">Document ingestion</span>
                              <h3>Upload Sources</h3>
                            </div>
                            <span className="pill">{deferredProject.documents.length}</span>
                          </div>
                          <input className="file-input" type="file" multiple onChange={uploadDocuments} />
                          <div className="card-grid compact">
                            {deferredProject.documents.map(document => (
                              <article className="mini-card" key={document.document_id}>
                                <h3>{document.title}</h3>
                                <p>{document.summary}</p>
                                <div className="chip-row">
                                  <span className="chip">{document.reading_level}</span>
                                  <span className="chip">{document.chunk_count} chunks</span>
                                  <span className="chip">{document.extraction_method}</span>
                                </div>
                              </article>
                            ))}
                          </div>
                        </div>

                        <div className="subpanel">
                          <div className="preview-topline">
                            <div>
                              <span className="mini-label">Workflow builder</span>
                              <h3>Stages</h3>
                            </div>
                            <span className="pill">{deferredProject.workflow.stages.filter(stage => stage.enabled).length} enabled</span>
                          </div>
                          <div className="workflow-stage-list">
                            {deferredProject.workflow.stages.map(stage => (
                              <label className="stage-toggle" key={stage.stage_id}>
                                <input
                                  type="checkbox"
                                  checked={stage.enabled}
                                  onChange={() => toggleWorkflowStage(stage.stage_id)}
                                />
                                <div>
                                  <strong>{stage.label}</strong>
                                  <p>{stage.description}</p>
                                </div>
                              </label>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="two-up">
                        <div className="subpanel">
                          <div className="preview-topline">
                            <div>
                              <span className="mini-label">Portability</span>
                              <h3>Backups and Imports</h3>
                            </div>
                            <span className="pill">{deferredSystemStatus?.portability.import_supported ? 'enabled' : 'limited'}</span>
                          </div>
                          <label className="field">
                            <span>Imported project title override</span>
                            <input value={importTitle} onChange={event => setImportTitle(event.target.value)} placeholder="Optional imported title" />
                          </label>
                          <input className="file-input" type="file" accept=".cpsbundle,.zip" onChange={importProjectBundle} />
                          <div className="action-row">
                            {bundleExport ? (
                              <a
                                className="text-button dark-on-light"
                                href={api.downloadUrl(deferredProject.slug, bundleExport.export_type)}
                                target="_blank"
                                rel="noreferrer"
                              >
                                Download Project Backup
                              </a>
                            ) : null}
                            <button className="text-button dark-on-light" type="button" onClick={() => void cloneProject()}>
                              Duplicate Current Project
                            </button>
                          </div>
                        </div>

                        <div className="subpanel">
                          <div className="preview-topline">
                            <div>
                              <span className="mini-label">Local AI</span>
                              <h3>Runtime Health</h3>
                            </div>
                            <span className="pill">
                              {deferredSystemStatus?.local_ai.ollama_reachable ? 'Ollama reachable' : 'Fallback mode'}
                            </span>
                          </div>
                          <div className="chip-row">
                            <span className="chip">Configured {deferredSystemStatus?.local_ai.configured_model || 'none'}</span>
                            <span className="chip">
                              OCR {deferredSystemStatus?.tools.tesseract_available ? 'tesseract ready' : 'not detected'}
                            </span>
                            <span className="chip">
                              Warmup {(deferredSystemStatus?.startup.state as string | undefined) ?? 'pending'}
                            </span>
                          </div>
                          <div className="card-grid compact">
                            {(deferredSystemStatus?.local_ai.available_models ?? []).slice(0, 4).map(model => (
                              <article className="mini-card" key={model}>
                                <h3>{model}</h3>
                                <p>Available through the local Ollama-compatible runtime.</p>
                              </article>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="empty-state">
                      Create a project from the starter wizard or select an existing workspace to begin.
                    </div>
                  )}
                </div>
              </div>
              </Panel>
            ) : null}

            {!isSimpleMode || projectView === 'review' ? (
              <Panel title="Evidence and Provenance" subtitle="Search uploaded chunks and inspect the compiled knowledge graph.">
              {deferredProject ? (
                <div className="stack-tight">
                  <div className="action-row">
                    <input
                      className="search-input"
                      value={searchQuery}
                      onChange={event => setSearchQuery(event.target.value)}
                      placeholder="Search uploaded evidence"
                    />
                    <button className="action-button" onClick={() => void runSearch()} disabled={isWorking}>
                      Search Evidence
                    </button>
                  </div>

                  <div className="card-grid compact">
                    {deferredSearchResults.map(result => (
                      <article className="mini-card" key={result.chunk_id}>
                        <div className="preview-topline">
                          <div>
                            <span className="mini-label">{result.citation_label}</span>
                            <h3>{result.score.toFixed(1)}%</h3>
                          </div>
                          <span className="pill">{result.match_reason}</span>
                        </div>
                        <p>{result.excerpt}</p>
                      </article>
                    ))}
                  </div>

                  {deferredGraph ? (
                    <div className="preview-card">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Knowledge graph</span>
                          <h3>{deferredGraph.nodes.length} nodes</h3>
                        </div>
                        <span className="pill">{deferredGraph.edges.length} edges</span>
                      </div>
                      <ul className="narrative-list">
                        {deferredGraph.highlights.map(highlight => (
                          <li key={highlight}>{highlight}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="empty-state">Evidence search activates after a project is selected.</div>
              )}
              </Panel>
            ) : null}

            {!isSimpleMode || projectView === 'review' ? (
              <Panel title="Agent Runtime and Exports" subtitle="Artifact-producing agents, rubric review, simulation blueprint, and local bundles.">
              {deferredProject ? (
                <div className="stack-tight">
                  {compileArtifacts ? (
                    <>
                      <div className="card-grid">
                        {compileArtifacts.agents.map(agent => (
                          <article className="agent-card" key={agent.agent_name}>
                            <div className="preview-topline">
                              <div>
                                <span className="mini-label">{agent.role}</span>
                                <h3>{agent.display_name}</h3>
                              </div>
                              <span className={`priority-pill ${agent.priority}`}>{agent.priority}</span>
                            </div>
                            <p>{agent.summary}</p>
                            <div className="chip-row">
                              <span className="chip">{agent.confidence.toFixed(1)}%</span>
                              {agent.signals.slice(0, 2).map(signal => (
                                <span className="chip" key={signal}>{signal}</span>
                              ))}
                            </div>
                          </article>
                        ))}
                      </div>

                      <div className="two-up">
                        <div className="subpanel">
                          <div className="preview-topline">
                            <div>
                              <span className="mini-label">Written sections</span>
                              <h3>Draft Artifacts</h3>
                            </div>
                          </div>
                          <div className="card-grid compact">
                            {(((compileArtifacts.artifacts.written_sections as Record<string, unknown> | undefined)?.sections) as Array<Record<string, unknown>> | undefined ?? []).map(section => (
                              <article className="mini-card" key={String(section.section_id)}>
                                <h3>{String(section.title)}</h3>
                                <p>{String(section.body)}</p>
                              </article>
                            ))}
                          </div>
                        </div>

                        <div className="subpanel">
                          <div className="preview-topline">
                            <div>
                              <span className="mini-label">Teacher review</span>
                              <h3>Rubric Signals</h3>
                            </div>
                          </div>
                          <div className="preview-card embedded">
                            <p>
                              Overall score:{' '}
                              {String((compileArtifacts.artifacts.teacher_review as Record<string, unknown> | undefined)?.overall_score ?? 'n/a')}
                            </p>
                            <ul className="narrative-list">
                              {((((compileArtifacts.artifacts.teacher_review as Record<string, unknown> | undefined)?.teacher_notes) as string[] | undefined) ?? []).map(note => (
                                <li key={note}>{note}</li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      </div>

                      <div className="two-up">
                        <div className="subpanel">
                          <div className="preview-topline">
                            <div>
                              <span className="mini-label">Simulation blueprint</span>
                              <h3>Branching Engine</h3>
                            </div>
                          </div>
                          <div className="preview-card embedded">
                            <p>
                              Enabled:{' '}
                              {String((compileArtifacts.artifacts.simulation_blueprint as Record<string, unknown> | undefined)?.enabled ?? false)}
                            </p>
                            <p>
                              Nodes:{' '}
                              {String((((compileArtifacts.artifacts.simulation_blueprint as Record<string, unknown> | undefined)?.nodes) as unknown[] | undefined)?.length ?? 0)}
                            </p>
                          </div>
                        </div>

                        <div className="subpanel">
                          <div className="preview-topline">
                            <div>
                              <span className="mini-label">Exports</span>
                              <h3>Local Bundles</h3>
                            </div>
                          </div>
                          <div className="card-grid compact">
                            {exports.map(exportEntry => (
                              <article className="mini-card" key={exportEntry.export_type}>
                                <h3>{exportEntry.export_type.replaceAll('_', ' ')}</h3>
                                <p>{exportEntry.path}</p>
                                <a className="text-button dark-on-light" href={api.downloadUrl(deferredProject.slug, exportEntry.export_type)} target="_blank" rel="noreferrer">
                                  Download
                                </a>
                              </article>
                            ))}
                          </div>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="empty-state">
                      Run the project workflow to generate research briefs, citations, drafts, design tokens, review, and exports.
                    </div>
                  )}

                  <div className="two-up">
                    <div className="subpanel">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Classroom review</span>
                          <h3>Rubric and Standards</h3>
                        </div>
                        <span className="pill">{standardsAlignment.length} standards</span>
                      </div>
                      <div className="chip-row">
                        {standardsAlignment.map(standard => (
                          <span className="chip" key={standard.standard_id}>
                            {standard.label}
                          </span>
                        ))}
                      </div>
                      <div className="preview-card embedded">
                        <p>
                          Rubric report:{' '}
                          {rubricExport ? (
                            <a
                              className="text-button dark-on-light"
                              href={api.downloadUrl(deferredProject.slug, rubricExport.export_type)}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Download latest report
                            </a>
                          ) : (
                            'Run workflow to generate a rubric export.'
                          )}
                        </p>
                        <ul className="narrative-list">
                          {standardsAlignment.map(standard => (
                            <li key={standard.standard_id}>{standard.reason}</li>
                          ))}
                        </ul>
                      </div>

                      <form className="form-grid" onSubmit={submitTeacherComment}>
                        <label className="field">
                          <span>Reviewer</span>
                          <input
                            value={teacherComment.author}
                            onChange={event => setTeacherComment(current => ({ ...current, author: event.target.value }))}
                          />
                        </label>
                        <label className="field">
                          <span>Criterion</span>
                          <input
                            value={teacherComment.criterion}
                            onChange={event => setTeacherComment(current => ({ ...current, criterion: event.target.value }))}
                            placeholder="Optional rubric criterion"
                          />
                        </label>
                        <label className="field">
                          <span>Comment</span>
                          <textarea
                            value={teacherComment.body}
                            onChange={event => setTeacherComment(current => ({ ...current, body: event.target.value }))}
                            placeholder="Add classroom feedback and revision direction"
                          />
                        </label>
                        <button className="action-button" disabled={isWorking || !teacherComment.body.trim()}>
                          Save Teacher Comment
                        </button>
                      </form>

                      <div className="card-grid compact">
                        {teacherComments.slice(0, 4).map(comment => (
                          <article className="mini-card" key={comment.comment_id}>
                            <div className="preview-topline">
                              <div>
                                <span className="mini-label">{comment.criterion || 'General review'}</span>
                                <h3>{comment.author}</h3>
                              </div>
                              <span className="pill">{formatTimestamp(comment.created_at)}</span>
                            </div>
                            <p>{comment.body}</p>
                          </article>
                        ))}
                        {teacherComments.length === 0 ? <div className="empty-state">No teacher comments yet.</div> : null}
                      </div>
                    </div>

                    <div className="subpanel">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Revision history</span>
                          <h3>Project Timeline</h3>
                        </div>
                        <span className="pill">{revisionHistory.length} entries</span>
                      </div>
                      {revisionHistory.length > 0 ? (
                        <ul className="narrative-list">
                          {revisionHistory.slice(0, 8).map(revision => (
                            <li key={revision.revision_id}>
                              <strong>{revision.action}</strong> by {revision.actor} on {formatTimestamp(revision.created_at)}
                              <br />
                              {revision.summary}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <div className="empty-state">Revision history will appear as the project evolves.</div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="empty-state">
                  Select a project to inspect agent outputs, teacher review, revision history, and export bundles.
                </div>
              )}
              </Panel>
            ) : null}
          </div>
            </section>
          </>
        ) : null}

        {activePage === 'classroom' ? (
          <>
            {isSimpleMode ? (
              <section className="focus-strip">
                <div className="preview-topline">
                  <div>
                    <span className="mini-label">Classroom flow</span>
                    <h3>Keep the classroom work focused</h3>
                  </div>
                  <span className="pill">{classroomView}</span>
                </div>
                <div className="focus-switch">
                  <button className={`focus-pill ${classroomView === 'setup' ? 'active' : ''}`} type="button" onClick={() => setClassroomView('setup')}>
                    Setup
                  </button>
                  <button className={`focus-pill ${classroomView === 'launch' ? 'active' : ''}`} type="button" onClick={() => setClassroomView('launch')}>
                    Launch
                  </button>
                  <button className={`focus-pill ${classroomView === 'safety' ? 'active' : ''}`} type="button" onClick={() => setClassroomView('safety')}>
                    Safety
                  </button>
                </div>
              </section>
            ) : null}

            <section className={`studio-grid ${isSimpleMode ? 'single-column' : ''}`}>
          <div className="column">
            {!isSimpleMode || classroomView === 'setup' ? (
              <Panel panelId="teacher-os" title="Teacher OS" subtitle="Create bounded classrooms, seed approved evidence, and launch assignment-driven student work.">
              <div className={`workspace-shell ${isSimpleMode ? 'single-column' : ''}`}>
                <div className="workspace-sidebar">
                  <p className="mini-label">Classrooms</p>
                  <div className="project-list">
                    {deferredEducationClassrooms.map(item => (
                      <button
                        className={`project-list-item ${selectedClassroomId === item.classroom_id ? 'active' : ''}`}
                        key={item.classroom_id}
                        type="button"
                        onClick={() => setSelectedClassroomId(item.classroom_id)}
                      >
                        <strong>{item.title}</strong>
                        <span>{item.subject}</span>
                        <small>{item.student_count} students</small>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="workspace-main">
                  <div className="stack-tight">
                    <div className="preview-card">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Education OS</span>
                          <h3>{deferredEducationOverview?.product_name ?? 'Education OS'}</h3>
                        </div>
                        <span className="pill">{deferredEducationSafety?.mode?.replaceAll('_', ' ') ?? 'bounded'}</span>
                      </div>
                      <p>{deferredEducationOverview?.positioning ?? 'Open-source local-first orchestration for teachers and students.'}</p>
                      <div className="chip-row">
                        {deferredEducationOverview?.role_models.map(model => (
                          <span className="chip" key={model.role}>{model.label}</span>
                        ))}
                      </div>
                    </div>

                    {!isSimpleMode || classroomView === 'setup' ? (
                      <form className="form-grid" onSubmit={createClassroom}>
                      <label className="field">
                        <span>Classroom title</span>
                        <input value={classroomDraft.title} onChange={event => setClassroomDraft(current => ({ ...current, title: event.target.value }))} />
                      </label>
                      <label className="field">
                        <span>Subject</span>
                        <input value={classroomDraft.subject} onChange={event => setClassroomDraft(current => ({ ...current, subject: event.target.value }))} />
                      </label>
                      <label className="field">
                        <span>Grade band</span>
                        <input value={classroomDraft.grade_band} onChange={event => setClassroomDraft(current => ({ ...current, grade_band: event.target.value }))} />
                      </label>
                      <label className="field">
                        <span>Teacher</span>
                        <input value={classroomDraft.teacher_name} onChange={event => setClassroomDraft(current => ({ ...current, teacher_name: event.target.value }))} />
                      </label>
                      <label className="field">
                        <span>Description</span>
                        <textarea value={classroomDraft.description} onChange={event => setClassroomDraft(current => ({ ...current, description: event.target.value }))} />
                      </label>
                      <div className="two-up">
                        <label className="field">
                          <span>Default template</span>
                          <select value={classroomDraft.default_template_id} onChange={event => setClassroomDraft(current => ({ ...current, default_template_id: event.target.value }))}>
                            {deferredTemplates.map(template => (
                              <option key={template.id} value={template.id}>
                                {template.label}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="field">
                          <span>Standards focus</span>
                          <textarea value={classroomDraft.standardsText} onChange={event => setClassroomDraft(current => ({ ...current, standardsText: event.target.value }))} />
                        </label>
                      </div>
                      <button className="action-button full-width" disabled={isWorking}>
                        {isWorking ? 'Saving classroom...' : 'Create Bounded Classroom'}
                      </button>
                      </form>
                    ) : null}

                    {selectedClassroom ? (
                      <>
                        <div className="preview-card embedded">
                          <div className="preview-topline">
                            <div>
                              <span className="mini-label">Selected classroom</span>
                              <h3>{selectedClassroom.title}</h3>
                            </div>
                            <span className="pill">{selectedClassroom.grade_band}</span>
                          </div>
                          <p>{selectedClassroom.description}</p>
                          <div className="chip-row">
                            <span className="chip">{selectedClassroom.student_count} students</span>
                            <span className="chip">{selectedClassroom.assignment_count} assignments</span>
                            <span className="chip">{selectedClassroom.evidence_count} materials</span>
                            <span className="chip">{selectedClassroom.project_count} launched projects</span>
                          </div>
                          <div className="chip-row">
                            <span className="chip">Protected {selectedClassroom.security_posture?.protected ? 'yes' : 'no'}</span>
                            <span className="chip">Audit chain {selectedClassroom.security_posture?.audit_chain_valid ? 'valid' : 'check required'}</span>
                            <span className="chip">Approval chain {selectedClassroom.security_posture?.approval_chain_valid ? 'valid' : 'check required'}</span>
                            <span className="chip">Vault {selectedClassroomKeys ? 'local keys present' : 'missing keys'}</span>
                          </div>
                        </div>

                        {!isSimpleMode || classroomView === 'launch' ? (
                          <div className="two-up">
                          <div className="subpanel">
                            <div className="preview-topline">
                              <div>
                                <span className="mini-label">Teacher roster</span>
                                <h3>Enroll Student</h3>
                              </div>
                            </div>
                            <form className="form-grid" onSubmit={enrollStudent}>
                              <label className="field">
                                <span>Name</span>
                                <input value={studentDraft.name} onChange={event => setStudentDraft(current => ({ ...current, name: event.target.value }))} />
                              </label>
                              <label className="field">
                                <span>Grade level</span>
                                <input value={studentDraft.grade_level} onChange={event => setStudentDraft(current => ({ ...current, grade_level: event.target.value }))} />
                              </label>
                              <label className="field">
                                <span>Learning goals</span>
                                <textarea value={studentDraft.learningGoalsText} onChange={event => setStudentDraft(current => ({ ...current, learningGoalsText: event.target.value }))} />
                              </label>
                              <label className="field">
                                <span>Notes</span>
                                <textarea value={studentDraft.notes} onChange={event => setStudentDraft(current => ({ ...current, notes: event.target.value }))} />
                              </label>
                              <button className="action-button" disabled={isWorking}>Enroll Student</button>
                            </form>
                          </div>

                          <div className="subpanel">
                            <div className="preview-topline">
                              <div>
                                <span className="mini-label">Assignment builder</span>
                                <h3>Create Assignment</h3>
                              </div>
                            </div>
                            <form className="form-grid" onSubmit={createAssignment}>
                              <label className="field">
                                <span>Title</span>
                                <input value={assignmentDraft.title} onChange={event => setAssignmentDraft(current => ({ ...current, title: event.target.value }))} />
                              </label>
                              <label className="field">
                                <span>Summary</span>
                                <textarea value={assignmentDraft.summary} onChange={event => setAssignmentDraft(current => ({ ...current, summary: event.target.value }))} />
                              </label>
                              <label className="field">
                                <span>Topic</span>
                                <input value={assignmentDraft.topic} onChange={event => setAssignmentDraft(current => ({ ...current, topic: event.target.value }))} />
                              </label>
                              <div className="two-up">
                                <label className="field">
                                  <span>Template</span>
                                  <select value={assignmentDraft.template_id} onChange={event => setAssignmentDraft(current => ({ ...current, template_id: event.target.value }))}>
                                    {deferredTemplates.map(template => (
                                      <option key={template.id} value={template.id}>
                                        {template.label}
                                      </option>
                                    ))}
                                  </select>
                                </label>
                                <label className="field">
                                  <span>Runtime mode</span>
                                  <select
                                    value={assignmentDraft.local_mode}
                                    onChange={event => setAssignmentDraft(current => ({ ...current, local_mode: event.target.value as typeof defaultAssignmentDraft.local_mode }))}
                                  >
                                    <option value="no-llm">No-LLM</option>
                                    <option value="local-llm">Local-LLM</option>
                                    <option value="provider-ai">Provider AI</option>
                                  </select>
                                </label>
                              </div>
                              {assignmentDraft.local_mode === 'provider-ai' ? (
                                <label className="field">
                                  <span>AI provider profile</span>
                                  <select
                                    value={assignmentDraft.ai_profile_id}
                                    onChange={event => setAssignmentDraft(current => ({ ...current, ai_profile_id: event.target.value }))}
                                  >
                                    <option value="">Choose a connected provider</option>
                                    {deferredAiProfiles.map(profile => (
                                      <option key={profile.profile_id} value={profile.profile_id}>
                                        {profile.label} · {profile.provider_label}
                                      </option>
                                    ))}
                                  </select>
                                </label>
                              ) : null}
                              <label className="field">
                                <span>Goals</span>
                                <textarea value={assignmentDraft.goalsText} onChange={event => setAssignmentDraft(current => ({ ...current, goalsText: event.target.value }))} />
                              </label>
                              <label className="field">
                                <span>Rubric</span>
                                <textarea value={assignmentDraft.rubricText} onChange={event => setAssignmentDraft(current => ({ ...current, rubricText: event.target.value }))} />
                              </label>
                              <div className="two-up">
                                <label className="field">
                                  <span>Standards</span>
                                  <textarea value={assignmentDraft.standardsText} onChange={event => setAssignmentDraft(current => ({ ...current, standardsText: event.target.value }))} />
                                </label>
                                <label className="field">
                                  <span>Due date</span>
                                  <input value={assignmentDraft.due_date} onChange={event => setAssignmentDraft(current => ({ ...current, due_date: event.target.value }))} />
                                </label>
                              </div>
                              <button className="action-button" disabled={isWorking}>Create Assignment</button>
                            </form>
                          </div>
                          </div>
                        ) : null}
                      </>
                    ) : (
                      <div className="empty-state">Create the first classroom to activate Teacher OS.</div>
                    )}
                  </div>
                </div>
              </div>
              </Panel>
            ) : null}
          </div>

          <div className="column">
            {!isSimpleMode || classroomView !== 'setup' ? (
              <Panel title="Student OS and Safety Layer" subtitle="Launch student projects from approved materials, run scoped agents, and inspect approvals and audit trails.">
              {selectedClassroom ? (
                <div className="stack-tight">
                  {!isSimpleMode || classroomView === 'launch' ? (
                    <div className="two-up">
                    <div className="subpanel">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Classroom controls</span>
                          <h3>Shared Classroom Layer</h3>
                        </div>
                        <span className="pill">{selectedClassroom.safety_mode.replaceAll('_', ' ')}</span>
                      </div>
                      <div className="two-up">
                        <label className="field">
                          <span>Assignment</span>
                          <select value={selectedAssignmentId} onChange={event => setSelectedAssignmentId(event.target.value)}>
                            {selectedClassroom.assignments.map(item => (
                              <option key={item.assignment_id} value={item.assignment_id}>
                                {item.title}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="field">
                          <span>Student</span>
                          <select value={selectedStudentId} onChange={event => setSelectedStudentId(event.target.value)}>
                            {selectedClassroom.students.map(item => (
                              <option key={item.student_id} value={item.student_id}>
                                {item.name}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>
                      <div className="chip-row">
                        <span className="chip">{selectedAssignment?.template_label ?? 'No assignment selected'}</span>
                        <span className="chip">{selectedStudent?.name ?? 'No student selected'}</span>
                        <span className="chip">{selectedClassroom.evidence_library.length} approved materials</span>
                        <span className="chip">Max upload {selectedClassroom.security_posture?.max_material_bytes ?? 0} bytes</span>
                        {selectedAssignment?.ai_profile_id ? <span className="chip">Provider AI linked</span> : null}
                      </div>
                      <div className="action-row">
                        <button className="action-button" type="button" onClick={() => void launchStudentProject()} disabled={isWorking || !selectedAssignment || !selectedStudent}>
                          Launch Student Project
                        </button>
                      </div>
                      <input className="file-input" type="file" multiple onChange={uploadClassroomMaterials} />
                      <div className="card-grid compact">
                        {selectedClassroom.evidence_library.slice(0, 6).map(material => (
                          <article className="mini-card" key={material.material_id}>
                            <div className="preview-topline">
                              <div>
                                <span className="mini-label">{material.scope}</span>
                                <h3>{material.title}</h3>
                              </div>
                              <span className="pill">{material.extraction_method}</span>
                            </div>
                            <p>{material.summary}</p>
                          </article>
                        ))}
                        {selectedClassroom.evidence_library.length === 0 ? <div className="empty-state">Upload approved classroom materials to seed student work.</div> : null}
                      </div>
                    </div>

                    <div className="subpanel">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Agent runtime</span>
                          <h3>Bounded Agent Studio</h3>
                        </div>
                        <span className="pill">{educationAgentDraft.role}</span>
                      </div>
                      <div className="two-up">
                        <label className="field">
                          <span>Role</span>
                          <select value={educationAgentDraft.role} onChange={event => updateEducationAgentRole(event.target.value as 'teacher' | 'student' | 'shared')}>
                            <option value="teacher">Teacher</option>
                            <option value="student">Student</option>
                            <option value="shared">Shared</option>
                          </select>
                        </label>
                        <label className="field">
                          <span>Agent</span>
                          <select
                            value={educationAgentDraft.agent_name}
                            onChange={event => setEducationAgentDraft(current => ({ ...current, agent_name: event.target.value }))}
                          >
                            {filteredEducationAgents.map(agent => (
                              <option key={agent.name} value={agent.name}>
                                {agent.display_name}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>
                      <label className="field">
                        <span>Prompt</span>
                        <textarea
                          value={educationAgentDraft.prompt}
                          onChange={event => setEducationAgentDraft(current => ({ ...current, prompt: event.target.value }))}
                          placeholder="Describe the classroom-safe task for the agent."
                        />
                      </label>
                      <label className="field">
                        <span>Provider override</span>
                        <select
                          value={educationAgentDraft.ai_profile_id}
                          onChange={event => setEducationAgentDraft(current => ({ ...current, ai_profile_id: event.target.value }))}
                        >
                          <option value="">Use assignment or project default</option>
                          {deferredAiProfiles.map(profile => (
                            <option key={profile.profile_id} value={profile.profile_id}>
                              {profile.label} · {profile.provider_label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button className="action-button full-width" type="button" onClick={() => void runEducationAgent()} disabled={isWorking}>
                        Run Bounded Agent
                      </button>

                      {educationAgentResult ? (
                        <div className="preview-card embedded">
                          <div className="preview-topline">
                            <div>
                              <span className="mini-label">{educationAgentResult.role}</span>
                              <h3>{educationAgentResult.display_name}</h3>
                            </div>
                            <span className={`priority-pill ${educationAgentResult.requires_approval ? 'high' : 'low'}`}>
                              {educationAgentResult.requires_approval ? 'approval required' : 'completed'}
                            </span>
                          </div>
                          <p>{educationAgentResult.summary}</p>
                          <div className="chip-row">
                            {educationAgentResult.allowed_actions.slice(0, 4).map(action => (
                              <span className="chip" key={action}>{action}</span>
                            ))}
                            <span className="chip">Risk {educationAgentResult.risk_assessment.band}</span>
                            <span className="chip">Score {educationAgentResult.risk_assessment.score}</span>
                            {educationAgentResult.provider_ai ? <span className="chip">Provider AI active</span> : null}
                          </div>
                          <div className="chip-row">
                            {educationAgentResult.risk_assessment.signals.map(signal => (
                              <span className="chip" key={signal}>{signal}</span>
                            ))}
                          </div>
                          <ul className="narrative-list">
                            {Object.entries(educationAgentResult.artifacts).map(([key, value]) => (
                              <li key={key}>
                                <strong>{key}</strong>: {typeof value === 'string' ? value : JSON.stringify(value).slice(0, 220)}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </div>
                    </div>
                  ) : null}

                  {!isSimpleMode || classroomView === 'safety' ? (
                    <div className="two-up">
                    <div className="subpanel">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Approval gates</span>
                          <h3>Safety Queue</h3>
                        </div>
                        <span className="pill">{deferredEducationApprovals.filter(item => item.status === 'pending').length} pending</span>
                      </div>
                      <div className="form-grid">
                        <label className="field">
                          <span>Reviewer</span>
                          <input value={approvalReview.reviewer} onChange={event => setApprovalReview(current => ({ ...current, reviewer: event.target.value }))} />
                        </label>
                        <label className="field">
                          <span>Resolution note</span>
                          <textarea value={approvalReview.note} onChange={event => setApprovalReview(current => ({ ...current, note: event.target.value }))} />
                        </label>
                      </div>
                      <div className="card-grid compact">
                        {deferredEducationApprovals.slice(0, 6).map(approval => (
                          <article className="mini-card" key={approval.approval_id}>
                            <div className="preview-topline">
                              <div>
                                <span className="mini-label">{approval.role}</span>
                                <h3>{approval.agent_name}</h3>
                              </div>
                              <span className="pill">{approval.status}</span>
                            </div>
                            <p>{approval.rationale}</p>
                            <div className="chip-row">
                              {approval.requested_actions.map(action => (
                                <span className="chip" key={action}>{action}</span>
                              ))}
                              {approval.risk_assessment ? <span className="chip">Risk {approval.risk_assessment.band}</span> : null}
                              {approval.entry_hash ? <span className="chip">Hash {approval.entry_hash.slice(0, 10)}</span> : null}
                            </div>
                            {approval.status === 'pending' ? (
                              <div className="action-row">
                                <button className="text-button dark-on-light" type="button" onClick={() => void resolveApproval(approval.approval_id, 'approved')}>
                                  Approve
                                </button>
                                <button className="text-button dark-on-light" type="button" onClick={() => void resolveApproval(approval.approval_id, 'rejected')}>
                                  Reject
                                </button>
                              </div>
                            ) : null}
                          </article>
                        ))}
                        {deferredEducationApprovals.length === 0 ? <div className="empty-state">No approval requests yet.</div> : null}
                      </div>
                    </div>

                    <div className="subpanel">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Audit and policy</span>
                          <h3>Safety Console</h3>
                        </div>
                        <span className="pill">{deferredEducationSafety?.policy_name ?? 'policy'}</span>
                      </div>
                      <div className="chip-row">
                        {(deferredEducationSafety?.blocked_capabilities ?? []).map(capability => (
                          <span className="chip" key={capability}>{capability}</span>
                        ))}
                        <span className="chip">Audit chain {deferredEducationSafety?.audit_chain_valid ? 'valid' : 'check required'}</span>
                        <span className="chip">Approval chain {deferredEducationSafety?.approval_chain_valid ? 'valid' : 'check required'}</span>
                      </div>
                      <ul className="narrative-list">
                        {(deferredEducationSafety?.approval_required_for ?? []).map(item => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                      <p className="mini-label">
                        Material policy: max {String((deferredEducationSafety?.material_policy?.max_material_bytes as number | undefined) ?? 0)} bytes, types{' '}
                        {((deferredEducationSafety?.material_policy?.allowed_content_types as string[] | undefined) ?? []).join(', ') || 'n/a'}
                      </p>
                      <div className="card-grid compact">
                        {deferredEducationAudit.slice(0, 6).map(entry => (
                          <article className="mini-card" key={entry.audit_id}>
                            <div className="preview-topline">
                              <div>
                                <span className="mini-label">{entry.actor_role}</span>
                                <h3>{entry.action}</h3>
                              </div>
                              <span className="pill">{entry.status}</span>
                            </div>
                            <p>{entry.summary}</p>
                            <div className="chip-row">
                              {entry.risk_assessment ? <span className="chip">Risk {entry.risk_assessment.band}</span> : null}
                              {entry.entry_hash ? <span className="chip">Hash {entry.entry_hash.slice(0, 10)}</span> : null}
                            </div>
                          </article>
                        ))}
                      </div>
                    </div>
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="empty-state">
                  Teacher OS activates after the first classroom is created.
                </div>
              )}
              </Panel>
            ) : null}
          </div>
            </section>
          </>
        ) : null}

        {activePage === 'autopilot' ? (
          <>
            <section className="studio-grid">
              <div className="column">
                <Panel title="Assignment Autopilot" subtitle="Enter a topic and rubric, then let EduClawn build the assignment, evidence pack, checkpoints, standards map, and export path.">
                  <form className="form-grid" onSubmit={runAssignmentAutopilot}>
                    <label className="field">
                      <span>Topic</span>
                      <input value={autopilotDraft.topic} onChange={event => setAutopilotDraft(current => ({ ...current, topic: event.target.value }))} />
                    </label>
                    <label className="field">
                      <span>Assignment title override</span>
                      <input value={autopilotDraft.title} onChange={event => setAutopilotDraft(current => ({ ...current, title: event.target.value }))} placeholder="Optional title override" />
                    </label>
                    <label className="field">
                      <span>Summary override</span>
                      <textarea value={autopilotDraft.summary} onChange={event => setAutopilotDraft(current => ({ ...current, summary: event.target.value }))} placeholder="Optional teacher-facing summary" />
                    </label>
                    <div className="two-up">
                      <label className="field">
                        <span>Audience</span>
                        <input value={autopilotDraft.audience} onChange={event => setAutopilotDraft(current => ({ ...current, audience: event.target.value }))} />
                      </label>
                      <label className="field">
                        <span>Due date</span>
                        <input value={autopilotDraft.due_date} onChange={event => setAutopilotDraft(current => ({ ...current, due_date: event.target.value }))} />
                      </label>
                    </div>
                    <div className="two-up">
                      <label className="field">
                        <span>Template</span>
                        <select value={autopilotDraft.template_id} onChange={event => setAutopilotDraft(current => ({ ...current, template_id: event.target.value }))}>
                          <option value="">Auto-pick from topic</option>
                          {deferredTemplates.map(template => (
                            <option key={template.id} value={template.id}>{template.label}</option>
                          ))}
                        </select>
                      </label>
                      <label className="field">
                        <span>Runtime mode</span>
                        <select value={autopilotDraft.local_mode} onChange={event => setAutopilotDraft(current => ({ ...current, local_mode: event.target.value as typeof defaultAutopilotDraft.local_mode }))}>
                          <option value="no-llm">No-LLM</option>
                          <option value="local-llm">Local-LLM</option>
                          <option value="provider-ai">Provider AI</option>
                        </select>
                      </label>
                    </div>
                    {autopilotDraft.local_mode === 'provider-ai' ? (
                      <label className="field">
                        <span>Provider profile</span>
                        <select value={autopilotDraft.ai_profile_id} onChange={event => setAutopilotDraft(current => ({ ...current, ai_profile_id: event.target.value }))}>
                          <option value="">Auto-route from provider catalog</option>
                          {deferredAiProfiles.map(profile => (
                            <option key={profile.profile_id} value={profile.profile_id}>{profile.label} · {profile.provider_label}</option>
                          ))}
                        </select>
                      </label>
                    ) : null}
                    <label className="field">
                      <span>Goals</span>
                      <textarea value={autopilotDraft.goalsText} onChange={event => setAutopilotDraft(current => ({ ...current, goalsText: event.target.value }))} />
                    </label>
                    <div className="two-up">
                      <label className="field">
                        <span>Rubric</span>
                        <textarea value={autopilotDraft.rubricText} onChange={event => setAutopilotDraft(current => ({ ...current, rubricText: event.target.value }))} />
                      </label>
                      <label className="field">
                        <span>Standards</span>
                        <textarea value={autopilotDraft.standardsText} onChange={event => setAutopilotDraft(current => ({ ...current, standardsText: event.target.value }))} />
                      </label>
                    </div>
                    <label className="field">
                      <span>Lesson seed</span>
                      <textarea value={autopilotDraft.lessonSeed} onChange={event => setAutopilotDraft(current => ({ ...current, lessonSeed: event.target.value }))} />
                    </label>
                    <button className="action-button full-width" disabled={isWorking || !selectedClassroomId}>
                      {isWorking ? 'Running Autopilot...' : 'Run Assignment Autopilot'}
                    </button>
                  </form>
                </Panel>
              </div>

              <div className="column">
                <Panel title="Autopilot Output" subtitle="See how the route, evidence pack, standards map, and export set came together.">
                  {deferredAutopilotResult ? (
                    <div className="stack-tight">
                      <div className="preview-card">
                        <div className="preview-topline">
                          <div>
                            <span className="mini-label">Created assignment</span>
                            <h3>{deferredAutopilotResult.assignment.title}</h3>
                          </div>
                          <span className="pill">{deferredAutopilotResult.route.execution_mode}</span>
                        </div>
                        <p>{deferredAutopilotResult.teacher_summary}</p>
                        <div className="chip-row">
                          <span className="chip">{deferredAutopilotResult.assignment.template_label}</span>
                          <span className="chip">{deferredAutopilotResult.evidence_pack.length} evidence items</span>
                          <span className="chip">{deferredAutopilotResult.export_targets.length} export targets</span>
                          {deferredAutopilotResult.route.selected_provider ? (
                            <span className="chip">{deferredAutopilotResult.route.selected_provider.provider_label}</span>
                          ) : null}
                        </div>
                      </div>
                      <div className="card-grid compact">
                        {deferredAutopilotResult.evidence_pack.map(item => (
                          <article className="mini-card" key={item.material_id}>
                            <h3>{item.title}</h3>
                            <p>{item.summary}</p>
                          </article>
                        ))}
                      </div>
                      <div className="preview-card embedded">
                        <p className="mini-label">Checkpoint plan</p>
                        <ul className="narrative-list">
                          {deferredAutopilotResult.checkpoints.map(checkpoint => (
                            <li key={String(checkpoint.checkpoint)}>
                              <strong>{String(checkpoint.checkpoint)}</strong>: {String(checkpoint.detail)}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  ) : (
                    <div className="empty-state">Run Assignment Autopilot after selecting a classroom.</div>
                  )}
                </Panel>
              </div>
            </section>

            <section className="studio-grid">
              <div className="column">
                <Panel title="Student Revision Coach" subtitle="Compare a draft to the rubric, generate revision tasks, and verify claims against uploaded evidence.">
                  <div className="stack-tight">
                    <label className="field">
                      <span>Draft</span>
                      <textarea value={revisionCoachDraft.draftText} onChange={event => setRevisionCoachDraft(current => ({ ...current, draftText: event.target.value }))} />
                    </label>
                    <label className="field">
                      <span>Teacher feedback</span>
                      <textarea value={revisionCoachDraft.teacherFeedbackText} onChange={event => setRevisionCoachDraft(current => ({ ...current, teacherFeedbackText: event.target.value }))} />
                    </label>
                    <label className="field">
                      <span>Provider override</span>
                      <select value={revisionCoachDraft.ai_profile_id} onChange={event => setRevisionCoachDraft(current => ({ ...current, ai_profile_id: event.target.value }))}>
                        <option value="">Auto-route</option>
                        {deferredAiProfiles.map(profile => (
                          <option key={profile.profile_id} value={profile.profile_id}>{profile.label} · {profile.provider_label}</option>
                        ))}
                      </select>
                    </label>
                    <div className="action-row">
                      <button className="action-button" type="button" onClick={() => void runRevisionCoach()} disabled={isWorking || !selectedAssignmentId}>
                        Run Revision Coach
                      </button>
                      <button className="text-button dark-on-light" type="button" onClick={() => void runCitationVerifier()} disabled={isWorking || !selectedProjectSlug}>
                        Verify Citations
                      </button>
                    </div>
                    {deferredRevisionCoachResult ? (
                      <div className="preview-card embedded">
                        <div className="preview-topline">
                          <div>
                            <span className="mini-label">Coach summary</span>
                            <h3>{deferredRevisionCoachResult.route.execution_mode}</h3>
                          </div>
                          <span className="pill">{deferredRevisionCoachResult.citation_verification.overall_score}% verified</span>
                        </div>
                        <p>{deferredRevisionCoachResult.student_summary}</p>
                        <ul className="narrative-list">
                          {deferredRevisionCoachResult.revision_tasks.map(task => (
                            <li key={task}>{task}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    {deferredCitationVerification ? (
                      <div className="preview-card embedded">
                        <p className="mini-label">Citation Verifier</p>
                        <div className="chip-row">
                          <span className="chip">Ready {deferredCitationVerification.ready_for_export ? 'yes' : 'no'}</span>
                          <span className="chip">{deferredCitationVerification.verified_claims.length} verified claims</span>
                          <span className="chip">{deferredCitationVerification.blocked_claims.length} blocked claims</span>
                        </div>
                      </div>
                    ) : null}
                  </div>
                </Panel>
              </div>

              <div className="column">
                <Panel title="Lesson-to-Project Agent" subtitle="Turn a lesson plan into a local project scaffold with reusable sections, goals, and seeded classroom evidence.">
                  <form className="form-grid" onSubmit={runLessonToProject}>
                    <label className="field">
                      <span>Lesson plan</span>
                      <textarea value={lessonProjectDraft.lessonPlan} onChange={event => setLessonProjectDraft(current => ({ ...current, lessonPlan: event.target.value }))} />
                    </label>
                    <div className="two-up">
                      <label className="field">
                        <span>Title override</span>
                        <input value={lessonProjectDraft.title} onChange={event => setLessonProjectDraft(current => ({ ...current, title: event.target.value }))} />
                      </label>
                      <label className="field">
                        <span>Template</span>
                        <select value={lessonProjectDraft.template_id} onChange={event => setLessonProjectDraft(current => ({ ...current, template_id: event.target.value }))}>
                          <option value="">Auto-pick</option>
                          {deferredTemplates.map(template => (
                            <option key={template.id} value={template.id}>{template.label}</option>
                          ))}
                        </select>
                      </label>
                    </div>
                    <label className="field">
                      <span>Provider override</span>
                      <select value={lessonProjectDraft.ai_profile_id} onChange={event => setLessonProjectDraft(current => ({ ...current, ai_profile_id: event.target.value }))}>
                        <option value="">Auto-route</option>
                        {deferredAiProfiles.map(profile => (
                          <option key={profile.profile_id} value={profile.profile_id}>{profile.label} · {profile.provider_label}</option>
                        ))}
                      </select>
                    </label>
                    <label className="stage-toggle">
                      <input
                        type="checkbox"
                        checked={lessonProjectDraft.seed_from_classroom}
                        onChange={() => setLessonProjectDraft(current => ({ ...current, seed_from_classroom: !current.seed_from_classroom }))}
                      />
                      <div>
                        <strong>Seed from classroom evidence</strong>
                        <p>Pull approved classroom materials into the generated project.</p>
                      </div>
                    </label>
                    <button className="action-button full-width" disabled={isWorking}>
                      {isWorking ? 'Converting lesson...' : 'Convert Lesson to Project'}
                    </button>
                  </form>
                  {deferredLessonProjectResult ? (
                    <div className="preview-card embedded">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Created project</span>
                          <h3>{deferredLessonProjectResult.project.title}</h3>
                        </div>
                        <span className="pill">{deferredLessonProjectResult.route.execution_mode}</span>
                      </div>
                      <p>{String(deferredLessonProjectResult.scaffold.planner_note ?? '')}</p>
                    </div>
                  ) : null}
                </Panel>
              </div>
            </section>
          </>
        ) : null}

        {activePage === 'ops' ? (
          <section className="studio-grid">
            <div className="column">
              <Panel title="Classroom Library" subtitle="Promote shared evidence into a teacher library that can be reused across classes and years.">
                <div className="stack-tight">
                  <div className="action-row">
                    <button className="action-button" type="button" onClick={() => void promoteLibrary()} disabled={isWorking || !selectedClassroomId}>
                      Promote Classroom Evidence
                    </button>
                    <button className="text-button dark-on-light" type="button" onClick={() => void refreshGrowth()}>
                      Refresh Library
                    </button>
                  </div>
                  {deferredClassroomLibrary ? (
                    <>
                      <div className="preview-card embedded">
                        <div className="preview-topline">
                          <div>
                            <span className="mini-label">Reusable vault</span>
                            <h3>{deferredClassroomLibrary.teacher_name}</h3>
                          </div>
                          <span className="pill">{deferredClassroomLibrary.item_count} items</span>
                        </div>
                        <div className="chip-row">
                          {deferredClassroomLibrary.collections.map(collection => (
                            <span className="chip" key={String(collection.collection_id)}>{String(collection.label)}</span>
                          ))}
                        </div>
                      </div>
                      <div className="card-grid compact">
                        {deferredClassroomLibrary.recommended_reuse.map(item => (
                          <article className="mini-card" key={String(item.library_item_id)}>
                            <h3>{String(item.title)}</h3>
                            <p>{String(item.summary)}</p>
                          </article>
                        ))}
                        {deferredClassroomLibrary.recommended_reuse.length === 0 ? <div className="empty-state">Reuse suggestions appear after evidence has been promoted across classrooms.</div> : null}
                      </div>
                    </>
                  ) : (
                    <div className="empty-state">Select a classroom to inspect the shared library.</div>
                  )}
                </div>
              </Panel>

              <Panel title="Peer Review Mode" subtitle="Let students draft rubric-guided peer feedback, then hold it behind a teacher approval gate.">
                <div className="stack-tight">
                  <label className="field">
                    <span>Peer review draft</span>
                    <textarea value={peerReviewDraft.draftText} onChange={event => setPeerReviewDraft(current => ({ ...current, draftText: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Rubric</span>
                    <textarea value={peerReviewDraft.rubricText} onChange={event => setPeerReviewDraft(current => ({ ...current, rubricText: event.target.value }))} />
                  </label>
                  <button className="action-button" type="button" onClick={() => void submitPeerReview()} disabled={isWorking || !selectedStudentId}>
                    Submit Peer Review
                  </button>
                  <div className="form-grid">
                    <label className="field">
                      <span>Moderator</span>
                      <input value={peerReviewResolution.reviewer} onChange={event => setPeerReviewResolution(current => ({ ...current, reviewer: event.target.value }))} />
                    </label>
                    <label className="field">
                      <span>Moderation note</span>
                      <textarea value={peerReviewResolution.note} onChange={event => setPeerReviewResolution(current => ({ ...current, note: event.target.value }))} />
                    </label>
                  </div>
                  <div className="card-grid compact">
                    {deferredPeerReviews.map(review => (
                      <article className="mini-card" key={review.review_id}>
                        <div className="preview-topline">
                          <div>
                            <span className="mini-label">{review.reviewer_name}</span>
                            <h3>{review.target_student_name}</h3>
                          </div>
                          <span className="pill">{review.status}</span>
                        </div>
                        <p>{review.summary}</p>
                        {review.status === 'pending_teacher_approval' ? (
                          <div className="action-row">
                            <button className="text-button dark-on-light" type="button" onClick={() => void resolvePeerReview(review.review_id, 'approved')}>
                              Approve
                            </button>
                            <button className="text-button dark-on-light" type="button" onClick={() => void resolvePeerReview(review.review_id, 'rejected')}>
                              Reject
                            </button>
                          </div>
                        ) : null}
                      </article>
                    ))}
                    {deferredPeerReviews.length === 0 ? <div className="empty-state">Peer review requests appear here after students submit them.</div> : null}
                  </div>
                  {deferredPeerReviewPairs ? (
                    <div className="preview-card embedded">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Suggested pairings</span>
                          <h3>{deferredPeerReviewPairs.assignment_title}</h3>
                        </div>
                        <span className="pill">{deferredPeerReviewPairs.pair_count} pairs</span>
                      </div>
                      <ul className="narrative-list">
                        {deferredPeerReviewPairs.pairs.slice(0, 4).map(pair => (
                          <li key={`${String(pair.reviewer_student_id)}-${String(pair.target_student_id)}`}>
                            {String(pair.reviewer_name)} reviews {String(pair.target_student_name)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              </Panel>
            </div>

            <div className="column">
              <Panel title="Teacher Ops" subtitle="Auto-map standards, identify intervention needs, replay classroom actions, train rubric patterns, and generate assessment packs.">
                <div className="stack-tight">
                  <div className="action-row">
                    <button className="action-button" type="button" onClick={() => void generateAssessmentPack()} disabled={isWorking || !selectedAssignmentId}>
                      Generate Assessment Pack
                    </button>
                    <button className="text-button dark-on-light" type="button" onClick={() => void trainRubricModel()} disabled={isWorking || !selectedProjectSlug}>
                      Train Rubric Model
                    </button>
                    <button className="text-button dark-on-light" type="button" onClick={() => void refreshGrowth()}>
                      Refresh Teacher Ops
                    </button>
                  </div>
                  {deferredStandardsMap ? (
                    <div className="preview-card embedded">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Standards Mapper</span>
                          <h3>{deferredStandardsMap.assignment_title}</h3>
                        </div>
                        <span className="pill">{deferredStandardsMap.standards_alignment.length} alignments</span>
                      </div>
                      <ul className="narrative-list">
                        {deferredStandardsMap.teacher_moves.map(move => (
                          <li key={move}>{move}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {deferredInterventionDashboard ? (
                    <div className="preview-card embedded">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Intervention Dashboard</span>
                          <h3>{deferredInterventionDashboard.classroom_title}</h3>
                        </div>
                        <span className="pill">{String(deferredInterventionDashboard.summary.students ?? 0)} students</span>
                      </div>
                      <div className="chip-row">
                        {deferredInterventionDashboard.interventions.map(item => (
                          <span className="chip" key={item}>{item}</span>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  {deferredClassroomRoster ? (
                    <div className="preview-card embedded">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Roster</span>
                          <h3>{deferredClassroomRoster.classroom_title}</h3>
                        </div>
                        <span className="pill">{String(deferredClassroomRoster.summary.students ?? 0)} students</span>
                      </div>
                      <div className="chip-row">
                        <span className="chip">Drafting {String(deferredClassroomRoster.summary.drafting ?? 0)}</span>
                        <span className="chip">Review {String(deferredClassroomRoster.summary.under_review ?? 0)}</span>
                        <span className="chip">Ready {String(deferredClassroomRoster.summary.ready_for_export ?? 0)}</span>
                      </div>
                    </div>
                  ) : null}
                  {deferredAssignmentStatusBoard ? (
                    <div className="preview-card embedded">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Assignment status board</span>
                          <h3>{deferredAssignmentStatusBoard.classroom_title}</h3>
                        </div>
                        <span className="pill">{deferredAssignmentStatusBoard.assignments.length} assignments</span>
                      </div>
                      <div className="card-grid compact">
                        {deferredAssignmentStatusBoard.assignments.slice(0, 4).map(item => (
                          <article className="mini-card" key={String(item.assignment_id)}>
                            <h3>{String(item.assignment_title)}</h3>
                            <p>Status: {String(item.status)}</p>
                            <div className="chip-row">
                              <span className="chip">Launched {String(item.launched_count)}</span>
                              <span className="chip">Ready {String(item.ready_count)}</span>
                            </div>
                          </article>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  {deferredAssessmentPack ? (
                    <div className="preview-card embedded">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Assessment Pack Generator</span>
                          <h3>{deferredAssessmentPack.assignment_title}</h3>
                        </div>
                        <span className="pill">{deferredAssessmentPack.quiz_questions.length} quiz prompts</span>
                      </div>
                      <p>{deferredAssessmentPack.teacher_note}</p>
                    </div>
                  ) : null}
                  {deferredRubricModel ? (
                    <div className="preview-card embedded">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Rubric Trainer</span>
                          <h3>{deferredRubricModel.model_id}</h3>
                        </div>
                        <span className="pill">{deferredRubricModel.trained_on_projects.length} projects</span>
                      </div>
                      <div className="chip-row">
                        {deferredRubricModel.quality_signals.map(signal => (
                          <span className="chip" key={signal}>{signal}</span>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  {deferredClassroomReplay ? (
                    <div className="preview-card embedded">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Classroom Replay</span>
                          <h3>{deferredClassroomReplay.classroom_title}</h3>
                        </div>
                        <span className="pill">{String(deferredClassroomReplay.counts.timeline_events ?? 0)} events</span>
                      </div>
                      <div className="card-grid compact">
                        {deferredClassroomReplay.timeline.slice(0, 6).map(entry => (
                          <article className="mini-card" key={String(entry.event_id)}>
                            <h3>{String(entry.headline)}</h3>
                            <p>{String(entry.summary)}</p>
                          </article>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              </Panel>
            </div>
          </section>
        ) : null}

        {activePage === 'family' ? (
          <section className="studio-grid single-column">
            <div className="column">
              <Panel title="Parent and Family View" subtitle="Use simple language, show progress clearly, and keep downloads one click away.">
                {deferredFamilyView ? (
                  <div className="stack-tight">
                    <div className="preview-card">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">{deferredFamilyView.classroom_title}</span>
                          <h3>{deferredFamilyView.project_title}</h3>
                        </div>
                        <span className="pill">{String(deferredFamilyView.progress.status ?? 'in progress')}</span>
                      </div>
                      <p>{deferredFamilyView.summary}</p>
                      <div className="chip-row">
                        <span className="chip">Student {deferredFamilyView.student_name || 'n/a'}</span>
                        <span className="chip">Assignment {deferredFamilyView.assignment_title || 'n/a'}</span>
                        <span className="chip">{String(deferredFamilyView.progress.documents ?? 0)} sources</span>
                        <span className="chip">{String(deferredFamilyView.progress.exports ?? 0)} downloads</span>
                      </div>
                    </div>
                    <div className="preview-card embedded">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Family-safe sharing</span>
                          <h3>Read-only link</h3>
                        </div>
                        <span className="pill">
                          {deferredFamilyView.share_link || deferredFamilyShareLink?.share_url ? 'ready' : 'not created'}
                        </span>
                      </div>
                      <p>{deferredFamilyView.share_link || deferredFamilyShareLink?.share_url || 'Create a read-only share link for families from the selected classroom project.'}</p>
                      <div className="action-row">
                        <button className="action-button secondary" type="button" onClick={() => void createFamilyShareLink()} disabled={isWorking || !selectedProjectSlug}>
                          Create Share Link
                        </button>
                      </div>
                    </div>
                    <div className="two-up">
                      <div className="subpanel">
                        <div className="preview-topline">
                          <div>
                            <span className="mini-label">Next steps</span>
                            <h3>What the family can do</h3>
                          </div>
                        </div>
                        <ul className="narrative-list">
                          {deferredFamilyView.next_steps.map(step => (
                            <li key={step}>{step}</li>
                          ))}
                        </ul>
                      </div>
                      <div className="subpanel">
                        <div className="preview-topline">
                          <div>
                            <span className="mini-label">Downloads</span>
                            <h3>Exported work</h3>
                          </div>
                        </div>
                        <div className="card-grid compact">
                          {deferredFamilyView.downloads.map(download => (
                            <article className="mini-card" key={download.export_type}>
                              <h3>{download.export_type.replaceAll('_', ' ')}</h3>
                              {selectedProjectSlug ? (
                                <a className="text-button dark-on-light" href={api.downloadUrl(selectedProjectSlug, download.export_type)} target="_blank" rel="noreferrer">
                                  Download
                                </a>
                              ) : null}
                            </article>
                          ))}
                        </div>
                      </div>
                    </div>
                    <div className="preview-card embedded">
                      <p className="mini-label">Teacher comments in simple language</p>
                      <ul className="narrative-list">
                        {deferredFamilyView.teacher_comments.map(comment => (
                          <li key={`${String(comment.created_at)}-${String(comment.criterion)}`}>
                            <strong>{String(comment.criterion)}</strong>: {String(comment.plain_language)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ) : (
                  <div className="empty-state">Launch and compile a student project to activate the family view.</div>
                )}
              </Panel>
            </div>
          </section>
        ) : null}

        {activePage === 'marketplace' ? (
          <section className="studio-grid">
            <div className="column">
              <Panel title="Template Marketplace" subtitle="Browse the open-source template system, install school packs, and reuse sample projects.">
                <div className="stack-tight">
                  <div className="card-grid compact">
                    {(deferredMarketplace?.school_packs ?? []).map(pack => (
                      <article className="mini-card" key={pack.pack_id}>
                        <div className="preview-topline">
                          <div>
                            <span className="mini-label">{pack.audience}</span>
                            <h3>{pack.label}</h3>
                          </div>
                          <span className="pill">{pack.installed ? 'installed' : 'available'}</span>
                        </div>
                        <p>{pack.description}</p>
                        <div className="chip-row">
                          {pack.recommended_template_ids.map(templateId => (
                            <span className="chip" key={templateId}>{templateId}</span>
                          ))}
                        </div>
                        <button className="text-button dark-on-light" type="button" onClick={() => void installSchoolPack(pack.pack_id)} disabled={isWorking}>
                          {pack.installed ? 'Reinstall Pack' : 'Install Pack'}
                        </button>
                      </article>
                    ))}
                  </div>
                  {deferredGrowthOverview ? (
                    <div className="preview-card embedded">
                      <div className="chip-row">
                        <span className="chip">{String(deferredGrowthOverview.counts.classrooms ?? 0)} classrooms</span>
                        <span className="chip">{String(deferredGrowthOverview.counts.library_items ?? 0)} library items</span>
                        <span className="chip">{String(deferredGrowthOverview.counts.school_packs ?? 0)} school packs</span>
                      </div>
                    </div>
                  ) : null}
                  {deferredLastInstalledPack ? (
                    <div className="preview-card embedded">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Installed school pack</span>
                          <h3>{deferredLastInstalledPack.label}</h3>
                        </div>
                        <span className="pill">{deferredLastInstalledPack.created_samples.length} samples</span>
                      </div>
                      <p>{deferredLastInstalledPack.manifest_path}</p>
                    </div>
                  ) : null}
                </div>
              </Panel>
            </div>

            <div className="column">
              <Panel title="Plugin SDK and Offline School Edition" subtitle="See how template/plugin extension points and local-first deployment fit together.">
                <div className="stack-tight">
                  <div className="preview-card embedded">
                    <div className="preview-topline">
                      <div>
                        <span className="mini-label">Plugin SDK</span>
                        <h3>{String(deferredMarketplace?.plugin_sdk.installed_plugins ?? 0)} installed plugins</h3>
                      </div>
                      <span className="pill">open source</span>
                    </div>
                    <div className="chip-row">
                      {(((deferredMarketplace?.plugin_sdk.extension_points as string[] | undefined) ?? [])).map(point => (
                        <span className="chip" key={point}>{point}</span>
                      ))}
                    </div>
                    <p>{String(deferredMarketplace?.plugin_sdk.plugin_sdk_path ?? '')}</p>
                  </div>
                  <div className="preview-card embedded">
                    <div className="preview-topline">
                      <div>
                        <span className="mini-label">Offline School Edition</span>
                        <h3>{deferredOfflineSchoolEdition?.edition_name ?? 'Offline edition pending'}</h3>
                      </div>
                      <span className="pill">{deferredOfflineSchoolEdition?.readiness_score ?? 0}% ready</span>
                    </div>
                    <div className="chip-row">
                      {(deferredOfflineSchoolEdition?.supported_modes ?? []).map(mode => (
                        <span className="chip" key={mode}>{mode}</span>
                      ))}
                    </div>
                    <ul className="narrative-list">
                      {(deferredOfflineSchoolEdition?.recommended_rollout ?? []).map(item => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="card-grid compact">
                    {(deferredMarketplace?.templates ?? []).slice(0, 6).map(template => (
                      <article className="mini-card" key={template.id}>
                        <h3>{template.label}</h3>
                        <p>{template.description}</p>
                      </article>
                    ))}
                  </div>
                </div>
              </Panel>
            </div>
          </section>
        ) : null}

        {activePage === 'ai' ? (
          <section className="studio-grid">
            <div className="column">
              <Panel panelId="ai-hub" title="Connected Providers" subtitle="Profiles are stored locally with encrypted secrets so projects and classroom agents can use your chosen provider or a managed subscription profile.">
                <div className="stack-tight">
                  <div className="preview-card">
                    <div className="preview-topline">
                      <div>
                        <span className="mini-label">AI control plane</span>
                        <h3>{deferredAiProfiles.length} connected profiles</h3>
                      </div>
                      <span className="pill">{deferredSystemStatus?.provider_ai.configured_profiles ?? 0} active</span>
                    </div>
                    <div className="chip-row">
                      <span className="chip">Managed subscriptions {deferredSystemStatus?.provider_ai.managed_profiles ?? 0}</span>
                      <span className="chip">Providers {deferredSystemStatus?.provider_ai.providers_available.length ?? 0}</span>
                      <span className="chip">Usage entries {deferredAiUsage.length}</span>
                    </div>
                  </div>

                  <div className="card-grid compact">
                    {deferredAiProfiles.length ? (
                      deferredAiProfiles.map(profile => (
                        <article className={`mini-card ${selectedAiProfileId === profile.profile_id ? 'selected' : ''}`} key={profile.profile_id}>
                          <div className="preview-topline">
                            <div>
                              <span className="mini-label">{profile.provider_label}</span>
                              <h3>{profile.label}</h3>
                            </div>
                            <span className="pill">{profile.auth_mode}</span>
                          </div>
                          <p>{profile.default_model}</p>
                          <div className="chip-row">
                            <span className="chip">{profile.api_key_hint}</span>
                            <span className="chip">Test {profile.last_test_status}</span>
                            <span className="chip">SDK {profile.sdk_installed ? 'installed' : 'missing'}</span>
                          </div>
                          <div className="chip-row">
                            <span className="chip">Today {profile.usage_summary.requests_today}/{profile.daily_request_limit}</span>
                            <span className="chip">Budget ${profile.usage_summary.spend_this_month_usd.toFixed(2)}/${profile.monthly_budget_usd.toFixed(2)}</span>
                            <span className="chip">Redaction {profile.redaction_mode}</span>
                          </div>
                          <div className="chip-row">
                            {profile.capabilities.map(capability => (
                              <span className="chip" key={capability}>{capability}</span>
                            ))}
                          </div>
                          <div className="action-row">
                            <button className="text-button dark-on-light" type="button" onClick={() => loadAiProfile(profile)}>
                              Edit
                            </button>
                            <button className="text-button dark-on-light" type="button" onClick={() => void testAiProfile(profile.profile_id)} disabled={isWorking}>
                              Test
                            </button>
                            <button className="text-button dark-on-light" type="button" onClick={() => void deleteAiProfile(profile.profile_id)} disabled={isWorking}>
                              Delete
                            </button>
                          </div>
                        </article>
                      ))
                    ) : (
                      <div className="empty-state">No provider profiles yet. Add OpenAI, Anthropic, Google Gemini, Groq, Mistral, Cohere, or xAI from this page.</div>
                    )}
                  </div>
                </div>
              </Panel>
            </div>

            <div className="column">
              <Panel title={selectedProviderProfile ? 'Update Provider Profile' : 'Add Provider Profile'} subtitle="Use user keys for bring-your-own credentials or managed-subscription mode when EduClawn should route work through a provider profile you manage locally.">
                <form className="form-grid" onSubmit={saveAiProfile}>
                  <label className="field">
                    <span>Profile label</span>
                    <input value={aiProfileDraft.label} onChange={event => updateAiProviderDraft('label', event.target.value)} />
                  </label>
                  <div className="two-up">
                    <label className="field">
                      <span>Provider</span>
                      <select value={aiProfileDraft.provider_id} onChange={event => updateAiProviderDraft('provider_id', event.target.value as AIProviderId)}>
                        {deferredAiCatalog.map(provider => (
                          <option key={provider.provider_id} value={provider.provider_id}>
                            {provider.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      <span>Auth mode</span>
                      <select value={aiProfileDraft.auth_mode} onChange={event => updateAiProviderDraft('auth_mode', event.target.value as AIAuthMode)}>
                        <option value="user-key">User key</option>
                        <option value="managed-subscription">Managed subscription</option>
                      </select>
                    </label>
                  </div>
                  <div className="two-up">
                    <label className="field">
                      <span>Default model</span>
                      <input value={aiProfileDraft.default_model} onChange={event => updateAiProviderDraft('default_model', event.target.value)} />
                    </label>
                    <label className="field">
                      <span>Base URL</span>
                      <input
                        value={aiProfileDraft.base_url}
                        disabled={!deferredAiCatalog.find(provider => provider.provider_id === aiProfileDraft.provider_id)?.supports_custom_base_url}
                        onChange={event => updateAiProviderDraft('base_url', event.target.value)}
                        placeholder="Optional custom endpoint"
                      />
                    </label>
                  </div>
                  <label className="field">
                    <span>{selectedProviderProfile ? 'New API key (leave blank to keep current secret)' : 'API key or provider secret'}</span>
                    <input
                      type="password"
                      value={aiProfileDraft.api_key}
                      onChange={event => updateAiProviderDraft('api_key', event.target.value)}
                      placeholder={selectedProviderProfile ? 'Keep existing secret' : 'Paste the provider key'}
                    />
                  </label>
                  <label className="field">
                    <span>Capabilities</span>
                    <textarea
                      value={aiProfileDraft.capabilitiesText}
                      onChange={event => updateAiProviderDraft('capabilitiesText', event.target.value)}
                      placeholder="research&#10;assignments&#10;feedback"
                    />
                  </label>
                  <div className="action-row">
                    <button className="action-button" disabled={isWorking}>
                      {isWorking ? 'Saving profile...' : selectedProviderProfile ? 'Update Profile' : 'Add Profile'}
                    </button>
                    <button className="text-button dark-on-light" type="button" onClick={resetAiProfileDraft}>
                      New Profile
                    </button>
                  </div>
                </form>

                <div className="stack-tight">
                  <div className="preview-card embedded">
                    <div className="preview-topline">
                      <div>
                        <span className="mini-label">Selected provider</span>
                        <h3>{deferredAiCatalog.find(provider => provider.provider_id === aiProfileDraft.provider_id)?.label ?? aiProfileDraft.provider_id}</h3>
                      </div>
                      <span className="pill">{aiProfileDraft.auth_mode}</span>
                    </div>
                    <div className="chip-row">
                      {(deferredAiCatalog.find(provider => provider.provider_id === aiProfileDraft.provider_id)?.recommended_models ?? []).map(model => (
                        <span className="chip" key={model}>{model}</span>
                      ))}
                    </div>
                    <p>{deferredAiCatalog.find(provider => provider.provider_id === aiProfileDraft.provider_id)?.notes ?? 'Provider details pending.'}</p>
                  </div>

                  <div className="card-grid compact">
                    {deferredAiCatalog.map(provider => (
                      <article className="mini-card" key={provider.provider_id}>
                        <div className="preview-topline">
                          <div>
                            <span className="mini-label">{provider.sdk_package}</span>
                            <h3>{provider.label}</h3>
                          </div>
                          <span className="pill">{provider.sdk_installed ? 'sdk ready' : 'sdk install needed'}</span>
                        </div>
                        <p>{provider.notes}</p>
                        <div className="chip-row">
                          {provider.supported_tasks.slice(0, 4).map(task => (
                            <span className="chip" key={task}>{task}</span>
                          ))}
                        </div>
                        <div className="action-row">
                          <button className="text-button dark-on-light" type="button" onClick={() => updateAiProviderDraft('provider_id', provider.provider_id)}>
                            Use Provider
                          </button>
                          <a className="text-button dark-on-light" href={provider.docs_url} target="_blank" rel="noreferrer">
                            SDK Docs
                          </a>
                        </div>
                      </article>
                    ))}
                  </div>

                  <div className="subpanel">
                    <div className="preview-topline">
                      <div>
                        <span className="mini-label">Recent AI usage</span>
                        <h3>Provider-backed actions</h3>
                      </div>
                      <span className="pill">{deferredAiUsage.length}</span>
                    </div>
                    <div className="card-grid compact">
                      {deferredAiUsage.length ? (
                        deferredAiUsage.slice(0, 8).map(entry => (
                          <article className="mini-card" key={entry.usage_id}>
                            <div className="preview-topline">
                              <div>
                                <span className="mini-label">{entry.source}</span>
                                <h3>{entry.profile_label}</h3>
                              </div>
                              <span className={`priority-pill ${entry.success ? 'low' : 'high'}`}>
                                {entry.success ? 'success' : 'error'}
                              </span>
                            </div>
                            <p>{entry.prompt_preview}</p>
                            <div className="chip-row">
                              <span className="chip">{entry.provider_label}</span>
                              <span className="chip">{entry.model}</span>
                              <span className="chip">{entry.task}</span>
                              <span className="chip">${entry.estimated_cost_usd.toFixed(4)}</span>
                              {entry.fallback_used ? <span className="chip">fallback</span> : null}
                            </div>
                          </article>
                        ))
                      ) : (
                        <div className="empty-state">Usage appears here after a project compile, assignment, or classroom agent run uses a provider profile.</div>
                      )}
                    </div>
                  </div>
                </div>
              </Panel>
            </div>
          </section>
        ) : null}

        {activePage === 'desktop' ? (
          <section className="studio-grid">
            <div className="column">
              <Panel panelId="desktop-tools" title="Desktop Tools" subtitle="Manage workspace location, updates, install behavior, and packaged-app convenience features.">
                <div className="stack-tight">
                  <div className="preview-card">
                    <div className="preview-topline">
                      <div>
                        <span className="mini-label">Desktop shell</span>
                        <h3>{deferredDesktopContext?.workspaceRoot ?? deferredSystemStatus?.workspace_root ?? 'Workspace pending'}</h3>
                      </div>
                      <span className="pill">v{deferredSystemStatus?.release.desktop_version ?? 'n/a'}</span>
                    </div>
                    <div className="chip-row">
                      <span className="chip">Updates {deferredDesktopContext?.updater.status ?? 'n/a'}</span>
                      <span className="chip">Launch at login {deferredDesktopContext?.preferences.launchAtLogin ? 'on' : 'off'}</span>
                      <span className="chip">OCR {deferredSystemStatus?.tools.tesseract_available ? 'ready' : 'not detected'}</span>
                      <span className="chip">Local AI {deferredSystemStatus?.local_ai.ollama_reachable ? 'reachable' : 'offline'}</span>
                    </div>
                  </div>

                  <div className="action-row">
                    {deferredDesktopContext ? (
                      <button className="action-button secondary" type="button" onClick={() => void chooseWorkspace()}>
                        Choose Workspace
                      </button>
                    ) : null}
                    {deferredDesktopContext ? (
                      <button className="text-button dark-on-light" type="button" onClick={() => void openWorkspace()}>
                        Open Workspace
                      </button>
                    ) : null}
                    {deferredDesktopContext ? (
                      <button className="text-button dark-on-light" type="button" onClick={() => void openReleaseNotes()}>
                        Release Notes
                      </button>
                    ) : null}
                    {deferredDesktopContext ? (
                      <button className="text-button dark-on-light" type="button" onClick={() => void checkForUpdates()}>
                        Check Updates
                      </button>
                    ) : null}
                    {deferredDesktopContext ? (
                      <button className="text-button dark-on-light" type="button" onClick={() => void toggleLaunchAtLogin()}>
                        {deferredDesktopContext.preferences.launchAtLogin ? 'Disable Launch at Login' : 'Enable Launch at Login'}
                      </button>
                    ) : null}
                    {deferredDesktopContext?.canInstallToApplications ? (
                      <button className="text-button dark-on-light" type="button" onClick={() => void installToApplications()}>
                        Install to Applications
                      </button>
                    ) : null}
                    {deferredDesktopContext?.updater.status === 'downloaded' ? (
                      <button className="text-button dark-on-light" type="button" onClick={() => void installDownloadedUpdate()}>
                        Install Update
                      </button>
                    ) : null}
                  </div>
                </div>
              </Panel>
            </div>

            <div className="column">
              <Panel title="Recent and Helpful" subtitle="Open recent work, review packaging status, and use the simplest launch path for this machine.">
                <div className="stack-tight">
                  <div className="card-grid compact">
                    {deferredDesktopContext?.recentProjects.length ? (
                      deferredDesktopContext.recentProjects.slice(0, 6).map(item => (
                        <article className="mini-card" key={item.slug}>
                          <h3>{item.title}</h3>
                          <p>{item.slug}</p>
                          <button className="text-button dark-on-light" type="button" onClick={() => openRecentProject(item.slug)}>
                            Open Project
                          </button>
                        </article>
                      ))
                    ) : (
                      <div className="empty-state">Recent projects will appear here after you open or create them.</div>
                    )}
                  </div>

                  <div className="preview-card embedded">
                    <div className="preview-topline">
                      <div>
                        <span className="mini-label">Best launch path</span>
                        <h3>Use the packaged desktop app when possible</h3>
                      </div>
                      <span className="pill">{deferredDesktopContext?.isDesktop ? 'desktop mode' : 'browser mode'}</span>
                    </div>
                    <p>{deferredDesktopContext?.updater.message ?? 'Desktop update status pending.'}</p>
                    <div className="chip-row">
                      <span className="chip">Packaged app {deferredSystemStatus?.release.packaged_app_path || 'n/a'}</span>
                      <span className="chip">Release notes {deferredSystemStatus?.release.release_notes_path || 'n/a'}</span>
                    </div>
                    <div className="action-row">
                      <a className="legacy-link" href={api.legacyUrl()} target="_blank" rel="noreferrer">
                        Open Preserved Legacy HTML
                      </a>
                    </div>
                  </div>
                </div>
              </Panel>
            </div>
          </section>
        ) : null}

        {activePage === 'advanced' && showAdvancedSystems ? (
          <section className="lower-grid">
            <Panel title="Open Source Guidance" subtitle="What this repo now ships for reusable local-first project building.">
              <div className="card-grid compact">
                {agentCatalog.map(agent => (
                  <article className="mini-card" key={agent.name}>
                    <h3>{agent.display_name}</h3>
                    <p>{agent.description}</p>
                  </article>
                ))}
              </div>
            </Panel>

            <Panel panelId="admin-ops" title="Admin Ops" subtitle="Optional monitoring for local orchestration and benchmark health.">
              {adminReady ? (
                <div className="stack-tight">
                  <div className="preview-card embedded">
                    <div className="preview-topline">
                      <div>
                        <span className="mini-label">Admin session</span>
                        <h3>{deferredAdminStatus?.current_user.username ?? 'admin'}</h3>
                      </div>
                      <button className="text-button dark-on-light" type="button" onClick={logout}>
                        Log out
                      </button>
                    </div>
                    <p>{maskDatabaseUrl(deferredAdminStatus?.database_url ?? '')}</p>
                    <div className="chip-row">
                      <span className="chip">Scheduler {deferredHealth?.scheduler.enabled ? 'enabled' : 'disabled'}</span>
                      <span className="chip">ETL {formatSeconds(deferredHealth?.scheduler.etl_interval_seconds)}</span>
                      <span className="chip">Retrain {formatSeconds(deferredHealth?.scheduler.retrain_interval_seconds)}</span>
                      <span className="chip">Benchmark {formatSeconds(deferredHealth?.scheduler.benchmark_interval_seconds)}</span>
                    </div>
                  </div>

                  {deferredBenchmark ? (
                    <div className="preview-card embedded">
                      <div className="preview-topline">
                        <div>
                          <span className="mini-label">Latest benchmark</span>
                          <h3>{deferredBenchmark.overall_score}%</h3>
                        </div>
                        <span className="pill">{formatTimestamp(deferredBenchmark.generated_at)}</span>
                      </div>
                      <ul className="narrative-list">
                        {deferredBenchmark.recommendations.map(item => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  ) : (
                    <div className="empty-state">No benchmark report has been generated yet.</div>
                  )}
                </div>
              ) : (
                <form className="form-grid" onSubmit={handleLogin}>
                  <label className="field">
                    <span>Username</span>
                    <input value={credentials.username} onChange={event => setCredentials(current => ({ ...current, username: event.target.value }))} />
                  </label>
                  <label className="field">
                    <span>Password</span>
                    <input
                      type="password"
                      value={credentials.password}
                      onChange={event => setCredentials(current => ({ ...current, password: event.target.value }))}
                    />
                  </label>
                  <button className="action-button full-width" disabled={isWorking}>
                    {isWorking ? 'Signing in...' : 'Log in for admin monitoring'}
                  </button>
                </form>
              )}
            </Panel>
          </section>
        ) : null}
        </section>
      </main>

      {(isBooting || isPending) ? <div className="loading-ribbon">Syncing local studio...</div> : null}
    </div>
  )
}

function Panel({
  title,
  subtitle,
  children,
  panelId,
}: {
  title: string
  subtitle: string
  children: ReactNode
  panelId?: string
}) {
  return (
    <section className="panel" id={panelId}>
      <header className="panel-header">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      </header>
      {children}
    </section>
  )
}

function MetricCard({
  label,
  value,
}: {
  label: string
  value: number | string | undefined
}) {
  return (
    <article className="metric-card">
      <p>{label}</p>
      <strong>{value ?? '--'}</strong>
    </article>
  )
}

function linesToArray(value: string): string[] {
  return value
    .split('\n')
    .map(item => item.trim())
    .filter(Boolean)
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}

function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 401 || error.status === 403)
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return 'n/a'
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

function formatSeconds(value: number | undefined): string {
  if (!value) {
    return 'n/a'
  }
  if (value < 60) {
    return `${value}s`
  }
  const minutes = Math.round(value / 60)
  return `${minutes}m`
}

function maskDatabaseUrl(databaseUrl: string): string {
  if (!databaseUrl) {
    return 'pending'
  }
  if (databaseUrl.startsWith('sqlite:///')) {
    const segments = databaseUrl.split('/')
    return `sqlite:///.../${segments.slice(-2).join('/')}`
  }
  return databaseUrl.replace(/:\/\/([^:]+):([^@]+)@/, '://$1:••••@')
}

function formatProfileLabel(profile: ExperienceProfile): string {
  switch (profile) {
    case 'teacher':
      return 'Teacher'
    case 'student':
      return 'Student'
    case 'family':
      return 'Family'
    case 'builder':
      return 'Advanced Builder'
    default:
      return 'User'
  }
}

function getVisiblePages(profile: ExperienceProfile, showAdvancedSystems: boolean): Array<{
  id: PageId
  label: string
  detail: string
}> {
  const basePages: Array<{
    id: PageId
    label: string
    detail: string
  }> = [
    {
      id: 'home',
      label: 'Home',
      detail: 'Guided setup, quick starts, and the simpler entry point into the product.',
    },
    {
      id: 'projects',
      label: 'Projects',
      detail: 'Create, edit, compile, and export local-first project work.',
    },
  ]

  if (profile !== 'family') {
    basePages.push({
      id: 'classroom',
      label: profile === 'student' ? 'Student' : 'Classroom',
      detail: 'Assignments, approved materials, bounded agents, and safety workflows.',
    })
    basePages.push({
      id: 'autopilot',
      label: 'Autopilot',
      detail: 'Assignment Autopilot, revision coaching, lesson-to-project conversion, and citation checks.',
    })
    basePages.push({
      id: 'ops',
      label: 'Teacher Ops',
      detail: 'Library reuse, peer review, standards mapping, interventions, replay, and assessment packs.',
    })
  }

  basePages.push({
    id: 'family',
    label: 'Family',
    detail: 'Read-only student progress, simple language, and export downloads.',
  })

  basePages.push({
    id: 'marketplace',
    label: 'Marketplace',
    detail: 'Templates, school packs, plugins, and offline school deployment assets.',
  })

  basePages.push({
    id: 'ai',
    label: 'AI',
    detail: 'Provider profiles, managed subscriptions, SDK status, and recent AI usage.',
  })

  basePages.push({
    id: 'desktop',
    label: 'Desktop',
    detail: 'Workspace, updates, recent projects, and install behavior.',
  })

  if (showAdvancedSystems) {
    basePages.push({
      id: 'advanced',
      label: 'Advanced',
      detail: 'EduClawn control plane, admin ops, and deeper orchestration surfaces.',
    })
  }

  return basePages
}

function formatLevelLabel(level: ExperienceLevel): string {
  switch (level) {
    case 'guided':
      return 'Guided'
    case 'standard':
      return 'Standard'
    case 'advanced':
      return 'Advanced'
    default:
      return 'Guided'
  }
}

function pickRecommendedSample(
  profile: ExperienceProfile,
  sampleProjects: StudioSampleProject[],
): StudioSampleProject | null {
  const wantedSlug =
    profile === 'teacher'
      ? 'community-water-justice-portfolio'
      : profile === 'student'
        ? 'mlk-movement-strategy-exhibit'
        : profile === 'family'
          ? 'neighborhood-transit-campaign-simulator'
          : 'community-water-justice-portfolio'

  return sampleProjects.find(sample => sample.slug === wantedSlug) ?? sampleProjects[0] ?? null
}

export default App
