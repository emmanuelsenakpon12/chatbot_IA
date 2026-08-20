"""
search_engine.py - Algorithmes de recherche sur le graphe (Etape 3)

Trois algorithmes sont implementes et instrumentes (noeuds explores, temps) :
  - BFS : parcours en largeur, chemin le plus court en nombre d'aretes
  - DFS : parcours en profondeur avec limite de profondeur
  - A*  : recherche informee avec heuristique admissible

MODELE DE COUT
  Chaque arete (u, v) de poids w dans [0, 1] a un cout : cost = 1 - w.
  Une relation forte (w proche de 1) est donc "peu chere" a traverser :
  A* privilegie les chemins semantiquement forts.

HEURISTIQUE ADMISSIBLE (justification pour le rapport / l'oral)
  Soit c_min = min des couts d'aretes du graphe (> 0 car w <= 0.9 ici).
  Pour tout noeud n != goal, le vrai cout restant h*(n) >= c_min
  (il reste au moins une arete a traverser).
  On definit : h(n) = c_min * (1 - sim(n, goal))   avec sim dans [0, 1]
  Donc 0 <= h(n) <= c_min <= h*(n) : l'heuristique ne surestime JAMAIS
  le cout restant => elle est admissible => A* retourne un chemin optimal.
  La similarite sim() guide la recherche vers les noeuds proches du but
  (cosinus sur les vecteurs de contexte des concepts ; remplacable par
  la similarite TF-IDF du LearningEngine a l'etape 4, embeddings en M2).
"""

import heapq
import math
import time
from collections import deque

from knowledge_base import KnowledgeBase


