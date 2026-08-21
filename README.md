# ChatBot IA - Sport, Musculation & Nutrition

Chatbot en langage naturel specialise sur le sport, la musculation et la nutrition, developpe en Python **sans framework NLP/ML externe** (pretraitement, TF-IDF, Naive Bayes et algorithmes de recherche de graphe implementes a la main).

## Fonctionnalites

- **Comprehension du langage naturel** : tokenisation, suppression des stop-words, stemming francais maison.
- **Classification d'intention** hybride : regles (V1) puis Naive Bayes multinomial (V2) en secours (`SALUTATION`, `QUITTER`, `IDENTITE`, `DEFINITION`, `COMPARAISON`, `QUESTION`).
- **Base de connaissances** sous forme de graphe oriente et pondere de concepts sportifs, avec paires question/reponse associees.
- **Recherche dans le graphe** : BFS, DFS et A* (heuristique admissible basee sur une similarite cosinus).
- **Apprentissage** : re-ranking TF-IDF + similarite cosinus des reponses candidates, et boucle de feedback utilisateur (1 a 5) qui renforce ou penalise les reponses et les poids du graphe, avec persistance et rejeu au redemarrage.
- **Gestion des relances conversationnelles** : une question sans sujet propre ("pourquoi ?") retombe sur le sujet de l'historique recent.
- **Deux interfaces** : ligne de commande et interface web (Flask) avec historique de discussions, feedback et tableau de statistiques/courbes d'apprentissage.

## Structure du projet

```
.
├── main.py              # Orchestrateur : pipeline complet d'une question (ChatBot)
├── nlp_engine.py         # Pretraitement NLP, stemmer maison, classification d'intention (regles), extraction d'entites
├── knowledge_base.py     # Graphe de connaissances (concepts/relations) + paires Q/R
├── search_engine.py       # BFS / DFS / A* sur le graphe de connaissances
├── learning_engine.py     # TF-IDF, Naive Bayes, boucle de feedback
├── ui.py                 # Interface CLI + interface web Flask (bonus)
├── data/
│   ├── knowledge_graph.json  # Concepts et relations ponderees
│   ├── qa_pairs.json         # Paires question/reponse (avec concepts et intention)
│   └── feedback_log.json     # Historique des feedbacks utilisateur
├── tests/                 # Tests unitaires et d'integration (pytest)
└── requirements.txt
```

## Installation

Necessite Python 3.11+ (utilise les generiques `list[str] | None`).

```bash
pip install -r requirements.txt
```

## Utilisation

### Interface en ligne de commande

```bash
python main.py
```

Tapez votre question, puis notez la reponse de 1 a 5 (Entree pour passer). Tapez `quit`, `quitter` ou `exit` pour arreter.

### Interface web (bonus)

```bash
python ui.py --web
```

Puis ouvrez [http://localhost:5000](http://localhost:5000). L'interface permet de gerer plusieurs discussions, de noter les reponses et de consulter les statistiques d'apprentissage (volet Parametres).

## Tests

```bash
pytest
```

Les tests couvrent chaque module (NLP, base de connaissances, recherche, apprentissage) ainsi que le chatbot complet en integration (conversation sur plusieurs questions, temps de reponse moyen).

## Documentation

Un rapport detaille (`Rapport_ChatBot_Sport_Emmanuel_AGBOTOME.pdf`) accompagne le projet et explique les choix de conception, notamment le modele de cout et la justification de l'admissibilite de l'heuristique A*.
