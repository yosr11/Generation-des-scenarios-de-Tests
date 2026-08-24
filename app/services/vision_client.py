"""
app/services/vision_client.py
─────────────────────────────
Extraction de texte/sémantique depuis les images (mockups, captures d'écran,
schémas) jointes aux user stories Jira, via Amazon Bedrock Nova 2 Lite.

Sortie : description textuelle en français qui peut s'injecter dans le RAG
documents comme n'importe quel autre extrait PDF/DOCX.

Cache disque par MD5 du contenu binaire → on ne re-VLMise jamais la même image.
"""

import hashlib
import io
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional

import boto3
from dotenv import load_dotenv

load_dotenv(override=True)
logger = logging.getLogger(__name__)

# Modèle VLM Bedrock. Surchargeable via env var `VISION_MODEL` ou
# `BEDROCK_MODEL_ID` pour conserver une configuration compatible avec le reste du projet.
VISION_MODEL = os.getenv("VISION_MODEL", "nova-lite-2")
BEDROCK_VISION_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID",
    "eu.amazon.nova-2-lite-v1:0"
    if VISION_MODEL == "nova-lite-2"
    else VISION_MODEL,
)
AWS_REGION = os.getenv("AWS_REGION", "eu-west-3")
# 1200 tokens : laisse à Qwen assez de budget pour produire les 5 sections détaillées.
VISION_MAX_TOKENS = int(os.getenv("VISION_MAX_TOKENS", "2800"))

# v5 : ajout pré-traitement OCR (grayscale, upscale x2, auto-inversion fond
#      sombre, binarisation Otsu) + double passe PSM 6/11 pour mieux capter
#      à la fois les blocs de texte et les pills/badges éparpillés.
# v6 : passage au VLM maverick + budget tokens 1200 → invalide l'ancien cache scout.
# v7 : durcissement anti-hallucination du prompt VLM (interdit de nommer un pattern UI
#      incertain : « champ de recherche » et non « onglet de recherche personnalisée », etc.).
# v9 : version du prompt vision utilisée pour invalider automatiquement le cache.
_PROMPT_VERSION = "v9"

# Configuration Tesseract (Windows). Si tesseract.exe n'est pas dans le PATH,
# pointe vers son emplacement via la variable d'env `TESSERACT_CMD`.
_TESSERACT_CMD_ENV = os.getenv("TESSERACT_CMD")

# Langues OCR (français + anglais par défaut pour gérer les libellés mixtes).
_OCR_LANGS = os.getenv("OCR_LANGS", "fra+eng")

# Limiter la taille des images envoyées au modèle vision.
MAX_IMAGE_DIM = 1568  # px sur le plus grand côté
JPEG_QUALITY = 85
MIN_IMAGE_BYTES = 4 * 1024  # < 4 Ko = icône, on skip

_SUPPORTED_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")

