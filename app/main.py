import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes_stories import router as stories_router
from app.api.routes_epic import router as epic_router
from app.api.routes_analysis import router as analysis_router
from app.api.routes_db import db_router
from app.api.routes_documents import router as documents_router
from app.api.routes_agent4 import router as agent4_router
from app.db.init_postgres import init_postgres
from app.api.manual_test_generation import router as manual_test_generation_router
from app.api.routes_agent5 import router as agent5_router
from app.api.routes_orchestrator import router as orchestrator_router
from app.api.routes_legacy_tests import router as legacy_tests_router
from app.api.routes_integration import router as integration_router
from app.api.routes_test_editing import router as test_editing_router
from app.api.routes_auth import router as auth_router
from app.api.routes_admin import router as admin_router
from app.api.routes_agent2 import router as agent2_router
from app.api.routes_graph_visualizer import router as graph_visualizer_router
from app.core.config import settings
from app.core.legacy_compat import warn_legacy_module
from app.logging_filter import NoiseFilter

logger = logging.getLogger(__name__)
logging.getLogger("uvicorn.access").addFilter(NoiseFilter())

@asynccontextmanager
async def lifespan(app: FastAPI):
    warn_legacy_module("app.main.lifespan", "startup bootstrap")
    try:
        await init_postgres()
    except Exception as exc:
        logger.error("FATAL: PostgreSQL init failed: %s", exc)
        raise
    yield


app = FastAPI(
    title="AI Test Agent",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled error on %s %s:\n%s",
        request.method,
        request.url,
        traceback.format_exc(),
    )
    response = JSONResponse(status_code=500, content={"detail": str(exc)})

    # ServerErrorMiddleware (qui gère ce handler) est situé EN DEHORS de
    # CORSMiddleware dans la pile Starlette : les headers CORS ne sont donc
    # jamais ajoutés automatiquement sur les 500. On les ajoute ici à la main
    # pour que le frontend voie la vraie erreur au lieu d'un faux blocage CORS.
    origin = request.headers.get("origin")
    if origin and origin in settings.ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"

    return response


app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(stories_router)
app.include_router(epic_router)
app.include_router(analysis_router)
app.include_router(db_router)
app.include_router(documents_router)
app.include_router(manual_test_generation_router)
app.include_router(agent4_router)
app.include_router(agent5_router)
app.include_router(orchestrator_router)
app.include_router(legacy_tests_router)
app.include_router(integration_router)
app.include_router(test_editing_router)
app.include_router(agent2_router)
app.include_router(graph_visualizer_router)


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs", "graph": "/pipeline/graph/diagram"}
