"""
Visualisation du graphe LangGraph — génère le diagramme du workflow.
"""

import os
from pathlib import Path


def visualize_pipeline_graph():
    """
    Génère et sauvegarde une visualisation Mermaid du graphe orchestrateur.
    Retourne le chemin du fichier PNG généré.
    """
    from app.services.agent_orchestrator import get_compiled_graph

    graph = get_compiled_graph()
    
    # Générer le diagramme Mermaid
    try:
        # LangGraph 0.2+ utilise draw_mermaid_png()
        png_data = graph.get_graph().draw_mermaid_png()
        
        # Sauvegarder dans un répertoire
        output_dir = Path(__file__).parent.parent.parent / "data" / "graphs"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / "pipeline_workflow.png"
        with open(output_path, "wb") as f:
            f.write(png_data)
        
        print(f"✓ Graphe sauvegardé : {output_path}")
        return str(output_path)
    
    except AttributeError:
        # Fallback : générer en ASCII
        return generate_ascii_diagram()


def generate_ascii_diagram() -> str:
    """
    Génère une représentation ASCII du pipeline si Mermaid n'est pas dispo.
    """
    diagram = """
╔════════════════════════════════════════════════════════════════════════════╗
║                    PIPELINE ORCHESTRATOR — WORKFLOW                        ║
╚════════════════════════════════════════════════════════════════════════════╝

                                    START
                                      │
                                      ▼
                        ┌─────────────────────────┐
                        │   1. Enrich Story       │
                        │   (Jira + Cache)        │
                        └────────────┬────────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │ 2. Classify Story       │
                        │ (Agent 1 — Type)        │
                        └────────────┬────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
            invalid/weak      functional        not_functional
                    │                │                │
                    ▼                ▼                ▼
                ┌──────┐    ┌──────────────────┐   ┌──────┐
                │ SKIP │    │ 3. Analysis      │   │ SKIP │
                └──────┘    │ (Agent 1 — Deep) │   └──────┘
                            └────────┬─────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │ 4. Business Modeling    │
                        │ (Agent 2 — Optional)    │
                        └────────────┬────────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │ 5. Generate Tests       │
                        │ (Agent 3 + RAG/Legacy)  │
                        └────────────┬────────────┘
                                     │
                            ┌────────┴────────┐
                            │                 │
                      No tests         Tests generated
                            │                 │
                            ▼                 ▼
                       ┌─────────┐  ┌─────────────────────┐
                       │ NO_TESTS │  │ 6. Validation       │
                       └─────────┘  │ (Agent 4 — Coverage)│
                                     └────────┬────────────┘
                                              │
                                ┌─────────────┴──────────────┐
                                │                            │
                        Coverage >= 70%            Coverage < 70%
                        No duplicates               OR duplicates
                        No ambiguities              OR ambiguities
                                │                            │
                                ▼                            ▼
                        ┌───────────────┐          ┌──────────────────────┐
                        │ 7. Report Gen │          │ 8. Gap-Fill (Agent 3)│
                        │ (Agent 5)     │          │ + Re-validate (Agent4)│
                        └───────┬───────┘          └──────────┬───────────┘
                                │                             │
                                │              Iteration < MAX
                                │              ┌──────────────┘
                                │              │
                                │              └────────────────┐
                                │                                 │
                                └─────────────────┬───────────────┘
                                                  │
                                                  ▼
                                          ┌──────────────┐
                                          │     END      │
                                          │ (Result JSON)│
                                          └──────────────┘

╔════════════════════════════════════════════════════════════════════════════╗
║                           ROUTING LOGIC                                    ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║ • enrich_story        → route_after_enrich                                ║
║   ├─ OK    → classify_story                                              ║
║   └─ ERROR → END                                                         ║
║                                                                            ║
║ • classify_story      → route_after_agent1                               ║
║   ├─ functional     → analysis_agent                                     ║
║   ├─ invalid/weak   → skip                                               ║
║   └─ not_functional → not_functional                                     ║
║                                                                            ║
║ • analysis_agent      → agent2_business_model (obligatoire)             ║
║                                                                            ║
║ • agent2_business_model → agent3_generate (optionnel si failure)         ║
║                                                                            ║
║ • agent3_generate     → route_after_agent3                              ║
║   ├─ tests generated   → agent4_validate                                ║
║   └─ no tests          → no_tests (END)                                 ║
║                                                                            ║
║ • agent4_validate     → route_after_agent4                              ║
║   ├─ VALID (coverage >= 70%) → agent5_report                           ║
║   ├─ ISSUES + iterations < MAX → agent3_gap_fill (boucle)              ║
║   └─ MAX iterations atteint → agent5_report                             ║
║                                                                            ║
║ • agent3_gap_fill     → agent4_validate (boucle de correction)          ║
║                                                                            ║
║ • agent5_report       → END                                              ║
║                                                                            ║
║ Terminal nodes: skip, no_tests, not_functional → END                    ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
"""
    return diagram


