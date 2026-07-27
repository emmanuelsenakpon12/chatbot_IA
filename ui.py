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
<link rel='icon' href='data:,'>
<style>
 body{font-family:sans-serif;max-width:660px;margin:2rem auto;padding:0 1rem}
 #log{border:1px solid #ccc;border-radius:8px;padding:1rem;height:340px;
      overflow-y:auto;margin-bottom:1rem;background:#fafafa}
 .u{color:#0b57d0;margin:.4rem 0}.b{color:#222;margin:.4rem 0}
 .fb{font-size:.85rem;color:#666;margin:0 0 .8rem 0}
 .fb button{padding:.1rem .45rem;margin-right:.2rem;cursor:pointer}
 form{display:flex;gap:.5rem}input[type=text]{flex:1;padding:.5rem}
 button{padding:.5rem 1rem}
</style></head><body>
<h2>ChatBot IA - Sport, musculation &amp; nutrition</h2>
<div id='log'></div>
<form id='chat'>
 <input type='text' id='q' placeholder='Votre question...' autocomplete='off' autofocus>
 <button type='submit'>Envoyer</button>
</form>
<script>
const log=document.getElementById('log');
const esc=s=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',
  '"':'&quot;',"'":'&#39;'}[c]));

async function ask(){
  const input=document.getElementById('q');
  const question=input.value.trim();
  if(!question)return;
  input.value='';
  log.insertAdjacentHTML('beforeend',
    `<p class='u'><b>Vous :</b> ${esc(question)}</p>`);
  log.scrollTop=log.scrollHeight;
  try{
    const r=await fetch('/ask',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({question})});
    const d=await r.json();
    const id='fb'+Date.now();
    log.insertAdjacentHTML('beforeend',
      `<p class='b'><b>Bot :</b> ${esc(d.answer)}</p>
       <p class='fb' id='${id}'>Noter cette reponse :
        ${[1,2,3,4,5].map(n=>`<button type='button'>${n}</button>`).join('')}</p>`);
    const zone=document.getElementById(id);
    zone.querySelectorAll('button').forEach((b,i)=>{
      b.onclick=async()=>{
        await fetch('/feedback',{method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({question,answer:d.answer,score:i+1})});
        zone.textContent='Merci, feedback enregistre !';};
    });
  }catch(e){
    log.insertAdjacentHTML('beforeend',
      `<p class='b'><b>Bot :</b> Erreur de connexion au serveur.</p>`);
  }
  log.scrollTop=log.scrollHeight;
}

// IMPORTANT : ask() est async donc retourne une Promise (toujours truthy).
// Un 'return ask()' ne bloquerait PAS l'envoi natif du formulaire et la page
// se rechargerait. On annule donc explicitement l'evenement.
document.getElementById('chat').addEventListener('submit',ev=>{
  ev.preventDefault();
  ask();
});
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
