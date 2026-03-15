from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.ai_routes import router as ai_router
from app.api.educlawn_routes import router as educlawn_router
from app.api.education_growth_routes import router as education_growth_router
from app.api.education_routes import router as education_router
from app.api.routes import router
from app.api.studio_routes import router as studio_router
from app.core.config import Settings
from app.core.security import AuthService
from app.services.agents import LocalAgentService
from app.services.benchmarking import BenchmarkService
from app.services.educlawn import EduClawnService
from app.services.education_growth import EducationGrowthService
from app.services.education_os import EducationOperatingSystemService
from app.services.experimentation import ExperimentationService
from app.services.graph import KnowledgeGraphService
from app.services.knowledge import LocalKnowledgeService
from app.services.ml import LearningIntelligenceService
from app.services.orchestration import WorkflowOrchestrator
from app.services.planner import MissionPlannerService
from app.services.provider_ai import ProviderAIService
from app.services.studio_agents import ProjectAgentRuntime
from app.services.studio_engine import ProjectStudioService, TemplateRegistryService
from app.services.temporal import TemporalLearnerModel
from app.services.warehouse import WarehouseService


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        warehouse = WarehouseService(resolved_settings.database_url)
        warehouse.initialize()
        warehouse.seed_demo_data()

        auth_service = AuthService(
            secret=resolved_settings.auth_secret,
            token_ttl_minutes=resolved_settings.auth_token_ttl_minutes,
        )
        warehouse.ensure_admin_user(
            resolved_settings.admin_username,
            resolved_settings.admin_password,
            auth_service,
        )

        intelligence = LearningIntelligenceService(warehouse, cache_dir=resolved_settings.model_cache_dir)
        knowledge_service = LocalKnowledgeService()
        latest_snapshot = warehouse.get_latest_snapshot()
        startup_status = {
            "mode": "eager" if resolved_settings.eager_model_training else "lazy",
            "state": "ready" if intelligence.is_trained and latest_snapshot is not None else "pending",
            "models": "cached" if intelligence.is_trained else "pending",
            "snapshot": "cached" if latest_snapshot is not None else "pending",
            "started_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat() if intelligence.is_trained and latest_snapshot is not None else None,
            "last_error": "",
        }

        async def warm_platform() -> None:
            startup_status["state"] = "warming"
            try:
                if intelligence.is_trained:
                    startup_status["models"] = "cached"
                else:
                    await asyncio.to_thread(intelligence.train_models)
                    startup_status["models"] = "ready"

                if warehouse.get_latest_snapshot() is not None:
                    startup_status["snapshot"] = "cached"
                else:
                    await asyncio.to_thread(warehouse.create_warehouse_snapshot)
                    startup_status["snapshot"] = "ready"
                startup_status["state"] = "ready"
                startup_status["completed_at"] = datetime.now(UTC).isoformat()
            except Exception as error:
                startup_status["state"] = "error"
                startup_status["last_error"] = str(error)

        warmup_task: asyncio.Task[None] | None = None
        warmup_required = not intelligence.is_trained or latest_snapshot is None
        if resolved_settings.eager_model_training and warmup_required:
            await warm_platform()
        elif not resolved_settings.eager_model_training and warmup_required:
            warmup_task = asyncio.create_task(warm_platform())

        warehouse.record_event(
            event_type="knowledge_index_refresh",
            source="knowledge_service",
            learner_id=None,
            payload=knowledge_service.get_index_status(),
        )
        template_registry = TemplateRegistryService(
            template_dir=resolved_settings.studio_template_dir,
            community_root=resolved_settings.community_root_dir,
        )
        ai_provider_service = ProviderAIService(resolved_settings)
        studio_agent_runtime = ProjectAgentRuntime(
            local_llm_model=resolved_settings.local_llm_model,
            local_llm_base_url=resolved_settings.local_llm_base_url,
            ai_provider_service=ai_provider_service,
        )
        agent_service = LocalAgentService(warehouse, intelligence, knowledge_service)
        graph_service = KnowledgeGraphService()
        temporal_model = TemporalLearnerModel(warehouse)
        experimentation_service = ExperimentationService(warehouse)
        planner_service = MissionPlannerService(
            warehouse=warehouse,
            agent_service=agent_service,
            temporal_model=temporal_model,
            graph_service=graph_service,
            experimentation_service=experimentation_service,
        )
        benchmark_service = BenchmarkService(
            warehouse=warehouse,
            knowledge_service=knowledge_service,
            graph_service=graph_service,
            temporal_model=temporal_model,
            planner_service=planner_service,
            experimentation_service=experimentation_service,
        )
        studio_service = ProjectStudioService(
            settings=resolved_settings,
            warehouse=warehouse,
            template_registry=template_registry,
            agent_runtime=studio_agent_runtime,
            ai_provider_service=ai_provider_service,
        )
        education_service = EducationOperatingSystemService(
            settings=resolved_settings,
            studio_service=studio_service,
            template_registry=template_registry,
            ai_provider_service=ai_provider_service,
        )
        studio_service.bind_education_service(education_service)
        education_growth_service = EducationGrowthService(
            settings=resolved_settings,
            studio_service=studio_service,
            education_service=education_service,
            template_registry=template_registry,
            ai_provider_service=ai_provider_service,
        )
        educlawn_service = EduClawnService(
            settings=resolved_settings,
            education_service=education_service,
            template_registry=template_registry,
        )

        orchestrator = WorkflowOrchestrator(
            settings=resolved_settings,
            warehouse=warehouse,
            intelligence=intelligence,
            benchmark_service=benchmark_service,
        )
        await orchestrator.start()

        app.state.settings = resolved_settings
        app.state.warehouse = warehouse
        app.state.intelligence = intelligence
        app.state.startup_status = startup_status
        app.state.knowledge_service = knowledge_service
        app.state.graph_service = graph_service
        app.state.temporal_model = temporal_model
        app.state.experimentation_service = experimentation_service
        app.state.agent_service = agent_service
        app.state.template_registry = template_registry
        app.state.ai_provider_service = ai_provider_service
        app.state.studio_agent_runtime = studio_agent_runtime
        app.state.studio_service = studio_service
        app.state.education_service = education_service
        app.state.education_growth_service = education_growth_service
        app.state.educlawn_service = educlawn_service
        app.state.planner_service = planner_service
        app.state.benchmark_service = benchmark_service
        app.state.auth_service = auth_service
        app.state.orchestrator = orchestrator
        yield
        if warmup_task is not None and not warmup_task.done():
            warmup_task.cancel()
        await orchestrator.shutdown()

    app = FastAPI(
        title=resolved_settings.app_name,
        version="0.2.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    app.include_router(ai_router)
    app.include_router(studio_router)
    app.include_router(education_router)
    app.include_router(education_growth_router)
    app.include_router(educlawn_router)
    if resolved_settings.frontend_dist_dir.exists():
        app.mount(
            "/desktop",
            StaticFiles(directory=resolved_settings.frontend_dist_dir, html=True),
            name="desktop_frontend",
        )
    return app


app = create_app()
