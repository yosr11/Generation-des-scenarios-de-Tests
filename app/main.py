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
from app.api.routes_agent3 import router as agent3_router
from app.db.init_postgres import init_postgres
from app.api.manual_test_generation import router as manual_test_generation_router
from app.api.routes_agent5 import router as agent5_router
from app.api.routes_orchestrator import router as orchestrator_router
from app.api.routes_legacy_tests import router as legacy_tests_router
from app.api.routes_integration import router as integration_router
from app.api.routes_test_editing import router as test_editing_router
from app.api.routes_auth import router as auth_router
from app.api.routes_admin import router as admin_router
from app.api.routes_agent15 import router as agent15_router
from app.core.legacy_compat import warn_legacy_module

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    warn_legacy_module("app.main.lifespan", "startup bootstrap")
    try:
        await init_postgres()
    except Exception as exc:
        logger.warning("PostgreSQL init skipped or failed: %s", exc)
    yield


app = FastAPI(
    title="AI Test Agent",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
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
    return JSONResponse(status_code=500, content={"detail": str(exc)})


app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(stories_router)
app.include_router(epic_router)
app.include_router(analysis_router)
app.include_router(db_router)
app.include_router(documents_router)
app.include_router(manual_test_generation_router)
app.include_router(agent3_router)
app.include_router(agent5_router)
app.include_router(orchestrator_router)
app.include_router(legacy_tests_router)
app.include_router(integration_router)
app.include_router(test_editing_router)
app.include_router(agent15_router)


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}
