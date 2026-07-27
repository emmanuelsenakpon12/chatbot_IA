"""Tests unitaires du module nlp_engine (Etape 2).

Inclut le benchmark exige par le sujet :
au moins 80% de precision d'intention sur 20 questions de test.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from knowledge_base import KnowledgeBase
from nlp_engine import NLPEngine

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _nlp():
    return NLPEngine()


def _kb():
    kb = KnowledgeBase()
    kb.load_from_json(os.path.join(DATA_DIR, "knowledge_graph.json"))
    return kb


# ----------------------------------------------------------------------
# Tokenisation
# ----------------------------------------------------------------------
def test_tokenize_minuscules_et_ponctuation():
    nlp = _nlp()
    assert nlp.tokenize("Le FOOTBALL, c'est GENIAL !") == \
        ["le", "football", "c", "est", "genial"]


def test_tokenize_apostrophes_et_accents():
    nlp = _nlp()
    tokens = nlp.tokenize("Qu'est-ce que l'échauffement ?")
    assert "echauffement" in tokens
    assert "qu" in tokens


def test_tokenize_texte_vide():
    assert _nlp().tokenize("   ") == []


# ----------------------------------------------------------------------
# Stopwords
# ----------------------------------------------------------------------
def test_remove_stopwords():
    nlp = _nlp()
    tokens = ["le", "football", "est", "un", "sport"]
    assert nlp.remove_stopwords(tokens) == ["football", "sport"]


# ----------------------------------------------------------------------
# Stemming
# ----------------------------------------------------------------------
def test_stem_regroupe_les_variantes():
    nlp = _nlp()
    assert nlp.stem(["proteines"]) == nlp.stem(["proteine"])
    assert nlp.stem(["entrainements"]) == nlp.stem(["entrainement"])


def test_preprocess_pipeline_complet():
    nlp = _nlp()
    result = nlp.preprocess("Les entraînements de musculation !")
    assert "muscul" in " ".join(result)
    assert "les" not in result


# ----------------------------------------------------------------------
# Levenshtein
# ----------------------------------------------------------------------
def test_levenshtein_valeurs_connues():
    lev = NLPEngine.levenshtein
    assert lev("chat", "chat") == 0
    assert lev("chat", "chats") == 1
    assert lev("footbal", "football") == 1
    assert lev("", "abc") == 3


# ----------------------------------------------------------------------
# Extraction d'entites
# ----------------------------------------------------------------------
def test_extract_entities_matching_direct():
    nlp, kb = _nlp(), _kb()
    tokens = nlp.tokenize("Parle-moi du football et du tennis")
    assert nlp.extract_entities(tokens, kb) == ["football", "tennis"]


def test_extract_entities_pluriel_via_stem():
    nlp, kb = _nlp(), _kb()
    tokens = nlp.tokenize("Le role des proteines dans les entrainements")
    entites = nlp.extract_entities(tokens, kb)
    assert "proteines" in entites
    assert "entrainement" in entites


def test_extract_entities_typo_via_levenshtein():
    nlp, kb = _nlp(), _kb()
    tokens = nlp.tokenize("j'adore le footbal et le tenis")
    entites = nlp.extract_entities(tokens, kb)
    assert "football" in entites
    assert "tennis" in entites


def test_extract_entities_aucun_concept():
    nlp, kb = _nlp(), _kb()
    tokens = nlp.tokenize("bonjour comment vas tu")
    assert nlp.extract_entities(tokens, kb) == []


# ----------------------------------------------------------------------
# BENCHMARK SUJET : >= 80% de precision d'intention sur 20 questions
# ----------------------------------------------------------------------
JEU_DE_TEST = [
    ("Bonjour !", "SALUTATION"),
    ("Salut, ca va ?", "SALUTATION"),
    ("Je veux quitter", "QUITTER"),
    ("Au revoir", "QUITTER"),
    ("Qu'est-ce que le football ?", "DEFINITION"),
    ("Qu'est-ce que la VO2max ?", "DEFINITION"),
    ("C'est quoi un marathon ?", "DEFINITION"),
    ("Que veut dire endurance ?", "DEFINITION"),
    ("Definis la musculation", "DEFINITION"),
    ("Quelle est la difference entre cardio et musculation ?", "COMPARAISON"),
    ("Compare le sprint et le marathon", "COMPARAISON"),
    ("Football versus rugby, lequel est plus physique ?", "COMPARAISON"),
    ("Le handball par rapport au basketball ?", "COMPARAISON"),
    ("Comment ameliorer son endurance ?", "QUESTION"),
    ("Pourquoi s'echauffer avant le sport ?", "QUESTION"),
    ("Combien de joueurs dans une equipe de rugby ?", "QUESTION"),
    ("Quand faut-il s'etirer ?", "QUESTION"),
    ("Quel sport est bon pour le cardio ?", "QUESTION"),
    ("Faut-il boire pendant l'effort ?", "QUESTION"),
    ("Que manger avant une seance ?", "QUESTION"),
]


def test_precision_intentions_sur_20_questions():
    """Exigence du sujet : >= 80% de bonnes intentions sur 20 questions."""
    nlp = _nlp()
    correct = 0
    erreurs = []
    for question, attendu in JEU_DE_TEST:
        predit = nlp.classify_intent(nlp.tokenize(question))
        if predit == attendu:
            correct += 1
        else:
            erreurs.append((question, attendu, predit))
    precision = correct / len(JEU_DE_TEST)
    assert precision >= 0.8, f"Precision {precision:.0%} < 80%. Erreurs : {erreurs}"


def test_precision_entites_sur_10_questions():
    """Bonus : verifie l'extraction d'entites sur des cas varies."""
    nlp, kb = _nlp(), _kb()
    jeu = [
        ("Qu'est-ce que le football ?", {"football"}),
        ("Compare le sprint et le marathon", {"sprint", "marathon"}),
        ("Comment eviter les crampes ?", {"crampes"}),
        ("Parle-moi de la natation en piscine", {"natation", "piscine"}),
        ("Le role des proteines en musculation", {"proteines", "musculation"}),
        ("Pourquoi l'hydratation est importante ?", {"hydratation"}),
        ("Les jeux olympiques et la coupe du monde", {"jeux_olympiques", "coupe_du_monde"} & set(kb.all_concepts()) or set()),
        ("Quelle equipe a gagne ?", {"equipe"}),
        ("J'aime le velo et le cyclisme", {"cyclisme"}),
        ("Comment progresser en endurance ?", {"endurance"}),
    ]
    ok = 0
    for question, attendues in jeu:
        trouvees = set(nlp.extract_entities(nlp.tokenize(question), kb))
        if attendues <= trouvees:
            ok += 1
    assert ok / len(jeu) >= 0.8, f"Seulement {ok}/10 extractions correctes"
