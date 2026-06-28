"""Manager for tracking asynchronous pipeline runs in memory."""

from typing import Dict, Any, List
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Global memory store for jobs
# story_id (UPPERCASE) -> Job dict
jobs_db: Dict[str, Dict[str, Any]] = {}

def create_job(story_id: str) -> Dict[str, Any]:
    sid = story_id.strip().upper()
    job = {
        "storyId": sid,
        "status": "running",
        "progress": 0,
        "steps": [
            {"agent": "Agent 1", "status": "pending", "output": None, "error": None},
            {"agent": "Agent 2", "status": "pending", "output": None, "error": None},
            {"agent": "Agent 3", "status": "pending", "output": None, "error": None},
            {"agent": "Agent 5", "status": "pending", "output": None, "error": None},
        ],
        "result": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    jobs_db[sid] = job
    return job

def update_job_step(story_id: str, agent_name: str, status: str, output: Any = None, error: str = None, progress: int = None):
    sid = story_id.strip().upper()
    if sid not in jobs_db:
        return
    
    job = jobs_db[sid]
    if progress is not None:
        job["progress"] = progress
        
    for step in job["steps"]:
        if step["agent"] == agent_name:
            step["status"] = status
            if output is not None:
                step["output"] = output
            if error is not None:
                step["error"] = error
            break
