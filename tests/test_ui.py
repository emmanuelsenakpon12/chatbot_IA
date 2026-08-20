"""Tests unitaires du module ui.py (Etape 5) : CLI et interface Flask.

Ce module n'avait aucune couverture de tests jusqu'ici, alors qu'il
contenait plusieurs anomalies reperees lors d'un audit (entrees
malformees non gerees sur /ask et /feedback, cf. corrections associees).
"""

import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from main import ChatBot
from ui import create_app, run_cli

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _bot() -> ChatBot:
    """Bot en lecture seule sur les vraies donnees du projet : NE JAMAIS
    appeler give_feedback (ou /feedback) dessus, ca ecrirait dans le
    data/feedback_log.json reel et fausserait durablement le classement
    (deja arrive une fois pendant le developpement de ces tests -- voir
    _bot_isole ci-dessous pour tout test qui declenche un feedback)."""
    return ChatBot(DATA_DIR)


def _bot_isole(tmp_path) -> ChatBot:
    """Bot pointant sur une copie jetable des donnees, pour les tests qui
    enregistrent un feedback (give_feedback ecrit sur disque)."""
    data_tmp = tmp_path / "data"
    shutil.copytree(DATA_DIR, data_tmp)
    return ChatBot(str(data_tmp))


# ----------------------------------------------------------------------
# run_cli
# ----------------------------------------------------------------------
def test_run_cli_question_puis_quitter(monkeypatch, capsys):
    entrees = iter(["Qu'est-ce que le football ?", "", "quitter"])
    monkeypatch.setattr("builtins.input", lambda *_: next(entrees))
    run_cli(_bot())
    sortie = capsys.readouterr().out
    assert "football" in sortie.lower() or "11" in sortie
    assert "Au revoir" in sortie


def test_run_cli_relance_sans_sujet_utilise_l_historique(monkeypatch, capsys):
    """Meme scenario que la relance web : la question precedente reste le
    sujet quand le message suivant n'a pas d'entite propre."""
    entrees = iter(["Que manger avant le sport ?", "", "pourquoi", "", "quitter"])
    monkeypatch.setattr("builtins.input", lambda *_: next(entrees))
    run_cli(_bot())
    sortie = capsys.readouterr().out
    assert "Je n'ai pas trouve de reponse" not in sortie.split("pourquoi")[-1]


def test_run_cli_feedback_enregistre(monkeypatch, capsys, tmp_path):
    entrees = iter(["Qu'est-ce que le football ?", "5", "quitter"])
    monkeypatch.setattr("builtins.input", lambda *_: next(entrees))
    run_cli(_bot_isole(tmp_path))
    sortie = capsys.readouterr().out
    assert "Merci, feedback enregistre" in sortie


def test_run_cli_entree_vide_est_ignoree(monkeypatch, capsys):
    """Une ligne vide ne doit pas etre traitee comme une question (le
    'while True: continue' initial) ni consommer le prompt de feedback."""
    entrees = iter(["", "quitter"])
    monkeypatch.setattr("builtins.input", lambda *_: next(entrees))
    run_cli(_bot())
    sortie = capsys.readouterr().out
    assert "Au revoir" in sortie


def test_run_cli_ctrl_c_pendant_la_saisie(monkeypatch, capsys):
    def leve_interrupt(*_):
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", leve_interrupt)
    run_cli(_bot())
    sortie = capsys.readouterr().out
    assert "Au revoir" in sortie


# ----------------------------------------------------------------------
# Flask : page d'accueil
# ----------------------------------------------------------------------
def test_index_sert_la_page():
    client = create_app(_bot()).test_client()
    r = client.get("/")
    assert r.status_code == 200
    assert b"ChatBot IA" in r.data


def test_index_le_volet_parametres_peut_reellement_se_cacher():
    """Regression : .chat-panel et .settings-panel ont toutes deux un
    'display' fixe pose par une regle de classe. Dans un vrai navigateur,
    une regle d'auteur de meme specificite l'emporte TOUJOURS sur le
    style par defaut de [hidden], quel que soit l'ordre des regles :
    sans un [hidden]{display:none !important} explicite, basculer
    l'attribut hidden en JS (chatPanel.hidden=true / settingsPanel.hidden
    =false) ne cache visuellement rien, et les deux volets s'affichent
    cote a cote en permanence (bug confirme avec un navigateur reel,
    Playwright, avant ce correctif -- pytest seul ne peut pas executer
    le CSS en cascade, d'ou cette verification textuelle ciblee)."""
    client = create_app(_bot()).test_client()
    html = client.get("/").data.decode("utf-8")
    assert "[hidden]" in html and "display:none !important" in html


# ----------------------------------------------------------------------
# Flask : /ask
# ----------------------------------------------------------------------
def test_ask_reponse_normale():
    client = create_app(_bot()).test_client()
    r = client.post("/ask", json={"question": "Qu'est-ce que le football ?"})
    assert r.status_code == 200
    assert "football" in r.get_json()["answer"].lower()


