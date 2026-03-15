# EduClawn

`EduClawn` is a local-first open-source education platform for students and teachers.

It combines:

- a desktop app that behaves like normal software
- a reusable project engine for building cited local projects
- a bounded classroom agent system for teachers and students
- a preserved legacy MLK experience in `Legacy_of_Justice.html`

The current product direction is:

- `EduClawn OS`: the school-safe agent operating system
- `EduClawn Studio`: the local project engine and studio UI

This repo intentionally keeps the original `Legacy_of_Justice.html` as a preserved artifact and first template seed. It is not deleted.

## What The Product Does

Students and teachers can:

- create projects from typed manifests and templates
- upload local documents and classroom evidence
- extract and search evidence locally
- generate provenance-backed project artifacts
- run Assignment Autopilot to turn a topic, rubric, and lesson seed into a full classroom-ready package
- compare drafts against rubrics with Student Revision Coach and Citation Verifier
- reuse evidence through a shared Classroom Library across classes and years
- run safe Peer Review Mode with teacher approval gates
- open a simpler Parent/Family View with progress, comments, and downloads
- create family-safe share links for read-only project updates
- track classroom roster progress states and assignment status boards
- connect preferred cloud AI providers with local encrypted profiles
- run bounded local agents with approval gates
- compile projects into multiple export formats
- use the desktop app without running terminal commands every time

## Main Product Layers

### 1. EduClawn OS

A school-safe, OpenClaw-shaped orchestration layer with:

- `Teacher OS`
- `Student OS`
- `Shared Classroom Layer`
- approvals
- audit trails
- signed control planes
- classroom access keys

### 2. EduClawn Studio

A local project engine that provides:

- project manifests
- template registry
- document ingestion
- provenance and retrieval
- knowledge graph compilation
- artifact-producing agents
- export pipeline

### 3. Desktop App

A packaged Electron desktop shell that:

- starts the backend automatically
- opens the studio with no terminal work
- stores workspace state locally
- restores recent projects
- supports bundle file opening
- includes updater/install scaffolding

## Current Capabilities

### Project Engine

- typed `project.yaml` manifests
- local document ingestion
- local retrieval and evidence search
- provenance chunking
- knowledge graph generation
- standards alignment
- teacher comments and revision history
- export generation
- enforced export readiness gates for citation coverage, rubric thresholds, and pending approvals

### Agent Runtime

- research
- planning
- writing
- history support
- citation support
- design support
- QA
- teacher review
- export support
- provider-backed research, assignment drafting, review, and classroom assistance through connected AI profiles

### Education OS

- classroom creation
- assignment creation
- protected evidence uploads
- student project launch
- teacher/student/shared bounded agents
- approval queue
- audit log
- classroom-safe collaboration model
- assignment autopilot
- student revision coach
- classroom library reuse
- peer review moderation
- family view
- family-safe share links
- standards mapper
- intervention dashboard
- classroom roster tools and assignment status boards
- classroom replay
- peer review pairing suggestions
- assessment pack generation
- rubric trainer
- lesson-to-project conversion
- citation verification
- hybrid local/cloud routing

### Growth and Open Source Layer

- template marketplace
- school pack installer
- plugin SDK surfaces
- offline school edition readiness
- district/nonprofit/teacher starter pack support

### Security

- classroom bootstrap access keys for `teacher`, `student`, and `reviewer`
- HMAC-hashed stored credentials
- prompt risk scoring
- approval-required flows for sensitive actions
- tamper-evident approval and audit chains
- upload policy enforcement for classroom materials
- signed EduClawn control-plane attestations

### Desktop Product Features

- first-run onboarding
- Easy Start Center for teachers, students, families, and advanced builders
- role-based frontend navigation with separate `Home`, `Projects`, `Classroom`, `Autopilot`, `Teacher Ops`, `Family`, `Marketplace`, `AI`, `Desktop`, and `Advanced` views
- simple dashboard mode
- larger text and reduced-motion comfort settings
- workspace chooser
- release notes access
- recent-project restore
- `.cpsbundle` file association support
- crash recovery for renderer/backend failures
- launch-at-login control
- macOS move-to-Applications prompt
- auto-update scaffolding for packaged releases

### Provider AI Control Plane

- local encrypted AI provider profiles stored inside the EduClawn workspace
- `user-key` mode for bring-your-own API access
- `managed-subscription` mode for locally managed provider seats that EduClawn agents can use on behalf of the classroom workflow
- per-profile daily request limits, monthly budgets, classroom caps, redaction modes, and fallback chains
- classroom AI policies for managed-subscription control and PII redaction
- supported providers:
  - OpenAI
  - Anthropic
  - Google Gemini
  - Groq
  - Mistral
  - Cohere
  - xAI
- supported provider tasks:
  - research
  - assignments
  - feedback
  - planning
  - review
  - export
  - classroom

Provider profiles can be used in three places:

