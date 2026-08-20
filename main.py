"""
main.py - Point d'entree et orchestrateur du ChatBot IA (Etape 5)

Pipeline complet d'une question :
  1. Pretraitement (tokens bruts pour l'intention, stemmes pour TF-IDF)
  2. Classification d'intention : regles (V1) puis Naive Bayes (V2)
     si les regles ne concluent pas
  3. Gestion des intentions speciales (SALUTATION, QUITTER)
  4. Extraction d'entites (concepts du graphe)
  5. Recherche dans le graphe (SearchEngine.find_best_answer)
  6. Re-ranking des candidats par TF-IDF (LearningEngine.rank_answers)
  7. Retour de la reponse (+ feedback optionnel via l'UI)
"""

import os

from knowledge_base import KnowledgeBase
from learning_engine import LearningEngine
from nlp_engine import NLPEngine
from search_engine import SearchEngine

REPONSE_INCONNUE = ("Je n'ai pas trouve de reponse a cette question. "
                    "Essayez de reformuler ou posez une question sur le "
                    "sport, la musculation ou la nutrition.")


class ChatBot:
    """Orchestrateur principal : relie les 4 modules du systeme."""

    # Exemples supplementaires pour entrainer Naive Bayes sur les
    # intentions absentes des paires Q/R (salutation, quitter, identite)
    _EXEMPLES_NB = [
        (["bonjour"], "SALUTATION"),
        (["salut", "ca", "va"], "SALUTATION"),
        (["bonsoir"], "SALUTATION"),
        (["hello"], "SALUTATION"),
        (["coucou"], "SALUTATION"),
        (["quitter"], "QUITTER"),
        (["au", "revoir"], "QUITTER"),
        (["bye"], "QUITTER"),
        (["exit"], "QUITTER"),
        (["stop"], "QUITTER"),
        (["qui", "es", "tu"], "IDENTITE"),
        (["tu", "es", "specialise", "dans", "quoi"], "IDENTITE"),
        (["que", "peux", "tu", "faire"], "IDENTITE"),
        (["presente", "toi"], "IDENTITE"),
    ]

    REPONSE_IDENTITE = (
        "Je suis un assistant specialise dans le sport, la musculation et "
        "la nutrition. Tu peux me poser des questions sur les differents "
        "sports, les exercices de musculation, l'entrainement, la "
        "recuperation, la perte de poids ou la prise de masse."
    )

    def __init__(self, data_dir: str = "data/") -> None:
        self.kb = KnowledgeBase()
        self.nlp = NLPEngine()
        self.search = SearchEngine(self.kb)
        self.learner = LearningEngine(self.kb)
        self._load_data(data_dir)

    # ------------------------------------------------------------------
    def _load_data(self, data_dir: str) -> None:
        """Charge le graphe, les Q/R, le feedback, puis entraine les modeles."""
        self.data_dir = data_dir
        self.kb.load_from_json(os.path.join(data_dir, "knowledge_graph.json"))
        self.kb.load_qa_pairs(os.path.join(data_dir, "qa_pairs.json"))
        self.learner.load_feedback(os.path.join(data_dir, "feedback_log.json"))
        # Reconstruit les poids appris des sessions precedentes : sans ce
        # rejeu, chaque redemarrage repartait des poids "d'auteur" fixes
        # de knowledge_graph.json et l'apprentissage ne survivait jamais
        # a un redemarrage du bot.
        self.learner.replay_feedback_sur_graphe()

        # TF-IDF sur les documents question+reponse pretraites
        documents = [self.nlp.preprocess(p["question"] + " " + p["answer"])
                     for p in self.kb.qa_pairs]
        self.learner.build_tfidf(documents)

        # Naive Bayes : questions du corpus (tokens bruts) + exemples dedies
        X = [self.nlp.tokenize(p["question"]) for p in self.kb.qa_pairs]
        y = [p["intent"] for p in self.kb.qa_pairs]
        for tokens, intent in self._EXEMPLES_NB:
            X.append(tokens)
            y.append(intent)
        self.learner.train_naive_bayes(X, y)

    # ------------------------------------------------------------------
    def answer(self, user_input: str, historique: list[str] | None = None) -> str:
        """Pipeline complet de traitement d'une question.

        `historique` : messages precedents de l'utilisateur dans la
        conversation en cours (le plus recent en dernier), optionnel.
        Sert uniquement de filet de secours pour les relances sans sujet
        propre ("pourquoi ?", "et donc ?") : si l'extraction d'entites sur
        `user_input` seul echoue, on retente sur le dernier message de
        l'historique pour retomber sur le sujet en cours plutot que de
        repondre REPONSE_INCONNUE. Le bot lui-meme reste sans etat (voir
        note d'architecture dans ui.py) ; c'est l'appelant (CLI ou client
        web) qui conserve et transmet cet historique."""
        if not user_input or not user_input.strip():
            return "Je vous ecoute ! Posez-moi une question sur le sport."

        # 1. Pretraitement : deux flux (voir note de conception nlp_engine)
        tokens_bruts = self.nlp.tokenize(user_input)
        tokens_pre = self.nlp.preprocess(user_input)

        # 2. Intention : regles V1, puis Naive Bayes V2 en secours
        intent = self.nlp.classify_intent(tokens_bruts)
        if intent == "INCONNU":
            prediction = self.learner.predict_intent(tokens_bruts)
            if prediction:
                intent = prediction

        # 3. Intentions speciales
        if intent == "SALUTATION":
            return ("Bonjour ! Je suis votre assistant sport, musculation "
                    "et nutrition. Comment puis-je vous aider ?")
        if intent == "QUITTER":
            return "Au revoir, et bon entrainement !"
        if intent == "IDENTITE":
            return self.REPONSE_IDENTITE

        # 4. Extraction d'entites (+ relance conversationnelle en secours)
        entities = self.nlp.extract_entities(tokens_bruts, self.kb)
        if not entities and historique:
            dernier_tokens = self.nlp.tokenize(historique[-1])
            entities = self.nlp.extract_entities(dernier_tokens, self.kb)
        if not entities:
            return REPONSE_INCONNUE

        # 5. Recherche dans le graphe : candidats par tag exact de concept
        # + candidats par proximite dans le graphe, calcules ENTITE PAR
        # ENTITE (et non sur le score combine de toutes les entites a la
        # fois). Sinon une entite tres generique et tres taguee (ex.
        # "sport", present dans ~15 paires) ecrase par son volume les
        # paires liees a une entite plus specifique mais moins frequente
        # (ex. "manger" -> "nutrition") : la bonne reponse n'apparaissait
        # alors jamais dans le pool soumis au re-ranking TF-IDF.
        candidats = self.kb.qa_for_concepts(entities)
        vus = {p["answer"] for p in candidats}
        for entity in entities:
            for pair in self.search.top_candidates([entity], intent, n=3):
                if pair["answer"] not in vus:
                    candidats.append(pair)
                    vus.add(pair["answer"])
        if not candidats:
            return REPONSE_INCONNUE

        # 6. Re-ranking par TF-IDF (+ bonus feedback)
        ranked = self.learner.rank_answers(tokens_pre, candidats)

        # 7. Reponse
        if not ranked:
            return REPONSE_INCONNUE
        meilleur = ranked[0]
        return meilleur["answer"] if isinstance(meilleur, dict) else meilleur

    # ------------------------------------------------------------------
    def give_feedback(self, question: str, reponse: str, score: int) -> None:
        """Enregistre un feedback, re-entraine et persiste le journal."""
        self.learner.record_feedback(question, reponse, score)
        self.learner.retrain()
        self.learner.save_feedback(
            os.path.join(self.data_dir, "feedback_log.json"))


def main() -> None:
    from ui import run_cli
    bot = ChatBot(os.path.join(os.path.dirname(__file__), "data/"))
    run_cli(bot)


if __name__ == "__main__":
    main()
