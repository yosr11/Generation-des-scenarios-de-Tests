"""
Audit sémantique avancé (optionnel) :
Recherche de similarité entre phrases de tests et une liste d'expressions vagues, via sentence-transformers.
"""
from sentence_transformers import SentenceTransformer, util
from typing import List, Tuple

# Liste d'expressions vagues (français)
VAGUE_PHRASES = [
    "vérifier que",
    "s'assurer que",
    "valider que",
    "confirmer que",
    "contrôler que",
    "vérifier"
]

class SemanticVagueDetector:
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.model = SentenceTransformer(model_name)
        self.vague_emb = self.model.encode(VAGUE_PHRASES, convert_to_tensor=True)

    def detect(self, sentences: List[str], threshold: float = 0.75) -> List[Tuple[str, str, float]]:
        sent_emb = self.model.encode(sentences, convert_to_tensor=True)
        results = []
        for idx, emb in enumerate(sent_emb):
            cos_scores = util.cos_sim(emb, self.vague_emb)[0]
            for j, score in enumerate(cos_scores):
                if score >= threshold:
                    results.append((sentences[idx], VAGUE_PHRASES[j], float(score)))
        return results
