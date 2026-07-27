"""Tests unitaires du module knowledge_base (Etape 1)."""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from knowledge_base import KnowledgeBase

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


# ----------------------------------------------------------------------
# add_concept
# ----------------------------------------------------------------------
def test_add_concept():
    kb = KnowledgeBase()
    kb.add_concept("football")
    assert kb.has_concept("football")
    assert kb.get_neighbors("football") == {}


def test_add_concept_normalise_et_sans_doublon():
    kb = KnowledgeBase()
    kb.add_concept("  Football ")
    kb.add_concept("football")
    assert len(kb) == 1
    assert kb.has_concept("football")


# ----------------------------------------------------------------------
# add_relation
# ----------------------------------------------------------------------
def test_add_relation():
    kb = KnowledgeBase()
    kb.add_relation("football", "sport", 0.9)
    assert kb.has_concept("football")
    assert kb.has_concept("sport")
    assert kb.get_neighbors("football") == {"sport": 0.9}


def test_add_relation_poids_borne():
    kb = KnowledgeBase()
    kb.add_relation("a", "b", 1.7)
    kb.add_relation("a", "c", -0.3)
    assert kb.get_neighbors("a") == {"b": 1.0, "c": 0.0}


def test_add_relation_invalide():
    kb = KnowledgeBase()
    with pytest.raises(ValueError):
        kb.add_relation("football", "football")
    with pytest.raises(ValueError):
        kb.add_relation("", "sport")


# ----------------------------------------------------------------------
# get_neighbors
# ----------------------------------------------------------------------
def test_get_neighbors_concept_inconnu():
    kb = KnowledgeBase()
    assert kb.get_neighbors("inexistant") == {}


def test_get_neighbors_retourne_une_copie():
    kb = KnowledgeBase()
    kb.add_relation("football", "sport", 0.9)
    voisins = kb.get_neighbors("football")
    voisins["sport"] = 0.1  # ne doit pas modifier le graphe
    assert kb.get_neighbors("football") == {"sport": 0.9}


# ----------------------------------------------------------------------
# Serialisation JSON
# ----------------------------------------------------------------------
def test_load_from_json_donnees_projet():
    kb = KnowledgeBase()
    kb.load_from_json(os.path.join(DATA_DIR, "knowledge_graph.json"))
    nb_relations = sum(len(v) for v in kb.graph.values())
    assert len(kb) >= 30, "Le sujet exige au moins 30 concepts"
    assert nb_relations >= 50, "Le sujet exige au moins 50 relations"
    assert kb.get_neighbors("football")["sport"] == pytest.approx(0.9)


def test_load_qa_pairs_donnees_projet():
    kb = KnowledgeBase()
    kb.load_qa_pairs(os.path.join(DATA_DIR, "qa_pairs.json"))
    assert len(kb.qa_pairs) >= 50, "Le sujet exige au moins 50 paires Q/R"
    for pair in kb.qa_pairs:
        assert {"question", "answer", "concepts", "intent"} <= set(pair)


def test_save_puis_load_round_trip():
    kb = KnowledgeBase()
    kb.add_relation("tennis", "raquette", 0.9)
    kb.add_relation("tennis", "sport", 0.8)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "graphe.json")
        kb.save_to_json(path)
        kb2 = KnowledgeBase()
        kb2.load_from_json(path)
        assert kb2.graph == kb.graph


def test_qa_for_concepts():
    kb = KnowledgeBase()
    kb.load_qa_pairs(os.path.join(DATA_DIR, "qa_pairs.json"))
    resultats = kb.qa_for_concepts(["marathon"])
    assert resultats, "Au moins une paire Q/R doit mentionner 'marathon'"
    assert all("marathon" in p["concepts"] for p in resultats)
