"""Tests d'integration du ChatBot complet (Etape 5).

Inclut les exigences du sujet :
- conversation fluide sur au moins 20 questions du domaine
- temps de reponse moyen < 2 secondes
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from main import ChatBot, REPONSE_INCONNUE

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _bot() -> ChatBot:
    return ChatBot(DATA_DIR)


# 20 questions du domaine pour la conversation fluide exigee par le sujet
CONVERSATION_20 = [
    "Bonjour !",
    "Qu'est-ce que le football ?",
    "Et le rugby c'est quoi ?",
    "Quelle est la difference entre football et rugby ?",
    "Combien de joueurs dans une equipe de basketball ?",
    "Qu'est-ce qu'un marathon ?",
    "Quelle est la distance d'un marathon ?",
    "Comment ameliorer son endurance ?",
    "Qu'est-ce que la VO2max ?",
    "Comment debuter la course a pied ?",
    "Qu'est-ce que la prise de masse ?",
    "Comment prendre de la masse musculaire ?",
    "Combien de proteines par jour ?",
    "Quels sont les meilleurs exercices de musculation ?",
    "Combien de series et de repetitions pour prendre du muscle ?",
    "Quelle est la difference entre prise de masse et seche ?",
    "Comment perdre du poids sainement ?",
    "Cardio ou musculation pour perdre du poids ?",
    "Pourquoi le sommeil est-il important pour le sportif ?",
    "Comment eviter les crampes ?",
]


def test_salutation_et_quitter():
    bot = _bot()
    assert "Bonjour" in bot.answer("Salut !")
    assert "Au revoir" in bot.answer("je veux quitter")


def test_definition_simple():
    bot = _bot()
    reponse = bot.answer("Qu'est-ce que le football ?")
    assert "11" in reponse or "football" in reponse.lower()


def test_question_musculation():
    bot = _bot()
    reponse = bot.answer("Combien de proteines par jour ?")
    assert "1,6" in reponse or "proteines" in reponse.lower()


def test_robustesse_faute_de_frappe():
    bot = _bot()
    reponse = bot.answer("c'est quoi le footbal ?")
    assert reponse != REPONSE_INCONNUE


def test_synonymes_courants_du_langage_naturel():
    """Formulations courantes qui passent par un alias du graphe (muscle,
    abdos, ventre) ou par le stemming (pompe/pompes, traction/tractions)
    plutot que par une correspondance exacte de concept."""
    bot = _bot()
    for question, mot_attendu in [
        ("Comment prendre du muscle rapidement ?", "muscul"),
        ("C'est quoi une pompe ?", "pompe"),
        ("Qu'est-ce qu'une traction ?", "traction"),
        ("Comment faire pour avoir des abdos ?", "abdo"),
        ("Comment perdre du ventre ?", "poids"),
    ]:
        reponse = bot.answer(question)
        assert reponse != REPONSE_INCONNUE, question
        assert mot_attendu in reponse.lower(), (question, reponse)


def test_question_hors_domaine():
    bot = _bot()
    assert bot.answer("quelle est la capitale de la France ?") == REPONSE_INCONNUE


def test_entree_vide():
    bot = _bot()
    assert "ecoute" in bot.answer("   ").lower()


def test_conversation_fluide_20_questions():
    """Exigence du sujet : conversation fluide sur >= 20 questions."""
    bot = _bot()
    echecs = []
    for question in CONVERSATION_20:
        reponse = bot.answer(question)
        if not reponse or reponse == REPONSE_INCONNUE:
            echecs.append(question)
    assert not echecs, f"Questions sans reponse : {echecs}"


def test_temps_de_reponse_moyen_sous_2s():
    """Exigence du sujet : temps de reponse moyen < 2 secondes."""
    bot = _bot()
    debut = time.perf_counter()
    for question in CONVERSATION_20:
        bot.answer(question)
    moyenne = (time.perf_counter() - debut) / len(CONVERSATION_20)
    assert moyenne < 2.0, f"Temps moyen {moyenne:.3f}s >= 2s"


def test_feedback_de_bout_en_bout(tmp_path):
    """Le feedback via le bot modifie le graphe et persiste le journal."""
    import json
    import shutil
    # Copie isolee des donnees pour ne pas polluer data/
    data_tmp = tmp_path / "data"
    shutil.copytree(DATA_DIR, data_tmp)
    # Nombre d'entrees deja presentes (le feedback_log.json reel accumule
    # l'historique des tests manuels) : on verifie un delta, pas un absolu.
    log_path = data_tmp / "feedback_log.json"
    try:
        with open(log_path, encoding="utf-8") as f:
            avant_nb = len(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        avant_nb = 0
    bot = ChatBot(str(data_tmp))
    question = "Qu'est-ce que le football ?"
    reponse = bot.answer(question)
    avant = bot.kb.graph["football"]["sport"]
    bot.give_feedback(question, reponse, 5)
    assert bot.kb.graph["football"]["sport"] >= avant
    with open(log_path, encoding="utf-8") as f:
        assert len(json.load(f)) == avant_nb + 1
