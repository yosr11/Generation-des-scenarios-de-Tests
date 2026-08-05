"""
Test rapide du VLM sur une image locale, sans passer par le pipeline complet.

Usage :
  py eval/test_vlm_on_image.py <chemin_image>

Compare scout (défaut) et maverick côte à côte si --compare est passé :
  py eval/test_vlm_on_image.py <chemin_image> --compare
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Permet d'importer app.services.* depuis la racine du repo
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Empêcher la lecture du cache pour ce test
os.environ["VLM_DISABLE_CACHE"] = "1"

from app.services import vision_client  # noqa: E402

# Patch monkey : ignorer le cache pour ce script
_original_read_cache = vision_client._read_cache
vision_client._read_cache = lambda h: None


def run_one(image_path: Path, model: str) -> tuple[str, float]:
    os.environ["VISION_MODEL"] = model
    # Forcer la relecture du module pour prendre la nouvelle env var
    import importlib

    importlib.reload(vision_client)
    vision_client._read_cache = lambda h: None  # re-patch après reload

    print(f"\n{'═' * 70}")
    print(f"  MODEL : {model}")
    print(f"{'═' * 70}")
    t0 = time.time()
    desc = vision_client.describe_image(
        image_path.read_bytes(),
        image_path.name,
    )
    elapsed = time.time() - t0
    return desc or "(aucune description renvoyée)", elapsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path, help="Chemin de l'image à analyser")
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare scout vs maverick",
    )
    args = parser.parse_args()

    if not args.image.exists():
        print(f"[ERREUR] Image introuvable : {args.image}")
        sys.exit(1)

    if args.compare:
        models = [
            "qwen/qwen3.6-27b",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
        ]
    else:
        models = [
            os.environ.get("VISION_MODEL", "qwen/qwen3.6-27b")
        ]

    for model in models:
        desc, elapsed = run_one(args.image, model)
        print(desc)
        print(f"\n  ⏱  {elapsed:.1f}s, {len(desc)} chars")


if __name__ == "__main__":
    main()
