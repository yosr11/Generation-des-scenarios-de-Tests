#!/usr/bin/env python3
"""
Script standalone pour générer et afficher la visualisation LangGraph du pipeline.

Usage:
    python scripts/visualize_pipeline.py                    # Génère HTML interactif
    python scripts/visualize_pipeline.py --ascii            # Affiche ASCII dans le terminal
    python scripts/visualize_pipeline.py --mermaid          # Affiche Mermaid brut
    python scripts/visualize_pipeline.py --open             # Ouvre HTML dans le navigateur
"""

import sys
import argparse
import webbrowser
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Visualiser le graphe LangGraph du pipeline orchestrator"
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="Afficher le diagramme ASCII dans le terminal"
    )
    parser.add_argument(
        "--mermaid",
        action="store_true",
        help="Afficher la définition Mermaid brute"
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Générer HTML et ouvrir dans le navigateur"
    )
    parser.add_argument(
        "--output",
        default="pipeline_workflow.html",
        help="Chemin du fichier de sortie HTML (défaut: pipeline_workflow.html)"
    )
    
    args = parser.parse_args()
    
    # Import les fonctions de visualisation
    from app.utils.graph_visualizer import (
        generate_ascii_diagram,
        get_mermaid_definition,
        save_mermaid_html
    )
    
    if args.ascii:
        print(generate_ascii_diagram())
    
    elif args.mermaid:
        print("\n=== MERMAID DEFINITION ===\n")
        print(get_mermaid_definition())
    
    else:
        # Générer HTML par défaut
        output_path = save_mermaid_html(args.output)
        print(f"\n✓ Visualisation générée : {output_path}")
        print(f"\n📖 Ouvre le fichier dans ton navigateur :")
        print(f"   file://{Path(output_path).absolute()}")
        
        if args.open:
            print(f"\n🌐 Ouverture du navigateur...")
            webbrowser.open(f"file://{Path(output_path).absolute()}")
        else:
            print(f"\n💡 Astuce: Ajoute --open pour ouvrir automatiquement")


if __name__ == "__main__":
    main()
