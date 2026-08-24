"""
Routes pour visualiser et debugger le pipeline orchestrator.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["pipeline-orchestrator"])


@router.get("/graph/diagram", response_class=HTMLResponse)
async def get_pipeline_diagram():
    """
    Retourne une visualisation HTML interactive du graphe LangGraph.
    Accessible : http://localhost:8000/pipeline/graph/diagram
    """
    from app.utils.graph_visualizer import save_mermaid_html
    
    try:
        html_path = save_mermaid_html()
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to generate graph diagram: {e}")
        raise HTTPException(status_code=500, detail=f"Cannot generate diagram: {str(e)}")


@router.get("/graph/png")
async def get_pipeline_graph_png():
    """
    Retourne l'image PNG du graphe LangGraph (si disponible).
    """
    from app.utils.graph_visualizer import visualize_pipeline_graph
    
    try:
        png_path = visualize_pipeline_graph()
        if png_path:
            return FileResponse(png_path, media_type="image/png")
        else:
            raise HTTPException(status_code=404, detail="PNG graph not available")
    except Exception as e:
        logger.error(f"Failed to generate PNG graph: {e}")
        raise HTTPException(status_code=500, detail=f"Cannot generate PNG: {str(e)}")


@router.get("/graph/ascii")
async def get_pipeline_graph_ascii():
    """
    Retourne une représentation ASCII du graphe.
    """
    from app.utils.graph_visualizer import generate_ascii_diagram
    
    try:
        diagram = generate_ascii_diagram()
        return {"diagram": diagram}
    except Exception as e:
        logger.error(f"Failed to generate ASCII diagram: {e}")
        raise HTTPException(status_code=500, detail=f"Cannot generate diagram: {str(e)}")


@router.get("/graph/mermaid")
async def get_pipeline_graph_mermaid():
    """
    Retourne la définition Mermaid du graphe pour utilisation externe.
    """
    from app.utils.graph_visualizer import get_mermaid_definition
    
    try:
        mermaid_def = get_mermaid_definition()
        return {"mermaid": mermaid_def}
    except Exception as e:
        logger.error(f"Failed to generate Mermaid definition: {e}")
        raise HTTPException(status_code=500, detail=f"Cannot generate Mermaid: {str(e)}")


@router.get("/info")
async def get_pipeline_info():
    """
    Retourne les informations du pipeline (nœuds, arêtes, configuration).
    """
    try:
        from app.services.agent_orchestrator import get_compiled_graph, PipelineState
        
        graph = get_compiled_graph()
        
        # Extraire les informations du graphe
        info = {
            "state_class": "PipelineState",
            "state_fields": list(PipelineState.__annotations__.keys()),
            "entry_point": "enrich_story",
            "terminal_states": ["skip", "no_tests", "not_functional"],
            "nodes": [
                "enrich_story",
                "classify_story",
                "analysis_agent",
                "agent2_business_model",
                "agent3_generate",
                "agent4_validate",
                "agent3_gap_fill",
                "agent5_report",
                "skip",
                "no_tests",
                "not_functional"
            ],
            "feedback_loop": {
                "trigger": "agent4_validate",
                "condition": "coverage < 70% OR duplicates OR ambiguities",
                "loop_to": "agent3_gap_fill",
                "re_entry": "agent4_validate",
                "max_iterations": "configurable (default=2)"
            }
        }
        
        return info
    except Exception as e:
        logger.error(f"Failed to get pipeline info: {e}")
        raise HTTPException(status_code=500, detail=f"Cannot get pipeline info: {str(e)}")