# Cache disque
_CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "image_descriptions"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_VISION_PROMPT = (
    "Tu analyses une capture d'écran ou un mockup d'interface fournie en pièce "
    "jointe d'une user story Sopra HR.\n\n"
    "IMPORTANT : un OCR a DÉJÀ extrait pour toi TOUS les textes visibles dans "
    "l'image. Ils te sont fournis ci-dessous sous la balise <OCR_TEXTS>. "
    "Tu n'as donc PAS à relire ni recopier ces textes. Fais-leur confiance.\n\n"
    "Ta mission est COMPLÉMENTAIRE de l'OCR : tu dois décrire UNIQUEMENT ce que "
    "l'OCR ne peut pas voir, c'est-à-dire le visuel non-textuel. Réponds en "
    "français, factuellement, structuré en 5 sections.\n\n"
    "1. CONTEXTE (1-2 phrases) : nature de l'écran (formulaire, liste, tableau, "
    "popup, dashboard, carrousel, mockup annoté…) et son intention probable.\n\n"
    "2. ANNOTATIONS AJOUTÉES PAR LE PO (section CRITIQUE) : tout ce qui a été "
    "ajouté PAR-DESSUS l'écran original pour attirer l'attention. Cela inclut : "
    "encadrés colorés (rouge, jaune, violet, vert, orange…), flèches, cercles, "
    "soulignements, surlignages, biffures (texte barré), étoiles, post-it, "
    "captures d'écran avec un cercle rouge à la souris. Pour CHAQUE annotation :\n"
    "   - type (cadre / flèche / cercle / soulignement / surlignage / biffure / autre),\n"
    "   - couleur,\n"
    "   - quel élément de la liste OCR ci-dessous elle entoure ou désigne "
    "(reprends le texte exact entre guillemets).\n"
    "   Si aucune annotation n'est ajoutée par-dessus, écris explicitement "
    "« Aucune annotation détectée ». Ne fais pas semblant d'en voir.\n\n"
    "3. ÉLÉMENTS GRAPHIQUES NATIFS DE L'UI : pastilles (pills), badges, "
    "étiquettes (tags/chips), boutons, puces colorées qui font partie de "
    "l'interface elle-même (pas ajoutés par le PO). Pour CHACUN, précise sa "
    "forme, sa couleur de fond, et le texte OCR qu'il contient. Tu n'as pas à "
    "deviner le texte — il est dans la liste OCR.\n\n"
    "4. ICÔNES ET PICTOGRAMMES : tout symbole sans texte (engrenage, poubelle, "
    "crayon, loupe, croix, plus, flèche de navigation, œil, cadenas…). Pour "
    "chaque icône : sa fonction probable et sa position.\n\n"
    "5. AGENCEMENT ET RELATIONS : structure générale (colonnes, lignes, "
    "sections), regroupements visuels, hiérarchie (titres vs sous-titres), "
    "champs obligatoires (étoile *), états (actif/inactif, sélectionné, "
    "désactivé), relations spatiales importantes (« le bouton X est juste sous "
    "le champ Y donc il le valide probablement »).\n\n"
    "Règles strictes :\n"
    "- N'invente jamais de texte qui n'est pas dans la liste OCR.\n"
    "- Ne re-liste pas les textes de l'OCR pour faire du remplissage.\n"
    "- Si l'image est illisible ou vide, dis-le.\n"
    "- Reste factuel : décris ce que tu vois, sans interprétation métier.\n"
    "- NE NOMME JAMAIS un pattern d'UI dont tu n'es pas certain. Décris ce que tu vois "
    "littéralement, avec le vocabulaire le plus neutre et générique possible :\n"
    "   * une loupe + une zone de saisie → dis « champ de recherche », JAMAIS « onglet de "
    "recherche personnalisée », « recherche avancée » ou « formulaire de recherche ».\n"
    "   * des éléments regroupés sous un intitulé → dis « catégorie » / « regroupement », "
    "JAMAIS « sous-catégorie » / « sous-onglet » sauf si une hiérarchie à 2 niveaux est "
    "VISIBLEMENT et clairement présente à l'écran.\n"
    "   * un conteneur cliquable en haut d'une zone → dis « onglet » seulement si des onglets "
    "sont réellement visibles ; sinon « section » / « bloc ».\n"
    "- N'attribue PAS de fonctionnalités à un élément (création, filtrage, tri, application de "
    "filtres…) : décris uniquement sa forme et son libellé OCR, pas ce qu'il est censé faire.\n"
    "- En cas de doute sur le nom d'un composant, préfère TOUJOURS la description générique la "
    "plus prudente plutôt qu'un terme précis potentiellement inventé.\n"
    "- Retourne uniquement les cinq sections finales, sans raisonnement ni étapes d'analyse.\n"
    "- N'affiche jamais les balises <think> ou leur contenu.\n"
    "- Commence directement par le titre Markdown ## 1. CONTEXTE.\n"
    "- Utilise exactement ces titres, dans cet ordre :\n"
    "  ## 1. CONTEXTE\n"
    "  ## 2. ANNOTATIONS AJOUTÉES PAR LE PO\n"
    "  ## 3. ÉLÉMENTS GRAPHIQUES NATIFS DE L'UI\n"
    "  ## 4. ICÔNES ET PICTOGRAMMES\n"
    "  ## 5. AGENCEMENT ET RELATIONS\n"
    "- Utilise des listes à puces pour les éléments détaillés."
)


