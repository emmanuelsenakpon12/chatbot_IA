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


def test_questions_sur_identite_du_bot():
    """Meta-questions sur le bot lui-meme (pas sur le domaine sport) :
    elles ne doivent pas partir en recherche d'entites dans le graphe
    et renvoyer REPONSE_INCONNUE, mais une reponse dediee."""
    bot = _bot()
    for question in [
        "Tu es specialise dans quoi ?",
        "Qui es-tu ?",
        "Que peux-tu faire ?",
        "Presente-toi",
        "Comment tu t'appelles ?",
    ]:
        reponse = bot.answer(question)
        assert reponse == bot.REPONSE_IDENTITE, (question, reponse)


def test_definition_simple():
    bot = _bot()
    reponse = bot.answer("Qu'est-ce que le football ?")
    assert "11" in reponse or "football" in reponse.lower()


def test_question_musculation():
    bot = _bot()
    reponse = bot.answer("Combien de proteines par jour ?")
    assert "1,6" in reponse or "proteines" in reponse.lower()


def test_relance_sans_sujet_reutilise_l_historique():
    """Une relance sans entite propre ("pourquoi ?") echoue seule, mais
    retombe sur le sujet de la question precedente si on lui transmet
    l'historique (comme le fait le client CLI/web)."""
    bot = _bot()
    assert bot.answer("pourquoi") == REPONSE_INCONNUE
    question_precedente = "Que manger avant le sport ?"
    bot.answer(question_precedente)
    reponse = bot.answer("pourquoi", historique=[question_precedente])
    assert reponse != REPONSE_INCONNUE


def test_chaine_de_relances_sans_sujet():
    """Regression : une 2e relance ('pourquoi ?' apres 'pourquoi ?') ne
    doit pas echouer sous pretexte que le message juste precedent est
    lui-meme sans sujet propre. Reproduit le scenario observe : Que
    manger avant le sport ? -> pourquoi -> pourquoi (echouait avant le
    correctif, l'historique s'arretant au 'pourquoi' precedent)."""
    bot = _bot()
    historique = ["Que manger avant le sport ?", "pourquoi"]
    reponse = bot.answer("pourquoi", historique=historique)
    assert reponse != REPONSE_INCONNUE


def test_historique_ignore_si_question_a_deja_un_sujet():
    """L'historique ne doit servir que de filet de secours : s'il y a deja
    une entite dans la question, l'historique (meme hors-sujet) ne doit
    pas influencer la reponse."""
    bot = _bot()
    with_hist = bot.answer("Qu'est-ce que le football ?",
                            historique=["Qu'est-ce que la nutrition ?"])
    without_hist = bot.answer("Qu'est-ce que le football ?")
    assert with_hist == without_hist


def test_candidats_entite_specifique_pas_ecrasee_par_entite_generique():
    """Regression : quand la question extrait a la fois une entite tres
    generique et tres frequente ('sport', tagguee sur ~15 paires) et une
    entite plus specifique ('manger' -> 'nutrition'), la bonne reponse
    (liee a la specifique) ne doit pas etre evincee du pool de candidats
    par le volume des paires liees a la generique."""
    bot = _bot()
    reponse = bot.answer("Que manger avant le sport ?")
    assert "avant" in reponse.lower() and "glucides" in reponse.lower()


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


def test_apprentissage_survit_a_un_redemarrage(tmp_path):
    """Regression : le poids du graphe appris via feedback ne doit pas
    etre perdu quand le bot est recree (simule un redemarrage du serveur
    web, qui garde une seule instance de ChatBot vivante entre les
    requetes mais la reconstruit entierement a chaque redeploiement)."""
    import shutil
    data_tmp = tmp_path / "data"
    shutil.copytree(DATA_DIR, data_tmp)

    bot1 = ChatBot(str(data_tmp))
    pair = bot1.kb.qa_pairs[1]  # definition du football
    bot1.give_feedback("qu est ce que le football", pair["answer"], 5)
    poids_appris = bot1.kb.graph["football"]["sport"]

    bot2 = ChatBot(str(data_tmp))  # nouvelle instance, memes fichiers
    assert bot2.kb.graph["football"]["sport"] == poids_appris
