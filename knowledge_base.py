"""
knowledge_base.py - Base de connaissances du ChatBot IA (domaine : sport)

Represente un graphe oriente pondere de concepts sportifs :
- noeuds  = concepts (ex : "football", "endurance")
- aretes  = relations ponderees entre concepts (poids dans [0, 1])

La classe charge egalement les paires question/reponse depuis un JSON.
"""

import json


class KnowledgeBase:
    """Graphe de connaissances oriente et pondere + paires Q/R."""

    def __init__(self) -> None:
        # {"football": {"sport": 0.9, "ballon": 0.9}, ...}
        self.graph: dict[str, dict[str, float]] = {}
        # [{"question": ..., "answer": ..., "concepts": [...], "intent": ...}]
        self.qa_pairs: list[dict] = []

    # ------------------------------------------------------------------
    # Construction du graphe
    # ------------------------------------------------------------------
    def add_concept(self, concept: str) -> None:
        """Ajoute un noeud au graphe (sans doublon)."""
        concept = concept.strip().lower()
        if concept and concept not in self.graph:
            self.graph[concept] = {}

    def add_relation(self, src: str, dst: str, weight: float = 1.0) -> None:
        """Ajoute une arete ponderee src -> dst.

        Les concepts manquants sont crees automatiquement.
        Le poids est borne dans [0, 1].
        """
        src = src.strip().lower()
        dst = dst.strip().lower()
        if not src or not dst or src == dst:
            raise ValueError("Relation invalide : src et dst doivent etre "
                             "des concepts distincts et non vides.")
        weight = max(0.0, min(1.0, float(weight)))
        self.add_concept(src)
        self.add_concept(dst)
        self.graph[src][dst] = weight

    def get_neighbors(self, concept: str) -> dict[str, float]:
        """Retourne les voisins sortants d'un concept et leurs poids.

        Retourne un dict vide si le concept est inconnu.
        """
        return dict(self.graph.get(concept.strip().lower(), {}))

    def has_concept(self, concept: str) -> bool:
        """Indique si un concept existe dans le graphe."""
        return concept.strip().lower() in self.graph

    def all_concepts(self) -> list[str]:
        """Liste de tous les concepts du graphe."""
        return list(self.graph.keys())

    # ------------------------------------------------------------------
    # Serialisation JSON
    # ------------------------------------------------------------------
    def load_from_json(self, filepath: str) -> None:
        """Charge le graphe (concepts + relations) depuis un fichier JSON.

        Format attendu :
        {
          "concepts": ["football", "sport", ...],
          "relations": [{"src": "football", "dst": "sport", "weight": 0.9}, ...]
        }
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for concept in data.get("concepts", []):
            self.add_concept(concept)
        for rel in data.get("relations", []):
            self.add_relation(rel["src"], rel["dst"], rel.get("weight", 1.0))

    def load_qa_pairs(self, filepath: str) -> None:
        """Charge les paires question/reponse depuis un fichier JSON."""
        with open(filepath, "r", encoding="utf-8") as f:
            self.qa_pairs = json.load(f)
        # Chaque concept mentionne dans une paire Q/R doit exister dans le graphe
        for pair in self.qa_pairs:
            for concept in pair.get("concepts", []):
                self.add_concept(concept)

    def save_to_json(self, filepath: str) -> None:
        """Serialise le graphe (concepts + relations) vers un fichier JSON."""
        data = {
            "concepts": self.all_concepts(),
            "relations": [
                {"src": src, "dst": dst, "weight": weight}
                for src, neighbors in self.graph.items()
                for dst, weight in neighbors.items()
            ],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Acces aux Q/R
    # ------------------------------------------------------------------
    def qa_for_concepts(self, concepts: list[str]) -> list[dict]:
        """Retourne les paires Q/R liees a au moins un des concepts donnes."""
        wanted = {c.strip().lower() for c in concepts}
        return [
            pair for pair in self.qa_pairs
            if wanted & {c.lower() for c in pair.get("concepts", [])}
        ]

    def __len__(self) -> int:
        return len(self.graph)

    def __repr__(self) -> str:
        nb_rel = sum(len(v) for v in self.graph.values())
        return (f"KnowledgeBase({len(self.graph)} concepts, "
                f"{nb_rel} relations, {len(self.qa_pairs)} paires Q/R)")
