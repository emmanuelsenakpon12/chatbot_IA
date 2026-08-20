"""
nlp_engine.py - Pretraitement NLP du ChatBot IA (domaine : sport)

Pipeline complet :
  tokenize -> remove_stopwords -> stem  (= preprocess)

Classification d'intention (V1 par regles ; V2 Naive Bayes via LearningEngine) :
  SALUTATION | QUITTER | DEFINITION | COMPARAISON | QUESTION | INCONNU

Extraction d'entites :
  matching direct + matching par racine (stem) + proximite (Levenshtein)

NOTE DE CONCEPTION : classify_intent attend des tokens BRUTS (sortie de
tokenize), pas des tokens stemmes. En effet le stemming detruit les
mots-cles d'intention ("comment" -> "comm", "difference" -> "differenc").
Le pipeline du ChatBot appellera donc :
  tokens_bruts = nlp.tokenize(texte)         # pour l'intention
  tokens_pre   = nlp.preprocess(texte)       # pour TF-IDF / recherche
"""

import re


# ----------------------------------------------------------------------
# Stemmer maison (suffixes francais courants)
# ----------------------------------------------------------------------
class SimpleFrenchStemmer:
    """Stemmer minimaliste pour le francais (implementation maison).

    Le sujet autorise SnowballStemmer (NLTK) ; cette version maison evite
    toute dependance externe et suffit pour un vocabulaire de domaine.
    Les suffixes sont testes du plus long au plus court, et on ne coupe
    jamais en dessous de 4 caracteres de racine.
    """

    _SUFFIXES = [
        "issements", "issement", "atrices", "atrice", "ationnel",
        "emments", "amments", "ivement", "ements", "emment", "amment",
        "ations", "ation", "ement", "euses", "istes", "ables", "iques",
        "elles", "aires", "ateur", "trice", "ances", "ences",
        "euse", "iste", "able", "ique", "elle", "aire", "ance", "ence",
        "ives", "eurs", "ants", "ente",
        "ive", "eur", "aux", "ant", "ent", "ees",
        "es", "ee", "er", "ir", "s", "e",
    ]

    def stem(self, word: str) -> str:
        w = word.lower()
        for suffix in self._SUFFIXES:
            if w.endswith(suffix) and len(w) - len(suffix) >= 4:
                return w[: len(w) - len(suffix)]
        return w