class SearchEngine:
    """Moteur de recherche sur le graphe de connaissances."""

    def __init__(self, kb: KnowledgeBase, similarity_fn=None) -> None:
        self.kb = kb
        # Statistiques du dernier appel : {"algo", "explored", "time_ms"}
        self.last_stats: dict = {}
        # Fonction de similarite injectable (TF-IDF a l'etape 4)
        self._sim = similarity_fn or self._context_similarity
        self._context_cache: dict[str, dict[str, int]] = {}

    # ------------------------------------------------------------------
    # Outils internes
    # ------------------------------------------------------------------
    @staticmethod
    def _edge_cost(weight: float) -> float:
        """Cout d'une arete : plus la relation est forte, moins elle coute."""
        return 1.0 - weight

    def _c_min(self) -> float:
        """Plus petit cout d'arete du graphe (borne pour l'admissibilite)."""
        couts = [self._edge_cost(w)
                 for nbrs in self.kb.graph.values() for w in nbrs.values()]
        return min(couts) if couts else 0.0

    def _record(self, algo: str, explored: int, t0: float) -> None:
        self.last_stats = {
            "algo": algo,
            "explored": explored,
            "time_ms": (time.perf_counter() - t0) * 1000,
        }

    # ------------------------------------------------------------------
    # BFS
    # ------------------------------------------------------------------
    def bfs(self, start: str, goal: str) -> list[str] | None:
        """Parcours en largeur. Retourne le chemin le plus court (en nombre
        d'aretes) entre deux concepts, ou None si inaccessible."""
        t0 = time.perf_counter()
        if start not in self.kb.graph or goal not in self.kb.graph:
            self._record("BFS", 0, t0)
            return None

        queue = deque([(start, [start])])
        visited = {start}
        explored = 0

        while queue:
            node, path = queue.popleft()
            explored += 1
            if node == goal:
                self._record("BFS", explored, t0)
                return path
            for neighbor in self.kb.get_neighbors(node):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        self._record("BFS", explored, t0)
        return None

    # ------------------------------------------------------------------
    # DFS
    # ------------------------------------------------------------------
    def dfs(self, start: str, goal: str, max_depth: int = 10) -> list[str] | None:
        """Parcours en profondeur iteratif avec limite de profondeur.
        Retourne UN chemin (pas forcement le plus court), ou None."""
        t0 = time.perf_counter()
        if start not in self.kb.graph or goal not in self.kb.graph:
            self._record("DFS", 0, t0)
            return None

        stack = [(start, [start])]
        visited = set()
        explored = 0

        while stack:
            node, path = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            explored += 1
            if node == goal:
                self._record("DFS", explored, t0)
                return path
            if len(path) <= max_depth:
                # Ordre inverse pour explorer les voisins forts en premier
                for neighbor, w in sorted(self.kb.get_neighbors(node).items(),
                                          key=lambda x: x[1]):
                    if neighbor not in visited:
                        stack.append((neighbor, path + [neighbor]))

        self._record("DFS", explored, t0)
        return None

    # ------------------------------------------------------------------
    # A*
    # ------------------------------------------------------------------
    def a_star(self, start: str, goal: str, heuristic=None) -> list[str] | None:
        """Recherche A* avec heuristique personnalisable.

        Par defaut : h(n) = c_min * (1 - similarite(n, goal)), admissible
        (voir justification en tete de module). Retourne le chemin de cout
        minimal selon cost = 1 - poids, ou None si inaccessible."""
        t0 = time.perf_counter()
        if start not in self.kb.graph or goal not in self.kb.graph:
            self._record("A*", 0, t0)
            return None

        c_min = self._c_min()
        if heuristic is None:
            def heuristic(n: str, g: str) -> float:
                if n == g:
                    return 0.0
                return c_min * (1.0 - self._sim(n, g))

        # (f, compteur, noeud, chemin, g_score) - compteur pour departager
        counter = 0
        open_set = [(heuristic(start, goal), counter, start, [start], 0.0)]
        best_g: dict[str, float] = {start: 0.0}
        explored = 0

        while open_set:
            _f, _c, node, path, g = heapq.heappop(open_set)
            if g > best_g.get(node, math.inf):
                continue  # entree obsolete
            explored += 1
            if node == goal:
                self._record("A*", explored, t0)
                return path
            for neighbor, weight in self.kb.get_neighbors(node).items():
                new_g = g + self._edge_cost(weight)
                if new_g < best_g.get(neighbor, math.inf):
                    best_g[neighbor] = new_g
                    counter += 1
                    f = new_g + heuristic(neighbor, goal)
                    heapq.heappush(open_set,
                                   (f, counter, neighbor, path + [neighbor], new_g))

        self._record("A*", explored, t0)
        return None

    # ------------------------------------------------------------------
    # Similarite de contexte (heuristique par defaut)
    # ------------------------------------------------------------------
    def _concept_context(self, concept: str) -> dict[str, int]:
        """Vecteur de contexte d'un concept : sac de mots construit avec
        ses voisins (entrants/sortants) et les Q/R qui le mentionnent.
        Sera remplace par un vrai vecteur TF-IDF a l'etape 4."""
        if concept in self._context_cache:
            return self._context_cache[concept]

        termes: dict[str, int] = {}

        def _add(mot: str, poids: int = 1) -> None:
            termes[mot] = termes.get(mot, 0) + poids

        _add(concept, 3)
        for voisin, w in self.kb.get_neighbors(concept).items():
            _add(voisin, 2)
        for src, nbrs in self.kb.graph.items():
            if concept in nbrs:
                _add(src, 2)
        for pair in self.kb.qa_pairs:
            if concept in pair.get("concepts", []):
                for c in pair["concepts"]:
                    _add(c)

        self._context_cache[concept] = termes
        return termes

    def _context_similarity(self, a: str, b: str) -> float:
        """Cosinus entre les vecteurs de contexte de deux concepts."""
        va, vb = self._concept_context(a), self._concept_context(b)
        communs = set(va) & set(vb)
        num = sum(va[t] * vb[t] for t in communs)
        na = math.sqrt(sum(v * v for v in va.values()))
        nb = math.sqrt(sum(v * v for v in vb.values()))
        if na == 0 or nb == 0:
            return 0.0
        return num / (na * nb)

    # ------------------------------------------------------------------
    # Orchestration : trouver la meilleure reponse
    # ------------------------------------------------------------------
    def _score_candidates(self, entities: list[str],
                           intent: str) -> list[tuple[float, dict]]:
        """Calcule le score de chaque paire Q/R par rapport aux entites :
        1. pour chaque entite, explore le voisinage (BFS borne, profondeur 2)
           en scorant chaque concept atteint par le produit des poids ;
        2. collecte les Q/R liees aux concepts atteints ;
        3. score chaque Q/R : somme des scores de ses concepts
           + bonus si son intention correspond.
        Retourne les paires (score, pair) triees du meilleur au moins bon
        (liste vide si aucune entite connue). Facteur commun a
        find_best_answer (le meilleur seul) et top_candidates (le top N,
        utilise par le chatbot pour construire un pool de candidats plus
        large que la correspondance exacte de concepts avant le
        re-ranking TF-IDF)."""
        if not entities:
            return []

        # 1. Exploration ponderee du voisinage
        scores: dict[str, float] = {}
        for entity in entities:
            if entity not in self.kb.graph:
                continue
            scores[entity] = max(scores.get(entity, 0.0), 1.0)
            frontier = [(entity, 1.0)]
            for _profondeur in range(2):
                suivant = []
                for node, s in frontier:
                    for voisin, w in self.kb.get_neighbors(node).items():
                        ns = s * w
                        if ns > scores.get(voisin, 0.0):
                            scores[voisin] = ns
                            suivant.append((voisin, ns))
                frontier = suivant

        if not scores:
            return []

        # 2-3. Scorer les paires Q/R candidates
        resultats = []
        for pair in self.kb.qa_pairs:
            concepts = pair.get("concepts", [])
            if not concepts:
                continue
            s = sum(scores.get(c, 0.0) for c in concepts)
            # Bonus : les entites explicitement citees comptent double
            s += sum(1.0 for c in concepts if c in entities)
            # Bonus intention
            if intent and pair.get("intent") == intent:
                s += 0.5
            if s > 0.0:
                resultats.append((s, pair))

        resultats.sort(key=lambda x: x[0], reverse=True)
        return resultats

    def find_best_answer(self, entities: list[str], intent: str) -> str | None:
        """Retourne la meilleure reponse selon le score du graphe (None si
        rien trouve). Le re-ranking fin par TF-IDF arrive a l'etape 4."""
        resultats = self._score_candidates(entities, intent)
        return resultats[0][1]["answer"] if resultats else None

    def top_candidates(self, entities: list[str], intent: str,
                        n: int = 5) -> list[dict]:
        """Retourne les N paires Q/R les mieux notees par le score du
        graphe (liste vide si aucune entite connue). Sert a fournir au
        re-ranking TF-IDF un pool de candidats plus large que la seule
        correspondance exacte de concepts (KnowledgeBase.qa_for_concepts) :
        une paire peut etre pertinente sans partager litteralement un
        concept avec les entites extraites, tant qu'elle est atteignable
        dans le graphe."""
        resultats = self._score_candidates(entities, intent)
        return [pair for _s, pair in resultats[:n]]

    # ------------------------------------------------------------------
    # Comparaison mesuree BFS / DFS / A* (pour le rapport)
    # ------------------------------------------------------------------
    def compare_algorithms(self, queries: list[tuple[str, str]]) -> list[dict]:
        """Execute BFS, DFS et A* sur une liste de couples (start, goal)
        et retourne un tableau de mesures (noeuds explores, temps, chemin)."""
        lignes = []
        for start, goal in queries:
            ligne = {"start": start, "goal": goal}
            for nom, algo in (("bfs", self.bfs), ("dfs", self.dfs),
                              ("a_star", self.a_star)):
                chemin = algo(start, goal)
                ligne[nom] = {
                    "chemin": chemin,
                    "longueur": len(chemin) if chemin else None,
                    "explores": self.last_stats["explored"],
                    "temps_ms": round(self.last_stats["time_ms"], 3),
                }
            lignes.append(ligne)
        return lignes
