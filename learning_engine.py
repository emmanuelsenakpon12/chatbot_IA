"""
learning_engine.py - Module d'apprentissage du ChatBot IA (Etape 4)

Trois briques, toutes implementees A LA MAIN (sans sklearn, conformement
au sujet) :

1. TF-IDF + similarite cosinus
   - tf(t, d)  = frequence relative du terme t dans le document d
   - idf(t)    = ln((1 + N) / (1 + df(t))) + 1   (lissage, jamais nul)
   - vecteurs creux representes par des dict {terme: poids}

2. Naive Bayes multinomial (classification d'intention, V2)
   - P(classe | doc) proportionnel a P(classe) * produit P(mot | classe)
   - lissage de Laplace, calcul en log-probabilites pour la stabilite

3. Boucle de feedback utilisateur
   - score >= 4 : renforce l'association question/reponse
     (bonus de ranking + renforcement des poids du graphe)
   - score <= 2 : penalise (malus de ranking + affaiblissement des poids)
   - retrain() : applique les feedbacks, reconstruit TF-IDF,
     re-entraine Naive Bayes
"""

import json
import math
import re
import time
from collections import defaultdict


class LearningEngine:
    """Moteur d'apprentissage : TF-IDF, Naive Bayes, feedback loop."""

    # Pas d'ajustement des poids du graphe a chaque feedback
    DELTA_POIDS = 0.05
    POIDS_MIN, POIDS_MAX = 0.05, 1.0
    # Bonus/malus de ranking par point de feedback cumule
    BONUS_RANKING = 0.15

    def __init__(self, kb=None) -> None:
        self.kb = kb                      # KnowledgeBase (optionnelle)
        self.tfidf_matrix: list[dict] = []   # un vecteur creux par document
        self.vocabulary: dict[str, int] = {} # terme -> index
        self.idf: dict[str, float] = {}
        self.documents: list[list[str]] = []
        self.feedback_log: list[dict] = []
        # Cumul de feedback par cle de reponse : {answer: score_cumule}
        self._feedback_boost: dict[str, float] = defaultdict(float)
        # Naive Bayes
        self._nb_priors: dict[str, float] = {}
        self._nb_likelihood: dict[str, dict[str, float]] = {}
        self._nb_vocab: set[str] = set()
        self._nb_trained = False
        self._nb_examples: list[tuple[list[str], str]] = []

    # ==================================================================
    # 1. TF-IDF
    # ==================================================================
    def build_tfidf(self, documents: list[list[str]]) -> None:
        """Construit la matrice TF-IDF a partir des documents
        (chaque document = liste de tokens pretraites).
        Implementation maison : TF, IDF et matrice calcules a la main."""
        self.documents = documents
        n = len(documents)
        # -- document frequencies --
        df: dict[str, int] = defaultdict(int)
        for doc in documents:
            for terme in set(doc):
                df[terme] += 1
        # -- vocabulaire et idf lisse --
        self.vocabulary = {t: i for i, t in enumerate(sorted(df))}
        self.idf = {t: math.log((1 + n) / (1 + df_t)) + 1.0
                    for t, df_t in df.items()}
        # -- matrice (vecteurs creux normalises par la taille du doc) --
        self.tfidf_matrix = [self.vectorize(doc) for doc in documents]

    def vectorize(self, tokens: list[str]) -> dict[str, float]:
        """Transforme une liste de tokens en vecteur creux TF-IDF.
        Les termes hors vocabulaire sont ignores (idf inconnu)."""
        if not tokens:
            return {}
        comptes: dict[str, int] = defaultdict(int)
        for t in tokens:
            comptes[t] += 1
        total = len(tokens)
        return {t: (c / total) * self.idf[t]
                for t, c in comptes.items() if t in self.idf}

    def cosine_similarity(self, vec_a: dict, vec_b: dict) -> float:
        """Similarite cosinus entre deux vecteurs creux (implementation
        maison, aucune bibliotheque externe)."""
        if not vec_a or not vec_b:
            return 0.0
        if len(vec_b) < len(vec_a):
            vec_a, vec_b = vec_b, vec_a
        num = sum(w * vec_b[t] for t, w in vec_a.items() if t in vec_b)
        norm_a = math.sqrt(sum(w * w for w in vec_a.values()))
        norm_b = math.sqrt(sum(w * w for w in vec_b.values()))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return num / (norm_a * norm_b)

    @staticmethod
    def _tokens_simples(texte: str) -> list[str]:
        """Tokenisation minimale interne (les candidats arrivent en texte)."""
        return [t for t in re.split(r"[^a-z0-9_]+", texte.lower()) if t]

    def rank_answers(self, query_tokens: list[str], candidates: list) -> list:
        """Classe les reponses candidates par pertinence TF-IDF.

        `candidates` : liste de chaines (reponses) ou de dicts Q/R.
        Score = cosinus(question, candidat) + bonus/malus de feedback.
        Retourne les candidats tries du meilleur au moins bon."""
        if not candidates:
            return []
        vq = self.vectorize(query_tokens)
        scores = []
        for cand in candidates:
            texte = cand["answer"] if isinstance(cand, dict) else str(cand)
            base = cand.get("question", "") if isinstance(cand, dict) else ""
            tokens = self._tokens_simples(base + " " + texte)
            s = self.cosine_similarity(vq, self.vectorize(tokens))
            s += self.BONUS_RANKING * self._feedback_boost.get(texte, 0.0)
            scores.append((s, cand))
        scores.sort(key=lambda x: x[0], reverse=True)
        return [cand for _s, cand in scores]

    # ==================================================================
    # 2. Naive Bayes multinomial (intention V2)
    # ==================================================================
    def train_naive_bayes(self, X: list[list[str]], y: list[str]) -> None:
        """Entraine un classifieur Naive Bayes multinomial pour la
        classification d'intention. Implementation maison :
        priors + probabilites conditionnelles avec lissage de Laplace."""
        if not X or len(X) != len(y):
            raise ValueError("X et y doivent etre non vides et de meme taille")
        self._nb_examples = list(zip([list(x) for x in X], y))
        comptes_classes: dict[str, int] = defaultdict(int)
        comptes_mots: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        total_mots: dict[str, int] = defaultdict(int)
        self._nb_vocab = set()

        for tokens, classe in self._nb_examples:
            comptes_classes[classe] += 1
            for t in tokens:
                comptes_mots[classe][t] += 1
                total_mots[classe] += 1
                self._nb_vocab.add(t)

        n = len(y)
        v = len(self._nb_vocab)
        self._nb_priors = {c: math.log(k / n) for c, k in comptes_classes.items()}
        self._nb_likelihood = {}
        for classe in comptes_classes:
            denom = total_mots[classe] + v  # lissage de Laplace
            self._nb_likelihood[classe] = {
                t: math.log((comptes_mots[classe][t] + 1) / denom)
                for t in self._nb_vocab
            }
            # log-prob par defaut pour un mot jamais vu dans la classe
            self._nb_likelihood[classe]["__defaut__"] = math.log(1 / denom)
        self._nb_trained = True

    def predict_intent(self, tokens: list[str]) -> str | None:
        """Predit l'intention via Naive Bayes (log-probabilites).
        Retourne None si le modele n'est pas entraine."""
        if not self._nb_trained:
            return None
        meilleur, meilleur_score = None, -math.inf
        for classe, prior in self._nb_priors.items():
            like = self._nb_likelihood[classe]
            score = prior + sum(
                like.get(t, like["__defaut__"])
                for t in tokens if t in self._nb_vocab
            )
            if score > meilleur_score:
                meilleur, meilleur_score = classe, score
        return meilleur

    # ==================================================================
    # 3. Feedback loop
    # ==================================================================
    def record_feedback(self, question: str, answer: str, score: int) -> None:
        """Enregistre le retour utilisateur (1-5).
        score >= 4 : renforce l'association question/reponse ;
        score <= 2 : penalise la reponse."""
        score = max(1, min(5, int(score)))
        self.feedback_log.append({
            "question": question,
            "answer": answer,
            "score": score,
            "timestamp": time.time(),
            "applique": False,
        })
        if score >= 4:
            self._feedback_boost[answer] += 1.0
        elif score <= 2:
            self._feedback_boost[answer] -= 1.0

    def retrain(self) -> dict:
        """Re-entraine le modele en integrant les nouveaux feedbacks :
        1. ajuste les poids du graphe (renforce / penalise les relations
           entre les concepts de la paire Q/R concernee) ;
        2. reconstruit la matrice TF-IDF ;
        3. re-entraine Naive Bayes si des exemples existent.
        Retourne un resume des ajustements pour la demo/rapport."""
        resume = {"renforces": 0, "penalises": 0, "aretes_modifiees": 0}
        if self.kb is not None:
            for fb in self.feedback_log:
                if fb["applique"]:
                    continue
                pair = self._trouver_pair(fb["answer"])
                if pair:
                    delta = (self.DELTA_POIDS if fb["score"] >= 4
                             else -self.DELTA_POIDS if fb["score"] <= 2 else 0.0)
                    if delta:
                        n = self._ajuster_poids(pair.get("concepts", []), delta)
                        resume["aretes_modifiees"] += n
                        if delta > 0:
                            resume["renforces"] += 1
                        else:
                            resume["penalises"] += 1
                fb["applique"] = True
        if self.documents:
            self.build_tfidf(self.documents)
        if self._nb_examples:
            X, y = zip(*self._nb_examples)
            self.train_naive_bayes(list(X), list(y))
        return resume

    def _trouver_pair(self, answer: str) -> dict | None:
        """Retrouve la paire Q/R correspondant a une reponse donnee."""
        if self.kb is None:
            return None
        for pair in self.kb.qa_pairs:
            if pair.get("answer") == answer:
                return pair
        return None

    def _ajuster_poids(self, concepts: list[str], delta: float) -> int:
        """Modifie les poids des aretes reliant les concepts donnes.
        Retourne le nombre d'aretes effectivement modifiees."""
        modifiees = 0
        ensemble = set(concepts)
        for src in ensemble:
            voisins = self.kb.graph.get(src, {})
            for dst in list(voisins):
                if dst in ensemble:
                    ancien = voisins[dst]
                    nouveau = max(self.POIDS_MIN,
                                  min(self.POIDS_MAX, ancien + delta))
                    if nouveau != ancien:
                        voisins[dst] = nouveau
                        modifiees += 1
        return modifiees

    # ==================================================================
    # Persistance du feedback
    # ==================================================================
    def save_feedback(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.feedback_log, f, ensure_ascii=False, indent=2)

    def load_feedback(self, filepath: str) -> None:
        try:
            with open(filepath, encoding="utf-8") as f:
                self.feedback_log = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.feedback_log = []
        for fb in self.feedback_log:
            if fb.get("score", 3) >= 4:
                self._feedback_boost[fb["answer"]] += 1.0
            elif fb.get("score", 3) <= 2:
                self._feedback_boost[fb["answer"]] -= 1.0
