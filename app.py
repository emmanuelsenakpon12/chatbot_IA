"""app.py - Point d'entree WSGI pour le deploiement (Render / gunicorn).

Expose l'objet Flask `app` attendu par gunicorn ("gunicorn app:app").
Usage local equivalent : python ui.py --web
"""

import os

from main import ChatBot
from ui import create_app

bot = ChatBot(os.path.join(os.path.dirname(__file__), "data/"))
app = create_app(bot)