def test_ask_avec_historique():
    client = create_app(_bot()).test_client()
    client.post("/ask", json={"question": "Que manger avant le sport ?"})
    r = client.post("/ask", json={
        "question": "pourquoi",
        "history": ["Que manger avant le sport ?"],
    })
    assert r.status_code == 200
    assert "Je n'ai pas trouve" not in r.get_json()["answer"]


def test_ask_sans_corps_json():
    """Requete sans JSON du tout : ne doit pas planter (500)."""
    client = create_app(_bot()).test_client()
    r = client.post("/ask")
    assert r.status_code == 200


def test_ask_question_type_invalide():
    """Regression : question non textuelle (ex. entier) plantait
    auparavant sur user_input.strip() dans ChatBot.answer."""
    client = create_app(_bot()).test_client()
    r = client.post("/ask", json={"question": 123})
    assert r.status_code == 200


def test_ask_history_type_invalide():
    """Regression : 'history' n'etant pas une liste doit etre ignore,
    pas provoquer d'erreur."""
    client = create_app(_bot()).test_client()
    r = client.post("/ask", json={"question": "Bonjour", "history": "oups"})
    assert r.status_code == 200


def test_ask_history_avec_elements_non_textuels():
    client = create_app(_bot()).test_client()
    r = client.post("/ask", json={
        "question": "Bonjour",
        "history": [1, None, {"a": 1}, "Qu'est-ce que le football ?"],
    })
    assert r.status_code == 200


# ----------------------------------------------------------------------
# Flask : /feedback
# ----------------------------------------------------------------------
def test_feedback_valide(tmp_path):
    client = create_app(_bot_isole(tmp_path)).test_client()
    r = client.post("/feedback", json={
        "question": "q", "answer": "a", "score": 5,
    })
    assert r.status_code == 200
    assert r.get_json()["ok"] is True


@pytest.mark.parametrize("payload", [
    {},
    {"question": "q"},
    {"question": "q", "answer": "a"},
    {"question": "q", "answer": "a", "score": "pas un nombre"},
    {"question": "q", "answer": "a", "score": None},
    {"question": "q", "answer": "a", "score": [1, 2, 3]},
    {"question": "q", "answer": "a", "score": {"x": 1}},
])
def test_feedback_entrees_invalides_renvoient_400_sans_planter(payload):
    """Regression : score non convertible en int (None, liste, dict...)
    levait TypeError, non capture auparavant -> erreur 500 au lieu d'un
    400 propre."""
    client = create_app(_bot()).test_client()
    r = client.post("/feedback", json=payload)
    assert r.status_code == 400
    assert r.get_json()["ok"] is False


def test_feedback_sans_corps_json():
    client = create_app(_bot()).test_client()
    r = client.post("/feedback")
    assert r.status_code == 400


# ----------------------------------------------------------------------
# Flask : /stats (volet Parametres : compteurs + courbes)
# ----------------------------------------------------------------------
def test_stats_structure():
    client = create_app(_bot()).test_client()
    r = client.get("/stats")
    assert r.status_code == 200
    data = r.get_json()
    for cle in ("concepts", "relations", "qa_pairs", "feedback_total",
                "feedback_positifs", "feedback_negatifs",
                "repartition_scores", "feedback_serie", "apprentissage_serie"):
        assert cle in data
    assert data["concepts"] > 0
    assert data["qa_pairs"] > 0
    assert len(data["feedback_serie"]) == data["feedback_total"]
    assert len(data["apprentissage_serie"]) == data["feedback_total"]
    assert sum(data["repartition_scores"].values()) == data["feedback_total"]


def test_stats_feedback_vide(tmp_path):
    """Un bot sans aucun feedback renvoie des series vides, pas une erreur
    (le volet Parametres doit pouvoir afficher un etat vide propre)."""
    data_tmp = tmp_path / "data"
    shutil.copytree(DATA_DIR, data_tmp)
    (data_tmp / "feedback_log.json").write_text("[]", encoding="utf-8")
    bot = ChatBot(str(data_tmp))
    client = create_app(bot).test_client()
    data = client.get("/stats").get_json()
    assert data["feedback_total"] == 0
    assert data["feedback_serie"] == []
    assert data["apprentissage_serie"] == []
    assert sum(data["repartition_scores"].values()) == 0


def test_stats_courbe_apprentissage_cumule_correctement(tmp_path):
    """La courbe d'apprentissage doit etre le cumul exact des +1/-1 derives
    des notes de la courbe de feedback (+1 si score>=4, -1 si score<=2,
    0 sinon), dans le meme ordre chronologique."""
    bot = _bot_isole(tmp_path)
    bot.give_feedback("q1", "r1", 5)   # +1
    bot.give_feedback("q2", "r2", 1)   # -1
    bot.give_feedback("q3", "r3", 3)   # 0 (neutre)
    bot.give_feedback("q4", "r4", 4)   # +1
    client = create_app(bot).test_client()
    data = client.get("/stats").get_json()
    scores = [p["score"] for p in data["feedback_serie"]]
    cumules = [p["cumule"] for p in data["apprentissage_serie"]]
    assert len(scores) == len(cumules)
    attendu = 0
    for score, cumule in zip(scores, cumules):
        attendu += 1 if score >= 4 else (-1 if score <= 2 else 0)
        assert cumule == attendu
