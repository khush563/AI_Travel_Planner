from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import make_router
from app.config import Settings
from app.services.plan_service import PlanService


def create_app(service: PlanService | None = None) -> FastAPI:
    settings = Settings.from_env()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    plan_service = service or PlanService.from_settings(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="plan-recovery")
        for plan_id in plan_service.repository.pending_ids():
            executor.submit(plan_service.run_initial, plan_id)
        yield
        executor.shutdown(wait=False, cancel_futures=False)

    app = FastAPI(title="AI Travel Planner", version="1.0.0", lifespan=lifespan)
    app.include_router(make_router(plan_service))
    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(static_dir / "index.html")

    @app.get("/config")
    def runtime_config() -> dict[str, str]:
        return {"mode": settings.mode}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