- project manifests through `provider-ai` runtime mode
- classroom assignments through `provider-ai` runtime mode
- bounded classroom agents through an optional provider override

The routing layer can also automatically choose different providers for different jobs:

- OpenAI for writing and assignment generation
- Anthropic for feedback and review
- Gemini for multimodal-oriented research flows
- Groq for fast planning tasks
- local models first when hybrid mode can stay fully on-device

## Desktop Use

If you want to use it like normal software, use the packaged desktop app.

Fastest paths:

- macOS packaged app: open `desktop/release/mac-arm64/EduClawn.app`
- macOS repo copy: double-click `Open-EduClawn.command`
- Windows repo copy: run `Open-EduClawn.bat`
- contributor setup: run `scripts/setup-local.sh` or `scripts/setup-local.ps1`

Artifacts produced by the desktop packaging flow include:

- `desktop/release/mac-arm64/EduClawn.app` from `npm run pack`
- `.dmg` and `.zip` artifacts from `npm run dist:mac`
- Windows installer artifacts from `npm run dist:win`
- Linux package artifacts from `npm run dist:linux`

The desktop app starts the bundled backend automatically and serves the studio locally at `/desktop/`. Users do not need to run the backend and frontend manually to use the packaged app.

For local macOS packaging without Apple credentials, the desktop build wrapper automatically disables hardened runtime so the generated `.app` remains usable on the builder machine. Signed release builds still keep the notarization-ready path.

## Trust And Readiness Gates

Final student-facing exports are no longer always produced automatically. EduClawn now blocks protected export types until:

- uploaded evidence is present
- citation coverage clears the project threshold
- rubric and teacher-review scores meet the minimum threshold
- pending classroom approvals are resolved

If a project is blocked, EduClawn still produces the rubric report so teachers and students can see what to fix next.

## Open-Source Starter Assets

The open-source layer now ships with:

- school pack blueprints in `community/school_packs/`
- template author starters in `community/template_starters/`
- sample community plugins in `community/plugins/`
- sample project manifests in `community/sample_projects/`

Use the Marketplace page or the school-pack install endpoint to install a pack and start from a local starter instead of building from scratch.

## One-Step Local Setup

If you are running from the repo instead of a packaged installer:

### macOS / Linux

```bash
./scripts/setup-local.sh
./scripts/start-desktop.sh
```

Or double-click:

- `Install-EduClawn.command`
- `Open-EduClawn.command`

### Windows

Run:

- `Install-EduClawn.bat`
- `Open-EduClawn.bat`

Or use PowerShell directly:

```powershell
.\scripts\setup-local.ps1
.\scripts\start-desktop.ps1
```

Environment check helpers:

- `scripts/doctor.sh`
- `scripts/doctor.ps1`

## Export Formats

Projects can be exported as:

- static site
- React app scaffold
- PDF report
- rubric report
- `.cpsbundle` project bundle

Family and classroom workflows can also reuse those exports through the family-facing read-only view.

## Local Modes

- `no-llm`: deterministic local generation and scoring
- `local-llm`: optional local model refinement through an Ollama-compatible endpoint
- `provider-ai`: uses a connected provider profile for cloud-backed research, assignments, feedback, and classroom assistance

If no local LLM is available, the platform falls back to deterministic local behavior.

If `provider-ai` is selected but no provider profile is attached, EduClawn keeps the workflow safe and falls back to deterministic local behavior until a profile is connected.

## AI Provider Setup

Use the `AI` page in the desktop or web UI to:

- add a provider profile
- choose `user-key` or `managed-subscription`
- select a default model
- optionally set a custom base URL when the provider supports it
- test the connection
- inspect recent provider-backed usage

The backend stores provider secrets encrypted at rest inside the local workspace using the EduClawn security secret. The raw API keys are not exposed back through the API after profile creation.

## New Teacher and Student Workflows

- `Assignment Autopilot`: creates assignments, evidence packs, checkpoint plans, standards maps, assessment packs, and export targets from one teacher input.
- `Student Revision Coach`: turns rubric gaps and teacher feedback into concrete revision tasks.
- `Citation Verifier`: checks whether draft claims map back to uploaded evidence before export.
- `Lesson-to-Project Agent`: converts a lesson plan into a reusable local project scaffold.
- `Classroom Library`: promotes approved evidence into a reusable teacher vault.
- `Peer Review Mode`: lets students draft rubric-guided feedback while keeping release behind teacher approval.
- `Teacher Ops`: maps standards, surfaces interventions, replays classroom activity, and trains local rubric patterns.
- `Marketplace`: exposes templates, school packs, plugin SDK entry points, and offline deployment assets.

## Repository Structure

- `backend/`: FastAPI backend, agents, security, ingestion, exports, analytics
- `frontend/`: React + TypeScript studio UI
- `desktop/`: Electron shell, packaging config, release assets
- `docs/`: template, plugin, and EduClawn docs
- `community/`: sample projects and community packs
- `studio/`: starter manifests and template assets
- `educlawn/`: EduClawn example manifests
- `Legacy_of_Justice.html`: preserved original standalone MLK experience