def get_mermaid_definition() -> str:
    """
    Retourne la définition Mermaid du graphe pour visualisation en ligne.
    Format: Horizontal (Left-Right) pour meilleure lisibilité.
    """
    mermaid_def = """
graph LR
    START([START]) --> ENRICH["1. Enrich<br/>Jira + Cache"]
    ENRICH --> CLASSIFY["2. Classify<br/>Agent 1"]
    
    CLASSIFY -->|invalid| SKIP["SKIP"]
    CLASSIFY -->|functional| ANALYSIS["3. Analysis<br/>Agent 1"]
    CLASSIFY -->|not_func| NOT_FUNC["NOT_FUNC"]
    
    ANALYSIS --> BIZ["4. Business<br/>Model<br/>Agent 2"]
    BIZ --> GEN["5. Generate<br/>Tests<br/>Agent 3"]
    
    GEN -->|no tests| NO_TESTS["NO_TESTS"]
    GEN -->|tests| VALIDATE["6. Validate<br/>Agent 4"]
    
    VALIDATE -->|cov>=70%| REPORT["7. Report<br/>Agent 5"]
    VALIDATE -->|cov<70%| GAPFILL["8. Gap-Fill<br/>Agent 3"]
    
    GAPFILL --> REVALIDATE["Re-Validate<br/>Agent 4"]
    REVALIDATE -->|issues| GAPFILL
    REVALIDATE -->|valid| REPORT
    
    SKIP --> END([END])
    NO_TESTS --> END
    NOT_FUNC --> END
    REPORT --> END
    
    style START fill:#90EE90
    style END fill:#FFB6C6
    style SKIP fill:#FFD700
    style NO_TESTS fill:#FFD700
    style NOT_FUNC fill:#FFD700
    style VALIDATE fill:#87CEEB
    style GAPFILL fill:#DDA0DD
    style REVALIDATE fill:#DDA0DD
    style REPORT fill:#FFB347
    """
    return mermaid_def


def save_mermaid_html(output_path: str = None) -> str:
    """
    Génère un fichier HTML avec la visualisation Mermaid interactive.
    """
    if output_path is None:
        output_path = "pipeline_workflow.html"
    
    mermaid_def = get_mermaid_definition()
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pipeline Orchestrator — LangGraph Workflow</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 30px;
        }}
        h1 {{
            color: #1e3c72;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}
        .subtitle {{
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 1.1em;
        }}
        .diagram {{
            display: flex;
            justify-content: center;
            overflow-x: auto;
            background: #f9f9f9;
            border-radius: 8px;
            padding: 20px;
            border: 2px solid #e0e0e0;
        }}
        .mermaid {{
            display: flex;
            justify-content: center;
        }}
        .legend {{
            margin-top: 30px;
            background: #f5f5f5;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #1e3c72;
        }}
        .legend h3 {{
            margin-top: 0;
            color: #1e3c72;
        }}
        .legend-item {{
            display: inline-block;
            margin-right: 30px;
            margin-bottom: 10px;
        }}
        .legend-color {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border-radius: 3px;
            margin-right: 8px;
            vertical-align: middle;
        }}
        .info {{
            background: #e8f4f8;
            border-left: 4px solid #00bcd4;
            padding: 15px;
            margin-top: 20px;
            border-radius: 4px;
            line-height: 1.6;
        }}
        .info strong {{
            color: #00838f;
        }}
        code {{
            background: #f0f0f0;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Pipeline Orchestrator</h1>
        <p class="subtitle">Multi-Agent LangGraph Workflow Visualization</p>
        
        <div class="diagram">
            <div class="mermaid">
{mermaid_def}
            </div>
        </div>
        
        <div class="legend">
            <h3>📊 Node Types</h3>
            <div class="legend-item">
                <span class="legend-color" style="background: #90EE90;"></span>
                <strong>Start</strong> — Pipeline entry point
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #FFB347;"></span>
                <strong>Agents</strong> — LLM-driven analysis & generation
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #87CEEB;"></span>
                <strong>Validation</strong> — Quality checks & coverage
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #DDA0DD;"></span>
                <strong>Gap-Fill</strong> — Correction loop
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #FFD700;"></span>
                <strong>Terminal</strong> — End states (skip/no tests)
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background: #FFB6C6;"></span>
                <strong>End</strong> — Pipeline completion
            </div>
        </div>
        
        <div class="info">
            <strong>📌 Key Features:</strong><br>
            • <strong>Conditional Routing</strong>: Dynamic path selection based on story type & validation results<br>
            • <strong>Feedback Loop</strong>: Gap-fill (Agent 3) + Re-validation (Agent 4) for coverage improvement<br>
            • <strong>Max Iterations</strong>: Prevents infinite loops with configurable correction limits<br>
            • <strong>Graceful Degradation</strong>: Non-blocking agents (e.g., Agent 2) don't fail the pipeline<br>
            • <strong>State Persistence</strong>: PipelineState carries all data through the workflow
        </div>
        
        <div class="info" style="background: #f0f8ff; border-left-color: #1976d2;">
            <strong>🔄 Feedback Loop Details:</strong><br>
            When Agent 4 detects issues (coverage < 70%, duplicates, ambiguities):<br>
            ① Agent 3 generates gap-fill tests for uncovered points<br>
            ② Tests are merged and deduplicated<br>
            ③ Agent 4 re-validates the expanded test suite<br>
            ④ Loop repeats until coverage ≥ 70% or max iterations reached<br>
            ⑤ Agent 5 generates final report with correction history
        </div>
    </div>
    
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default', securityLevel: 'loose' }});
        mermaid.contentLoaded();
    </script>
</body>
</html>
"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✓ Visualisation HTML générée : {output_path}")
    return output_path
