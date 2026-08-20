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
 body{font-family:sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;
      display:flex;gap:1rem}
 .sidebar{width:220px;flex-shrink:0;display:flex;flex-direction:column}
 .sidebar h3{margin:.2rem 0 .6rem 0;font-size:1rem}
 #newThread{padding:.5rem;margin-bottom:.6rem;cursor:pointer}
 #threads{border:1px solid #ccc;border-radius:8px;overflow-y:auto;
          flex:1;height:420px}
 .thread-item{display:flex;align-items:center;justify-content:space-between;
              padding:.5rem .6rem;cursor:pointer;border-bottom:1px solid #eee;
              font-size:.9rem}
 .thread-item:hover{background:#f0f0f0}
 .thread-item.active{background:#e3ecfb;font-weight:bold}
 .thread-title{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
 .thread-del{background:none;border:none;color:#999;cursor:pointer;
             padding:0 .2rem;font-size:1rem}
 .thread-del:hover{color:#c00}
 .main{flex:1;min-width:0}
 h2{font-size:1.15rem}
 #log{border:1px solid #ccc;border-radius:8px;padding:1rem;height:340px;
      overflow-y:auto;margin-bottom:1rem;background:#fafafa}
 .u{color:#0b57d0;margin:.4rem 0}.b{color:#222;margin:.4rem 0}
 .fb{font-size:.85rem;color:#666;margin:0 0 .8rem 0}
 .fb button{padding:.1rem .45rem;margin-right:.2rem;cursor:pointer}
 form{display:flex;gap:.5rem}input[type=text]{flex:1;padding:.5rem}
 button{padding:.5rem 1rem}
</style></head><body>
<div class='sidebar'>
 <h3>Fils de conversation</h3>
 <button id='newThread' type='button'>+ Nouvelle conversation</button>
 <div id='threads'></div>
</div>
<div class='main'>
<h2>ChatBot IA - Sport, musculation &amp; nutrition</h2>
<div id='log'></div>
<form id='chat'>
 <input type='text' id='q' placeholder='Votre question...' autocomplete='off' autofocus>
 <button type='submit'>Envoyer</button>
</form>
</div>
<script>
const log=document.getElementById('log');
const threadList=document.getElementById('threads');
const esc=s=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',
  '"':'&quot;',"'":'&#39;'}[c]));
const genId=()=>'t'+Date.now()+Math.random().toString(36).slice(2,7);

let threads=[];
let currentId=null;

function newEmptyThread(){
  return {id:genId(), title:'Nouvelle conversation', messages:[]};
}

function loadThreads(){
  try{
    threads=JSON.parse(localStorage.getItem('chatbot_threads')||'[]');
  }catch(e){threads=[];}
  currentId=localStorage.getItem('chatbot_current');
  if(!Array.isArray(threads)||!threads.length){
    const t=newEmptyThread();
    threads=[t];
    currentId=t.id;
  }
  if(!threads.some(t=>t.id===currentId)){
    currentId=threads[0].id;
  }
}

function saveThreads(){
  localStorage.setItem('chatbot_threads', JSON.stringify(threads));
  localStorage.setItem('chatbot_current', currentId);
}

function getCurrentThread(){
  return threads.find(t=>t.id===currentId);
}

function switchThread(id){
  currentId=id;
  saveThreads();
  renderSidebar();
  renderLog();
}

function deleteThread(id){
  const idx=threads.findIndex(t=>t.id===id);
  if(idx===-1)return;
  threads.splice(idx,1);
  if(!threads.length){
    threads=[newEmptyThread()];
  }
  if(currentId===id){
    currentId=threads[0].id;
  }
  saveThreads();
  renderSidebar();
  renderLog();
}

function renameThread(id){
  const t=threads.find(x=>x.id===id);
  if(!t)return;
  const name=prompt('Renommer la conversation :', t.title);
  if(name && name.trim()){
    t.title=name.trim();
    saveThreads();
    renderSidebar();
  }
}

function renderSidebar(){
  threadList.innerHTML='';
  threads.forEach(t=>{
    const item=document.createElement('div');
    item.className='thread-item'+(t.id===currentId?' active':'');
    const title=document.createElement('span');
    title.className='thread-title';
    title.textContent=t.title;
    title.onclick=()=>switchThread(t.id);
    const del=document.createElement('button');
    del.className='thread-del';
    del.type='button';
    del.title='Supprimer';
    del.textContent='\\u00d7';
    del.onclick=ev=>{ev.stopPropagation();deleteThread(t.id);};
    item.appendChild(title);
    item.appendChild(del);
    item.ondblclick=()=>renameThread(t.id);
    threadList.appendChild(item);
  });
}

function renderLog(){
  log.innerHTML='';
  const thread=getCurrentThread();
  if(!thread)return;
  thread.messages.forEach(m=>{
    if(m.type==='u'){
      log.insertAdjacentHTML('beforeend',
        `<p class='u'><b>Vous :</b> ${esc(m.text)}</p>`);
      return;
    }
    log.insertAdjacentHTML('beforeend',
      `<p class='b'><b>Bot :</b> ${esc(m.text)}</p>`);
    if(m.noFeedback)return;
    if(m.feedback){
      log.insertAdjacentHTML('beforeend',
        `<p class='fb' id='${m.id}'>Merci, feedback enregistre !</p>`);
      return;
    }
    log.insertAdjacentHTML('beforeend',
      `<p class='fb' id='${m.id}'>Noter cette reponse :
       ${[1,2,3,4,5].map(n=>`<button type='button' data-score='${n}'>${n}</button>`).join('')}</p>`);
    const zone=document.getElementById(m.id);
    zone.querySelectorAll('button').forEach(b=>{
      b.onclick=async()=>{
        const score=parseInt(b.dataset.score,10);
        await fetch('/feedback',{method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({question:m.question,answer:m.text,score})});
        m.feedback=score;
        saveThreads();
        zone.textContent='Merci, feedback enregistre !';
      };
    });
  });
  log.scrollTop=log.scrollHeight;
}

async function ask(){
  const input=document.getElementById('q');
  const question=input.value.trim();
  if(!question)return;
  input.value='';
  const thread=getCurrentThread();
  thread.messages.push({type:'u', text:question});
  const userMsgCount=thread.messages.filter(m=>m.type==='u').length;
  if(thread.title==='Nouvelle conversation' && userMsgCount===1){
    thread.title = question.length>30 ? question.slice(0,30)+'…' : question;
  }
  saveThreads();
  renderSidebar();
  renderLog();
  try{
    const r=await fetch('/ask',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({question})});
    const d=await r.json();
    thread.messages.push({type:'b', text:d.answer, question, id:genId(), feedback:null});
  }catch(e){
    thread.messages.push({type:'b', text:'Erreur de connexion au serveur.',
      question, id:genId(), noFeedback:true});
  }
  saveThreads();
  renderLog();
}

document.getElementById('newThread').addEventListener('click',()=>{
  const t=newEmptyThread();
  threads.unshift(t);
  currentId=t.id;
  saveThreads();
  renderSidebar();
  renderLog();
});

// IMPORTANT : ask() est async donc retourne une Promise (toujours truthy).
// Un 'return ask()' ne bloquerait PAS l'envoi natif du formulaire et la page
// se rechargerait. On annule donc explicitement l'evenement.
document.getElementById('chat').addEventListener('submit',ev=>{
  ev.preventDefault();
  ask();
});

loadThreads();
renderSidebar();
renderLog();
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
