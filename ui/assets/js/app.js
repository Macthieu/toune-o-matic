/* toune-o-matic UI
   Objectifs:
   - code séparé de index.html (plus propre)
   - rafraîchissement robuste (timeout + pas de blocage)
   - timer "qui défile" visuellement même si l'API répond plus lentement
*/

(function(){
  "use strict";

  // =========================
  // Helpers
  // =========================
  function $(id){ return document.getElementById(id); }

  function pretty(text){
    try { return JSON.stringify(JSON.parse(text), null, 2); }
    catch { return text; }
  }

  function fmtTime(sec){
    const s = Math.max(0, Number(sec) || 0);
    const m = Math.floor(s/60);
    const r = Math.floor(s%60);
    return `${m}:${String(r).padStart(2,'0')}`;
  }

  function setDot(id, on){
    const el = $(id);
    if(!el) return;
    el.classList.remove("on","off");
    el.classList.add(on ? "on" : "off");
  }

  // =========================
  // API key (localStorage)
  // =========================
  const KEY_LS = "toune_api_key";

  function getKey(){
    return (($("apiKey")?.value) || localStorage.getItem(KEY_LS) || "").trim();
  }

  function saveKey(withPing=false){
    const k = getKey();
    if(k) localStorage.setItem(KEY_LS, k);
    if(withPing) refreshAll();
  }

  function clearKey(){
    localStorage.removeItem(KEY_LS);
    if($("apiKey")) $("apiKey").value = "";
  }

  // Expose pour les onclick="" (si tu les gardes)
  window.saveKey  = saveKey;
  window.clearKey = clearKey;

  // =========================
  // fetch() robuste (timeout)
  // =========================
  async function apiFetch(url, opts={}, includeKey=true, timeoutMs=2500){
    const headers = new Headers(opts.headers || {});
    if(includeKey && url.startsWith("/api") && url !== "/api/health"){
      const k = getKey();
      if(k) headers.set("X-API-Key", k);
    }

    const controller = new AbortController();
    const timer = setTimeout(()=>controller.abort(), timeoutMs);

    try{
      return await fetch(url, { ...opts, headers, signal: controller.signal });
    }finally{
      clearTimeout(timer);
    }
  }

  async function getText(url, outId, includeKey=true){
    const out = $(outId);
    if(out) out.textContent = "…";
    try{
      const r = await apiFetch(url, {}, includeKey);
      const t = await r.text();
      if(out) out.textContent = `${r.status} ${r.statusText}\n\n${pretty(t)}`;
    }catch(e){
      if(out) out.textContent = "Erreur: " + (e?.name === "AbortError" ? "timeout" : e);
    }
  }

  async function postJson(url, obj, outId, after){
    const out = $(outId);
    if(out) out.textContent = "…";
    try{
      const r = await apiFetch(url, {
        method: "POST",
        headers: {"Content-Type":"application/json"},
        body: JSON.stringify(obj)
      }, true);
      const t = await r.text();
      if(out) out.textContent = `${r.status} ${r.statusText}\n\n${pretty(t)}`;
      if(after) after();
    }catch(e){
      if(out) out.textContent = "Erreur: " + (e?.name === "AbortError" ? "timeout" : e);
    }
  }

  // Expose pour onclick=""
  window.getText  = getText;
  window.postJson = postJson;

  // =========================
  // Actions
  // =========================
  function cmd(action){
    action = (action || "").trim().toLowerCase();
    if(!action) return;
    postJson("/api/cmd", {action}, "out_queue", () => refreshAll()); // out_queue volontaire
  }

  function setMode(mode){
    postJson("/api/mode", {mode}, "out_queue", () => refreshAll());
  }

  function queuePlay(pos){
    postJson("/api/queue/play", {pos}, "out_queue", () => refreshAll());
  }

  window.cmd = cmd;
  window.setMode = setMode;
  window.queuePlay = queuePlay;

  // =========================
  // Now Playing (UI + ticking local)
  // =========================
  function computeMode(outputs){
    const dac  = outputs && outputs["DAC strict"] && outputs["DAC strict"].outputenabled === "1";
    const snap = outputs && outputs["snapcast"]   && outputs["snapcast"].outputenabled   === "1";
    if(dac && snap) return "both";
    if(dac) return "dac";
    if(snap) return "snap";
    return "none";
  }

  // snapshot pour animer le temps même entre 2 polls
  const NP = {
    state: "—",
    elapsed: 0,
    duration: 0,
    updatedAtMs: 0
  };

  function renderElapsed(elapsed, duration){
    if($("np_elapsed")) $("np_elapsed").textContent = fmtTime(elapsed);
    if($("np_duration")) $("np_duration").textContent = duration ? fmtTime(duration) : "—";

    const prog = $("np_prog");
    if(prog){
      if(duration > 0){
        prog.max = 100;
        prog.value = Math.max(0, Math.min(100, (elapsed/duration)*100));
      }else{
        prog.value = 0;
      }
    }
  }

  function updateNowPlayingUI(data){
    const st   = data.status  || {};
    const song = data.song    || {};
    const outs = data.outputs || {};

    const state = st.state || "—";
    NP.state = state;

    $("np_state").textContent = state;
    setDot("dot_play", state === "play");

    $("np_vol").textContent     = st.volume  ?? "—";
    $("np_bitrate").textContent = st.bitrate ?? "—";
    $("np_audio").textContent   = st.audio   ?? "—";

    const title  = song.title || (song.file ? song.file.split("/").pop() : "—");
    const artist = song.artist || "—";
    const album  = song.album  || "—";
    $("np_title").textContent = title;
    $("np_artist_album").textContent = `${artist} • ${album}`;

    const elapsed  = Number(st.elapsed || 0);
    const duration = Number(st.duration || song.duration || 0);

    NP.elapsed = elapsed;
    NP.duration = duration;
    NP.updatedAtMs = Date.now();

    renderElapsed(elapsed, duration);

    const dacOn  = outs["DAC strict"] && outs["DAC strict"].outputenabled === "1";
    const snapOn = outs["snapcast"]   && outs["snapcast"].outputenabled   === "1";
    setDot("dot_dac",  !!dacOn);
    setDot("dot_snap", !!snapOn);
    $("np_mode").textContent = computeMode(outs);
  }

  function tickNowPlaying(){
    // Si on joue, on avance visuellement le temps depuis le dernier status reçu
    if(NP.state !== "play") return;
    if(!NP.updatedAtMs) return;

    const dt = (Date.now() - NP.updatedAtMs) / 1000;
    const duration = Number(NP.duration || 0);
    let elapsed = Number(NP.elapsed || 0) + dt;

    if(duration > 0) elapsed = Math.min(elapsed, duration);
    renderElapsed(elapsed, duration);
  }

  // tick rapide pour que le temps "défile"
  setInterval(tickNowPlaying, 250);

  // =========================
  // Poll status (robuste)
  // =========================
  let _statusLoopHandle = null;
  let _statusBusy = false;

  async function getStatusUI(){
    if(_statusBusy) return;
    _statusBusy = true;
    try{
      const r = await apiFetch("/api/status", {}, true, 2500);
      const t = await r.text();
      if(!r.ok) return;
      try{ updateNowPlayingUI(JSON.parse(t)); } catch {}
    }catch{
      // silencieux: on ne veut pas "geler" l'UI
    }finally{
      _statusBusy = false;
    }
  }

  async function getStatusDebug(){
    const out = $("out_status");
    if(out) out.textContent = "…";
    try{
      const r = await apiFetch("/api/status", {}, true, 3500);
      const t = await r.text();
      if(out) out.textContent = `${r.status} ${r.statusText}\n\n${pretty(t)}`;
      if(!r.ok) return;
      try{ updateNowPlayingUI(JSON.parse(t)); } catch {}
    }catch(e){
      if(out) out.textContent = "Erreur: " + (e?.name === "AbortError" ? "timeout" : e);
    }
  }

  function startStatusLoop(){
    stopStatusLoop();

    const loop = async ()=>{
      await getStatusUI();
      _statusLoopHandle = setTimeout(loop, 1000);
    };

    loop();
  }

  function stopStatusLoop(){
    if(_statusLoopHandle){
      clearTimeout(_statusLoopHandle);
      _statusLoopHandle = null;
    }
  }

  document.addEventListener("visibilitychange", ()=>{
    if(document.hidden) stopStatusLoop();
    else{
      startStatusLoop();
      getStatusUI();
    }
  });

  // expose pour bouton "↻"
  window.refreshAll = refreshAll;

  // =========================
  // Queue
  // =========================
  async function getQueue(){
    await getText("/api/queue", "out_queue");
  }
  window.getQueue = getQueue;

  // =========================
  // Browse + Add
  // =========================
  let CURRENT_PATH = "";

  function browseGo(p){
    CURRENT_PATH = (p || "").trim();
    if($("browse_path")) $("browse_path").value = CURRENT_PATH;
    browseReload();
  }

  function browseUp(){
    const p = (CURRENT_PATH || "").trim();
    if(!p){ browseGo(""); return; }
    const parts = p.split("/").filter(Boolean);
    parts.pop();
    browseGo(parts.join("/"));
  }

  async function browseReload(){
    const out  = $("out_browse");
    const list = $("browse_list");
    if(out) out.textContent = "…";
    if(list) list.innerHTML = "";

    const qs = new URLSearchParams();
    if(CURRENT_PATH) qs.set("path", CURRENT_PATH);

    try{
      const r = await apiFetch("/api/browse?" + qs.toString(), {}, true, 3500);
      const t = await r.text();
      if(out) out.textContent = `${r.status} ${r.statusText}\n\n${pretty(t)}`;

      if(!r.ok) return;
      let data = {};
      try{ data = JSON.parse(t); } catch { return; }
      renderBrowse(data.items || []);
    }catch(e){
      if(out) out.textContent = "Erreur: " + (e?.name === "AbortError" ? "timeout" : e);
    }
  }

  function renderBrowse(items){
    const list = $("browse_list");
    if(!list) return;

    if(!items.length){
      list.innerHTML = `<div class="rowitem"><div class="grow"><b>(vide)</b></div></div>`;
      return;
    }

    items.sort((a,b)=>{
      const ta = a.type === "dir" ? 0 : 1;
      const tb = b.type === "dir" ? 0 : 1;
      if(ta !== tb) return ta - tb;
      return (a.path || "").localeCompare(b.path || "");
    });

    for(const it of items){
      const type = it.type || "";
      const path = it.path || "";

      const row = document.createElement("div");
      row.className = "rowitem";

      const icon = document.createElement("div");
      icon.className = "icon";
      icon.textContent = (type === "dir") ? "📁" : "🎵";

      const main = document.createElement("div");
      main.className = "grow";

      const top = document.createElement("div");
      top.className = "mono";
      top.textContent = path;

      const meta = document.createElement("div");
      meta.className = "tag";
      meta.textContent = (type === "dir") ? "dossier" : "fichier";

      main.appendChild(top);
      main.appendChild(meta);

      const actions = document.createElement("div");
      actions.className = "btns";

      if(type === "dir"){
        const b = document.createElement("button");
        b.textContent = "Ouvrir";
        b.onclick = ()=> browseGo(path);
        actions.appendChild(b);
      }else{
        const add = document.createElement("button");
        add.textContent = "Ajouter";
        add.onclick = ()=> addToQueue(path, false);

        const play = document.createElement("button");
        play.className = "primary";
        play.textContent = "Ajouter & jouer";
        play.onclick = ()=> addToQueue(path, true);

        actions.appendChild(add);
        actions.appendChild(play);
      }

      row.appendChild(icon);
      row.appendChild(main);
      row.appendChild(actions);
      list.appendChild(row);
    }
  }

  async function addToQueue(uri, forcePlay){
    const autoPlay = $("autoPlay")?.checked;
    const play = !!(forcePlay || autoPlay);
    await postJson("/api/queue/add", {uri, play}, "out_queue", () => refreshAll());
  }

  window.browseGo = browseGo;
  window.browseUp = browseUp;
  window.browseReload = browseReload;

  // =========================
  // Refresh global (bouton ↻)
  // =========================
  function refreshAll(){
    getStatusDebug();
    getQueue();
    browseReload();
  }

  // =========================
  // Init
  // =========================
  function init(){
    // remplit le champ API key depuis localStorage
    if($("apiKey")) $("apiKey").value = localStorage.getItem(KEY_LS) || "";

    // init browse + status
    browseGo("");
    getStatusUI();
    startStatusLoop();
  }

  if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
