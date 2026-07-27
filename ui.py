"""
ui.py - Interfaces utilisateur du ChatBot IA (Etape 5)

- run_cli(bot)   : interface en ligne de commande avec feedback 1-5
- create_app(bot): interface web Flask (BONUS, optionnelle)
                   lancement : python ui.py --web
"""


def run_cli(bot) -> None:
    """Interface en ligne de commande avec boucle de feedback."""
    print("=" * 56)
    print("  ChatBot IA - Sport, musculation & nutrition")
    print("  Tapez 'quit' pour quitter")
    print("=" * 56)
    while True:
        try:
            user_input = input("\nVous : ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBot : Au revoir, et bon entrainement !")
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "quitter", "exit"):
            print("Bot : Au revoir, et bon entrainement !")
            break

        response = bot.answer(user_input)
        print(f"Bot : {response}")

        # Feedback optionnel (Entree pour passer)
        try:
            fb = input("Note (1-5, Entree pour passer) : ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if fb.isdigit() and 1 <= int(fb) <= 5:
            bot.give_feedback(user_input, response, int(fb))
            print("Merci, feedback enregistre !")


# ----------------------------------------------------------------------
# BONUS : interface web Flask
# ----------------------------------------------------------------------
def create_app(bot):
    """Cree l'application Flask (bonus web du sujet).

    Endpoints :
      GET  /            : mini page de chat HTML
      POST /ask         : {"question": "..."} -> {"answer": "..."}
      POST /feedback    : {"question", "answer", "score"} -> {"ok": true}
    """
    from flask import Flask, jsonify, request

    app = Flask(__name__)

    PAGE = """<!doctype html><html lang='fr'><head><meta charset='utf-8'>
<title>ChatBot IA - Sport</title>
<style>
 body{font-family:sans-serif;max-width:640px;margin:2rem auto;padding:0 1rem}
 #log{border:1px solid #ccc;border-radius:8px;padding:1rem;height:340px;
      overflow-y:auto;margin-bottom:1rem;background:#fafafa}
 .u{color:#0b57d0;margin:.4rem 0}.b{color:#222;margin:.4rem 0}
 form{display:flex;gap:.5rem}input[type=text]{flex:1;padding:.5rem}
 button{padding:.5rem 1rem}
</style></head><body>
<h2>ChatBot IA - Sport, musculation &amp; nutrition</h2>
<div id='log'></div>
<form onsubmit='return ask()'>
 <input type='text' id='q' placeholder='Votre question...' autofocus>
 <button>Envoyer</button>
</form>
<script>
async function ask(){
 const q=document.getElementById('q');const log=document.getElementById('log');
 const question=q.value.trim();if(!question)return false;
 log.innerHTML+=`<p class='u'><b>Vous :</b> ${question}</p>`;q.value='';
 const r=await fetch('/ask',{method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({question})});
 const d=await r.json();
 log.innerHTML+=`<p class='b'><b>Bot :</b> ${d.answer}</p>`;
 log.scrollTop=log.scrollHeight;return false;}
</script></body></html>"""

    @app.route("/")
    def index():
        return PAGE

    @app.route("/ask", methods=["POST"])
    def ask():
        data = request.get_json(silent=True) or {}
        question = data.get("question", "")
        return jsonify({"answer": bot.answer(question)})

    @app.route("/feedback", methods=["POST"])
    def feedback():
        data = request.get_json(silent=True) or {}
        try:
            bot.give_feedback(data["question"], data["answer"],
                              int(data["score"]))
        except (KeyError, ValueError):
            return jsonify({"ok": False}), 400
        return jsonify({"ok": True})

    return app


if __name__ == "__main__":
    import sys
    from main import ChatBot
    bot = ChatBot("data/")
    if "--web" in sys.argv:
        create_app(bot).run(debug=False, port=5000)
    else:
        run_cli(bot)