# ----------------------------------------------------------------------
# NLPEngine
# ----------------------------------------------------------------------
class NLPEngine:
    """Moteur de traitement du langage naturel pour le domaine sport."""

    INTENTS = ("SALUTATION", "QUITTER", "IDENTITE", "DEFINITION",
               "COMPARAISON", "QUESTION", "INCONNU")

    # Regles V1 : mots-cles par intention, appliquees sur tokens BRUTS.
    # Les cles multi-mots sont cherchees comme sous-chaines du texte joint.
    _INTENT_RULES: dict[str, list[str]] = {
        "SALUTATION": [
            "bonjour", "salut", "hello", "bonsoir", "coucou", "hey", "yo",
        ],
        "QUITTER": [
            "quitter", "quitte", "quit", "exit", "bye", "aurevoir",
            "au revoir", "stop", "terminer", "fin de la conversation",
        ],
        # Questions sur le bot lui-meme (pas sur le domaine sport) : elles
        # ne doivent pas partir en recherche d'entites dans le graphe.
        "IDENTITE": [
            "specialise", "specialisee", "specialite", "specialites",
            "qui es tu", "qui etes vous", "tu es qui",
            "que peux tu faire", "que sais tu faire", "tu sais faire quoi",
            "tu fais quoi", "que fais tu", "a quoi tu sers", "a quoi sers tu",
            "tes capacites", "capable de faire", "presente toi",
            "quel est ton role", "c est quoi ton role",
            "tu t appelles", "ton nom", "quel est ton nom",
        ],
        "DEFINITION": [
            "qu est ce que", "qu est ce qu", "c est quoi", "cest quoi",
            "definition", "definir", "definis", "signifie", "veut dire",
            "que veut dire", "explique moi ce que", "qu appelle t on",
        ],
        "COMPARAISON": [
            "difference", "differences", "compare", "comparer",
            "comparaison", "versus", "vs", "plutot que", "par rapport a",
            "mieux que", "meilleur que", "distingue", "distinguer",
            "ou bien",
        ],
        "QUESTION": [
            "comment", "pourquoi", "combien", "quand", "quel", "quelle",
            "quels", "quelles", "lequel", "laquelle", "est ce que",
            "est il", "est elle", "faut il", "peut on", "doit on",
            "que faire", "que manger", "qui",
        ],
    }

    def __init__(self) -> None:
        # Mots vides francais (liste maison, module re/string/collections
        # uniquement, conformement au sujet)
        self.stopwords: set[str] = {
            "le", "la", "les", "l", "de", "du", "des", "d", "un", "une",
            "et", "en", "est", "sont", "etre", "avoir", "a", "ai", "as",
            "il", "elle", "ils", "elles", "je", "j", "tu", "nous", "vous",
            "on", "ce", "c", "cet", "cette", "ces", "se", "s", "sa", "son",
            "ses", "mon", "ma", "mes", "ton", "ta", "tes", "notre", "votre",
            "au", "aux", "par", "pour", "sur", "sous", "dans", "vers",
            "avec", "sans", "que", "qu", "qui", "quoi", "dont", "y", "ne",
            "n", "pas", "plus", "moins", "tres", "aussi", "mais", "donc",
            "or", "ni", "car", "si", "comme", "tout", "tous", "toute",
            "toutes", "meme", "bien", "peu", "beaucoup", "faire", "fait",
        }
        self.stemmer = SimpleFrenchStemmer()

    # ------------------------------------------------------------------
    # 1. Tokenisation
    # ------------------------------------------------------------------
    def tokenize(self, text: str) -> list[str]:
        """Decoupe le texte en tokens minuscules, gere ponctuation,
        apostrophes (l'endurance -> l endurance) et accents typographiques."""
        text = text.replace("\u2019", "'").replace("\u2018", "'")
        text = re.sub(r"([a-zA-Za-yA-ÿà-ÿ])'", r"\1 ", text)
        text = self._strip_accents(text.lower())
        text = re.sub(r"[^a-z0-9_\s]", " ", text)
        return [t for t in text.split() if t]

    @staticmethod
    def _strip_accents(text: str) -> str:
        """Normalise les accents (é->e, à->a ...) sans lib externe."""
        table = str.maketrans(
            "àâäéèêëîïôöùûüçñ",
            "aaaeeeeiioouuucn",
        )
        return text.translate(table)

    # ------------------------------------------------------------------
    # 2. Stopwords
    # ------------------------------------------------------------------
    def remove_stopwords(self, tokens: list[str]) -> list[str]:
        """Supprime les mots vides (le, la, de, est ...)."""
        return [t for t in tokens if t not in self.stopwords]

    # ------------------------------------------------------------------
    # 3. Stemming
    # ------------------------------------------------------------------
    def stem(self, tokens: list[str]) -> list[str]:
        """Reduit chaque token a sa racine."""
        return [self.stemmer.stem(t) for t in tokens]

    # ------------------------------------------------------------------
    # 4. Pipeline complet
    # ------------------------------------------------------------------
    def preprocess(self, text: str) -> list[str]:
        """Pipeline complet : minuscules -> tokenize -> stopwords -> stem."""
        return self.stem(self.remove_stopwords(self.tokenize(text)))

    # ------------------------------------------------------------------
    # 5. Classification d'intention (V1 : regles)
    # ------------------------------------------------------------------
    def classify_intent(self, tokens: list[str]) -> str:
        """Classifie l'intention par regles de mots-cles.

        `tokens` = tokens BRUTS (sortie de tokenize, sans stemming).
        Priorite : SALUTATION > QUITTER > IDENTITE > DEFINITION >
        COMPARAISON > QUESTION > INCONNU. La priorite garantit par exemple
        que "qu est ce que la difference entre X et Y" -> on regarde d'abord
        DEFINITION... mais 'difference' etant plus specifique, COMPARAISON
        est teste via une regle dediee ci-dessous. IDENTITE passe avant
        QUESTION pour que "qui es-tu ?" ne soit pas capture par le
        mot-cle generique "qui" de QUESTION.
        """
        text = " ".join(tokens)

        # Cas particulier : "qu'est-ce que la difference entre..."
        # contient a la fois un marqueur DEFINITION et COMPARAISON ;
        # la presence de 'difference'/'compare' l'emporte.
        for kw in self._INTENT_RULES["COMPARAISON"]:
            if (kw in tokens) if " " not in kw else (kw in text):
                return "COMPARAISON"

        for intent in ("SALUTATION", "QUITTER", "IDENTITE", "DEFINITION", "QUESTION"):
            for kw in self._INTENT_RULES[intent]:
                if " " not in kw:
                    if kw in tokens:
                        return intent
                elif kw in text:
                    return intent

        return "INCONNU"

    # ------------------------------------------------------------------
    # 6. Distance de Levenshtein (implementation maison)
    # ------------------------------------------------------------------
    @staticmethod
    def levenshtein(a: str, b: str) -> int:
        """Distance d'edition entre deux chaines (prog. dynamique, O(n*m))."""
        if a == b:
            return 0
        if len(a) < len(b):
            a, b = b, a
        if not b:
            return len(a)
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            curr = [i]
            for j, cb in enumerate(b, 1):
                curr.append(min(
                    prev[j] + 1,                            # suppression
                    curr[j - 1] + 1,                        # insertion
                    prev[j - 1] + (ca != cb),               # substitution
                ))
            prev = curr
        return prev[-1]

    # ------------------------------------------------------------------
    # 7. Extraction d'entites
    # ------------------------------------------------------------------
    def extract_entities(self, tokens: list[str], kb) -> list[str]:
        """Identifie les tokens correspondant a des concepts du graphe.

        `tokens` = tokens BRUTS (sortie de tokenize). Strategie en cascade :
          0. matching n-grammes : concepts multi-mots joints par '_'
             (ex : 'jeux olympiques' -> 'jeux_olympiques',
                   'coupe du monde'  -> 'coupe_du_monde')
          1. matching direct   : token == concept
          2. matching par stem : stem(token) == stem(concept)
             (ex : 'proteine' / 'proteines', 'entrainements' / 'entrainement')
          3. matching approche : distance de Levenshtein <= seuil
             (seuil 1 si len < 6, sinon 2 ; ex : 'footbal' -> 'football')
        Retourne les concepts uniques dans l'ordre d'apparition.
        """
        concepts = kb.all_concepts()
        # Pre-calcul des racines des concepts (une seule fois par appel)
        stems_map: dict[str, str] = {}
        for c in concepts:
            stems_map.setdefault(self.stemmer.stem(c), c)

        entities: list[str] = []
        seen: set[str] = set()

        def _add(concept: str) -> None:
            if concept not in seen:
                entities.append(concept)
                seen.add(concept)

        # 0) Matching n-grammes (trigrammes puis bigrammes) pour les
        #    concepts multi-mots serialises avec '_' dans le graphe.
        consumed: set[int] = set()
        for n in (3, 2):
            for i in range(len(tokens) - n + 1):
                if any(j in consumed for j in range(i, i + n)):
                    continue
                ngram = "_".join(tokens[i:i + n])
                if ngram in kb.graph:
                    _add(ngram)
                    consumed.update(range(i, i + n))

        for idx, token in enumerate(tokens):
            if idx in consumed or token in self.stopwords:
                continue

            # 1) direct
            if token in kb.graph:
                _add(token)
                continue

            # 2) par racine
            t_stem = self.stemmer.stem(token)
            if t_stem in stems_map:
                _add(stems_map[t_stem])
                continue

            # 3) par proximite (Levenshtein)
            if len(token) < 4:
                continue  # trop court : risque de faux positifs
            seuil = 1 if len(token) < 6 else 2
            best_concept, best_dist = None, seuil + 1
            for concept in concepts:
                # Un concept court (< 5 caracteres, ex. "foot", "hand")
                # n'est jamais une cible fiable pour le rapprochement flou :
                # a distance 1, il collisionne avec des mots francais
                # courants sans rapport (ex. "font" -> "foot"). Ces
                # concepts restent bien sur accessibles par correspondance
                # exacte ou par racine (etapes 1 et 2 ci-dessus).
                if len(concept) < 5:
                    continue
                # borne rapide : difference de longueur > seuil => inutile
                if abs(len(concept) - len(token)) > seuil:
                    continue
                d = self.levenshtein(token, concept)
                if d < best_dist:
                    best_concept, best_dist = concept, d
                    if d == 0:
                        break
            if best_concept:
                _add(best_concept)

        return entities
