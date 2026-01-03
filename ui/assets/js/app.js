(function() {
    "use strict";
    const $ = (id) => document.getElementById(id);
    const KEY_LS = "toune_api_key";
    
    let currentElapsed = 0, currentDuration = 0, isPlaying = false, timerInterval = null;
    let observer = null, isLoading = false, currentPage = 1, currentView = "artists";
    let navHistory = []; 

    window.selectedPaths = new Set();
    window.isDragging = false; 

    // =========================================
    // SECTION 1: CŒUR (API & UTILS)
    // =========================================
    async function apiFetch(url, method = "GET", body = null) {
        const key = $("apiKey")?.value || localStorage.getItem(KEY_LS) || "secret";
        const headers = { "X-API-Key": key, "Content-Type": "application/json" };
        const opts = { method, headers };
        if (body) opts.body = JSON.stringify(body);
        try { const r = await fetch(url, opts); return await r.json(); } catch(e) { return null; }
    }

    function esc(s) { return s.replace(/'/g, "\\'"); }
    function formatTime(s) { if(isNaN(s)) return "0:00"; return `${Math.floor(s/60)}:${Math.floor(s%60).toString().padStart(2,'0')}`; }

// --- GESTION CONFIGURATION ---

// Charge les réglages au démarrage
async function loadSettings() {
    const d = await apiFetch('/api/settings/');
    if(d && d.ok && d.config) {
        const c = d.config;
        
        // Remplissage Audio
        if($("conf_audio_device")) $("conf_audio_device").value = c.audio.output_device;
        if($("conf_audio_mixer")) $("conf_audio_mixer").value = c.audio.mixer_type;
        if($("conf_audio_dual")) $("conf_audio_dual").checked = c.audio.dual_audio;

        // Remplissage Playback
        if($("conf_pb_buffer")) $("conf_pb_buffer").value = c.playback.buffer_size;
        if($("conf_pb_dsd")) $("conf_pb_dsd").value = c.playback.dsd_mode;

        // Remplissage Système
        if($("conf_sys_name")) $("conf_sys_name").value = c.system.player_name;
    }
}

// Sauvegarde automatique quand on change une valeur
window.saveSetting = async (section, key, value) => {
    // Petit feedback visuel (optionnel)
    console.log(`Saving ${section}.${key} = ${value}`);
    
    await apiFetch('/api/settings/update', 'POST', {
        section: section,
        key: key,
        value: value
    });
};

// Ajouter l'appel à loadSettings() dans l'initialisation à la fin du fichier
// document.addEventListener("DOMContentLoaded", ... loadSettings(); ...);

    // =========================================
    // SECTION 2: NAVIGATION & TOOLBAR
    // =========================================
    window.switchTab = (t) => { 
        document.querySelectorAll(".tab-content,.tab-btn").forEach(e=>e.classList.remove("active")); 
        const btn = document.querySelector(`button[onclick="switchTab('${t}')"]`);
        if(btn) btn.classList.add("active");
        $(`tab-${t}`).classList.add("active");
        if(t==='biblio' && !$("biblio_list").innerHTML) loadArtists(); 
        if(t==='playlists') loadPlaylists(); 
        if(t==='queue') refreshQueue(); 
        if(t==='parametres') loadAudioOutputs(); 
    };

// Dans ui/assets/js/app.js - Remplacer la fonction renderToolbar()

    function renderToolbar() {
        const count = window.selectedPaths.size;
        const ctx = $("biblio_context_hidden")?.innerText || "";
        const isDetail = ['detail_album', 'detail_artist', 'detail_genre', 'folders'].includes(currentView);
        
        // --- NOUVEAU : Barre de recherche ---
        // On affiche la recherche seulement si on est en vue racine (Artistes/Albums)
        const showSearch = !isDetail && (currentView === 'artists' || currentView === 'albums');

        let html = `
        <div class="toolbar-unified">
            <div style="display:flex; gap:5px; flex-wrap:wrap;">
                <button onclick="navHistory=[]; loadArtists()" class="${currentView==='artists'?'primary':''}">Artistes</button>
                <button onclick="navHistory=[]; loadGlobalAlbums()" class="${currentView==='albums'?'primary':''}">Albums</button>
                <button onclick="navHistory=[]; loadGenres()" class="${currentView==='genres'?'primary':''}">Genres</button>
                <button onclick="navHistory=[]; loadFolders('')" class="${currentView==='folders'?'primary':''}">Dossiers</button>
            </div>
            
            ${showSearch ? `
            <div class="search-box">
                <i class="fas fa-search search-icon"></i>
                <input type="text" id="lib_search" placeholder="Filtrer..." oninput="handleSearch(this.value)">
            </div>` : ''}

            <div style="flex-grow:1"></div>

            <div style="display:flex; gap:5px;">
                <button onclick="toggleAllVisible()">✅</button>
                <button onclick="addSelectionToQueue()" ${count===0?'disabled':''} class="primary">Ajouter (${count})</button>
            </div>
        </div>`;

        // Barre de contexte (Bouton Retour)
        if (ctx || navHistory.length > 0 || isDetail) {
            html += `
            <div class="toolbar-unified" style="margin-top:-10px; background:#2c2c2c; border-top:none;">
                <button onclick="goBack()" class="primary">⬅ Retour</button>
                <div style="font-weight:bold; margin-left:10px;">${ctx}</div>
            </div>`;
        }
        return html;
    }

// Gestionnaire de recherche avec petit délai (pour ne pas spammer l'API)
    let searchTimeout;
    window.handleSearch = (val) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            if(currentView === 'artists') { currentPage=1; loadArtists(false, false, val); }
            // Vous pourrez ajouter la recherche d'albums ici plus tard
        }, 300);
    };

    function updateToolbar() { $("biblio_header").innerHTML = renderToolbar(); }

    window.goBack = () => {
        if (navHistory.length > 0) {
            const previous = navHistory.pop();
            currentView = previous.view;
            $("biblio_context_hidden").innerText = previous.title;
            if (previous.view === 'artists') loadArtists(false, true);
            else if (previous.view === 'albums') loadGlobalAlbums(false, true);
            else if (previous.view === 'genres') loadGenres(true);
            else loadArtists(false, true);
            return;
        }
        if (currentView === 'folders') loadArtists(); 
        else loadArtists();
    };

    // =========================================
    // SECTION 3: CHARGEMENT CONTENU (Bibliothèque)
    // =========================================
    function renderGrid(data, append, renderFn) {
        const list = $("biblio_list");
        if(!append) list.className = "list grid-list";
        if(data?.ok && data.items.length) {
            list.insertAdjacentHTML('beforeend', data.items.map(renderFn).join(""));
            setSentinel(data.items.length < 50 ? 'empty' : 'loading');
        } else { setSentinel('empty'); }
        isLoading = false;
    }
    function renderList(data, append, renderFn) {
        const list = $("biblio_list");
        if(!append) list.className = "list";
        if(data?.ok && data.items.length) {
            list.insertAdjacentHTML('beforeend', data.items.map(renderFn).join(""));
            setSentinel(data.items.length < 50 ? 'empty' : 'loading');
        } else { setSentinel('empty'); }
        isLoading = false;
    }

    function setupView(view, skipClear=false) {
        if(!skipClear) {
            currentPage = 1; $("biblio_list").innerHTML = ""; window.scrollTo(0,0); $("biblio_context_hidden").innerText = ""; 
        }
        updateToolbar();
        setupScroll();
    }

    // --- Chargeurs ---
// Remplacer loadArtists par ceci :
    window.loadArtists = async (append=false, isRestoring=false, query="") => {
        if(!append && !isRestoring) { navHistory = []; setupView('artists'); }
        if(isRestoring) { setupView('artists', true); }
        
        // On envoie le paramètre ?q=... à l'API
        const url = `/api/content/browse/artists?page=${currentPage}&limit=50&q=${encodeURIComponent(query)}`;
        const d = await apiFetch(url);
        
        renderGrid(d, append, i => `<div class="grid-item" onclick="openArtist('${esc(i.artist)}')"><img class="grid-img" src="/api/content/artist_image?name=${encodeURIComponent(i.artist)}" onerror="this.src='assets/img/no_cover.png'"><div><b>${i.artist}</b></div></div>`);
        
        // Petit hack pour garder le focus dans le champ de recherche après rechargement
        if(query && $("lib_search")) { $("lib_search").value = query; $("lib_search").focus(); }
    };

    window.openArtist = async (artist) => {
        navHistory.push({view: 'artists', title: 'Artistes'}); 
        currentView = 'detail_artist';
        $("biblio_context_hidden").innerText = artist;
        updateToolbar();
        $("biblio_list").innerHTML = ""; window.scrollTo(0,0);
        const d = await apiFetch(`/api/content/browse/albums?artist=${encodeURIComponent(artist)}`);
        renderGrid(d, false, i => `<div class="grid-item" onclick="openAlbum('${esc(i.album)}')"><img class="grid-img" src="/api/content/cover?path=${encodeURIComponent(i.path)}&album=${encodeURIComponent(i.album)}" onerror="this.src='assets/img/no_cover.png'"><div><b>${i.album}</b></div></div>`);
    };

    window.openAlbum = async (album) => {
        navHistory.push({view: currentView, title: $("biblio_context_hidden").innerText || "Retour"});
        currentView = 'detail_album';
        $("biblio_context_hidden").innerText = album;
        updateToolbar();
        $("biblio_list").innerHTML = ""; window.scrollTo(0,0);
        const d = await apiFetch(`/api/content/browse/tracks?album=${encodeURIComponent(album)}`);
        renderList(d, false, renderTrackRow);
    };

    window.loadGlobalAlbums = async (append=false) => {
        if(!append) { navHistory=[]; setupView('albums'); }
        const d = await apiFetch(`/api/content/browse/albums_global?page=${currentPage}&limit=50`);
        renderGrid(d, append, i => `<div class="grid-item" onclick="openAlbum('${esc(i.album)}')"><img class="grid-img" src="/api/content/cover?path=${encodeURIComponent(i.path)}&album=${encodeURIComponent(i.album)}" onerror="this.src='assets/img/no_cover.png'"><div><b>${i.album}</b></div><small>${i.artist}</small></div>`);
    };
    
    window.loadGenres = async () => { navHistory=[]; setupView('genres'); const d=await apiFetch("/api/content/browse/genres"); renderList(d,false,i=>`<div class="rowitem" onclick="openGenre('${esc(i.genre)}')"><div class="grow"><b>${i.genre}</b></div><div class="tag">${i.count}</div></div>`); };
    window.openGenre = async (g) => { navHistory.push({view:'genres', title:'Genres'}); currentView='detail_genre'; $("biblio_context_hidden").innerText=g; updateToolbar(); $("biblio_list").innerHTML=""; const d=await apiFetch(`/api/content/browse/albums?genre=${encodeURIComponent(g)}`); renderGrid(d,false,i=>`<div class="grid-item" onclick="openAlbum('${esc(i.album)}')"><img class="grid-img" src="/api/content/cover?path=${encodeURIComponent(i.path)}&album=${encodeURIComponent(i.album)}" onerror="this.src='assets/img/no_cover.png'"><div><b>${i.album}</b></div></div>`); };

    window.loadFolders = async (path) => {
        if(!path) { navHistory=[]; setupView('folders'); }
        $("biblio_context_hidden").innerText = path ? `/${path}` : "/"; updateToolbar();
        const d = await apiFetch(`/api/content/browse/folders?path=${encodeURIComponent(path)}`);
        let html = path ? `<div class="rowitem" onclick="loadFolders('${d.parent||''}')" style="background:#eee;cursor:pointer"><b>⬅ Dossier Parent</b></div>` : "";
        if(d?.ok) {
            html += d.items.map(i => {
                const isDir = i.type==='folder';
                return `<div class="rowitem"><input type="checkbox" data-path="${esc(i.path)}" onchange="toggleSelection('${esc(i.path)}', this)"><div class="grow" onclick="${isDir?`loadFolders('${esc(i.path)}')`:''}" style="cursor:pointer">${isDir?'📁':'🎵'} ${i.name}</div>${!isDir?`<button onclick="playNowPath('${esc(i.path)}')" class="primary">▶</button>`:''}</div>`;
            }).join("");
            $("biblio_list").innerHTML = html; setSentinel('empty');
        }
    };

    function setSentinel(s) { $("scroll_sentinel").style.display = (s==='loading')?'block':'none'; }
    function setupScroll() { if(observer) observer.disconnect(); observer=new IntersectionObserver(e=>{if(e[0].isIntersecting && !isLoading && !['detail_album','detail_artist','folders','genres'].includes(currentView)) loadMore();}); observer.observe($("scroll_sentinel")); }
    window.loadMore = () => { currentPage++; if(currentView==='artists') loadArtists(true); else if(currentView==='albums') loadGlobalAlbums(true); };

    // =========================================
    // SECTION 4: BLUETOOTH
    // =========================================
    window.scanBluetooth = async () => {
        $("bt_list").innerHTML = "📡 Scan en cours...";
        const paired = await apiFetch("/api/bluetooth/paired");
        const scan = await apiFetch("/api/bluetooth/scan", "POST");
        let h = "";
        const known = paired?.ok ? paired.devices : [];
        if(known.length) h += "<b>Déjà mémorisés</b>" + known.map(d=>`<div class="rowitem"><div class="grow">${d.name} <small>${d.mac}</small></div>${d.connected?'<span style="color:green;font-weight:bold">Connecté</span>':''}<button onclick="disconnectBT('${d.mac}')">Oublier</button>${!d.connected?`<button onclick="connectBT('${d.mac}')" class="primary">Connecter</button>`:''}</div>`).join("");
        h += "<br><b>Appareils détectés</b>";
        if(scan?.ok) {
             const knownMacs = known.map(d=>d.mac);
             h += scan.devices.filter(d=>!knownMacs.includes(d.mac)).map(d=>`<div class="rowitem"><div class="grow">${d.name} <small>${d.mac}</small></div><button onclick="connectBT('${d.mac}')" class="primary">Jumeler</button></div>`).join("");
        }
        $("bt_list").innerHTML = h || "Rien trouvé.";
    };
    
    window.connectBT = async (mac) => { 
        $("progress_text").innerText = "Connexion Bluetooth en cours (20s max)...";
        $("progress_fill").style.width = "100%";
        $("progress_count").innerText = "";
        $("progress_modal").style.display = "flex";
        const r = await apiFetch("/api/bluetooth/connect", "POST", {mac});
        $("progress_modal").style.display = "none";
        if(r?.ok) alert("✅ Connecté ! Pensez à activer la sortie 'Bluetooth' dans la liste Audio.");
        else alert("❌ Echec: " + (r?.error || "Inconnu"));
        window.scanBluetooth(); 
    };
    window.disconnectBT = async (mac) => { await apiFetch("/api/bluetooth/disconnect", "POST", {mac}); window.scanBluetooth(); };

    // =========================================
    // SECTION 5: CONFIG AUDIO
    // =========================================
    window.loadAudioOutputs = async () => { 
        const d = await apiFetch("/api/audio/status");
        const div = $("audio_outputs_list");
        if(!div) return;
        if(d?.ok) {
            div.innerHTML = d.outputs.map(o => `
            <div class="rowitem" style="flex-wrap:wrap">
                <div class="grow"><b>${o.name}</b> <small>(ID: ${o.id})</small></div>
                <button onclick="openDacConfig(${o.id}, '${esc(o.name)}')" style="margin-right:10px; padding:5px 10px;">⚙️ Config</button>
                <label class="switch">
                    <input type="checkbox" ${o.enabled?'checked':''} onchange="toggleAudioOutput(${o.id}, this.checked)">
                    <span class="slider" style="font-weight:bold; color:${o.enabled?'green':'#ccc'}">${o.enabled?'ON':'OFF'}</span>
                </label>
            </div>`).join("");
        } else { div.innerHTML = "Erreur chargement sorties."; }
    };
    window.openDacConfig = (id, name) => { $("cfg_id").value = id; $("config_title").innerText = `Sortie : ${name}`; $("cfg_mixer").value = "hardware"; $("config_modal").style.display = "flex"; };
    window.saveDacConfig = async () => { const id = $("cfg_id").value; const mixer = $("cfg_mixer").value; $("config_modal").style.display = "none"; const r = await apiFetch("/api/audio/configure", "POST", {id: parseInt(id), mixer: mixer}); alert(r?.ok ? "Sauvegardé !" : "Erreur"); };
    window.toggleAudioOutput = async (id, en) => { await apiFetch("/api/audio/outputs/toggle", "POST", {id, enabled:en}); setTimeout(loadAudioOutputs, 600); };

window.refreshSystemStats = async () => {
    // On ne rafraichit que si l'onglet Paramètres est actif
    if(!document.getElementById('tab-parametres').classList.contains('active')) return;

    const d = await apiFetch("/api/system/stats");
    if(d) {
        // Mise à jour textes
        $("sys_cpu").innerText = d.cpu;
        $("sys_ram").innerText = d.ram;
        $("sys_ram_mb").innerText = d.ram_used_mb;
        $("sys_temp").innerText = d.temp;
        $("sys_disk").innerText = d.disk;
        $("sys_disk_gb").innerText = d.disk_free_gb;

        // Mise à jour barres avec couleurs dynamiques
        updateBar("bar_cpu", d.cpu);
        updateBar("bar_ram", d.ram);
        updateBar("bar_disk", d.disk);
        
        // Couleur température
        const t = d.temp;
        const tElem = $("sys_temp").parentElement; // Le parent .gauge-value
        tElem.style.color = (t > 75) ? "#dc3545" : (t > 60 ? "#ffc107" : "#28a745");
    }
};

function updateBar(id, val) {
    const el = $(id);
    el.style.width = val + "%";
    // Changement couleur (Vert -> Jaune -> Rouge)
    el.className = "progress-fill " + (val > 80 ? "status-crit" : (val > 60 ? "status-warn" : "status-ok"));
}

    // =========================================
    // SECTION 6: LECTEUR & STATUS (Modifié)
    // =========================================
    function startTimer() { if(timerInterval) clearInterval(timerInterval); timerInterval = setInterval(()=> { if(isPlaying && currentElapsed < currentDuration && !window.isDragging) { currentElapsed++; updateTimeUI(); } }, 1000); }
    function updateTimeUI() { $("time_elapsed").innerText = formatTime(currentElapsed); $("time_total").innerText = formatTime(currentDuration); $("seek_bar").max = currentDuration; $("seek_bar").value = currentElapsed; }
    
    window.seekTrack = async (s) => { window.isDragging = false; currentElapsed = parseInt(s); updateTimeUI(); await apiFetch("/api/player/seek", "POST", {seconds: currentElapsed}); refreshStatus(); };
    
    // --- NOUVEAU: Fonctions Shuffle/Repeat ---
    window.toggleShuffle = async () => { await apiFetch("/api/player/shuffle", "POST"); refreshStatus(); };
    window.toggleRepeat = async () => { await apiFetch("/api/player/repeat", "POST"); refreshStatus(); };

    // --- REFRESH GLOBAL (Boucle principale) ---
    async function refreshStatus() { 
        const d = await apiFetch("/api/status"); 
        if(d?.ok) { 
            const c=d.current||{}, s=d.status||{}; 
            $("np_title").innerText=c.title||"-"; 
            $("np_artist").innerText=c.artist||"-"; 
            $("np_album").innerText=c.album||""; 
            isPlaying = (s.state === "play"); 

            // Mise à jour Bouton Play/Pause
            const btnPlay = $("btn-play-pause");
            if(btnPlay) btnPlay.innerHTML = isPlaying ? '<i class="fas fa-pause"></i>' : '<i class="fas fa-play"></i>';

            // Mise à jour Boutons Shuffle/Repeat (Illuminé si actif)
            const btnShuf = $("btn-shuffle");
            const btnRep = $("btn-repeat");
            if(btnShuf) btnShuf.classList.toggle("active", s.random == 1 || s.random === true);
            if(btnRep) btnRep.classList.toggle("active", s.repeat == 1 || s.repeat === true);

            // Mise à jour Temps
            if(s.time && s.time.includes(":")){ 
                const p = s.time.split(':'); 
                if(!window.isDragging) { 
                    currentElapsed = parseInt(p[0]); 
                    currentDuration = parseInt(p[1]); 
                    updateTimeUI(); 
                } 
            } else if(s.state === "stop") { 
                currentElapsed=0; currentDuration=0; updateTimeUI(); 
            } 
            
            // Mise à jour Pochette
            if(c.file && $("np_cover").dataset.last !== c.file) { 
                $("np_cover").src=`/api/content/cover?path=${encodeURIComponent(c.file)}&t=${Date.now()}`; 
                $("np_cover").dataset.last=c.file; 
            } 
        } 
    }

    // =========================================
    // SECTION 7: ACTIONS UTILISATEUR
    // =========================================
    function renderTrackRow(t) { return `<div class="rowitem"><input type="checkbox" data-path="${esc(t.path)}" onchange="toggleSelection('${esc(t.path)}', this)"><div class="grow"><b>${t.title}</b><br><small>${t.artist}</small></div><button onclick="playNowPath('${esc(t.path)}')" class="primary">▶</button><button onclick="addToQueuePath('${esc(t.path)}', this)">+</button></div>`; }
    window.toggleSelection = (p, el) => { if(el.checked) window.selectedPaths.add(p); else window.selectedPaths.delete(p); updateToolbar(); };
    window.apiAction = async (a) => { await apiFetch(`/api/player/${a}`, "POST"); refreshStatus(); };
    window.setVolume = (v) => apiFetch(`/api/volume/${v}`, "POST");
    window.playNowPath = async (p) => { await apiFetch("/api/queue/play_now", "POST", {path:decodeURIComponent(p)}); switchTab('lecteur'); };
    window.addToQueuePath = async (p, b) => { await apiFetch("/api/queue/add", "POST", {path:decodeURIComponent(p)}); if(b){b.innerText="OK"; setTimeout(()=>b.innerText="+",1000);} };
    window.refreshQueue = async () => { const d=await apiFetch("/api/queue"); $("queue_list").innerHTML=(d?.ok)?d.queue.map((s,i)=>`<div class="rowitem"><b>${i+1}</b> <div class="grow">${s.title||s.file}</div></div>`).join(""):""; };
    window.saveCurrentPlaylist = () => { const n=prompt("Nom?"); if(n) apiFetch("/api/content/playlist/save", "POST", {name:n}); };
    window.clearQueue = () => { if(confirm("Vider?")) apiFetch("/api/queue/clear", "POST").then(refreshQueue); };
    window.loadPlaylists = async () => { const d=await apiFetch("/api/content/playlists"); $("playlist_list").innerHTML=d?.ok?d.playlists.map(p=>`<div class="rowitem"><div class="grow">${p.playlist}</div><button onclick="apiFetch('/api/content/playlist/load','POST',{name:'${p.playlist}',clear:true}).then(()=>switchTab('lecteur'))">▶</button></div>`).join(""):""; };
    window.addSelectionToPlaylist = async () => { const p=Array.from(window.selectedPaths); if(p.length && confirm(`Ajouter ${p.length} pistes ?`)) { const d=await apiFetch("/api/content/playlists"); const n=prompt("Nom de la playlist ?\n" + (d?.playlists||[]).map(x=>x.playlist).join(", ")); if(n) await apiFetch("/api/content/playlist/add_items", "POST", {playlist:n, paths:p}); window.selectedPaths.clear(); updateToolbar(); }};
    window.addSelectionToQueue = async () => { const p=Array.from(window.selectedPaths); if(p.length && confirm(`Ajouter ${p.length}?`)) { for(let x of p) await apiFetch("/api/queue/add", "POST", {path:x}); window.selectedPaths.clear(); updateToolbar(); refreshQueue(); } };
    window.taskAction = async (t) => { await apiFetch({'albums':'/api/content/tasks/albums','artists':'/api/content/tasks/artists','mpd_update':'/api/content/tasks/mpd_update'}[t], "POST"); alert("Tâche lancée en arrière-plan"); };
    window.saveApiKey = () => { localStorage.setItem(KEY_LS, $("apiKey").value); alert("Sauvegardé"); };
    window.toggleAllVisible = () => { const bs=document.querySelectorAll('#biblio_list input[type="checkbox"]'); const all=Array.from(bs).every(c=>c.checked); bs.forEach(c=>{c.checked=!all; if(!all) window.selectedPaths.add(c.dataset.path); else window.selectedPaths.delete(c.dataset.path);}); updateToolbar(); };
    window.closeModal = () => { $("progress_modal").style.display="none"; };

    // --- INITIALISATION ---
    document.addEventListener("DOMContentLoaded", () => { const k=localStorage.getItem(KEY_LS); if(k)$("apiKey").value=k; startTimer(); setInterval(refreshStatus, 1000); refreshStatus(); });
    setInterval(refreshSystemStats, 2000); // Rafraichissement système toutes les 2 sec
})();