def _hash_bytes(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()


def _preprocess_for_ocr(img):
    """
    Pré-traitement pour booster Tesseract sur des mockups :
      - conversion en niveaux de gris,
      - upscale x2 (texte petit/tronqué devient lisible),
      - auto-inversion si fond sombre (Tesseract est entraîné sur noir/blanc),
      - binarisation Otsu si numpy dispo (sinon on s'en passe).
    Renvoie une nouvelle PIL.Image.
    """
    from PIL import Image, ImageOps

    # Niveaux de gris
    gray = img.convert("L")

    # Upscale x2 (LANCZOS = meilleure qualité pour texte)
    w, h = gray.size
    gray = gray.resize((w * 2, h * 2), Image.LANCZOS)

    # Auto-inversion si fond globalement sombre.
    # Moyenne pixel < 128 ⇒ fond sombre ⇒ on inverse pour que Tesseract voie
    # du texte noir sur fond blanc.
    try:
        import numpy as np

        arr = np.asarray(gray)
        if arr.mean() < 128:
            gray = ImageOps.invert(gray)
            arr = 255 - arr
        # Binarisation Otsu (seuil global optimal)
        from numpy import histogram

        hist, _ = histogram(arr.ravel(), bins=256, range=(0, 256))
        total = arr.size
        sum_total = (np.arange(256) * hist).sum()
        sumB, wB, max_var, threshold = 0.0, 0, 0.0, 127
        for t in range(256):
            wB += hist[t]
            if wB == 0:
                continue
            wF = total - wB
            if wF == 0:
                break
            sumB += t * hist[t]
            mB = sumB / wB
            mF = (sum_total - sumB) / wF
            var_between = wB * wF * (mB - mF) ** 2
            if var_between > max_var:
                max_var, threshold = var_between, t
        gray = gray.point(lambda p: 255 if p > threshold else 0, mode="L")
    except ImportError:
        # Pas de numpy → on s'arrête à l'upscale + grayscale.
        # On tente quand même l'auto-inversion basique via PIL.
        from PIL import ImageStat

        if ImageStat.Stat(gray).mean[0] < 128:
            gray = ImageOps.invert(gray)

    return gray


def _run_ocr(content: bytes, filename: str) -> Optional[str]:
    """
    Exécute Tesseract sur l'image (avec pré-traitement) et renvoie un bloc
    texte (un fragment par ligne, dédupliqué). Renvoie :
      - None si Tesseract n'est pas installé / introuvable,
      - "" si Tesseract a tourné mais n'a détecté aucun texte exploitable.
    Ne lève jamais d'exception.

    Stratégie : on lance Tesseract avec deux modes PSM (6 = bloc uniforme,
    11 = texte épars) et on fusionne les résultats. Cela maximise la
    couverture sur des images hétérogènes (à la fois blocs de texte et
    pills/badges éparpillés).
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.warning("pytesseract ou Pillow non installé — OCR désactivé.")
        return None

    if _TESSERACT_CMD_ENV:
        pytesseract.pytesseract.tesseract_cmd = _TESSERACT_CMD_ENV

    try:
        img = Image.open(io.BytesIO(content))
        pre = _preprocess_for_ocr(img)
    except Exception as exc:
        logger.warning("Pré-traitement OCR a échoué sur %s : %s", filename, exc)
        return None

    outputs = []
    for psm in (6, 11):
        try:
            raw = pytesseract.image_to_string(
                pre, lang=_OCR_LANGS, config=f"--oem 3 --psm {psm}"
            )
            outputs.append(raw)
        except pytesseract.TesseractNotFoundError:
            logger.warning(
                "Tesseract introuvable. Installe-le (https://github.com/UB-Mannheim/tesseract/wiki) "
                "ou définis la variable d'env TESSERACT_CMD vers tesseract.exe."
            )
            return None
        except Exception as exc:
            # Souvent : langue manquante. On retombe sur l'anglais seul.
            logger.debug(
                "OCR psm=%d lang=%s a échoué (%s), retry en eng", psm, _OCR_LANGS, exc
            )
            try:
                raw = pytesseract.image_to_string(
                    pre, lang="eng", config=f"--oem 3 --psm {psm}"
                )
                outputs.append(raw)
            except Exception as exc2:
                logger.warning("OCR a échoué sur %s (psm=%d) : %s", filename, psm, exc2)

    # Nettoyage : strip, dédup case-insensitive, fragments >= 2 chars.
    seen = set()
    fragments = []
    for raw in outputs:
        for line in raw.splitlines():
            s = line.strip()
            if len(s) < 2:
                continue
            key = s.lower()
            if key in seen:
                continue
            seen.add(key)
            fragments.append(s)

    if not fragments:
        return ""
    return "\n".join(fragments)


def _cache_path(content_hash: str) -> Path:
    # Inclut la version du prompt → bumper _PROMPT_VERSION invalide automatiquement
    # les anciennes descriptions sans avoir à vider le dossier.
    return _CACHE_DIR / f"{content_hash}_{_PROMPT_VERSION}.txt"


def _read_cache(content_hash: str) -> Optional[str]:
    path = _cache_path(content_hash)
    if path.exists():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None
    return None


def _write_cache(content_hash: str, text: str) -> None:
    try:
        _cache_path(content_hash).write_text(text, encoding="utf-8")
    except OSError as exc:
        logger.warning("Impossible d'écrire le cache vision %s : %s", content_hash, exc)


def _remove_thinking_block(text: str) -> str:
    """Retire le raisonnement éventuellement exposé par le modèle."""
    # Keep only the requested answer when the model adds an English preamble.
    section_markers = (
        "## 1. CONTEXTE",
        "1. CONTEXTE",
    )
    positions = [text.find(marker) for marker in section_markers]
    positions = [position for position in positions if position >= 0]
    if positions:
        cleaned = text[min(positions):]
    else:
        cleaned = text

    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<think>.*$", "", cleaned, flags=re.DOTALL | re.IGNORECASE)

    return cleaned.strip()


def _prepare_image_bytes(content: bytes, filename: str) -> Optional[bytes]:
    """
    Redimensionne si nécessaire et encode l'image en JPEG pour Bedrock.
    Retourne None si Pillow ne peut pas ouvrir l'image.
    """
    try:
        from PIL import Image
    except ImportError:
        logger.error("Pillow n'est pas installé — impossible de traiter les images.")
        return None

    try:
        img = Image.open(io.BytesIO(content))
        # Convertir en RGB (JPEG ne gère pas la transparence)
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(
                img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None
            )
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Redimensionner si trop grand
        max_dim = max(img.size)
        if max_dim > MAX_IMAGE_DIM:
            ratio = MAX_IMAGE_DIM / max_dim
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return buf.getvalue()
    except Exception as exc:
        logger.warning("Pillow n'a pas pu ouvrir %s : %s", filename, exc)
        return None


def _build_client():
    return boto3.client("bedrock-runtime", region_name=AWS_REGION)


def describe_image(
    content: bytes,
    filename: str,
    context: Optional[str] = None,
    max_retries: int = 2,
) -> Optional[str]:
    """
    Renvoie une description textuelle française de l'image, ou None si :
      - format non supporté,
      - image trop petite (icône),
      - Pillow ne peut pas l'ouvrir,
      - le VLM échoue après les retries.

    Utilise un cache disque par hash MD5 (collision-safe pour cet usage).
    `context` (optionnel) : un court rappel de la story pour guider la VLM.
    """
    name_lower = filename.lower()
    if not name_lower.endswith(_SUPPORTED_EXTS):
        return None
    if len(content) < MIN_IMAGE_BYTES:
        logger.info("Skip image %s (trop petite : %d octets)", filename, len(content))
        return None

    content_hash = _hash_bytes(content)
    cached = _read_cache(content_hash)
    if cached:
        logger.debug("Cache hit vision pour %s (%s)", filename, content_hash[:8])
        return cached

    image_bytes = _prepare_image_bytes(content, filename)
    if not image_bytes:
        return None

    # ── 1) OCR Tesseract (rapide, local) ──────────────────────────────────
    ocr_text = _run_ocr(content, filename)
    if ocr_text is None:
        ocr_block = "(OCR indisponible — Tesseract non installé)"
    elif ocr_text == "":
        ocr_block = "(aucun texte détecté par l'OCR)"
    else:
        ocr_block = ocr_text

    # ── 2) Prompt VLM avec OCR injecté ────────────────────────────────────
    user_text_parts = []
    if context:
        user_text_parts.append(
            "Contexte de la user story (pour orientation, sans la sur-interpréter) :\n"
            f"{context.strip()}\n"
        )
    user_text_parts.append(_VISION_PROMPT)
    user_text_parts.append("\n\n<OCR_TEXTS>\n" f"{ocr_block}\n" "</OCR_TEXTS>")
    user_text = "\n".join(user_text_parts)

    client = _build_client()
    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            response = client.converse(
                modelId=BEDROCK_VISION_MODEL_ID,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"text": user_text},
                            {"image": {"format": "jpeg", "source": {"bytes": image_bytes}}},
                        ],
                    }
                ],
                inferenceConfig={
                    "temperature": 0.0,
                    "maxTokens": min(VISION_MAX_TOKENS, 5120),
                },
            )
            output_message = response.get("output", {}).get("message", {})
            output_content = output_message.get("content", [])
            description = _remove_thinking_block(
                next((item.get("text", "") for item in output_content if item.get("text")), "")
            )
            if not description:
                return None

            # Sortie finale : header + bloc OCR brut + analyse VLM.
            # Les deux signaux sont préservés pour l'agent en aval.
            parts = [f"[Image jointe : {filename}]"]
            if ocr_text:
                parts.append("── Textes détectés (OCR) ──")
                parts.append(ocr_text)
            parts.append("── Analyse visuelle (VLM) ──")
            parts.append(description)
            full_text = "\n".join(parts)

            _write_cache(content_hash, full_text)
            logger.info(
                "Vision OK pour %s (OCR %s, VLM %d chars)",
                filename,
                f"{len(ocr_text.splitlines())} lignes" if ocr_text else "vide/off",
                len(description),
            )
            return full_text

        except Exception as exc:
            last_error = exc
            if attempt < max_retries - 1:
                sleep_for = 2.0 * (attempt + 1)
                logger.warning(
                    "Vision Bedrock indisponible pour %s (tentative %d/%d), retry dans %.1fs : %s",
                    filename,
                    attempt + 1,
                    max_retries,
                    sleep_for,
                    exc,
                )
                time.sleep(sleep_for)
                continue
            logger.error("Vision Bedrock échouée sur %s : %s", filename, exc)
            return None

    logger.error(
        "Vision a échoué pour %s après %d tentatives : %s",
        filename,
        max_retries,
        last_error,
    )
    return None


def ocr_only(content: bytes, filename: str) -> Optional[str]:
    """
    Exécute uniquement l'OCR local (Tesseract) et retourne un bloc de texte minimal
    identique à la portion OCR renvoyée par `describe_image` (header + OCR block).
    Ne fait AUCUN appel au VLM distant — usage gratuit/local.
    """
    ocr_text = _run_ocr(content, filename)
    if ocr_text is None:
        return None

    parts = [f"[Image jointe (OCR seulement) : {filename}]"]
    if ocr_text:
        parts.append("── Textes détectés (OCR) ──")
        parts.append(ocr_text)
    full_text = "\n".join(parts)
    return full_text
