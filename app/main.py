import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api.routes_stories import router as stories_router
from app.api.routes_epic import router as epic_router
from app.api.routes_analysis import router as analysis_router
from app.api.routes_db import db_router
from app.api.routes_documents import router as documents_router
from app.api.routes_audit import router as audit_router
from app.api.routes_agent3 import router as agent3_router
from app.db.init_db import init_tables
from app.api.manual_test_generation import router as manual_test_generation_router
from app.api.routes_xray_tests import router as xray_tests_router

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Test Agent - Stories (JSON)", version="0.1.0")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s:\n%s", request.method, request.url, traceback.format_exc())
    return JSONResponse(status_code=500, content={"detail": str(exc)})

# Initialisation SQLite au démarrage
init_tables()

app.include_router(stories_router)
app.include_router(epic_router)
app.include_router(analysis_router)
app.include_router(db_router)
app.include_router(documents_router)
app.include_router(manual_test_generation_router)
app.include_router(xray_tests_router)
app.include_router(audit_router)
app.include_router(agent3_router)


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs"}

