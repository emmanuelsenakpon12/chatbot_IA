"""Tests unitaires du module search_engine (Etape 3).

Inclut le benchmark exige par le sujet : comparaison mesuree
(noeuds explores, temps) sur au moins 10 requetes, avec A* < BFS.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from knowledge_base import KnowledgeBase
from search_engine import SearchEngine

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _engine() -> SearchEngine:
    kb = KnowledgeBase()
    kb.load_from_json(os.path.join(DATA_DIR, "knowledge_graph.json"))
    kb.load_qa_pairs(os.path.join(DATA_DIR, "qa_pairs.json"))
    return SearchEngine(kb)


# 10 requetes de benchmark (le sujet exige >= 10)
REQUETES = [
    ("football", "sport"),
    ("football", "competition"),
    ("marathon", "cardio"),
    ("sprint", "cardio"),
    ("squat", "recuperation"),
    ("prise_de_masse", "calories"),
    ("perte_de_poids", "metabolisme"),
    ("seche", "nutrition"),
    ("natation", "competition"),
    ("hypertrophie", "proteines"),
]


# ----------------------------------------------------------------------
# BFS
# ----------------------------------------------------------------------
def test_bfs_chemin_direct():
    se = _engine()
    assert se.bfs("football", "sport") == ["football", "sport"]


def test_bfs_chemin_multi_sauts():
    se = _engine()
    chemin = se.bfs("squat", "recuperation")
    assert chemin is not None
    assert chemin[0] == "squat" and chemin[-1] == "recuperation"
    # Chaque paire consecutive doit etre une arete reelle du graphe
    for u, v in zip(chemin, chemin[1:]):
        assert v in se.kb.get_neighbors(u)


def test_bfs_plus_court_en_aretes():
    se = _engine()
    chemin = se.bfs("marathon", "cardio")  # marathon->course->cardio
    assert chemin == ["marathon", "course", "cardio"]


def test_bfs_inaccessible_ou_inconnu():
    se = _engine()
    assert se.bfs("sport", "football") is None      # graphe oriente
    assert se.bfs("inconnu", "sport") is None


# ----------------------------------------------------------------------
# DFS
# ----------------------------------------------------------------------
def test_dfs_trouve_un_chemin_valide():
    se = _engine()
    chemin = se.dfs("prise_de_masse", "calories")
    assert chemin is not None
    assert chemin[0] == "prise_de_masse" and chemin[-1] == "calories"
    for u, v in zip(chemin, chemin[1:]):
        assert v in se.kb.get_neighbors(u)


def test_dfs_respecte_max_depth():
    se = _engine()
    # profondeur 1 = une seule arete possible : squat -> recuperation impossible
    assert se.dfs("squat", "recuperation", max_depth=1) is None


# ----------------------------------------------------------------------
# A*
# ----------------------------------------------------------------------
def test_a_star_chemin_valide_et_optimal():
    """A* doit retourner un chemin de cout minimal (cout = 1 - poids)."""
    se = _engine()
    for start, goal in REQUETES:
        chemin = se.a_star(start, goal)
        assert chemin is not None, f"{start} -> {goal} devrait etre accessible"
        # Verifier le cout face a un Dijkstra de reference (h = 0)
        ref = se.a_star(start, goal, heuristic=lambda n, g: 0.0)

        def cout(p):
            return sum(1 - se.kb.get_neighbors(u)[v] for u, v in zip(p, p[1:]))
        assert abs(cout(chemin) - cout(ref)) < 1e-9, \
            f"A* non optimal sur {start} -> {goal}"


def test_heuristique_admissible():
    """h(n) ne doit jamais depasser c_min, borne inferieure du cout restant."""
    se = _engine()
    c_min = se._c_min()
    goal = "nutrition"
    for concept in se.kb.all_concepts():
        if concept == goal:
            continue
        h = c_min * (1.0 - se._context_similarity(concept, goal))
        assert 0.0 <= h <= c_min + 1e-9


def test_benchmark_a_star_explore_moins_que_bfs():
    """Exigence du sujet : comparaison mesuree sur >= 10 requetes, A* < BFS."""
    se = _engine()
    mesures = se.compare_algorithms(REQUETES)
    total_bfs = sum(m["bfs"]["explores"] for m in mesures)
    total_astar = sum(m["a_star"]["explores"] for m in mesures)
    assert len(mesures) >= 10
    assert total_astar < total_bfs, \
        f"A* ({total_astar} noeuds) devrait explorer moins que BFS ({total_bfs})"


# ----------------------------------------------------------------------
# find_best_answer
# ----------------------------------------------------------------------
def test_find_best_answer_definition():
    se = _engine()
    reponse = se.find_best_answer(["marathon"], "DEFINITION")
    assert reponse is not None
    assert "42" in reponse  # la definition du marathon mentionne 42,195 km


def test_find_best_answer_comparaison():
    se = _engine()
    reponse = se.find_best_answer(["prise_de_masse", "seche"], "COMPARAISON")
    assert reponse is not None
    assert "surplus" in reponse or "deficit" in reponse


def test_find_best_answer_sans_entites():
    se = _engine()
    assert se.find_best_answer([], "QUESTION") is None
    assert se.find_best_answer(["concept_inconnu"], "QUESTION") is None


def test_find_best_answer_via_voisinage():
    """Une entite sans Q/R directe doit remonter une reponse via ses voisins."""
    se = _engine()
    reponse = se.find_best_answer(["developpe_couche"], "QUESTION")
    assert reponse is not None


# ----------------------------------------------------------------------
# top_candidates
# ----------------------------------------------------------------------
def test_top_candidates_taille_et_ordre():
    se = _engine()
    top = se.top_candidates(["endurance"], "QUESTION", n=3)
    assert len(top) <= 3
    scores = [s for s, _p in se._score_candidates(["endurance"], "QUESTION")]
    assert scores == sorted(scores, reverse=True)


def test_top_candidates_sans_entites_connues():
    se = _engine()
    assert se.top_candidates([], "QUESTION") == []
    assert se.top_candidates(["concept_inconnu"], "QUESTION") == []


def test_top_candidates_coherent_avec_find_best_answer():
    """find_best_answer doit toujours correspondre au premier candidat
    de top_candidates (meme scoring, juste une vue tronquee a 1 vs N)."""
    se = _engine()
    reponse = se.find_best_answer(["endurance"], "QUESTION")
    top = se.top_candidates(["endurance"], "QUESTION", n=1)
    assert top[0]["answer"] == reponse