## Run In Developer Mode

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Run The Desktop Shell From Source

```bash
cd desktop
npm install
npm run dev
```

If you want the shortest repo path, use `./scripts/start-desktop.sh` or `.\scripts\start-desktop.ps1` instead.

## Package The Desktop App

```bash
cd desktop
npm run pack
```

Platform-targeted packaging commands:

```bash
cd desktop
npm run dist:mac
npm run dist:win
npm run dist:linux
```

## Docker Compose

```bash
docker compose up --build
```

Then open:

- studio UI: `http://127.0.0.1:5173`
- backend API: `http://127.0.0.1:8000`
- preserved legacy page: `http://127.0.0.1:8000/legacy`

## EduClawn Security Model

EduClawn is intentionally not a general unrestricted agent.

It is built as bounded educational orchestration:

- no unrestricted shell execution
- no silent external messaging
- no uncontrolled browser automation
- no hidden destructive filesystem actions
- no sensitive classroom action without approval and audit coverage

See `docs/EDUCLAWN.md` for the detailed contract.

## Templates

Templates in the studio include examples such as:

- MLK Legacy Lab
- Research Portfolio
- Civic Campaign Simulator
- Museum Exhibit Site
- Lesson Module
- Documentary Story Project
- science-fair style flows
- debate prep flows
- reading intervention flows

## Project Manifest Example

```yaml
version: "1.0"
title: Neighborhood Memory Archive
summary: A locally built historical project
topic: Neighborhood memory and public history
audience: Middle and high school students
template_id: documentary-story
local_mode: no-llm
goals:
  - Explain the issue
  - Curate source evidence
  - Build an interactive local project
rubric:
  - Evidence Quality
  - Clarity
  - Audience Fit
```

## Admin Access

Default local admin credentials:

- username: `admin`
- password: `mlk-admin-demo`

Admin surfaces include:

- scheduler state
- benchmark reporting
- experiment metrics
- workflow orchestration
- older MLK intelligence admin flows

## Important Environment Variables

Useful backend overrides:

- `EDUCLAWN_DATABASE_URL`
- `EDUCLAWN_DB_PATH`
- `EDUCLAWN_ADMIN_USERNAME`
- `EDUCLAWN_ADMIN_PASSWORD`
- `EDUCLAWN_AUTH_SECRET`
- `EDUCLAWN_WORKFLOW_SCHEDULER_ENABLED`
- `EDUCLAWN_ETL_INTERVAL_SECONDS`
- `EDUCLAWN_RETRAIN_INTERVAL_SECONDS`
- `EDUCLAWN_BENCHMARK_INTERVAL_SECONDS`
- `EDUCLAWN_STUDIO_ROOT`
- `EDUCLAWN_STUDIO_TEMPLATE_DIR`
- `EDUCLAWN_COMMUNITY_ROOT`
- `EDUCLAWN_LOCAL_LLM_MODEL`
- `EDUCLAWN_LOCAL_LLM_BASE_URL`
- `EDUCLAWN_MODEL_CACHE_DIR`
- `EDUCLAWN_SECURITY_SECRET`
- `EDUCLAWN_EDU_MATERIAL_MAX_BYTES`

Legacy `MLK_*` aliases are still accepted for backward compatibility.

## Packaging, Signing, And Releases

The desktop release pipeline now includes:

- macOS packaging
- Windows packaging configuration
- Linux packaging configuration
- GitHub Actions workflow for desktop release builds
- updater metadata publishing configuration

Files to inspect:

- `desktop/README.md`
- `desktop/signing.env.example`
- `.github/workflows/desktop-release.yml`

For full macOS public distribution you still need real credentials:

- `CSC_LINK`
- `CSC_KEY_PASSWORD`
- `APPLE_ID`
- `APPLE_APP_SPECIFIC_PASSWORD`
- `APPLE_TEAM_ID`
- `GH_TOKEN`

Without those, local builds remain ad-hoc signed and not notarized.

## Open Source

- code license: `Apache-2.0`
- educational content contributions: `CC-BY` or `CC-BY-SA` recommended

## Contributing And SDK Docs

- `CONTRIBUTING.md`
- `docs/TEMPLATE_SDK.md`
- `docs/PLUGIN_SDK.md`
- `docs/EDUCLAWN.md`
- `desktop/README.md`

## Verification

The current repo state has been validated with:

- `cd backend && uv run pytest`
- `cd frontend && npm run build`
- `cd desktop && npm run pack`

The packaged macOS app was also smoke-tested against:

- `/health`
- `/desktop/`
- `/api/v1/studio/system/status`

## Legacy Note

`Legacy_of_Justice.html` is still preserved in this repository and still served by the platform. It remains available as a historical standalone artifact and template seed.
