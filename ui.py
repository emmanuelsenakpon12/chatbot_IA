"""
ui.py - Interfaces utilisateur du ChatBot IA (Etape 5)

- run_cli(bot)   : interface en ligne de commande avec feedback 1-5
- create_app(bot): interface web Flask (BONUS, optionnelle)
                   lancement : python ui.py --web
"""


HISTORIQUE_MAX = 5  # nombre de messages recents conserves pour les relances


def run_cli(bot) -> None:
    """Interface en ligne de commande avec boucle de feedback."""
    print("=" * 56)
    print("  ChatBot IA - Sport, musculation & nutrition")
    print("  Tapez 'quit' pour quitter")
    print("=" * 56)
    historique: list[str] = []
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

        response = bot.answer(user_input, historique=historique)
        print(f"Bot : {response}")
        historique.append(user_input)
        del historique[:-HISTORIQUE_MAX]

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
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>ChatBot IA - Sport</title>
<link rel='icon' href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='16' fill='%233b6fd6'/%3E%3Ctext x='16' y='21' font-family='Arial,sans-serif' font-size='16' font-weight='700' fill='white' text-anchor='middle'%3EC%3C/text%3E%3C/svg%3E">
<link rel='preconnect' href='https://fonts.googleapis.com'>
<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>
<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap' rel='stylesheet'>
<style>
 :root{
   --blue-50:#eef4ff;--blue-100:#dbe7fe;--blue-200:#bfd7fe;
   --blue-500:#3b6fd6;--blue-600:#2f5fc4;--blue-700:#254aa0;
   --bg:#f6f8fc;--bg-sidebar:#eef2fa;--surface:#ffffff;
   --border:#e1e7f2;--text:#1c2230;--text-muted:#68708a;
   --radius-lg:16px;--radius-md:12px;--radius-sm:8px;
   --shadow-sm:0 1px 2px rgba(20,30,60,.06);--shadow-md:0 4px 16px rgba(20,30,60,.08);
 }
 *{box-sizing:border-box}
 html,body{height:100%;margin:0}
 body{font-family:'Inter',ui-sans-serif,system-ui,-apple-system,'Segoe UI',sans-serif;
      background:var(--bg);color:var(--text)}
 .app{display:flex;height:100vh;overflow:hidden}
 .sidebar{width:220px;flex-shrink:0;display:flex;flex-direction:column;
          background:var(--bg-sidebar);border-right:1px solid var(--border);
          padding:1rem .75rem;gap:.5rem;overflow-y:auto}
 .brand{display:flex;align-items:center;gap:.5rem;font-weight:600;font-size:1rem;
        padding:.25rem .25rem .75rem}
 .brand-dot{width:10px;height:10px;border-radius:50%;background:var(--blue-500);
            box-shadow:0 0 0 4px var(--blue-100)}
 .new-chat-btn{display:flex;align-items:center;justify-content:center;gap:.4rem;
               background:var(--blue-500);color:#fff;border:none;border-radius:var(--radius-md);
               padding:.65rem .8rem;font:inherit;font-weight:600;font-size:.9rem;cursor:pointer;
               box-shadow:var(--shadow-sm);margin-bottom:.6rem;width:100%;
               transition:background .15s ease, transform .1s ease}
 .new-chat-btn:hover{background:var(--blue-600)}
 .new-chat-btn:active{transform:scale(.98)}
 .thread-section-label{font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;
                        color:var(--text-muted);padding:.4rem .4rem .3rem}
 .thread-list{border:none;overflow-y:auto;flex:1;display:flex;
              flex-direction:column;gap:.1rem}
 .thread-item{display:flex;align-items:center;justify-content:space-between;gap:.4rem;
              padding:.55rem .6rem;cursor:pointer;border-radius:var(--radius-sm);
              font-size:.87rem;color:var(--text);transition:background .12s ease}
 .thread-item:hover{background:var(--blue-50)}
 .thread-item.active{background:var(--blue-100);color:var(--blue-700);font-weight:600}
 .thread-title{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
 .thread-del{background:none;border:none;color:var(--text-muted);cursor:pointer;
             padding:.1rem .3rem;font-size:.9rem;border-radius:6px;opacity:0;
             transition:opacity .1s ease, color .1s ease, background .1s ease}
 .thread-item:hover .thread-del{opacity:1}
 .thread-del:hover{color:#c0362c;background:#fde8e6}
 .chat-panel{flex:1;display:flex;flex-direction:column;min-width:0;background:var(--surface)}
 .chat-header{padding:.9rem 1.5rem;border-bottom:1px solid var(--border)}
 .chat-header h1{font-size:.95rem;font-weight:600;margin:0}
 .log{flex:1;overflow-y:auto;padding:1.25rem 1.5rem;background:#fafafa}
 .log-inner{max-width:720px;margin:0 auto;display:flex;flex-direction:column;gap:1rem}
 .welcome{max-width:560px;margin:3rem auto;text-align:center;
          display:flex;flex-direction:column;align-items:center;gap:1rem}
 .welcome-avatar{width:56px;height:56px;border-radius:50%;background:var(--blue-100);
                  display:flex;align-items:center;justify-content:center;font-size:1.6rem}
 .welcome h2{font-size:1.3rem;margin:0;font-weight:600}
 .suggestions{display:flex;flex-wrap:wrap;gap:.5rem;justify-content:center;margin-top:.5rem}
 .chip{background:var(--blue-50);border:1px solid var(--blue-100);color:var(--blue-700);
       border-radius:999px;padding:.5rem .9rem;font:inherit;font-size:.83rem;cursor:pointer;
       transition:background .12s ease}
 .chip:hover{background:var(--blue-100)}
 .log::-webkit-scrollbar,.thread-list::-webkit-scrollbar{width:8px}
 .log::-webkit-scrollbar-thumb,.thread-list::-webkit-scrollbar-thumb{
   background:var(--blue-200);border-radius:8px}
 .log::-webkit-scrollbar-track,.thread-list::-webkit-scrollbar-track{background:transparent}
 .sidebar-toggle{display:none;position:fixed;top:.75rem;left:.75rem;z-index:20;
                 background:var(--surface);border:1px solid var(--border);
                 border-radius:var(--radius-sm);width:36px;height:36px;cursor:pointer;
                 font-size:1rem;box-shadow:var(--shadow-sm);align-items:center;
                 justify-content:center}
 @media (max-width:760px){
   .sidebar{position:fixed;inset:0 auto 0 0;z-index:15;transform:translateX(-100%);
            transition:transform .2s ease;box-shadow:var(--shadow-md)}
   .sidebar.open{transform:translateX(0)}
   .sidebar-toggle{display:flex}
   .chat-header{padding-left:3.2rem}
 }
 .msg{display:flex;gap:.65rem;max-width:100%}
 .msg.user{justify-content:flex-end}
 .msg-avatar{width:28px;height:28px;border-radius:50%;flex-shrink:0;
             display:flex;align-items:center;justify-content:center;font-size:.85rem;
             background:var(--blue-500);color:#fff;font-weight:600}
 .msg-body{max-width:74%}
 .msg.user .msg-body{background:var(--blue-500);color:#fff;padding:.65rem .95rem;
                      border-radius:18px 18px 4px 18px}
 .msg.bot .msg-body{background:transparent;color:var(--text);padding:.15rem 0;max-width:100%}
 .msg-text{white-space:pre-wrap;line-height:1.5;font-size:.93rem}
 .fb{display:flex;align-items:center;gap:.3rem;margin-top:.4rem;
     font-size:.78rem;color:var(--text-muted)}
 .fb-label{margin-right:.25rem}
 .fb-btn{width:24px;height:24px;border-radius:50%;border:1px solid var(--border);
         background:var(--surface);cursor:pointer;font-size:.72rem;color:var(--text-muted);
         display:flex;align-items:center;justify-content:center;
         transition:all .12s ease}
 .fb-btn:hover{border-color:var(--blue-500);color:var(--blue-600);background:var(--blue-50)}
 .fb-done{color:var(--blue-600);font-weight:500}
 .composer{border-top:1px solid var(--border);padding:1rem 1.5rem 1.25rem}
 .composer-form{max-width:720px;margin:0 auto;display:flex;align-items:center;gap:.5rem;
                background:var(--bg);border:1px solid var(--border);border-radius:26px;
                padding:.4rem .5rem .4rem 1.1rem;
                transition:border-color .12s ease, box-shadow .12s ease}
 .composer-form:focus-within{border-color:var(--blue-500);box-shadow:0 0 0 3px var(--blue-100)}
 .composer-form input{flex:1;border:none;background:transparent;font:inherit;font-size:.93rem;
                       padding:.5rem 0;outline:none;color:var(--text)}
 .send-btn{width:36px;height:36px;border-radius:50%;border:none;background:var(--blue-500);
           color:#fff;font-size:1rem;cursor:pointer;flex-shrink:0;
           display:flex;align-items:center;justify-content:center;
           transition:background .12s ease, transform .1s ease}
 .send-btn:hover{background:var(--blue-600)}
 .send-btn:active{transform:scale(.94)}
 .composer-hint{max-width:720px;margin:.5rem auto 0;text-align:center;font-size:.72rem;
                color:var(--text-muted)}
</style></head><body>
<div class='app'>
<aside class='sidebar' id='sidebar'>
 <div class='brand'><span class='brand-dot'></span>ChatBot IA</div>
 <button id='newThread' class='new-chat-btn' type='button'>+ Nouvelle discussion</button>
 <div class='thread-section-label'>Discussions</div>
 <div id='threads' class='thread-list'></div>
</aside>
<button id='sidebarToggle' class='sidebar-toggle' type='button' aria-label='Menu'>&#9776;</button>
<main class='chat-panel'>
<header class='chat-header'><h1 id='chatTitle'>Nouvelle discussion</h1></header>
<div id='log' class='log'></div>
<div class='composer'>
<form id='chat' class='composer-form'>
 <input type='text' id='q' placeholder='Envoyer un message...' autocomplete='off' autofocus>
 <button type='submit' class='send-btn' aria-label='Envoyer'>&#8593;</button>
</form>
<p class='composer-hint'>Sport, musculation &amp; nutrition</p>
</div>
</main>
</div>
<script>
const log=document.getElementById('log');
const chatTitle=document.getElementById('chatTitle');
const threadList=document.getElementById('threads');
const sidebar=document.getElementById('sidebar');
const esc=s=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',
  '"':'&quot;',"'":'&#39;'}[c]));
const genId=()=>'t'+Date.now()+Math.random().toString(36).slice(2,7);

let threads=[];
let currentId=null;

function newEmptyThread(){
  return {id:genId(), title:'Nouvelle discussion', messages:[]};
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
  sidebar.classList.remove('open');
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
  chatTitle.textContent=thread.title;
  if(!thread.messages.length){
    log.innerHTML=`<div class='welcome'>
      <div class='welcome-avatar'>🏋️</div>
      <h2>Comment puis-je vous aider aujourd'hui ?</h2>
      <div class='suggestions'>
        <button type='button' class='chip' data-q='Comment prendre du muscle rapidement ?'>Comment prendre du muscle rapidement ?</button>
        <button type='button' class='chip' data-q='Que manger avant le sport ?'>Que manger avant le sport ?</button>
        <button type='button' class='chip' data-q='Comment bien recuperer apres un entrainement ?'>Comment bien recuperer apres un entrainement ?</button>
      </div>
    </div>`;
    log.querySelectorAll('.chip').forEach(c=>{
      c.onclick=()=>{
        document.getElementById('q').value=c.dataset.q;
        ask();
      };
    });
    return;
  }
  const inner=document.createElement('div');
  inner.className='log-inner';
  log.appendChild(inner);
  thread.messages.forEach(m=>{
    if(m.type==='u'){
      inner.insertAdjacentHTML('beforeend',
        `<div class='msg user'><div class='msg-body'><div class='msg-text'>${esc(m.text)}</div></div></div>`);
      return;
    }
    inner.insertAdjacentHTML('beforeend',
      `<div class='msg bot'><div class='msg-avatar'>B</div><div class='msg-body'>
         <div class='msg-text'>${esc(m.text)}</div>
         <div class='fb' id='${m.id}'></div>
       </div></div>`);
    const zone=document.getElementById(m.id);
    if(m.noFeedback)return;
    if(m.feedback){
      zone.innerHTML=`<span class='fb-done'>Merci, feedback enregistre !</span>`;
      return;
    }
    zone.innerHTML=`<span class='fb-label'>Utile ?</span>`+
      [1,2,3,4,5].map(n=>`<button type='button' class='fb-btn' data-score='${n}'>${n}</button>`).join('');
    zone.querySelectorAll('.fb-btn').forEach(b=>{
      b.onclick=async()=>{
        const score=parseInt(b.dataset.score,10);
        await fetch('/feedback',{method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({question:m.question,answer:m.text,score})});
        m.feedback=score;
        saveThreads();
        zone.innerHTML=`<span class='fb-done'>Merci, feedback enregistre !</span>`;
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
  if(thread.title==='Nouvelle discussion' && userMsgCount===1){
    thread.title = question.length>30 ? question.slice(0,30)+'…' : question;
  }
  saveThreads();
  renderSidebar();
  renderLog();
  try{
    // Historique : les questions precedentes de CE fil, pour que le
    // serveur (sans etat) puisse resoudre une relance sans sujet propre
    // ("pourquoi ?") en retombant sur le sujet de la question precedente.
    const history=thread.messages
      .filter(m=>m.type==='u')
      .slice(-6,-1)
      .map(m=>m.text);
    const r=await fetch('/ask',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({question,history})});
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
  sidebar.classList.remove('open');
});

document.getElementById('sidebarToggle').addEventListener('click',()=>{
  sidebar.classList.toggle('open');
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
        history = data.get("history", "")
        historique = [h for h in history if isinstance(h, str)] \
            if isinstance(history, list) else None
        return jsonify({"answer": bot.answer(question, historique=historique)})

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
