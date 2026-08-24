"""
Test script — Génère les visualisations LangGraph
"""
import sys
import os

# Ajouter le répertoire racine au path
sys.path.insert(0, r'c:\Users\yomahfoudh\Desktop\Agent_Test')

from app.utils.graph_visualizer import (
    generate_ascii_diagram,
    save_mermaid_html,
    get_mermaid_definition
)

if __name__ == "__main__":
    print("=" * 80)
    print("LANGRAPH PIPELINE VISUALIZATION")
    print("=" * 80)
    
    # 1. Générer ASCII
    print("\n1️⃣ Generating ASCII diagram...")
    ascii_diagram = generate_ascii_diagram()
    print("\n" + ascii_diagram)
    
    # 2. Générer HTML
    print("\n2️⃣ Generating HTML visualization...")
    html_path = save_mermaid_html(
        r"c:\Users\yomahfoudh\Desktop\Agent_Test\pipeline_workflow.html"
    )
    print(f"✓ HTML saved to: {html_path}")
    
    # 3. Afficher Mermaid
    print("\n3️⃣ Mermaid definition:")
    print("-" * 80)
    print(get_mermaid_definition())
    print("-" * 80)
    
    print("\n" + "=" * 80)
    print("✅ All visualizations generated successfully!")
    print("=" * 80)
    print(f"\n📊 Open in browser: file:///{html_path}")
