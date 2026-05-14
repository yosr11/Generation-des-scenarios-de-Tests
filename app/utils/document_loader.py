"""
app/utils/document_loader.py
─────────────────────────────
Extraction de texte depuis des fichiers binaires (PDF, Word, texte brut).
Utilisé par le collecteur de documents pour le RAG.
"""

import io
from typing import Optional


def extract_text_from_bytes(content: bytes, filename: str) -> Optional[str]:
    """
    Extrait le texte brut d'un fichier à partir de son contenu binaire.
    Supporte : PDF, DOCX, TXT/CSV/JSON/XML/properties/cfg.
    Retourne None si le format n'est pas supporté.
    """
    name_lower = filename.lower()

    if name_lower.endswith(".pdf"):
        return _extract_pdf(content)
    elif name_lower.endswith(".docx"):
        return _extract_docx(content)
    elif name_lower.endswith((".txt", ".csv", ".json", ".xml", ".properties", ".cfg", ".conf", ".md")):
        return _extract_text(content)
    else:
        return None


def _extract_pdf(content: bytes) -> Optional[str]:
    try:
        import pdfplumber
        pages_text = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text)
        return "\n\n".join(pages_text) if pages_text else None
    except Exception:
        return None


def _extract_docx(content: bytes) -> Optional[str]:
    try:
        from docx import Document
        doc = Document(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs) if paragraphs else None
    except Exception:
        return None


def _extract_text(content: bytes) -> Optional[str]:
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, ValueError):
            continue
    return None
