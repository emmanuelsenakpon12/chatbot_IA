"""Point d'entree du ChatBot IA (domaine : sport).

Etape 1 : chargement et verification de la base de connaissances.
Les etapes suivantes brancheront NLPEngine, SearchEngine et LearningEngine.
"""

from knowledge_base import KnowledgeBase


def main() -> None:
    kb = KnowledgeBase()
    kb.load_from_json("data/knowledge_graph.json")
    kb.load_qa_pairs("data/qa_pairs.json")
    print(kb)
    print("Exemple - voisins de 'football' :", kb.get_neighbors("football"))
    print("Exemple - Q/R liees a 'marathon' :",
          [p["question"] for p in kb.qa_for_concepts(["marathon"])])


if __name__ == "__main__":
    main()
