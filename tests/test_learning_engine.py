"""Tests unitaires du module learning_engine (Etape 4).

Inclut la demonstration exigee par le sujet : 3 cycles de feedback
qui ameliorent effectivement le classement des reponses et modifient
les poids du graphe.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from knowledge_base import KnowledgeBase
from learning_engine import LearningEngine
from nlp_engine import NLPEngine

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _kb() -> KnowledgeBase:
    kb = KnowledgeBase()
    kb.load_from_json(os.path.join(DATA_DIR, "knowledge_graph.json"))
    kb.load_qa_pairs(os.path.join(DATA_DIR, "qa_pairs.json"))
    return kb


# ----------------------------------------------------------------------
# TF-IDF
# ----------------------------------------------------------------------
def test_build_tfidf_vocabulaire_et_idf():
    le = LearningEngine()
    docs = [["sport", "football"], ["sport", "tennis"], ["nutrition"]]
    le.build_tfidf(docs)
    assert set(le.vocabulary) == {"sport", "football", "tennis", "nutrition"}
    # 'sport' apparait dans 2 docs sur 3 : idf plus faible que 'nutrition'
    assert le.idf["sport"] < le.idf["nutrition"]
    assert len(le.tfidf_matrix) == 3


def test_vectorize_ignore_hors_vocabulaire():
    le = LearningEngine()
    le.build_tfidf([["sport", "football"]])
    vec = le.vectorize(["sport", "inconnu"])
    assert "sport" in vec and "inconnu" not in vec


def test_cosine_similarity_proprietes():
    le = LearningEngine()
    v1 = {"a": 1.0, "b": 2.0}
    v2 = {"a": 2.0, "b": 4.0}     # colineaire a v1
    v3 = {"c": 1.0}               # orthogonal
    assert le.cosine_similarity(v1, v2) == pytest.approx(1.0)
    assert le.cosine_similarity(v1, v3) == 0.0
    assert le.cosine_similarity(v1, {}) == 0.0
    s = le.cosine_similarity(v1, {"a": 1.0})
    assert 0.0 < s < 1.0


def test_rank_answers_pertinence():
    le = LearningEngine()
    nlp = NLPEngine()
    docs = [nlp.preprocess("le football est un sport collectif"),
            nlp.preprocess("les proteines aident les muscles")]
    le.build_tfidf(docs)
    query = nlp.preprocess("parle moi de football")
    ranked = le.rank_answers(query, [
        "les proteines aident les muscles",
        "le football est un sport collectif",
    ])
    assert ranked[0] == "le football est un sport collectif"


# ----------------------------------------------------------------------
# Naive Bayes
# ----------------------------------------------------------------------
NB_X = [
    ["bonjour"], ["salut", "ca", "va"], ["bonsoir"],
    ["quitter"], ["au", "revoir"], ["bye"],
    ["qu", "est", "ce", "que", "football"], ["c", "est", "quoi", "marathon"],
    ["definis", "musculation"],
    ["difference", "entre", "cardio", "musculation"],
    ["compare", "sprint", "marathon"], ["football", "versus", "rugby"],
    ["comment", "perdre", "poids"], ["pourquoi", "echauffer"],
    ["combien", "proteines", "jour"],
]
NB_Y = (["SALUTATION"] * 3 + ["QUITTER"] * 3 + ["DEFINITION"] * 3
        + ["COMPARAISON"] * 3 + ["QUESTION"] * 3)


def test_naive_bayes_apprend_et_predit():
    le = LearningEngine()
    le.train_naive_bayes(NB_X, NB_Y)
    assert le.predict_intent(["bonjour"]) == "SALUTATION"
    assert le.predict_intent(["difference", "entre", "seche", "masse"]) == "COMPARAISON"
    assert le.predict_intent(["comment", "prendre", "masse"]) == "QUESTION"
    assert le.predict_intent(["qu", "est", "ce", "que", "imc"]) == "DEFINITION"


def test_naive_bayes_non_entraine():
    assert LearningEngine().predict_intent(["bonjour"]) is None


def test_naive_bayes_entrees_invalides():
    with pytest.raises(ValueError):
        LearningEngine().train_naive_bayes([], [])


# ----------------------------------------------------------------------
# Feedback loop
# ----------------------------------------------------------------------
def test_record_feedback_et_boost():
    le = LearningEngine()
    le.record_feedback("q", "bonne reponse", 5)
    le.record_feedback("q", "mauvaise reponse", 1)
    assert le._feedback_boost["bonne reponse"] == 1.0
    assert le._feedback_boost["mauvaise reponse"] == -1.0
    assert len(le.feedback_log) == 2


def test_retrain_modifie_les_poids_du_graphe():
    kb = _kb()
    le = LearningEngine(kb)
    pair = kb.qa_pairs[1]  # definition du football
    # Poids avant : football -> sport
    avant = kb.graph["football"]["sport"]
    le.record_feedback("qu est ce que le football", pair["answer"], 5)
    resume = le.retrain()
    assert resume["renforces"] == 1
    assert resume["aretes_modifiees"] >= 1
    assert kb.graph["football"]["sport"] == pytest.approx(
        min(1.0, avant + LearningEngine.DELTA_POIDS))


def test_retrain_penalise_les_poids():
    kb = _kb()
    le = LearningEngine(kb)
    pair = kb.qa_pairs[1]
    avant = kb.graph["football"]["sport"]
    le.record_feedback("q", pair["answer"], 1)
    le.retrain()
    assert kb.graph["football"]["sport"] == pytest.approx(
        max(0.05, avant - LearningEngine.DELTA_POIDS))


def test_feedback_non_applique_deux_fois():
    kb = _kb()
    le = LearningEngine(kb)
    pair = kb.qa_pairs[1]
    le.record_feedback("q", pair["answer"], 5)
    le.retrain()
    apres_1 = kb.graph["football"]["sport"]
    le.retrain()  # aucun nouveau feedback : rien ne doit bouger
    assert kb.graph["football"]["sport"] == apres_1


def test_demo_3_cycles_de_feedback():
    """Exigence du sujet : demonstration sur 3 cycles de feedback.

    Scenario : la question 'comment progresser en endurance' hesite entre
    plusieurs reponses. Au fil de 3 cycles (feedback positif sur la bonne
    reponse, negatif sur l'intruse), le classement doit se stabiliser sur
    la bonne reponse et les poids du graphe doivent evoluer.
    """
    kb = _kb()
    nlp = NLPEngine()
    le = LearningEngine(kb)
    docs = [nlp.preprocess(p["question"] + " " + p["answer"])
            for p in kb.qa_pairs]
    le.build_tfidf(docs)

    bonne = next(p for p in kb.qa_pairs
                 if p["question"].startswith("Comment ameliorer son endurance"))
    intruse = next(p for p in kb.qa_pairs
                   if p["question"].startswith("Comment gagner en force"))
    query = nlp.preprocess("comment progresser et ameliorer mon endurance")
    candidats = [intruse, bonne]

    classements = []
    for _cycle in range(3):
        ranked = le.rank_answers(query, candidats)
        classements.append(ranked[0]["question"])
        le.record_feedback("progresser endurance", bonne["answer"], 5)
        le.record_feedback("progresser endurance", intruse["answer"], 1)
        le.retrain()

    ranked_final = le.rank_answers(query, candidats)
    # Apres 3 cycles, la bonne reponse est en tete
    assert ranked_final[0]["question"] == bonne["question"]
    # Et les poids du graphe ont ete renforces (endurance <-> cardio)
    assert kb.graph["cardio"]["endurance"] > 0.85


def test_persistance_feedback(tmp_path):
    le = LearningEngine()
    le.record_feedback("q1", "r1", 5)
    chemin = str(tmp_path / "feedback_log.json")
    le.save_feedback(chemin)
    le2 = LearningEngine()
    le2.load_feedback(chemin)
    assert len(le2.feedback_log) == 1
    assert le2._feedback_boost["r1"] == 1.0
