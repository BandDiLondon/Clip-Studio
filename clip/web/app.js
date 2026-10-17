// Clip Studio : interface (étapes, appels à l'API locale de clip/web.py)
// Bilingue : chaque texte est écrit tr("français", "English"). Langue choisie en haut à droite (mémorisée),
// sinon celle du navigateur ; envoyée au serveur (en-tête X-Lang) pour ses messages et ceux des commandes.
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const store = {get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } },
               set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} }};
const LANG = (new URLSearchParams(location.search).get("lang") || store.get("lang")
              || (navigator.language || "fr")).toLowerCase().startsWith("en") ? "en" : "fr";
const tr = (fr, en) => LANG === "en" ? en : fr;
document.documentElement.lang = LANG;
let S = null, step = location.hash.slice(1) || store.get("step") || "projet", polling = null;

const STEPS = [
  ["projet", tr("Projet", "Project"), tr("Chanson et paroles", "Song and lyrics")],
  ["preparer", tr("Préparer", "Prepare"), tr("Beats et paroles calées", "Beats and aligned lyrics")],
  ["descriptions", tr("Descriptions", "Descriptions"), tr("Scènes à illustrer", "Scenes to illustrate")],
  ["planches", tr("Planches", "Panels"), tr("Images à générer", "Images to generate")],
  ["videos", tr("Vidéos", "Videos"), tr("Animer des images (optionnel)", "Animate images (optional)")],
  ["options", tr("Options", "Options"), tr("Effets et réglages", "Effects and settings")],
  ["rendu", tr("Rendu", "Render"), tr("Aperçu et vidéo finale", "Preview and final video")],
  ["publication", tr("Publication", "Publishing"), tr("Titre, description, miniature", "Title, description, thumbnail")],
];

function toast(msg, ms = 3200) { const t = $("#toast"); t.textContent = msg; t.classList.add("on");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("on"), ms); }
async function api(url, opts = {}) {
  const r = await fetch(url, {...opts, headers: {...(opts.headers || {}), "X-Lang": LANG}});
  const j = await r.json().catch(() => ({}));
  if (!r.ok || j.erreur) throw new Error(j.erreur || r.statusText); return j; }
const post = (url, body) => api(url, {method: "POST", body: typeof body === "string" ? body : JSON.stringify(body || {})});
const nom = () => $("#projet").value;
const file = p => `/fichier/${encodeURIComponent(nom())}/${p}?v=${Date.now()}`;

// ------------------------------------------------------------------ en-tête (textes de index.html, langue)
function header() {
  $("#nouveau").textContent = tr("+ Nouveau projet", "+ New project");
  $("#dossier").textContent = tr("📁 Dossier", "📁 Folder");
  $("#dossier").title = tr("Ouvrir le dossier du projet", "Open the project folder");
  $("#maj").innerHTML = tr("⚠ Clip Studio a été mis à jour : ferme la fenêtre de Clip Studio et relance-le, sinon certains boutons répondront « Action inconnue ».",
    "⚠ Clip Studio was updated: close the Clip Studio window and start it again, otherwise some buttons will answer “Unknown action”.");
  $("#jobstop").textContent = tr("Arrêter", "Stop");
  $("#jobhide").textContent = tr("Masquer", "Hide");
  $("#lang").innerHTML = ["fr", "en"].map(l => `<option value="${l}" ${l === LANG ? "selected" : ""}>${l === "fr" ? "Français" : "English"}</option>`).join("");
  $("#lang").onchange = e => { store.set("lang", e.target.value); location.reload(); };
}

// ------------------------------------------------------------------ état des étapes
function stepState(k) {
  if (!S) return "";
  const allDesc = S.shots.length && S.shots.every(s => s.description);
  const allPl = S.planches.length && S.planches.every(p => p.fichier);
  return {
    projet: S.audio && S.paroles ? "done" : "todo",
    preparer: S.beats && S.words && S.shots.length ? "done" : (S.audio && S.paroles ? "todo" : ""),
    descriptions: allDesc ? "done" : (S.shots.length ? "todo" : ""),
    planches: allPl && S.planches.every(p => p.decoupees) ? "done" : (allDesc ? "todo" : ""),
    videos: S.clips.length ? "done" : "",
    options: "",
    rendu: S.videos.length ? "done" : (allPl ? "todo" : ""),
    publication: S.publication ? "done" : (S.videos.length ? "todo" : ""),
  }[k];
}
function renderNav() {
  $("#nav").innerHTML = STEPS.map(([k, t, d], i) =>
    `<a class="${k === step ? "on" : ""} ${stepState(k)}" data-k="${k}"><span class="n">${stepState(k) === "done" ? "✓" : i + 1}</span>
     <span class="t"><div>${t}</div><div class="small muted">${d}</div></span></a>`).join("");
  document.querySelectorAll("nav a").forEach(a => a.onclick = () => go(a.dataset.k));
}
function go(k) { step = k; store.set("step", k); renderNav(); renderStep(); window.scrollTo(0, 0); }
function nextHint(k, txt) { return `<div class="row" style="margin-top:14px"><button class="primary" onclick="go('${k}')">${txt} →</button></div>`; }
const next = name => tr(`Étape suivante : ${name}`, `Next step: ${name}`);

// ------------------------------------------------------------------ chargement
async function loadProjects(select) {
  const list = await api("/api/projets");
  $("#projet").innerHTML = list.length ? list.map(n => `<option>${esc(n)}</option>`).join("")
    : `<option value="">${tr("(aucun projet)", "(no project)")}</option>`;
  const want = select || new URLSearchParams(location.search).get("projet") || store.get("projet");
  if (want && list.includes(want)) $("#projet").value = want;
  await refresh();
}
async function checkVersion() {
  const r = await api("/api/version").catch(() => null);   // ancien serveur : route absente → bandeau aussi
  $("#maj").style.display = !r || r.perime ? "block" : "none";
}
async function refresh() {
  checkVersion();
  if (!nom()) { S = null; renderNav(); $("#main").innerHTML = `<h2>${tr("Bienvenue", "Welcome")}</h2>
    <p class="lead">${tr("Crée ton premier projet avec « + Nouveau projet ».", "Create your first project with “+ New project”.")}</p>`; return; }
  store.set("projet", nom());
  try { S = await api(`/api/projet/${encodeURIComponent(nom())}`); } catch (e) { toast(e.message); return; }
  renderNav(); renderStep();
}

// ------------------------------------------------------------------ tâches
async function run(cmd, args = [], label) {
  try { await post(`/api/projet/${encodeURIComponent(nom())}/run`, {cmd, args}); }
  catch (e) { toast(e.message); return; }
  $("#job").classList.remove("hide"); $("#jobtitle").textContent = label || cmd; pollJob();
}
function pollJob() {
  clearInterval(polling);
  polling = setInterval(async () => {
    const j = await api("/api/job").catch(() => null); if (!j) return;
    $("#jobtitle").textContent = (j.running ? "⏳ " : j.code === 0 ? "✅ " : "⚠️ ") + (j.label || "");
    $("#jobtime").textContent = ` · ${j.elapsed} s`;
    $("#jobbar").style.width = j.pct != null ? j.pct + "%" : (j.running ? "15%" : "100%");
    $("#jobprog").textContent = j.pct != null ? tr(`Rendu : ${j.pct} %`, `Render: ${j.pct}%`) : "";
    const log = $("#joblog"); log.textContent = j.lines.join("\n"); log.scrollTop = log.scrollHeight;
    $("#jobstop").disabled = !j.running;
    if (!j.running) {
      clearInterval(polling);
      await refresh();
      toast(j.code === 0 ? tr("Terminé ✅", "Done ✅") : tr("Terminé avec un problème — voir le journal en bas", "Finished with a problem — see the log below"), 4500);
    }
  }, 1000);
}

// ------------------------------------------------------------------ téléversement
function pick(accept, cb) { const p = $("#picker"); p.accept = accept; p.value = "";
  p.onchange = () => p.files[0] && cb(p.files[0]); p.click(); }
async function upload(type, f, id = "") {
  const url = `/api/projet/${encodeURIComponent(nom())}/upload?type=${type}&nom=${encodeURIComponent(f.name)}&id=${id}`;
  toast(tr(`Envoi de ${f.name}…`, `Uploading ${f.name}…`));
  try { await api(url, {method: "POST", body: f}); toast(tr(`${f.name} ajouté ✅`, `${f.name} added ✅`)); await refresh(); }
  catch (e) { toast(e.message); }
}
// ------------------------------------------------------------------ coller une image (Ctrl+V / bouton)
let HOVER = null;                                   // zone de dépôt survolée : {type, id}
const imgFile = (blob, id) => new File([blob], `${id || "image"}.${(blob.type.split("/")[1] || "png").replace("jpeg", "jpg")}`,
  {type: blob.type || "image/png"});
async function readClipboardImage() {
  if (!navigator.clipboard || !navigator.clipboard.read)
    throw new Error(tr("Ce navigateur ne permet pas le bouton : utilise Ctrl+V", "This browser does not allow the button: use Ctrl+V"));
  for (const item of await navigator.clipboard.read()) {
    const t = item.types.find(x => x.startsWith("image/"));
    if (t) return await item.getType(t);
  }
  throw new Error(tr("Aucune image dans le presse-papiers (clic droit sur l'image → « Copier l'image »)",
    "No image in the clipboard (right-click the image → “Copy image”)"));
}
function pasteTarget() {
  if (HOVER && HOVER.type !== "audio" && HOVER.type !== "paroles") return HOVER;
  if (step === "planches" && S) {
    const p = S.planches.find(p => !p.fichier);
    return p ? {type: "planche", id: p.id} : null;
  }
  if (step === "preparer" && S) {                   // première photo de solo encore vide
    const n = Math.max(S.solos_prompts.length, 1);
    for (let k = 1; k <= n; k++)
      if (!S.solos.some(f => f.toLowerCase().replace(/\.[^.]+$/, "") === `solo${k}`)) return {type: "solo", id: `solo${k}`};
    return null;
  }
  return null;
}
document.addEventListener("paste", e => {
  if (!S || ["TEXTAREA", "INPUT"].includes(document.activeElement?.tagName)) return;   // collage de texte normal
  const item = [...(e.clipboardData?.items || [])].find(i => i.type.startsWith("image/"));
  if (!item) return;
  e.preventDefault();
  const tgt = pasteTarget();
  if (!tgt) return toast(step === "planches"
    ? tr("Toutes les planches ont une image : survole la planche à remplacer puis Ctrl+V", "All panels have an image: hover the panel to replace, then Ctrl+V")
    : tr("Va à l'étape 4 (Planches) pour coller une planche", "Go to step 4 (Panels) to paste a panel"));
  upload(tgt.type, imgFile(item.getAsFile(), tgt.id), tgt.id);
});

function dropzone(el, type, accept, id = "") {
  el.onclick = () => pick(accept, f => upload(type, f, id));
  el.onmouseenter = () => HOVER = {type, id};
  el.onmouseleave = () => { if (HOVER && HOVER.type === type && HOVER.id === id) HOVER = null; };
  if (accept.startsWith("image")) {                 // bouton « Coller » pour les zones d'image
    const b = document.createElement("button");
    b.textContent = tr("📋 Coller", "📋 Paste"); b.style.marginTop = "8px";
    b.title = tr("Coller l'image copiée (ou Ctrl+V en survolant la zone)", "Paste the copied image (or Ctrl+V while hovering the area)");
    b.onclick = async ev => { ev.stopPropagation();
      try { upload(type, imgFile(await readClipboardImage(), id), id); } catch (err) { toast(err.message, 5000); } };
    el.appendChild(document.createElement("br")); el.appendChild(b);
  }
  el.ondragover = e => { e.preventDefault(); el.classList.add("over"); };
  el.ondragleave = () => el.classList.remove("over");
  el.ondrop = e => { e.preventDefault(); el.classList.remove("over"); const f = e.dataTransfer.files[0]; if (f) upload(type, f, id); };
}
async function copy(txt) { await navigator.clipboard.writeText(txt); toast(tr("Copié dans le presse-papiers ✅", "Copied to the clipboard ✅")); }
const ok = tr("fait", "done"), todoPill = tr("à faire", "to do");
const replaceDrop = (has, what) => has ? tr(`Remplacer ${what}`, `Replace ${what}`) : tr(`Déposer ${what}`, `Drop ${what}`);

// ------------------------------------------------------------------ étapes
const V = {};
function renderStep() { if (!S) return; HOVER = null; $("#main").innerHTML = V[step](); (V[step + "_bind"] || (() => {}))(); }

V.projet = () => `
  <h2>1. ${tr("Projet", "Project")}</h2><p class="lead">${tr("Dépose la chanson et ses paroles. Tout le reste en découle.", "Drop the song and its lyrics. Everything else follows from them.")}</p>
  <div class="grid2">
    <div class="card"><h3>🎵 ${tr("Chanson", "Song")}</h3>
      ${S.audio ? `<p><span class="pill ok">OK</span> ${esc(S.audio)}</p><audio controls src="${file(encodeURIComponent(S.audio))}" style="width:100%"></audio>` : ""}
      <div class="drop" id="dz-audio"><b>${S.audio ? tr("Remplacer le fichier audio", "Replace the audio file") : tr("Déposer le fichier audio", "Drop the audio file")}</b><br>
        <span class="small">${tr("mp3, wav, m4a… (glisser ici ou cliquer)", "mp3, wav, m4a… (drag here or click)")}</span></div>
      ${S.audio && S.beats ? `<p class="small muted">${tr("Si tu changes l'audio, « Préparer » (ou le prochain rendu) refait automatiquement le rythme et le calage des paroles.",
        "If you change the audio, “Prepare” (or the next render) automatically redoes the rhythm and the lyrics alignment.")}</p>` : ""}
    </div>
    <div class="card"><h3>📝 ${tr("Paroles", "Lyrics")}</h3>
      ${S.paroles ? `<p><span class="pill ok">OK</span> ${esc(S.paroles)}</p>` : ""}
      <div class="drop" id="dz-paroles"><b>${S.paroles ? tr("Remplacer les paroles (.txt)", "Replace the lyrics (.txt)") : tr("Déposer les paroles (.txt)", "Drop the lyrics (.txt)")}</b><br>
        <span class="small">${tr("Un vers par ligne, sections entre crochets : [Verse 1], [Chorus]…", "One line per lyric line, sections in brackets: [Verse 1], [Chorus]…")}</span></div>
    </div>
  </div>
  <div class="card"><h3>🌐 ${tr("Langue de la chanson", "Language of the song")}</h3>
    <div class="row"><select id="langue">${[["fr", "Français"], ["en", "English"]].map(([v, t]) =>
      `<option value="${v}" ${(S.cfg.langue || "fr") === v ? "selected" : ""}>${t}</option>`).join("")}</select>
      <span class="small muted">${tr("Sert au calage des paroles et à la langue des textes que Claude rédige (descriptions, publication) et des prompts d'images.",
        "Used for the lyrics alignment and for the language of the texts Claude writes (descriptions, publishing) and of the image prompts.")}</span></div></div>
  <div class="card"><h3>✏️ ${S.paroles ? tr("Modifier les paroles", "Edit the lyrics") : tr("Ou coller les paroles ici", "Or paste the lyrics here")}</h3>
    <p class="small muted">${tr("Un vers par ligne, une ligne vide entre les parties. En-têtes facultatifs : [Verse 1], [Chorus], [Bridge]… (sans en-têtes, les blocs répétés sont reconnus comme refrains).",
      "One lyric line per line, an empty line between parts. Optional headers: [Verse 1], [Chorus], [Bridge]… (without headers, repeated blocks are recognized as choruses).")}</p>
    <textarea id="lyr" rows="16" placeholder="${tr("[Verse 1]&#10;Premier vers&#10;Deuxième vers&#10;&#10;[Chorus]&#10;…", "[Verse 1]&#10;First line&#10;Second line&#10;&#10;[Chorus]&#10;…")}">${esc(S.paroles_texte)}</textarea>
    <div class="row" style="margin-top:10px"><button class="primary" id="lyr-save">💾 ${tr("Enregistrer les paroles", "Save the lyrics")}</button>
      <span class="small muted" id="lyr-info"></span></div>
    ${S.words ? `<p class="small muted" style="margin-top:8px">${tr("Les paroles sont déjà calées sur la chanson : après une modification, relance « Préparer » (le calage est refait automatiquement; si des vers ont changé, leurs images aussi).",
      "The lyrics are already aligned with the song: after a change, run “Prepare” again (the alignment is redone automatically; if lines changed, their images too).")}</p>` : ""}
  </div>
  ${perimeHint()}
  ${(S.historique || []).length ? `<details class="card"><summary><b>🕘 ${tr("Historique des réglages", "Settings history")}</b> <span class="muted small">— ${tr("revenir à une version précédente de projet.json", "go back to a previous version of projet.json")}</span></summary>
    <p class="small muted">${tr(`Une copie est gardée avant chaque modification (au plus une par minute, ${S.historique.length} version(s)). Restaurer garde aussi la version actuelle dans l'historique.`,
      `A copy is kept before each change (at most one per minute, ${S.historique.length} version(s)). Restoring also keeps the current version in the history.`)}</p>
    <div class="row"><select id="hi-f">${S.historique.map(x => `<option value="${x.nom}">${esc(x.date)}</option>`).join("")}</select>
      <button id="hi-go">${tr("Restaurer cette version", "Restore this version")}</button></div></details>` : ""}
  ${S.audio && S.paroles ? nextHint("preparer", next(tr("Préparer", "Prepare"))) : ""}`;
V.projet_bind = () => {
  dropzone($("#dz-audio"), "audio", "audio/*,.mp3,.wav,.m4a,.flac,.ogg");
  dropzone($("#dz-paroles"), "paroles", ".txt,text/plain");
  const lyr = $("#lyr"), info = () => {
    const n = lyr.value.split(/\r?\n/).filter(l => l.trim() && !/^\s*\[.+\]\s*$/.test(l)).length;
    $("#lyr-info").textContent = n ? tr(`${n} vers`, `${n} lines`) : ""; };
  lyr.oninput = info; info();
  $("#langue").onchange = async e => {
    try { await post(`/api/projet/${encodeURIComponent(nom())}/config`, {langue: e.target.value});
      toast(S.words ? tr("Langue enregistrée : relance « Préparer » pour recaler les paroles", "Language saved: run “Prepare” again to realign the lyrics")
                    : tr("Langue enregistrée ✅", "Language saved ✅"));
      await refresh(); }
    catch (err) { toast(err.message); }
  };
  $("#hi-go") && ($("#hi-go").onclick = async () => {
    const f = $("#hi-f").value, d = $("#hi-f").selectedOptions[0].textContent;
    if (!confirm(tr(`Revenir aux réglages du ${d}?`, `Go back to the settings of ${d}?`))) return;
    try { await post(`/api/projet/${encodeURIComponent(nom())}/restaurer?f=${encodeURIComponent(f)}`); toast(tr("Version restaurée ✅", "Version restored ✅")); refresh(); }
    catch (e) { toast(e.message); } });
  $("#lyr-save").onclick = async () => {
    const txt = lyr.value.replace(/\r\n/g, "\n").trim();
    if (!txt) return toast(tr("Colle d'abord les paroles", "Paste the lyrics first"));
    if (txt === S.paroles_texte.replace(/\r\n/g, "\n").trim()) return toast(tr("Aucun changement", "No change"));
    const name = S.paroles || (LANG === "en" ? "lyrics.txt" : "paroles.txt");
    try {
      await api(`/api/projet/${encodeURIComponent(nom())}/upload?type=paroles&nom=${encodeURIComponent(name)}`,
        {method: "POST", body: txt + "\n"});
      toast(tr(`Paroles enregistrées dans ${name} ✅`, `Lyrics saved in ${name} ✅`)); await refresh();
    } catch (e) { toast(e.message); }
  };
};

function perimeHint() {
  const P = S.perimes || [];
  if (!P.length) return "";
  const quoi = P.includes("beats") ? tr("Le mp3 a changé", "The mp3 changed")
    : tr("Les paroles, le mp3, le début du chant, le modèle de calage ou la langue ont changé", "The lyrics, the mp3, the singing start, the alignment model or the language changed");
  return `<div class="steps-hint" style="border-color:var(--warn)">⚠ <b>${quoi} ${tr("depuis la dernière préparation.", "since the last preparation.")}</b>
    ${tr("Le karaoké et le montage ne sont plus synchronisés : relance <b>Préparer</b> (fait automatiquement au prochain rendu, compte environ 1 minute de plus).",
      "The karaoke and the edit are no longer in sync: run <b>Prepare</b> again (done automatically at the next render, about 1 more minute).")}</div>`;
}
V.preparer = () => {
  const n = S.shots.length, amb = S.shots.filter(s => s.ambiance).length;
  return `
  <h2>2. ${tr("Préparer", "Prepare")}</h2><p class="lead">${tr("Détecte le rythme, cale chaque mot des paroles sur la voix, et calcule le nombre d'images à générer.",
    "Detects the rhythm, aligns each word of the lyrics with the voice, and computes the number of images to generate.")}</p>
  ${perimeHint()}
  <div class="card"><h3>🎯 ${tr("Intention de la chanson", "Intent of the song")} <span class="muted small">(${tr("recommandé", "recommended")})</span></h3>
    <p class="small muted">${tr("Explique à Claude ce que les paroles ne disent pas : il s'en servira pour l'évaluation, les descriptions de scènes et la publication.",
      "Tell Claude what the lyrics don't say: it will use it for the evaluation, the scene descriptions and the publishing.")}</p>
    <textarea id="intention" rows="5" maxlength="1500" placeholder="${tr("De quoi parle vraiment la chanson? Premier ou second degré (ironie, hommage, colère, nostalgie)?&#10;Histoire vraie, contexte, époque, lieu? Genre et énergie (punk, ballade, folk…)?&#10;Références visuelles souhaitées? Ce qu'il faut éviter (personne réelle, violence, clichés…)?",
      "What is the song really about? Literal or tongue-in-cheek (irony, tribute, anger, nostalgia)?&#10;True story, context, era, place? Genre and energy (punk, ballad, folk…)?&#10;Wanted visual references? What to avoid (real person, violence, clichés…)?")}">${esc(S.cfg.intention || "")}</textarea>
    <p class="small muted" style="margin:10px 0 4px">${tr("Style visuel des images (envoyé aussi au générateur d'images) :", "Visual style of the images (also sent to the image generator):")}</p>
    <input type="text" id="style" value="${esc(S.cfg.style || "")}" style="width:100%">
    <div class="row" style="margin-top:10px"><button class="primary" id="int-save">💾 ${tr("Enregistrer", "Save")}</button>
      <span class="small muted" id="int-info"></span></div>
    ${S.shots.some(s => s.description) ? `<p class="small muted" style="margin-top:8px">${tr("Descriptions déjà rédigées : pour qu'elles tiennent compte d'une nouvelle intention, relance la rédaction (étape 3) avec « tout réécrire ».",
      "Descriptions already written: for them to take a new intent into account, run the writing again (step 3) with “rewrite all”.")}</p>` : ""}
  </div>
  <div class="card">
    <div class="row"><button class="primary" id="go-prep" ${S.audio && S.paroles ? "" : "disabled"}>▶ ${tr("Préparer", "Prepare")}</button>
      <label class="small"><input type="checkbox" id="prep-force"> ${tr("tout refaire (après changement d'audio ou de paroles)", "redo everything (after changing the audio or the lyrics)")}</label></div>
    <div class="row" style="margin-top:10px"><label class="small">${tr("Calage des paroles :", "Lyrics alignment:")}
      <select id="whisper">${[["medium", tr("Précis : modèle medium (environ 5 Go de mémoire libre)", "Accurate: medium model (about 5 GB of free memory)")],
        ["small", tr("Mémoire limitée : modèle small (environ 2 Go), karaoké moins précis", "Limited memory: small model (about 2 GB), less accurate karaoke")]].map(([v, t]) =>
        `<option value="${v}" ${(S.cfg.whisper || "medium") === v ? "selected" : ""}>${t}</option>`).join("")}</select></label></div>
    ${S.cfg.whisper === "small" ? `<p class="small muted" style="margin-top:6px">${tr("Avec « small », des vers peuvent être décalés d'une demi-seconde ou plus. Utilise-le seulement si le calage plante faute de mémoire.",
      "With “small”, lines can be off by half a second or more. Use it only if the alignment crashes for lack of memory.")}</p>` : ""}
    <p class="small muted" style="margin-top:10px">${tr("Durée : environ 1 minute pour une chanson de 3 min (le calage des paroles est le plus long), plus un téléchargement unique de 1,5 Go la toute première fois.",
      "Duration: about 1 minute for a 3-minute song (the lyrics alignment takes the longest), plus a one-time 1.5 GB download the very first time.")}</p>
  </div>
  <div class="card"><h3>${tr("État", "Status")}</h3><table>
    <tr><td>${tr("Rythme (beats)", "Rhythm (beats)")}</td><td>${S.beats ? `<span class="pill ok">${ok}</span>` : `<span class="pill">${todoPill}</span>`}
      ${S.cfg.bpm_detecte ? ` <b>${S.cfg.bpm_detecte} BPM</b> <span class="muted small">${S.cfg.bpm_hint === "auto" || !S.cfg.bpm_hint ? tr("(détecté automatiquement)", "(detected automatically)") : tr(`(tempo imposé : ${S.cfg.bpm_hint})`, `(forced tempo: ${S.cfg.bpm_hint})`)}</span>` : ""}</td></tr>
    <tr><td>${tr("Paroles calées mot à mot", "Lyrics aligned word by word")}</td><td>${S.words ? `<span class="pill ok">${ok}</span>` : `<span class="pill">${todoPill}</span>`}</td></tr>
    <tr><td>${tr("Images nécessaires", "Images needed")}</td><td>${n ? tr(`<b>${n}</b> (${n - amb} vers + ${amb} ambiance) → <b>${S.planches.length}</b> planche(s)`,
      `<b>${n}</b> (${n - amb} lines + ${amb} ambiance) → <b>${S.planches.length}</b> panel(s)`) : "—"}</td></tr>
  </table>
  <div class="row" style="margin-top:12px">
    <label class="small">${tr("Images d'ambiance en plus (passages instrumentaux) :", "Extra ambiance images (instrumental parts):")}
      <input type="number" id="amb" min="0" max="24" value="${S.cfg.ambiance || 0}" style="width:70px"></label>
    <button id="amb-save">${tr("Appliquer", "Apply")}</button></div>
  </div>
  ${S.words ? `<div class="card"><h3>🎤 ${tr("Début du chant", "Singing start")}</h3>
    <p class="small muted">${tr("Si le karaoké commence trop tôt (des vers affichés pendant l'intro), indique la seconde où le chant commence vraiment : les vers placés avant sont recalés à partir de ce moment. 0 = automatique.",
      "If the karaoke starts too early (lines shown during the intro), enter the second where the singing really starts: the lines placed before are realigned from that moment. 0 = automatic.")}</p>
    <div class="row"><label class="small">${tr("Le chant commence à", "The singing starts at")} <input type="text" id="dc" value="${S.cfg.debut_chant ? fmtT(S.cfg.debut_chant) : "0"}" style="width:70px"> ${tr("(m:ss ou secondes)", "(m:ss or seconds)")}</label>
      <button class="primary" id="dc-go">${tr("Recaler les paroles", "Realign the lyrics")}</button></div>
    <p class="small muted" style="margin-top:6px">${tr("Ensuite, fais un rendu complet (étape 7) : le montage des images suit les nouveaux temps.", "Then make a full render (step 7): the image edit follows the new times.")}</p></div>` : ""}
  ${S.words ? evalCard() : ""}
  ${S.words ? solosCard() : ""}
  ${S.words ? calageCard() : ""}
  ${n ? nextHint("descriptions", next(tr("Descriptions", "Descriptions"))) : ""}`;
};
// vérification du calage : sections, alertes, et outils de correction (écouter, recaler, décaler)
function calageCard() {
  const C = S.calage;
  const titre = `<h3>🎤 ${tr("Vérifier le calage", "Check the alignment")}</h3>`;
  const apercu = `<button onclick="go('rendu')">${tr("Faire un aperçu rapide", "Make a quick preview")}</button>`;
  if (!C) return `<div class="card">${titre}${apercu}</div>`;
  const nbad = C.sections.reduce((a, x) => a + x.mal_cales, 0);
  const fin = C.fin_trop_tot && S.cfg.calage_fin_ok !== C.derniere_fin;
  const prevEnd = i => { for (let j = i - 1; j >= 0; j--) if (C.sections[j].fin != null) return C.sections[j].fin; return 0; };
  const t = v => v == null ? "—" : fmtT(v);
  return `<div class="card">${titre}
    ${nbad ? `<p class="small"><span class="pill warn">⚠ ${tr(`${nbad} vers mal calé(s)`, `${nbad} badly aligned line(s)`)}</span>
      ${tr("Écoute la section (▶), indique la seconde où elle commence vraiment, puis « Recaler » : Whisper la réaligne seule (~20 s).",
        "Listen to the section (▶), enter the second where it really starts, then “Realign”: Whisper realigns it alone (~20 s).")}</p>`
      : `<p class="small muted">✅ ${tr("Aucun vers tassé détecté. Si le karaoké se décale quand même sur une section, corrige-la ci-dessous.",
        "No squashed line detected. If the karaoke still drifts on a section, fix it below.")}</p>`}
    ${fin ? `<p class="small"><span class="pill warn">⚠ ${tr("Fin de chanson", "End of song")}</span>
      ${tr(`Les paroles finissent ${C.fin_trop_tot} s avant la fin de l'audio (dernier vers à ${fmtT(C.derniere_fin)}). Si un refrain est chanté après, recale la dernière section.`,
        `The lyrics end ${C.fin_trop_tot} s before the end of the audio (last line at ${fmtT(C.derniere_fin)}). If a chorus is sung after, realign the last section.`)}
      <button id="cal-finok">${tr("C'est normal (outro instrumentale)", "It's normal (instrumental outro)")}</button></p>` : ""}
    <audio id="cal-audio" preload="none" src="${S.audio ? file(encodeURIComponent(S.audio)) : ""}"></audio>
    <table class="small" style="margin-top:8px"><tr><th>${tr("Section", "Section")}</th><th>${tr("Temps", "Time")}</th><th>${tr("Vers", "Lines")}</th><th></th>
      <th>${tr("Commence à", "Starts at")}</th><th>${tr("Décaler (s)", "Shift (s)")}</th></tr>
    ${C.sections.map((x, i) => `<tr>
      <td title="${esc(x.texte)}"><b>${esc(x.section || "—")}</b><br><span class="muted">${esc(x.texte.slice(0, 32))}${x.texte.length > 32 ? "…" : ""}</span></td>
      <td>${t(x.debut)} → ${t(x.fin)}</td>
      <td>${x.mal_cales ? `<span class="pill warn">${x.mal_cales}/${x.vers}</span>` : x.vers}</td>
      <td><button data-cal-play="${x.debut ?? prevEnd(i)}" title="${tr("Écouter à partir d'ici", "Listen from here")}">▶</button></td>
      <td><input type="text" id="cal-t${i}" value="${fmtT(x.mal_cales ? prevEnd(i) : (x.debut ?? prevEnd(i)))}" style="width:64px">
        <button data-cal-go="${i}">${tr("Recaler", "Realign")}</button></td>
      <td><input type="number" id="cal-d${i}" value="0" step="0.1" style="width:64px"> <button data-cal-dec="${i}">${tr("Décaler", "Shift")}</button></td></tr>`).join("")}
    </table>
    <div class="row" style="margin-top:10px"><button id="cal-stop">⏹ ${tr("Arrêter l'écoute", "Stop listening")}</button>${apercu}
      <span class="small muted">${tr("Après une correction, refais un rendu (étape 7) : le montage des images suit les nouveaux temps.", "After a fix, render again (step 7): the image edit follows the new times.")}</span></div></div>`;
}
function calageBind() {
  const au = $("#cal-audio"); if (!au) return;
  document.querySelectorAll("[data-cal-play]").forEach(b => b.onclick = () => {
    const t0 = Math.max(0, +b.dataset.calPlay - 1);
    const go = () => { au.currentTime = t0; au.play(); };
    au.readyState >= 1 ? go() : (au.addEventListener("loadedmetadata", go, {once: true}), au.load());
  });
  $("#cal-stop").onclick = () => au.pause();
  document.querySelectorAll("[data-cal-go]").forEach(b => b.onclick = () => {
    const i = +b.dataset.calGo, s = parseT($("#cal-t" + i).value);
    if (!(s >= 0)) return toast(tr("Temps invalide (ex. 2:26 ou 146)", "Invalid time (e.g. 2:26 or 146)"));
    au.pause();
    run("section", ["--index", String(i), "--debut", s.toFixed(2)], tr(`Recalage de la section ${i + 1} à ${fmtT(s)}`, `Realigning section ${i + 1} at ${fmtT(s)}`));
  });
  document.querySelectorAll("[data-cal-dec]").forEach(b => b.onclick = () => {
    const i = +b.dataset.calDec, d = Math.round(+$("#cal-d" + i).value * 100) / 100;
    if (!d || Math.abs(d) >= 1000) return toast(tr("Indique un décalage en secondes (ex. -0.5 ou 1.2)", "Enter a shift in seconds (e.g. -0.5 or 1.2)"));
    run("section", ["--index", String(i), "--decaler", d.toFixed(2)], tr(`Décalage de la section ${i + 1} : ${d > 0 ? "+" : ""}${d} s`, `Shifting section ${i + 1}: ${d > 0 ? "+" : ""}${d} s`));
  });
  $("#cal-finok") && ($("#cal-finok").onclick = async () => {
    S.cfg.calage_fin_ok = S.calage.derniere_fin;
    await post(`/api/projet/${encodeURIComponent(nom())}/config`, {calage_fin_ok: S.calage.derniere_fin}); renderStep();
  });
}
const parseT = v => { const p = String(v).trim().split(":").map(Number);
  return !p.length || p.some(isNaN) ? NaN : p.reduce((a, x) => a * 60 + x, 0); };
const passageType = t =>({intro: "Intro", outro: "Outro", instrumental: tr("Instrumental", "Instrumental")}[t] || t);
function solosCard() {
  const passages = S.evaluation ? S.evaluation.faits.passages_sans_paroles.length : 3;
  const n = S.solos_prompts.length || Math.max(1, Math.min(8, passages || 3));
  const fileFor = k => S.solos.find(f => f.toLowerCase().replace(/\.[^.]+$/, "") === `solo${k}`);
  const extras = S.solos.filter(f => !/^solo\d+\.[^.]+$/i.test(f));
  const slots = Math.max(S.solos_prompts.length, ...S.solos.map(f => +(f.match(/^solo(\d+)\./i) || [0, 0])[1]));
  return `<div class="card"><h3>🎸 ${tr("Photos de solo", "Solo photos")} <span class="muted small">(${tr("optionnel — passages instrumentaux", "optional — instrumental parts")})</span></h3>
    <p class="small muted">${tr("Images panoramiques (21:9) sur lesquelles la caméra glisse pendant les passages sans paroles. Avec elles, il faut moins d'images d'ambiance",
      "Panoramic images (21:9) the camera glides across during the parts without lyrics. With them, fewer ambiance images are needed")}${S.evaluation ? tr(" : pense à « ↻ Réévaluer » après les avoir ajoutées", ": remember to “↻ Re-evaluate” after adding them") : ""}.</p>
    ${CLAUDE ? `<div class="row"><label class="small">${tr("Nombre :", "Number:")} <input type="number" id="so-n" min="1" max="8" value="${n}" style="width:60px"></label>
      <input type="text" id="so-c" placeholder="${tr("Consigne facultative : ex. le groupe sur scène, la foule, un lieu de la chanson…", "Optional instruction: e.g. the band on stage, the crowd, a place from the song…")}" style="flex:1;min-width:240px">
      <button class="primary" id="so-go">✨ ${S.solos_prompts.length ? tr("Refaire les prompts avec Claude", "Redo the prompts with Claude") : tr("Créer les prompts avec Claude", "Create the prompts with Claude")}</button></div>` :
      `<p class="small muted">${tr("Claude Code introuvable : dépose simplement tes photos panoramiques ci-dessous.", "Claude Code not found: simply drop your panoramic photos below.")}</p>`}
    <div class="planches" style="margin-top:14px">
    ${Array.from({length: Math.max(slots, S.solos_prompts.length ? 0 : 1)}, (_, i) => i + 1).map(k => {
      const sp = S.solos_prompts[k - 1], f = fileFor(k);
      return `<div class="planche" style="grid-template-columns:1fr 300px">
        <div><div class="row"><b>solo${k}</b>${sp ? ` <span class="muted small">— ${esc(sp.titre || "")}</span>` : ""}
          ${f ? `<span class="pill ok">${tr("image déposée", "image dropped")}</span>` : `<span class="pill warn">${tr("à générer", "to generate")}</span>`}
          <div style="flex:1"></div>${sp ? `<button class="primary" data-socp="${k - 1}">📋 ${tr("Copier le prompt", "Copy the prompt")}</button>` : ""}</div>
          ${sp ? `<pre class="code" style="max-height:160px">${esc(sp.prompt)}</pre>` : ""}</div>
        <div>${f ? `<img class="thumb" src="${file(encodeURIComponent(S.solos_dir) + "/" + encodeURIComponent(f))}">` : ""}
          <div class="drop" data-sodz="solo${k}" style="margin-top:8px"><b>${replaceDrop(f, `solo${k}`)}</b></div></div></div>`;
    }).join("")}</div>
    ${extras.length ? `<p class="small muted">${tr("Autres photos de solo utilisées :", "Other solo photos used:")} ${extras.map(esc).join(" · ")}</p>` : ""}
  </div>`;
}
const PRESET_KEYS = {ballade: "ballade", rock: "rock", sobre: "sobre"};
function evalCard() {
  const E = S.evaluation;
  const title = `<h3>🧠 ${tr("Évaluation par Claude", "Evaluation by Claude")}</h3>`;
  if (!E) return `<div class="card">${title}
    <p class="small muted">${tr("Claude analyse les passages sans paroles et recommande le nombre d'images d'ambiance, avec des idées de scènes.",
      "Claude analyzes the parts without lyrics and recommends the number of ambiance images, with scene ideas.")}</p>
    ${CLAUDE ? `<button id="ev-go">🧠 ${tr("Évaluer le storyboard", "Evaluate the storyboard")}</button>` : `<p class="small muted">${tr("Claude Code introuvable (voir étape 3).", "Claude Code not found (see step 3).")}</p>`}</div>`;
  const F = E.faits, I = E.ia, applied = (S.cfg.ambiance || 0) === I.ambiance;
  const planches = n => n <= 0 ? 0 : Math.floor(n / 6) + (n % 6 ? 1 : 0);
  const preset = PRESETS[PRESET_KEYS[I.preset]];
  return `<div class="card">${title}
    <table class="small">
      <tr><td>${tr("Passages sans paroles", "Parts without lyrics")}</td><td>${F.passages_sans_paroles.map(t => `${passageType(t.type)} ${t.duree} s`).join(" · ") || tr("aucun", "none")}
        (total <b>${F.instrumental_total} s</b>)</td></tr>
      <tr><td>${tr("Photos de solo", "Solo photos")}</td><td>${F.photos_de_solo}</td></tr>
      <tr><td>${tr("Recommandation", "Recommendation")}</td><td>${tr(`<b>${I.ambiance}</b> image(s) d'ambiance → <b>${F.images_de_vers + I.ambiance}</b> images, <b>${planches(F.images_de_vers + I.ambiance)}</b> planche(s)`,
        `<b>${I.ambiance}</b> ambiance image(s) → <b>${F.images_de_vers + I.ambiance}</b> images, <b>${planches(F.images_de_vers + I.ambiance)}</b> panel(s)`)}
        ${applied ? `<span class="pill ok">${tr("appliquée", "applied")}</span>` : `<span class="pill warn">${tr("non appliquée", "not applied")}</span>`}</td></tr>
      <tr><td>${tr("Préréglage conseillé", "Suggested preset")}</td><td>${preset ? preset.label : esc(I.preset || "—")}</td></tr>
    </table>
    <p class="small" style="margin-top:10px">${esc(I.raison || "")}</p>
    ${(I.idees_ambiance || []).length ? `<p class="small muted" style="margin-bottom:4px">${tr("Idées pour les images d'ambiance :", "Ideas for the ambiance images:")}</p>
      <ol class="small" style="margin-top:0">${I.idees_ambiance.map(x => `<li>${esc(x)}</li>`).join("")}</ol>` : ""}
    ${(I.remarques || []).length ? `<p class="small muted" style="margin-bottom:4px">${tr("Remarques :", "Remarks:")}</p>
      <ul class="small" style="margin-top:0">${I.remarques.map(x => `<li>${esc(x)}</li>`).join("")}</ul>` : ""}
    <div class="row">
      ${applied ? "" : `<button class="primary" id="ev-apply">${tr(`Appliquer ${I.ambiance} image(s) d'ambiance`, `Apply ${I.ambiance} ambiance image(s)`)}</button>`}
      ${preset ? `<button id="ev-preset">${tr("Appliquer le préréglage", "Apply the preset")} ${preset.label}</button>` : ""}
      ${CLAUDE ? `<button id="ev-go">↻ ${tr("Réévaluer", "Re-evaluate")}</button>` : ""}</div>
    ${!applied ? (() => {
      const done = S.planches.filter(p => p.fichier).length, n0 = planches(F.images_de_vers + (S.cfg.ambiance || 0)),
            n1 = planches(F.images_de_vers + I.ambiance), full = (F.images_de_vers + (S.cfg.ambiance || 0)) % 6 === 0;
      if (!done) return "";
      const reste = Array.from({length: n1 - n0}, (_, i) => "P" + (n0 + i + 1)).join(tr(" et ", " and "));
      return `<p class="small muted" style="margin-top:8px">${tr(`Non appliquée automatiquement car ${done} planche(s) sont déjà générées.`, `Not applied automatically because ${done} panel(s) are already generated.`)}
        ${n1 > n0 && full ? tr(`En l'appliquant, ${S.planches.map(p => p.id.toUpperCase()).join(", ")} restent inchangées : il faudra seulement générer ${reste}.`,
          `If you apply it, ${S.planches.map(p => p.id.toUpperCase()).join(", ")} stay unchanged: you will only need to generate ${reste}.`)
          : tr("⚠ En l'appliquant, la dernière planche change : elle devra être régénérée.", "⚠ If you apply it, the last panel changes: it will have to be regenerated.")}
        ${tr("Sinon, garde le storyboard actuel : les passages sans paroles utilisent les photos de solo.", "Otherwise, keep the current storyboard: the parts without lyrics use the solo photos.")}</p>`; })() : ""}
  </div>`;
}
const fmtT = s => `${Math.floor(s / 60)}:${String(Math.round((s % 60) * 10) / 10).padStart(2, "0")}`;
V.preparer_bind = () => {
  calageBind();
  $("#dc-go") && ($("#dc-go").onclick = async () => {
    const v = $("#dc").value.trim(), p = v.split(":").map(Number);
    const s = p.some(isNaN) ? NaN : p.reduce((a, x) => a * 60 + x, 0);
    if (!(s >= 0)) return toast(tr("Temps invalide (ex. 0:34 ou 34)", "Invalid time (e.g. 0:34 or 34)"));
    await post(`/api/projet/${encodeURIComponent(nom())}/config`, {debut_chant: s});
    run("align", ["--repair-only"], s ? tr(`Recalage : chant à ${fmtT(s)}`, `Realignment: singing at ${fmtT(s)}`) : tr("Recalage automatique", "Automatic realignment"));
  });
  const it = $("#intention"), cnt = () => $("#int-info").textContent = tr(`${it.value.length} / 1500 caractères`, `${it.value.length} / 1500 characters`);
  it.oninput = cnt; cnt();
  $("#int-save").onclick = async () => {
    try { await post(`/api/projet/${encodeURIComponent(nom())}/config`,
        {intention: it.value.trim(), style: $("#style").value.trim() || S.cfg.style});
      toast(tr("Intention et style enregistrés ✅", "Intent and style saved ✅")); await refresh(); }
    catch (e) { toast(e.message); }
  };
  $("#whisper").onchange = async e => {
    try { await post(`/api/projet/${encodeURIComponent(nom())}/config`, {whisper: e.target.value});
      toast(S.words ? tr("Modèle enregistré : relance « Préparer » pour recaler les paroles", "Model saved: run “Prepare” again to realign the lyrics")
                    : tr("Modèle enregistré ✅", "Model saved ✅"));
      await refresh(); }
    catch (err) { toast(err.message); }
  };
  $("#go-prep").onclick = () => run("prepare", $("#prep-force").checked ? ["--force"] : [], tr("Préparer", "Prepare"));
  $("#ev-go") && ($("#ev-go").onclick = () => run("evaluate", [], tr("Évaluation du storyboard", "Storyboard evaluation")));
  $("#so-go") && ($("#so-go").onclick = () => {
    const args = ["--nombre", String(Math.max(1, Math.min(8, +$("#so-n").value || 3)))], c = $("#so-c").value.trim();
    if (c) args.push("--consigne", c.slice(0, 300));
    run("solos", args, tr("Prompts des photos de solo", "Solo photo prompts"));
  });
  document.querySelectorAll("[data-socp]").forEach(b => b.onclick = () => copy(S.solos_prompts[+b.dataset.socp].prompt));
  document.querySelectorAll("[data-sodz]").forEach(d => dropzone(d, "solo", "image/*", d.dataset.sodz));
  $("#ev-apply") && ($("#ev-apply").onclick = () => run("evaluate", ["--appliquer"], tr("Application de la recommandation", "Applying the recommendation")));
  $("#ev-preset") && ($("#ev-preset").onclick = async () => {
    const p = PRESETS[PRESET_KEYS[S.evaluation.ia.preset]];
    await post(`/api/projet/${encodeURIComponent(nom())}/config`, p.cfg);
    toast(tr("Préréglage appliqué ✅ (modifiable à l'étape 6)", "Preset applied ✅ (can be changed at step 6)")); refresh();
  });
  $("#amb-save").onclick = async () => { await post(`/api/projet/${encodeURIComponent(nom())}/config`, {ambiance: +$("#amb").value});
    run("prompts", [], tr("Recalcul des images", "Recomputing the images")); };
};

let CLAUDE = null;   // chemin de Claude Code, ou null
V.descriptions = () => {
  const todo = S.shots.filter(s => !s.description).length;
  const planchesFaites = S.planches.some(p => p.fichier);
  return `
  <h2>3. ${tr("Descriptions des scènes", "Scene descriptions")}</h2><p class="lead">${tr("Chaque image doit illustrer son vers. Claude les rédige avec ton abonnement, en un clic.", "Each image must illustrate its lyric line. Claude writes them with your subscription, in one click.")}</p>
  ${S.desc_erreur ? `<div class="steps-hint"><b>${tr("descriptions.json est invalide.", "descriptions.json is invalid.")}</b> ${tr("Relance la rédaction ou recolle une réponse ci-dessous.", "Run the writing again or paste an answer again below.")}</div>` : ""}
  <div class="card"><h3>✨ ${tr("Rédaction par Claude", "Writing by Claude")}</h3>
    ${CLAUDE ? `
      <p class="small muted">${tr("Utilise Claude Code avec ton compte Claude (quota de ton abonnement, sans coût en plus).", "Uses Claude Code with your Claude account (your subscription quota, no extra cost).")}
        ${todo ? tr(`<b>${todo}</b> image(s) à décrire.`, `<b>${todo}</b> image(s) to describe.`) : tr("Toutes les images sont décrites.", "All images are described.")}</p>
      <div class="row"><input type="text" id="ai-consigne" placeholder="${tr("Consigne facultative : ex. plus sombre, ton absurde, décor années 80…", "Optional instruction: e.g. darker, absurd tone, 80s setting…")}" style="flex:1;min-width:260px">
        <label class="small"><input type="checkbox" id="ai-tout"> ${tr("tout réécrire", "rewrite all")}</label>
        <button class="primary" id="ai-go">✨ ${tr("Rédiger avec Claude", "Write with Claude")}</button></div>
      ${planchesFaites ? `<p class="small muted" style="margin-top:8px">${tr("⚠ Des planches sont déjà générées : une description modifiée demandera de régénérer sa planche, ou de retoucher la case (étape 4).",
        "⚠ Some panels are already generated: a changed description will require regenerating its panel, or retouching the cell (step 4).")}</p>` : ""}`
    : `<p>${tr("Claude Code est introuvable sur ce PC.", "Claude Code was not found on this computer.")}</p><p class="small muted">${tr("Installe l'extension <b>Claude Code</b> dans VS Code (ou Claude Code seul), connecte-toi une fois avec ton compte Claude (Pro ou Max), puis recharge cette page. En attendant, utilise le copier-coller ci-dessous.",
        "Install the <b>Claude Code</b> extension in VS Code (or Claude Code alone), sign in once with your Claude account (Pro or Max), then reload this page. Meanwhile, use the copy-paste below.")}</p>`}
  </div>
  ${Object.keys(S.cfg.personnages || {}).length ? `<div class="card"><h3>${tr("Personnages récurrents", "Recurring characters")}</h3><table>
    ${Object.entries(S.cfg.personnages).map(([k, v]) => `<tr><td><b>${esc(k)}</b></td><td>${esc(v)}</td></tr>`).join("")}</table></div>` : ""}
  <div class="card"><h3>${tr("Images", "Images")}</h3><table><tr><th>Image</th><th>${tr("Vers", "Line")}</th><th>Description</th><th></th></tr>
    ${S.shots.map(s => `<tr><td>${s.id}</td><td>${s.ambiance ? `<i class="muted">${tr("ambiance", "ambiance")}</i>` : esc(s.texte)}</td>
      <td class="small">${s.description ? esc(s.description) : `<span class="pill warn">${tr("à décrire", "to describe")}</span>`}</td>
      <td>${CLAUDE && s.description ? `<button title="${tr("Faire réécrire cette image par Claude", "Have Claude rewrite this image")}" data-redo="${s.id}">↻</button>` : ""}</td></tr>`).join("")}</table></div>
  <details class="card" ${CLAUDE ? "" : "open"}><summary><b>${tr("Sans Claude Code : copier-coller", "Without Claude Code: copy-paste")}</b> <span class="muted small">— ${tr("avec n'importe quelle IA", "with any AI")}</span></summary>
    ${todo ? `<p class="small muted">${tr("Copie la demande, colle-la dans une IA, puis colle sa réponse JSON ci-dessous.", "Copy the request, paste it into an AI, then paste its JSON answer below.")}</p>
      <div class="row"><button id="cp-ask">📋 ${tr("Copier la demande", "Copy the request")}</button></div>
      <pre class="code">${esc(S.a_decrire || tr("Lance d'abord « Préparer ».", "Run “Prepare” first."))}</pre>` : ""}
    <textarea id="resp" rows="6" placeholder='${tr('{"p1_c1": "Plan : … ; Sujet : … ; Action : … ; Décor : … ; Lumière : …", …}', '{"p1_c1": "Shot: … ; Subject: … ; Action: … ; Setting: … ; Lighting: …", …}')}'></textarea>
    <div class="row" style="margin-top:10px"><button id="save-resp">${tr("Enregistrer et générer les prompts", "Save and generate the prompts")}</button></div></details>
  ${!todo && S.shots.length ? nextHint("planches", next(tr("Planches", "Panels"))) : ""}`;
};
V.descriptions_bind = () => {
  $("#ai-go") && ($("#ai-go").onclick = () => {
    const args = [], c = $("#ai-consigne").value.trim();
    if ($("#ai-tout").checked) args.push("--tout");
    if (c) args.push("--consigne", c.slice(0, 300));
    run("describe", args, tr("Rédaction par Claude", "Writing by Claude"));
  });
  document.querySelectorAll("[data-redo]").forEach(b => b.onclick = () => {
    const c = prompt(tr(`Réécrire ${b.dataset.redo}.\nConsigne facultative (ex. « plus drôle », « sans personnage ») :`,
      `Rewrite ${b.dataset.redo}.\nOptional instruction (e.g. “funnier”, “no character”):`), "");
    if (c === null) return;
    const args = ["--ids", b.dataset.redo]; if (c.trim()) args.push("--consigne", c.trim().slice(0, 300));
    run("describe", args, tr(`Réécriture de ${b.dataset.redo}`, `Rewriting ${b.dataset.redo}`));
  });
  $("#cp-ask") && ($("#cp-ask").onclick = () => copy(S.a_decrire));
  $("#save-resp").onclick = async () => {
    const txt = $("#resp").value.trim(); if (!txt) return toast(tr("Colle d'abord la réponse de Claude", "Paste Claude's answer first"));
    try { const r = await post(`/api/projet/${encodeURIComponent(nom())}/descriptions`, txt);
      toast(tr(`${r.n} description(s) enregistrée(s)`, `${r.n} description(s) saved`)); run("prompts", [], tr("Génération des prompts", "Generating the prompts")); }
    catch (e) { toast(tr("JSON invalide : ", "Invalid JSON: ") + e.message, 6000); }
  };
};

// ------------------------------------------------------------------ vidéos (image → vidéo)
let VSEL = new URLSearchParams(location.search).get("sel");     // ?sel=p1_c3 : image présélectionnée
function vidItems() {
  const solos = S.solos.map(f => ({id: f.toLowerCase().replace(/\.[^.]+$/, ""), texte: tr("Solo (travelling)", "Solo (tracking shot)"),
    src: file(encodeURIComponent(S.solos_dir) + "/" + encodeURIComponent(f))}));
  const cases = S.shots.filter(s => s.case).map(s => ({id: s.id, texte: s.texte || tr("ambiance", "ambiance"), src: file("cases/" + s.id + ".png")}));
  return [...solos, ...cases];
}
const clipOf = id => S.clips.find(f => f.toLowerCase().replace(/\.[^.]+$/, "") === id);
const vpOf = id => S.clips_prompts.find(v => v.id === id);
V.videos = () => {
  const items = vidItems();
  const h = `<h2>5. ${tr("Vidéos", "Videos")}`;
  if (!items.length) return `${h}</h2><div class="card"><p class="muted">${tr("Découpe d'abord les planches (étape 4) : les images apparaîtront ici.", "Cut the panels first (step 4): the images will show up here.")}</p></div>`;
  if (!items.some(i => i.id === VSEL)) VSEL = null;
  const sel = items.find(i => i.id === VSEL), vp = sel && vpOf(sel.id), clip = sel && clipOf(sel.id);
  return `${h} <span class="muted small">— ${tr("optionnel", "optional")}</span></h2>
  <div class="steps-hint small">${tr("Choisis une image pour la changer en <b>vidéo de ~10 s</b> (Flow, Veo…). La vidéo remplace l'image au montage partout où elle apparaît, les effets et le karaoké restent par-dessus. Rien n'est demandé à Claude sans ton clic.",
    "Pick an image to turn it into a <b>~10 s video</b> (Flow, Veo…). The video replaces the image in the edit wherever it appears; effects and karaoke stay on top. Nothing is asked of Claude without your click.")}</div>
  ${sel ? `<div class="card planche" style="grid-template-columns:1fr 320px"><div>
      <div class="row"><h3 style="margin:0">${sel.id}</h3><span class="muted small">— ${esc(sel.texte)}</span>
        ${clip ? `<span class="pill ok">${tr("vidéo déposée", "video dropped")}</span>` : vp ? `<span class="pill warn">${tr("prompt prêt, vidéo à générer", "prompt ready, video to generate")}</span>` : `<span class="pill">${tr("image fixe", "still image")}</span>`}
        <div style="flex:1"></div><button id="vs-close">✕</button></div>
      <ol class="small" style="margin:8px 0 8px 18px;padding:0">
        <li>${tr("Dans Flow : <b>« Images vers vidéo »</b>, format 16:9, image de départ = l'image ci-contre (clic droit → Enregistrer).", "In Flow: <b>“Images to video”</b>, 16:9 format, starting image = the image opposite (right-click → Save).")}</li>
        <li>${vp ? tr("Colle le prompt ci-dessous.", "Paste the prompt below.") : tr("Colle le prompt (demande-le à Claude, ou écris le tien).", "Paste the prompt (ask Claude for it, or write your own).")}</li>
        <li>${tr("Dépose la vidéo obtenue ici, puis fais un rendu (étape 7).", "Drop the resulting video here, then make a render (step 7).")}</li></ol>
      ${vp ? `<div class="row"><b>${esc(vp.titre || "")}</b><div style="flex:1"></div><button class="primary" id="vs-copy">📋 ${tr("Copier le prompt", "Copy the prompt")}</button></div>
        <pre class="code" style="max-height:200px">${esc(vp.prompt)}</pre>` : ""}
      ${CLAUDE ? `<div class="row" style="margin-top:8px"><button id="vs-ai">✨ ${vp ? tr("Refaire le prompt vidéo avec Claude", "Redo the video prompt with Claude") : tr("Écrire le prompt vidéo avec Claude", "Write the video prompt with Claude")}</button>
        <input id="vs-c" placeholder="${tr("Consigne (optionnel), ex. « la caméra tourne autour »", "Instruction (optional), e.g. “the camera circles around”")}" style="flex:1" maxlength="300"></div>` : ""}
    </div><div>
      ${clip ? `<video class="thumb" src="${file("videos/" + encodeURIComponent(clip))}" controls muted loop></video>`
             : `<img class="thumb" src="${sel.src}" title="${tr("Image de départ", "Starting image")}">`}
      <div class="drop" data-vdz="${sel.id}" style="margin-top:8px"><b>${replaceDrop(clip, sel.id + ".mp4")}</b></div>
      ${clip ? `<button data-vdel="${sel.id}" style="margin-top:6px">${tr("Retirer la vidéo (revenir à l'image)", "Remove the video (back to the image)")}</button>` : ""}
    </div></div>` : ""}
  <div class="card"><h3>${tr("Images du clip", "Video images")} <span class="muted small">— ${tr("clique pour animer", "click to animate")}</span></h3>
    <div class="vgrid">${items.map(i => `<a class="vtile ${i.id === VSEL ? "on" : ""}" data-vsel="${i.id}">
      <img src="${i.src}" loading="lazy"><div class="small"><b>${i.id}</b>
      ${clipOf(i.id) ? `<span class="pill ok">🎬 ${tr("vidéo", "video")}</span>` : vpOf(i.id) ? '<span class="pill warn">prompt</span>' : ""}</div>
      <div class="small muted vt">${esc(i.texte)}</div></a>`).join("")}</div></div>
  ${CLAUDE ? `<details class="card"><summary><b>${tr("Laisser Claude choisir plusieurs images", "Let Claude pick several images")}</b> <span class="muted small">— ${tr("celles qui restent le plus longtemps à l'écran", "those that stay on screen the longest")}</span></summary>
    <div class="row" style="margin-top:8px"><button id="vi-go">✨ ${tr("Créer les prompts vidéo", "Create the video prompts")}</button>
      <label class="small">${tr("Nombre", "Number")} <input id="vi-n" type="number" min="1" max="8" value="5" style="width:52px"></label>
      <input id="vi-c" placeholder="${tr("Consigne (optionnel), ex. « surtout les solos »", "Instruction (optional), e.g. “mostly the solos”")}" style="flex:1" maxlength="300"></div>
    <p class="small muted">${tr("Nécessite un aperçu ou un rendu déjà fait. Remplace les prompts existants.", "Requires a preview or a render already made. Replaces the existing prompts.")}</p></details>` : ""}
  ${S.clips.length ? `<p class="small">➡ ${tr(`${S.clips.length} vidéo(s) déposée(s) : fais un <b>Rendu final</b> pour les intégrer.`, `${S.clips.length} video(s) dropped: make a <b>Final render</b> to include them.`)}</p>` : ""}
  ${nextHint("options", next(tr("Options", "Options")))}`;
};
V.videos_bind = () => {
  document.querySelectorAll("[data-vsel]").forEach(a => a.onclick = () => { VSEL = a.dataset.vsel; renderStep(); window.scrollTo(0, 0); });
  $("#vs-close") && ($("#vs-close").onclick = () => { VSEL = null; renderStep(); });
  $("#vs-copy") && ($("#vs-copy").onclick = () => copy(vpOf(VSEL).prompt));
  $("#vs-ai") && ($("#vs-ai").onclick = () => {
    const args = ["--ids", VSEL], c = $("#vs-c").value.trim();
    if (c) args.push("--consigne", c.slice(0, 300));
    run("videos", args, tr(`Prompt vidéo ${VSEL}`, `Video prompt ${VSEL}`));
  });
  $("#vi-go") && ($("#vi-go").onclick = () => {
    if (S.clips_prompts.length && !confirm(tr("Remplacer les prompts vidéo actuels?", "Replace the current video prompts?"))) return;
    const args = ["--nombre", String(Math.max(1, Math.min(8, +$("#vi-n").value || 5)))], c = $("#vi-c").value.trim();
    if (c) args.push("--consigne", c.slice(0, 300));
    run("videos", args, tr("Prompts vidéo", "Video prompts"));
  });
  document.querySelectorAll("[data-vcp]").forEach(b => b.onclick = () => copy(S.clips_prompts.find(v => v.id === b.dataset.vcp).prompt));
  document.querySelectorAll("[data-vdz]").forEach(d => dropzone(d, "video", "video/*,.mp4,.mov,.webm,.m4v", d.dataset.vdz));
  document.querySelectorAll("[data-vdel]").forEach(b => b.onclick = async () => {
    if (!confirm(tr(`Retirer la vidéo ${b.dataset.vdel}? L'image reprend sa place au prochain rendu.`, `Remove the video ${b.dataset.vdel}? The image takes its place back at the next render.`))) return;
    try { await post(`/api/projet/${encodeURIComponent(nom())}/retirer-clip?id=${b.dataset.vdel}`); toast(tr("Vidéo retirée", "Video removed")); refresh(); }
    catch (e) { toast(e.message); } });
};
function promptFor(id) {
  const m = S.prompts.split(/\n## /).find(b => b.toUpperCase().startsWith(id.toUpperCase() + " "));
  const code = m && m.match(/```\n([\s\S]*?)```/); return code ? code[1].trim() : "";
}
V.planches = () => `
  <h2>4. ${tr("Planches", "Panels")}</h2><p class="lead">${tr("Génère chaque planche avec son prompt, puis dépose l'image ici.", "Generate each panel with its prompt, then drop the image here.")}</p>
  ${!S.prompts ? `<div class="card"><h3>${tr("Les prompts ne sont pas encore prêts", "The prompts are not ready yet")}</h3>
    <p class="small muted">${tr("Il faut d'abord une description pour chaque image", "Each image first needs a description")}${S.shots.length
      ? tr(` (${S.shots.filter(s => !s.description).length} manquante(s) sur ${S.shots.length})`, ` (${S.shots.filter(s => !s.description).length} missing out of ${S.shots.length})`)
      : tr(" : lance d'abord « Préparer » (étape 2)", ": run “Prepare” first (step 2)")}.</p>
    <div class="row">${CLAUDE && S.shots.length ? `<button class="primary" id="pl-describe">✨ ${tr("Rédiger les descriptions avec Claude", "Write the descriptions with Claude")}</button>` : ""}
      <button onclick="go('descriptions')">${tr("Voir l'étape 3", "See step 3")} →</button></div></div>` : `
  <div class="steps-hint small">${tr(`Dans le générateur : <b>nouvelle génération vierge</b> (pas une variation de l'image précédente), format <b>${esc(S.planches[0]?.ratio || "32:27")}</b> si disponible (sinon carré), puis dépose le résultat dans la bonne planche.<br>
    <b>Astuce :</b> clic droit sur l'image dans le générateur → « Copier l'image », puis <b>Ctrl+V</b> ici : elle va dans la planche survolée, ou sinon dans la première planche encore vide.`,
    `In the generator: <b>new blank generation</b> (not a variation of the previous image), <b>${esc(S.planches[0]?.ratio || "32:27")}</b> format if available (otherwise square), then drop the result in the right panel.<br>
    <b>Tip:</b> right-click the image in the generator → “Copy image”, then <b>Ctrl+V</b> here: it goes into the hovered panel, or otherwise into the first panel still empty.`)}</div>
  <div class="planches">${S.planches.map(p => `
    <div class="card planche"><div>
      <div class="row"><h3 style="margin:0">${p.id.toUpperCase()}</h3>
        <span class="pill">${tr("grille", "grid")} ${p.grid[0]}×${p.grid[1]}</span>
        ${p.fichier ? `<span class="pill ok">${tr("image déposée", "image dropped")}</span>` : `<span class="pill warn">${tr("à générer", "to generate")}</span>`}
        ${p.decoupees ? `<span class="pill ok">${tr(`${p.decoupees} cases découpées`, `${p.decoupees} cells cut`)}</span>` : ""}
        <div style="flex:1"></div>
        ${CLAUDE ? `<button data-redopl="${p.id}" title="${tr("Réécrire les descriptions des cases de cette planche", "Rewrite the descriptions of this panel's cells")}">✨ ${tr("Refaire avec Claude", "Redo with Claude")}</button>` : ""}
        <button class="primary" data-cp="${p.id}">📋 ${tr("Copier le prompt", "Copy the prompt")}</button></div>
      <pre class="code">${esc(promptFor(p.id))}</pre></div>
      <div>${p.fichier ? `<img class="thumb" src="${file(encodeURIComponent(S.cfg.planches || "planches") + "/" + encodeURIComponent(p.fichier))}">` : ""}
        <div class="drop" data-dz="${p.id}" style="margin-top:8px"><b>${replaceDrop(p.fichier, p.id.toUpperCase())}</b></div></div>
    </div>`).join("")}</div>
  <div class="card"><h3>${tr("Vérifier et découper", "Check and cut")}</h3>
    <p class="small muted">${tr("Contrôle le format et la grille, découpe les cases et les agrandit (×4). Fait aussi automatiquement au rendu.", "Checks the format and the grid, cuts the cells and upscales them (×4). Also done automatically at render time.")}</p>
    <div class="row"><button id="verify">${tr("Vérifier les planches", "Check the panels")}</button><button class="primary" id="cut">${tr("Découper les cases", "Cut the cells")}</button></div>
    ${Object.keys(S.texte_detecte || {}).length ? `<div class="steps-hint" style="margin-top:12px;border-color:var(--warn)">
      ⚠ <b>${tr("Texte lisible détecté", "Readable text detected")}</b> ${tr("(légende, enseigne…) : retouche la case si ce n'est pas voulu (ci-dessous « Retoucher une seule case »).", "(caption, sign…): retouch the cell if it is not intended (below, “Retouch a single cell”).")}
      <ul class="small" style="margin:6px 0 0">${Object.entries(S.texte_detecte).map(([k, v]) =>
        `<li><b>${k}</b> — « ${esc(v.join(" / ").slice(0, 80))} »</li>`).join("")}</ul></div>` : ""}
    ${S.contact ? `<img class="thumb" style="margin-top:12px" src="${file("build/planche_contact.jpg")}">` : ""}</div>
  <details class="card"><summary><b>${tr("Retoucher une seule case", "Retouch a single cell")}</b> <span class="muted small">— ${tr("sans refaire toute la planche", "without redoing the whole panel")}</span></summary>
    <p class="small muted">${tr("Génère une image 16:9 seule pour la case ratée et dépose-la : elle remplace la case au prochain rendu.", "Generate a single 16:9 image for the failed cell and drop it: it replaces the cell at the next render.")}</p>
    <div class="row"><select id="rt-id">${S.shots.map(s => `<option value="${s.id}">${s.id} — ${esc(s.texte || tr("ambiance", "ambiance"))}${s.retouche ? tr(" (retouchée)", " (retouched)") : ""}</option>`).join("")}</select>
      <button id="rt-up">${tr("Déposer l'image de retouche", "Drop the retouch image")}</button><button id="rt-paste">📋 ${tr("Coller", "Paste")}</button></div></details>
  ${S.planches.every(p => p.fichier) ? nextHint("videos", next(tr("Vidéos (optionnel)", "Videos (optional)"))) : ""}`}`;
V.planches_bind = () => {
  document.querySelectorAll("[data-cp]").forEach(b => b.onclick = () => copy(promptFor(b.dataset.cp)));
  $("#pl-describe") && ($("#pl-describe").onclick = () => run("describe", [], tr("Rédaction par Claude", "Writing by Claude")));
  document.querySelectorAll("[data-redopl]").forEach(b => b.onclick = () => {
    const pid = b.dataset.redopl, ids = S.shots.filter(s => s.id.startsWith(pid + "_")).map(s => s.id);
    const pl = S.planches.find(p => p.id === pid);
    const c = prompt(tr(`Réécrire les ${ids.length} descriptions de ${pid.toUpperCase()} (scènes différentes).`, `Rewrite the ${ids.length} descriptions of ${pid.toUpperCase()} (different scenes).`)
      + (pl && pl.fichier ? tr("\n⚠ Cette planche est déjà générée : il faudra la régénérer.", "\n⚠ This panel is already generated: it will have to be regenerated.") : "")
      + tr("\nConsigne facultative (ex. « plus drôle », « plus sombre ») :", "\nOptional instruction (e.g. “funnier”, “darker”):"), "");
    if (c === null) return;
    const args = ["--ids", ids.join(",")]; if (c.trim()) args.push("--consigne", c.trim().slice(0, 300));
    run("describe", args, tr(`Réécriture de ${pid.toUpperCase()}`, `Rewriting ${pid.toUpperCase()}`));
  });
  document.querySelectorAll("[data-dz]").forEach(d => dropzone(d, "planche", "image/*", d.dataset.dz));
  $("#verify") && ($("#verify").onclick = () => run("verify", [], tr("Vérification des planches", "Checking the panels")));
  $("#cut") && ($("#cut").onclick = () => run("cut", [], tr("Découpe des cases", "Cutting the cells")));
  $("#rt-up") && ($("#rt-up").onclick = () => pick("image/*", f => upload("retouche", f, $("#rt-id").value)));
  $("#rt-paste") && ($("#rt-paste").onclick = async () => {
    try { const id = $("#rt-id").value; upload("retouche", imgFile(await readClipboardImage(), id), id); }
    catch (err) { toast(err.message, 5000); } });
};

// ------------------------------------------------------------------ options
const PRESETS = {
  ballade: {label: tr("🎻 Ballade", "🎻 Ballad"), cfg: {pulse: 0, pulse_mesure: false, fondu: 1.2, transition: "fondu", camera: "auto", look: "cinema",
    harmonisation: true, variantes: true, look_sections: true, particules: "auto", karaoke_animation: "remplir", fuites_lumiere: 0.4, tremblement: 0, projecteurs: 0, glitch: null}},
  rock: {label: "🎸 Rock", cfg: {pulse: 1, pulse_mesure: true, fondu: 0.15, transition: "fondu", camera: "auto", look: "cinema",
    harmonisation: true, variantes: true, look_sections: true, particules: "auto", karaoke_animation: "grossir", tremblement: 0.4, tremblement_zone: "refrains", projecteurs: 0.5, fuites_lumiere: 0}},
  vhs: {label: tr("📼 VHS rétro", "📼 Retro VHS"), cfg: {pulse: 0.5, pulse_mesure: true, fondu: 0.3, transition: "flash", camera: "auto", look: "vhs",
    harmonisation: true, variantes: true, look_sections: false, letterbox: false, karaoke_animation: "aucune", glitch: "transitions", rvb_beat: 0.3}},
  sobre: {label: tr("▫️ Sobre", "▫️ Plain"), cfg: {pulse: 0, pulse_mesure: false, fondu: 0.5, transition: "fondu", camera: "zoom", look: "aucun",
    letterbox: false, harmonisation: false, variantes: false, look_sections: false, particules: null,
    parallaxe: false, karaoke_animation: "aucune", fuites_lumiere: 0, projecteurs: 0, tremblement: 0,
    rvb_beat: 0, glitch: null, vieux_film: 0, eclairs: null, rayons: null, fumee: null, flammes: null, visualiseur: null, flou_fond: 0, brume_profondeur: 0}},
};
const FONTS = ["Arial", "Arial Black", "Impact", "Bahnschrift", "Segoe UI Black", "Trebuchet MS", "Verdana",
  "Georgia", "Courier New", "Comic Sans MS"];
const CORNER_OPTS = tr("haut-gauche=En haut à gauche|haut-droite=En haut à droite|bas-gauche=En bas à gauche|bas-droite=En bas à droite",
  "haut-gauche=Top left|haut-droite=Top right|bas-gauche=Bottom left|bas-droite=Bottom right");
const PSEC = [["intro", "Intro"], ["couplet", tr("Couplets", "Verses")], ["refrain", tr("Refrains", "Choruses")], ["pont", tr("Pont", "Bridge")],
  ["instrumental", tr("Instrumentaux", "Instrumentals")], ["outro", "Outro"]];
const PART = tr("braises=Braises|etincelles=Étincelles|neige=Neige|pluie=Pluie|confettis=Confettis dorés|bokeh=Bokeh / lucioles|poussiere=Poussière",
  "braises=Embers|etincelles=Sparks|neige=Snow|pluie=Rain|confettis=Gold confetti|bokeh=Bokeh / fireflies|poussiere=Dust");
const OPTS = [
  [tr("Titre et signature", "Title and signature"), [
    ["titre", "text", tr("Titre de la chanson", "Song title"), tr("Affiché en fondu sur l'intro. Vide = pas de titre.", "Faded in over the intro. Empty = no title.")],
    ["artiste", "text", tr("Artiste / groupe", "Artist / band"), tr("Sous le titre et dans le générique.", "Under the title and in the end credits.")],
    ["generique", "bool", tr("Générique de fin", "End credits"), tr("« Titre — Artiste » sur les dernières secondes.", "“Title — Artist” over the last seconds.")],
    ["mention_ia_ecran", "bool", tr("Mention IA à l'écran", "AI notice on screen"), tr("Petit texte discret affiché pendant tout le clip.", "Small discreet text shown during the whole video.")],
    ["mention_ia_texte", "text", tr("Texte de la mention", "Notice text"), tr("Ex. « Version IA », « Clip IA ». Vide = selon la langue de la chanson.", "E.g. “AI Version”, “AI Video”. Empty = based on the song's language.")],
    ["mention_ia_position", "select:" + CORNER_OPTS, tr("Coin de la mention", "Notice corner"), ""],
    ["logo", "logo", tr("Logo du groupe", "Band logo"), tr("PNG avec fond transparent de préférence.", "PNG with a transparent background preferably.")],
    ["logo_position", "select:" + CORNER_OPTS, tr("Coin du logo", "Logo corner"), ""]]],
  [tr("Karaoké", "Karaoke"), [
    ["karaoke_mode", tr("select:mot=Mot à mot (karaoké)|ligne=Ligne entière (sous-titre simple)|aucun=Aucune parole", "select:mot=Word by word (karaoke)|ligne=Whole line (simple subtitle)|aucun=No lyrics"), tr("Affichage des paroles", "Lyrics display"), ""],
    ["font", "font", tr("Police", "Font"), ""],
    ["karaoke_taille", "range:24:96:2", tr("Taille du texte", "Text size"), tr("46 = taille habituelle.", "46 = usual size.")],
    ["karaoke_couleur", "color", tr("Couleur du mot chanté", "Sung word color"), ""],
    ["karaoke_texte", "color", tr("Couleur du texte", "Text color"), ""],
    ["karaoke_position", tr("select:bas=En bas|haut=En haut|centre=Au centre", "select:bas=Bottom|haut=Top|centre=Center"), tr("Position", "Position"), ""],
    ["karaoke_animation", tr("select:aucune=Changement de couleur|grossir=Le mot grossit|remplir=Remplissage progressif", "select:aucune=Color change|grossir=The word grows|remplir=Progressive fill"), tr("Animation du mot", "Word animation"), ""],
    ["karaoke_suivante", "bool", tr("Afficher la ligne suivante", "Show the next line"), tr("En plus petit, pour anticiper (style karaoké).", "Smaller, to read ahead (karaoke style).")],
    ["karaoke_majuscules", "bool", tr("Tout en majuscules", "All caps"), ""],
    ["karaoke_decalage", "range:-2:2:0.05", tr("Décalage des paroles (s)", "Lyrics offset (s)"), tr("Si tout le karaoké est en avance (+) ou en retard (−).", "If the whole karaoke is early (+) or late (−).")],
    ["bar_alpha", "range:0:255:5", tr("Ombre sous les paroles", "Shadow under the lyrics"), tr("Opacité du dégradé derrière le texte (sans bandes noires).", "Opacity of the gradient behind the text (no black bars).")]]],
  [tr("Rythme et montage", "Rhythm and editing"), [
    ["pulse", "range:0:1:0.1", tr("Effet au beat", "Beat effect"), tr("Gonflement + flash blanc sur les temps. 0 pour une ballade.", "Swell + white flash on the beats. 0 for a ballad.")],
    ["pulse_mesure", "bool", tr("Seulement le 1er temps", "First beat only"), tr("Effet beat 1 fois par mesure (moins répétitif, idéal rock).", "Beat effect once per bar (less repetitive, great for rock).")],
    ["transition", tr("select:fondu=Fondu enchaîné|coupe=Coupe sèche|noir=Fondu au noir|flash=Flash blanc|glissement=Glissement latéral|zoom=Zoom qui s'efface",
      "select:fondu=Crossfade|coupe=Hard cut|noir=Fade to black|flash=White flash|glissement=Side slide|zoom=Fading zoom"), tr("Transition entre images", "Transition between images"), ""],
    ["fondu", "range:0.1:3:0.05", tr("Durée de la transition (s)", "Transition duration (s)"), tr("0,15 = rapide (rock) · 1,2 = douce (ballade).", "0.15 = fast (rock) · 1.2 = soft (ballad).")],
    ["duree_max_image", "range:0:20:1", tr("Durée max d'une image (s)", "Max image duration (s)"), tr("0 = désactivé. Au-delà, le plan est redécoupé avec un autre mouvement de caméra.", "0 = off. Beyond it, the shot is split again with another camera move.")],
    ["tremblement", "range:0:1:0.05", tr("Tremblement de caméra au beat", "Camera shake on the beat"), tr("0 = aucun.", "0 = none.")],
    ["tremblement_zone", tr("select:partout=Toute la chanson|refrains=Seulement les refrains", "select:partout=The whole song|refrains=Choruses only"), tr("Tremblement : où", "Shake: where"), ""],
    ["rvb_beat", "range:0:1:0.05", tr("Décalage RVB au beat", "RGB split on the beat"), tr("Les couleurs se séparent un instant sur chaque temps. 0 = aucun.", "The colors split for an instant on each beat. 0 = none.")],
    ["glitch", tr("select:null=Aucun|beats=Sur certains beats|transitions=Aux changements d'image|les_deux=Les deux", "select:null=None|beats=On some beats|transitions=On image changes|les_deux=Both"), tr("Glitch numérique", "Digital glitch"), ""],
    ["glitch_intensite", "range:0.3:2:0.1", tr("Intensité du glitch", "Glitch intensity"), ""]]],
  [tr("Lumière", "Light"), [
    ["fuites_lumiere", "range:0:1:0.05", tr("Fuites de lumière", "Light leaks"), tr("Halos chauds qui traversent l'image, plus forts aux changements d'image. 0 = aucune.", "Warm halos crossing the image, stronger on image changes. 0 = none.")],
    ["projecteurs", "range:0:1:0.05", tr("Projecteurs de concert au beat", "Concert spotlights on the beat"), tr("Lavage coloré (rouge, bleu, rose…) depuis un coin, à chaque temps. 0 = aucun.", "Colored wash (red, blue, pink…) from a corner, on each beat. 0 = none.")],
    ["eclairs", tr("select:null=Aucun|auto=Automatique (orage, tempête, foudre…)|partout=Partout", "select:null=None|auto=Automatic (storm, lightning, thunder…)|partout=Everywhere"), tr("Éclairs", "Lightning"), tr("Double flash bleuté toutes les ~7 s.", "Bluish double flash every ~7 s.")],
    ["rayons", tr("select:null=Aucun|auto=Automatique (église, projecteur, faisceau…)|partout=Partout", "select:null=None|auto=Automatic (church, spotlight, beam…)|partout=Everywhere"), tr("Rayons de lumière", "Light rays"), tr("Faisceaux qui tombent d'en haut à travers l'air.", "Beams falling from above through the air.")],
    ["rayons_intensite", "range:0.3:2:0.1", tr("Intensité des rayons", "Ray intensity"), ""]]],
  [tr("Pellicule et son", "Film and sound"), [
    ["vieux_film", "range:0:1:0.05", tr("Vieux film", "Old film"), tr("Rayures, poussières, sautillement et scintillement. Se marie bien avec Sépia ou Noir et blanc. 0 = aucun.", "Scratches, dust, jitter and flicker. Goes well with Sepia or Black and white. 0 = none.")],
    ["visualiseur", tr("select:null=Aucun|barres=Barres de spectre|onde=Forme d'onde", "select:null=None|barres=Spectrum bars|onde=Waveform"), tr("Visualiseur audio", "Audio visualizer"), tr("Réagit à la musique, en bas de l'image.", "Reacts to the music, at the bottom of the image.")],
    ["visualiseur_zone", tr("select:instrumentaux=Seulement sans paroles (instrumentaux)|partout=Toute la chanson", "select:instrumentaux=Only without lyrics (instrumentals)|partout=The whole song"), tr("Visualiseur : quand", "Visualizer: when"), ""],
    ["visualiseur_couleur", "color", tr("Couleur du visualiseur", "Visualizer color"), ""],
    ["visualiseur_hauteur", "range:0.05:0.3:0.01", tr("Hauteur du visualiseur", "Visualizer height"), tr("Fraction de la hauteur de l'image.", "Fraction of the image height.")]]],
  [tr("Profondeur", "Depth"), [
    ["flou_fond", "range:0:1:0.05", tr("Flou d'arrière-plan", "Background blur"), tr("Le fond devient flou, le sujet reste net (effet objectif photo). 0 = aucun.", "The background gets blurry, the subject stays sharp (camera lens effect). 0 = none.")],
    ["brume_profondeur", "range:0:1:0.05", tr("Brume en profondeur", "Depth haze"), tr("Le fond s'efface dans une brume claire. 0 = aucune. (Utilisent les cartes de profondeur, calculées une fois.)", "The background fades into a light haze. 0 = none. (Both use depth maps, computed once.)")]]],
  [tr("Caméra", "Camera"), [
    ["camera", tr("select:zoom=Zoom lent qui oscille|auto=Selon le plan (large, moyen, gros plan)", "select:zoom=Slow oscillating zoom|auto=Based on the shot (wide, medium, close-up)"), tr("Mouvement", "Movement"), tr("« Selon le plan » : travelling sur les plans larges, zoom avant sur les gros plans.", "“Based on the shot”: tracking on wide shots, zoom-in on close-ups.")],
    ["camera_intensite", "range:0.3:2:0.1", tr("Intensité du mouvement", "Movement intensity"), tr("1 = normal.", "1 = normal.")],
    ["parallaxe", tr("select:false=Désactivée|0.02=Légère|0.03=Moyenne|0.05=Forte|0.07=Très forte", "select:false=Off|0.02=Light|0.03=Medium|0.05=Strong|0.07=Very strong"), tr("Profondeur 3D (parallaxe)", "3D depth (parallax)"), tr("Le premier plan bouge plus que le fond. Rendu ~40 % plus long.", "The foreground moves more than the background. Render ~40% longer.")]]],
  ["Look", [
    ["look", tr("select:aucun=Naturel|cinema=Cinéma|nb=Noir et blanc|sepia=Sépia|vhs=VHS rétro (lignes, bavures de couleur)|neon=Néon saturé|froid=Froid désaturé",
      "select:aucun=Natural|cinema=Cinema|nb=Black and white|sepia=Sepia|vhs=Retro VHS (lines, color bleeding)|neon=Saturated neon|froid=Cold desaturated"), tr("Étalonnage", "Color grading"), ""],
    ["grain", tr("select:null=Selon l'étalonnage|0=Aucun|4=Léger|8=Moyen|12=Fort|18=Très fort", "select:null=Based on the grading|0=None|4=Light|8=Medium|12=Strong|18=Very strong"), tr("Grain de film", "Film grain"), ""],
    ["vignettage", tr("select:null=Selon l'étalonnage|0=Aucun|0.3=Léger|0.6=Moyen|1=Fort", "select:null=Based on the grading|0=None|0.3=Light|0.6=Medium|1=Strong"), tr("Vignettage (bords sombres)", "Vignetting (dark edges)"), ""],
    ["luminosite", "range:-0.2:0.2:0.01", tr("Luminosité", "Brightness"), tr("0 = inchangée.", "0 = unchanged.")],
    ["contraste", "range:0.7:1.4:0.02", tr("Contraste", "Contrast"), tr("1 = inchangé.", "1 = unchanged.")],
    ["letterbox", "bool", tr("Bandes noires cinéma", "Cinema black bars"), tr("Format 2,39 (paysage seulement); paroles dans la bande.", "2.39 format (landscape only); lyrics in the bar.")],
    ["harmonisation", "bool", tr("Harmoniser les couleurs", "Harmonize the colors"), tr("Rapproche les couleurs des différentes planches.", "Brings the colors of the different panels closer.")],
    ["look_sections", "bool", tr("Ambiance par section", "Mood per section"), tr("Refrain plus lumineux, couplets plus sombres, pont désaturé.", "Brighter chorus, darker verses, desaturated bridge.")],
    ["variantes", "bool", tr("Varier les répétitions", "Vary the repetitions"), tr("Image répétée : miroir et sens alternés, dernière fois presque en N&B.", "Repeated image: alternating mirror and direction, last time almost in B&W.")]]],
  [tr("Particules, feu et fumée", "Particles, fire and smoke"), [
    ["particules", tr("select:null=Aucune|auto=Automatique (selon la scène)|", "select:null=None|auto=Automatic (based on the scene)|") + PART, tr("Particules", "Particles"),
      tr("Automatique : selon la description de chaque scène (feu → braises, orage → pluie, fête → confettis, bougies → bokeh, hiver → neige, bar → poussière…).",
        "Automatic: based on the description of each scene (fire → embers, storm → rain, party → confetti, candles → bokeh, winter → snow, bar → dust…).")],
    ["particules_densite", "range:0.3:2:0.1", tr("Densité", "Density"), tr("1 = normale.", "1 = normal.")],
    ["_psec", "psec", tr("Particules par section", "Particles per section"), tr("Remplace le réglage ci-dessus pour certaines parties de la chanson.", "Overrides the setting above for some parts of the song.")],
    ["flammes", tr("select:null=Aucun|auto=Automatique (incendie, brasier, flammes, enfer…)|partout=Partout", "select:null=None|auto=Automatic (fire, blaze, flames, inferno…)|partout=Everywhere"), tr("Feu (flammes)", "Fire (flames)"),
      tr("Flammes animées qui montent du bas de l'image, avec lueur et ondulation de chaleur. Superbe avec braises + fumée.", "Animated flames rising from the bottom of the image, with glow and heat shimmer. Great with embers + smoke.")],
    ["flammes_hauteur", "range:0.1:0.7:0.05", tr("Hauteur des flammes", "Flame height"), tr("Fraction de la hauteur de l'image.", "Fraction of the image height.")],
    ["flammes_intensite", "range:0.3:1.5:0.1", tr("Intensité du feu", "Fire intensity"), ""],
    ["fumee", tr("select:null=Aucune|auto=Automatique (selon la scène : fumée, brume, feu…)|fumee=Fumée qui monte, partout|brouillard=Brouillard bas, partout",
      "select:null=None|auto=Automatic (based on the scene: smoke, mist, fire…)|fumee=Rising smoke, everywhere|brouillard=Low fog, everywhere"), tr("Fumée / brouillard", "Smoke / fog"),
      tr("Se combine avec les particules (ex. fumée + braises). Par image : ajustement « fumee ».", "Combines with the particles (e.g. smoke + embers). Per image: “fumee” adjustment.")],
    ["fumee_densite", "range:0.3:2:0.1", tr("Densité de la fumée", "Smoke density"), tr("1 = normale.", "1 = normal.")]]],
  [tr("Format et son", "Format and sound"), [
    ["format", tr("select:16:9=16:9 Full HD (YouTube)|4k=16:9 4K (plus long à rendre)|9:16=Vertical 9:16 (Shorts, TikTok, Reels)|1:1=Carré 1:1",
      "select:16:9=16:9 Full HD (YouTube)|4k=16:9 4K (longer to render)|9:16=Vertical 9:16 (Shorts, TikTok, Reels)|1:1=Square 1:1"), tr("Format de la vidéo", "Video format"),
      tr("Vertical / carré : le fichier reçoit un suffixe (_vertical, _carre).", "Vertical / square: the file gets a suffix (_vertical, _carre).")],
    ["volume_normalise", "bool", tr("Volume normalisé YouTube", "YouTube normalized volume"), tr("-14 LUFS : même volume perçu que les autres vidéos.", "-14 LUFS: same perceived volume as other videos.")],
    ["debut", "number", tr("Couper le début (s)", "Cut the start (s)"), tr("0 = rien. Fondu d'entrée automatique.", "0 = nothing. Automatic fade-in.")],
    ["fin", "number", tr("Couper à partir de (s)", "Cut from (s)"), tr("0 = jusqu'à la fin de la chanson.", "0 = until the end of the song.")],
    ["fade_out", "range:0:6:0.5", tr("Fondu de fin (s)", "Fade-out (s)"), ""],
    ["fps", tr("select:30=30 images/s|25=25 images/s", "select:30=30 frames/s|25=25 frames/s"), tr("Images par seconde", "Frames per second"), ""],
    ["encoder", tr("select:auto=Automatique (carte graphique si possible)|amf=Carte graphique AMD|x264=Processeur (libx264)", "select:auto=Automatic (graphics card if possible)|amf=AMD graphics card|x264=Processor (libx264)"), tr("Encodeur vidéo", "Video encoder"), ""]]],
  [tr("Technique", "Technical"), [
    ["cy", "range:0:1:0.05", tr("Cadrage vertical par défaut", "Default vertical framing"), tr("0 = garder le haut de l'image, 1 = le bas.", "0 = keep the top of the image, 1 = the bottom.")],
    ["bpm_hint", "tempo", tr("Tempo (BPM)", "Tempo (BPM)"), tr("« auto » = détecté automatiquement. Mets un nombre seulement si le rythme détecté est faux (ex. le double ou la moitié), puis refais « Préparer » en cochant « tout refaire ».",
      "“auto” = detected automatically. Enter a number only if the detected rhythm is wrong (e.g. double or half), then run “Prepare” again with “redo everything” checked.")]]],
];
const DEFAULTS = {karaoke_taille: 46, karaoke_couleur: "#FFDC50", karaoke_texte: "#FFFFFF", karaoke_decalage: 0,
  camera_intensite: 1, luminosite: 0, contraste: 1, particules_densite: 1, fumee_densite: 1, flammes_hauteur: 0.3, flammes_intensite: 1, duree_max_image: 0, tremblement: 0, rvb_beat: 0, glitch_intensite: 1,
  fuites_lumiere: 0, projecteurs: 0, rayons_intensite: 1, vieux_film: 0, visualiseur_couleur: "#FFDC50",
  visualiseur_hauteur: 0.12, flou_fond: 0, brume_profondeur: 0, bar_alpha: 150,
  fondu: 0.15, pulse: 1, cy: 0.4, fade_out: 2.5};
function optInput([k, type, label, help]) {
  const v = S.cfg[k] ?? DEFAULTS[k];
  const hp = help ? `<p>${help}</p>` : "";
  if (type === "bool") return `<div class="opt"><label>${label} <label class="switch"><input type="checkbox" data-k="${k}" data-t="bool" ${v ? "checked" : ""}><span></span></label></label>${hp}</div>`;
  if (type.startsWith("range")) { const [, a, b, st] = type.split(":");
    return `<div class="opt"><label>${label} <span class="muted small" id="rv-${k}">${v ?? a}</span></label><input type="range" data-k="${k}" data-t="num" min="${a}" max="${b}" step="${st}" value="${v ?? a}"
      oninput="document.getElementById('rv-${k}').textContent=this.value">${hp}</div>`; }
  if (type.startsWith("select")) { const items = type.slice(7).split("|").map(x => [x.slice(0, x.indexOf("=")), x.slice(x.indexOf("=") + 1)]);
    const cur = k === "parallaxe" && v === true ? "0.03" : String(v === undefined || v === null ? (items.find(i => i[0] === "null") ? "null" : items[0][0]) : v);
    return `<div class="opt"><label>${label}</label><select data-k="${k}" data-t="sel">${items.map(([val, t]) =>
      `<option value="${val}" ${val === cur ? "selected" : ""}>${t}</option>`).join("")}</select>${hp}</div>`; }
  if (type === "tempo") return `<div class="opt"><label>${label}
      ${S.cfg.bpm_detecte ? `<span class="muted small">${tr("détecté :", "detected:")} ${S.cfg.bpm_detecte}</span>` : ""}</label>
    <input type="text" data-k="${k}" data-t="tempo" value="${esc(v === undefined || v === null || v === "" ? "auto" : v)}" placeholder="auto">${hp}</div>`;
  if (type === "color") return `<div class="opt"><label>${label} <input type="color" data-k="${k}" data-t="txt" value="${esc(v || "#FFFFFF")}"></label>${hp}</div>`;
  if (type === "font") return `<div class="opt"><label>${label}</label><select data-k="${k}" data-t="sel">${FONTS.map(f =>
      `<option value="${f}" ${f === (v || "Arial") ? "selected" : ""} style="font-family:'${f}'">${f}</option>`).join("")}</select>${hp}</div>`;
  if (type === "logo") return `<div class="opt"><label>${label}</label>
      ${S.cfg.logo ? `<img src="${file(encodeURIComponent(S.cfg.logo))}" style="max-height:60px;margin-top:6px;display:block">` : ""}
      <div class="drop" id="dz-logo" style="padding:10px;margin-top:6px"><b>${S.cfg.logo ? tr("Remplacer le logo", "Replace the logo") : tr("Déposer le logo", "Drop the logo")}</b></div>
      ${S.cfg.logo ? `<button id="logo-del" style="margin-top:6px">${tr("Retirer le logo", "Remove the logo")}</button>` : ""}${hp}</div>`;
  if (type === "psec") { const cur = S.cfg.particules_sections || {};
    const choix = [["auto", tr("Réglage général", "General setting")], ["aucune", tr("Aucune", "None")],
      ...PART.split("|").map(x => x.split("="))];
    return `<div class="opt" style="grid-column:1/-1"><label>${label}</label><div class="opts" style="margin-top:6px">${PSEC.map(([sk, sl]) =>
      `<div><span class="small">${sl}</span><select data-k="${sk}" data-t="psec" style="width:100%">${choix.map(([val, t]) =>
        `<option value="${val}" ${(cur[sk] || "auto") === val ? "selected" : ""}>${t}</option>`).join("")}</select></div>`).join("")}</div>${hp}</div>`; }
  if (type === "number") return `<div class="opt"><label>${label}</label><input type="number" step="0.1" data-k="${k}" data-t="num" value="${v ?? ""}">${hp}</div>`;
  return `<div class="opt"><label>${label}</label><input type="text" data-k="${k}" data-t="txt" value="${esc(v ?? "")}">${hp}</div>`;
}
V.options = () => `
  <h2>6. ${tr("Options", "Options")}</h2><p class="lead">${tr("Choisis un préréglage, ajuste si besoin, puis enregistre. Les réglages restent d'un rendu à l'autre.", "Pick a preset, adjust if needed, then save. The settings stay from one render to the next.")}</p>
  <div class="card"><h3>${tr("Préréglages", "Presets")}</h3><div class="row">${Object.entries(PRESETS).map(([k, p]) => `<button data-preset="${k}">${p.label}</button>`).join("")}</div>
    <p class="small muted">${tr("Un préréglage remplit le formulaire; rien n'est enregistré avant « Enregistrer ».", "A preset fills in the form; nothing is saved before “Save”.")}</p></div>
  ${OPTS.map(([g, list]) => `<div class="card"><h3>${g}</h3><div class="opts">${list.map(optInput).join("")}</div></div>`).join("")}
  <details class="card"><summary><b>${tr("Avancé", "Advanced")}</b> <span class="muted small">— ${tr("cadrage par image, intro / outro", "framing per image, intro / outro")}</span></summary>
    <div class="opts" style="margin-top:12px">
      <div class="opt"><label>${tr("Image fixe sur l'intro", "Still image over the intro")}</label><select data-k="intro_image" data-t="sel"><option value="null">${tr("(automatique)", "(automatic)")}</option>
        ${S.shots.map(s => `<option ${S.cfg.intro_image === s.id ? "selected" : ""}>${s.id}</option>`).join("")}</select></div>
      <div class="opt"><label>${tr("Image fixe sur l'outro", "Still image over the outro")}</label><select data-k="outro_image" data-t="sel"><option value="null">${tr("(automatique)", "(automatic)")}</option>
        ${S.shots.map(s => `<option ${S.cfg.outro_image === s.id ? "selected" : ""}>${s.id}</option>`).join("")}</select></div>
    </div>
    <p class="small muted" style="margin-top:12px">${tr("Ajustements par image (JSON) — ex.", "Adjustments per image (JSON) — e.g.")} <code>{"p2_c3": {"cy": 0.1}, "p4_c4": {"parallaxe": false, "particules": "braises", "fumee": "fumee"}}</code></p>
    <textarea id="adj" rows="5">${esc(JSON.stringify(S.cfg.ajustements || {}, null, 1))}</textarea></details>
  <div class="row"><button class="primary" id="save-opts">💾 ${tr("Enregistrer les options", "Save the options")}</button>
    <button onclick="go('rendu')">${tr("Aller au rendu", "Go to the render")} →</button></div>`;
function readOpts() {
  const out = {particules_sections: {}};
  document.querySelectorAll("#main [data-k]").forEach(el => {
    const k = el.dataset.k, t = el.dataset.t;
    if (t === "psec") { if (el.value !== "auto") out.particules_sections[k] = el.value; }
    else if (t === "tempo") { const n = parseFloat(el.value.replace(",", "."));
      out[k] = n >= 40 && n <= 240 ? n : "auto"; }
    else if (t === "bool") out[k] = el.checked;
    else if (t === "num") out[k] = el.value === "" ? null : +el.value;
    else if (t === "sel") { const v = el.value;
      out[k] = v === "null" ? null : v === "false" ? false : v === "true" ? true :
        (["format", "font"].includes(k) || isNaN(+v) || v === "" ? v : +v); }
    else out[k] = el.value.trim() || null;
  });
  const adj = $("#adj").value.trim();
  out.ajustements = adj ? JSON.parse(adj) : {};
  return out;
}
V.options_bind = () => {
  document.querySelectorAll("[data-preset]").forEach(b => b.onclick = () => {
    const p = PRESETS[b.dataset.preset];
    Object.entries(p.cfg).forEach(([k, v]) => {
      const el = document.querySelector(`#main [data-k="${k}"]`); if (!el) return;
      if (el.dataset.t === "bool") el.checked = !!v;
      else { el.value = String(v); el.dispatchEvent(new Event("input")); }
    });
    toast(tr(`Préréglage ${p.label} appliqué — pense à enregistrer`, `Preset ${p.label} applied — remember to save`));
  });
  $("#dz-logo") && dropzone($("#dz-logo"), "logo", "image/png,image/webp,image/jpeg");
  $("#logo-del") && ($("#logo-del").onclick = async () => {
    await post(`/api/projet/${encodeURIComponent(nom())}/config`, {logo: null}); toast(tr("Logo retiré", "Logo removed")); refresh(); });
  $("#save-opts").onclick = async () => {
    let o; try { o = readOpts(); } catch (e) { return toast(tr("Ajustements : JSON invalide", "Adjustments: invalid JSON")); }
    try { await post(`/api/projet/${encodeURIComponent(nom())}/config`, o); toast(tr("Options enregistrées ✅", "Options saved ✅")); await refresh(); }
    catch (e) { toast(e.message); }
  };
};

// ------------------------------------------------------------------ rendu
const size = b => b > 1e9 ? (b / 1e9).toFixed(2) + tr(" Go", " GB") : (b / 1e6).toFixed(0) + tr(" Mo", " MB");
V.rendu = () => {
  const ready = S.planches.length && S.planches.every(p => p.fichier);
  const fmt = {"4k": "4K", "9:16": tr("verticale 9:16", "vertical 9:16"), "1:1": tr("carrée", "square")}[S.cfg.format] || "1080p";
  const suffix = {"4k": "_4k", "9:16": "_vertical", "1:1": "_carre"}[S.cfg.format] || "";
  return `
  <h2>7. ${tr("Rendu", "Render")}</h2><p class="lead">${tr("L'aperçu est rapide (petite taille) pour vérifier le montage; le rendu final produit la vidéo 1080p avec le son.", "The preview is fast (small size) to check the edit; the final render produces the 1080p video with sound.")}</p>
  ${perimeHint()}
  ${ready ? "" : `<div class="steps-hint">${tr("Il manque des planches (étape 4) : le rendu utilisera les cases déjà découpées.", "Some panels are missing (step 4): the render will use the cells already cut.")}</div>`}
  <div class="grid2">
    <div class="card"><h3>👁 ${tr("Aperçu rapide", "Quick preview")}</h3><p class="small muted">${tr("Vérif + découpe + montage + vidéo 960×540. Environ 30 s pour une chanson de 3 min.", "Check + cut + edit + 960×540 video. About 30 s for a 3-minute song.")}</p>
      <button class="primary" id="r-prev">▶ ${tr("Aperçu", "Preview")}</button></div>
    <div class="card"><h3>🎬 ${tr("Rendu final", "Final render")}</h3><p class="small muted">${tr(`Vérif + découpe + montage + vidéo ${fmt} →`, `Check + cut + edit + ${fmt} video →`)}
      <b>${esc(S.nom)}${suffix}.mp4</b>. ${tr(`Environ 1 à 1 min 30 pour une chanson de 3 min${S.cfg.format === "4k" ? " (4K : environ 3× plus)" : ""}; 4 à 6 min avec beaucoup d'effets (parallaxe 3D, fumée, flou de fond).`,
        `About 1 to 1.5 min for a 3-minute song${S.cfg.format === "4k" ? " (4K: about 3× more)" : ""}; 4 to 6 min with many effects (3D parallax, smoke, background blur).`)}</p>
      <button class="primary" id="r-final">▶ ${tr("Rendu final", "Final render")}</button></div>
  </div>
  <div class="card"><h3>🔎 ${tr("Aperçu d'un passage", "Preview of a part")}</h3>
    <p class="small muted">${tr("Vérifie vite un passage précis (karaoké, transition, effet) sans rendre toute la chanson. Utilise le montage actuel : fais au moins un aperçu rapide complet avant.",
      "Quickly check a specific part (karaoke, transition, effect) without rendering the whole song. Uses the current edit: make at least one full quick preview first.")}</p>
    <div class="row"><label class="small">${tr("De", "From")} <input type="text" id="pv-a" value="0:30" style="width:70px"></label>
      <label class="small">${tr("à", "to")} <input type="text" id="pv-b" value="0:50" style="width:70px"></label>
      <button id="pv-go">▶ ${tr("Aperçu du passage", "Preview the part")}</button></div></div>
  <div class="card"><h3>${tr("Variante sous un autre nom", "Variant under another name")}</h3>
    <p class="small muted">${tr("Rend avec les options actuelles, sans refaire la découpe ni le montage — pratique pour comparer des réglages.", "Renders with the current options, without redoing the cutting or the edit — handy to compare settings.")}</p>
    <div class="row"><input type="text" id="r-name" value="${esc(S.nom)}_variante" style="width:260px"><span class="muted">.mp4</span>
      <button id="r-var">▶ ${tr("Rendre la variante", "Render the variant")}</button></div></div>
  <label class="small"><input type="checkbox" id="r-force"> ${tr("continuer même si la vérification des planches signale un problème", "continue even if the panel check reports a problem")}</label>
  <div class="card" style="margin-top:16px"><h3>${tr("Vidéos du projet", "Project videos")}</h3>
    ${S.videos.length ? `<video id="player" controls src="${file("build/" + encodeURIComponent(S.videos[0].nom))}"></video>
      <table style="margin-top:10px">${S.videos.map(v => `<tr><td><a href="#" data-play="${esc(v.nom)}">${esc(v.nom)}</a></td>
        <td class="muted">${size(v.taille)}</td><td class="muted">${new Date(v.date * 1000).toLocaleString(LANG === "en" ? "en-CA" : "fr-CA")}</td>
        <td style="white-space:nowrap"><button data-open="build/${esc(v.nom)}" title="${tr("Ouvrir dans le lecteur vidéo", "Open in the video player")}">▶ ${tr("Ouvrir", "Open")}</button>
          <button data-reveal="${esc(v.nom)}" title="${tr("Afficher le fichier dans l'explorateur", "Show the file in the file manager")}">📁 ${tr("Dossier", "Folder")}</button>
          <button data-del="${esc(v.nom)}" title="${tr("Supprimer cette vidéo", "Delete this video")}">🗑 ${tr("Supprimer", "Delete")}</button></td></tr>`).join("")}</table>`
      : `<p class="muted">${tr("Aucune vidéo pour l'instant.", "No video yet.")}</p>`}</div>`;
};
V.rendu_bind = () => {
  const f = () => $("#r-force").checked ? ["--force"] : [];
  $("#r-prev").onclick = () => run("build-preview", f(), tr("Aperçu rapide", "Quick preview"));
  $("#r-final").onclick = () => run("build", f(), tr("Rendu final", "Final render"));
  const secs = s => { const p = s.trim().split(":").map(Number); return p.some(isNaN) ? NaN : p.reduce((a, x) => a * 60 + x, 0); };
  $("#pv-go").onclick = () => {
    const a = secs($("#pv-a").value), b = secs($("#pv-b").value);
    if (!(b > a && a >= 0)) return toast(tr("Plage invalide (ex. de 1:20 à 1:45)", "Invalid range (e.g. from 1:20 to 1:45)"));
    run("preview", ["--start", a.toFixed(2), "--duration", Math.min(600, b - a).toFixed(2)],
      tr(`Aperçu de ${$("#pv-a").value} à ${$("#pv-b").value}`, `Preview from ${$("#pv-a").value} to ${$("#pv-b").value}`));
  };
  $("#r-var").onclick = () => { const n = $("#r-name").value.trim().replace(/\.mp4$/i, "");
    if (!/^[\w\-]+$/.test(n)) return toast(tr("Nom : lettres, chiffres, - et _ seulement", "Name: letters, digits, - and _ only"));
    run("render", ["--out", n + ".mp4"], tr(`Rendu de ${n}.mp4`, `Rendering ${n}.mp4`)); };
  document.querySelectorAll("[data-play]").forEach(a => a.onclick = e => { e.preventDefault();
    $("#player").src = file("build/" + encodeURIComponent(a.dataset.play)); $("#player").play(); });
  document.querySelectorAll("[data-open]").forEach(b => b.onclick = () =>
    post(`/api/projet/${encodeURIComponent(nom())}/ouvrir?chemin=${encodeURIComponent(b.dataset.open)}`).catch(e => toast(e.message)));
  document.querySelectorAll("[data-reveal]").forEach(b => b.onclick = () =>
    post(`/api/projet/${encodeURIComponent(nom())}/reveler?nom=${encodeURIComponent(b.dataset.reveal)}`).catch(e => toast(e.message)));
  document.querySelectorAll("[data-del]").forEach(b => b.onclick = async () => {
    const v = b.dataset.del;
    if (!confirm(tr(`Supprimer définitivement « ${v} »?\n(La vidéo pourra être recréée avec un nouveau rendu.)`, `Permanently delete “${v}”?\n(The video can be recreated with a new render.)`))) return;
    const player = $("#player");
    if (player && decodeURIComponent(player.src).includes("/" + v)) { player.pause(); player.removeAttribute("src"); player.load(); }
    try { await post(`/api/projet/${encodeURIComponent(nom())}/supprimer-video?nom=${encodeURIComponent(v)}`);
      toast(tr(`${v} supprimée ✅`, `${v} deleted ✅`)); await refresh(); }
    catch (e) { toast(e.message, 5000); }
  });
};

// ------------------------------------------------------------------ publication
const ORIGINES = {
  suno: tr("Chanson originale réinterprétée avec Suno (IA) + images IA", "Original song reinterpreted with Suno (AI) + AI images"),
  images: tr("Musique originale (sans IA), seules les images sont IA", "Original music (no AI), only the images are AI"),
  complete: tr("Chanson et images entièrement créées par IA", "Song and images fully created by AI"),
  fan: tr("Fan-made : chanson d'un autre artiste (aucun droit) + images IA", "Fan-made: another artist's song (no rights) + AI images"),
  fan_ia: tr("Fan-made : reprise IA (Suno) d'une chanson d'un autre artiste + images IA", "Fan-made: AI cover (Suno) of another artist's song + AI images"),
};
// mention par défaut du bandeau de miniature (dans la langue de la chanson, comme clip/publish.py)
const MENTIONS = {fr: {suno: "Version IA", images: "Clip IA", complete: "Version IA", fan: "Fan-made", fan_ia: "Fan-made IA"},
                  en: {suno: "AI Version", images: "AI Video", complete: "AI Version", fan: "Fan-made", fan_ia: "AI Fan-made"}};
// options de publication et valeurs par défaut (REGLAGES dans clip/publish.py)
const PUB_DEF = {credits: {paroles: "", musique: "", interpretation: "", clip: ""}, clip_studio: false, liens: "", lien_officiel: "",
  ton: "auto", accroche: "normale", emojis: true,
  blocs: {accroche: true, mention: true, chapitres: true, paroles: true, credits: true, liens: true, hashtags: true},
  vignette: null, bandeau: "", bandeau_couleur: "rouge", formats: []};
const pubReg = () => { const p = S.cfg.publication || {};
  return {...PUB_DEF, ...p, credits: {...PUB_DEF.credits, ...(p.credits || {})}, blocs: {...PUB_DEF.blocs, ...(p.blocs || {})}}; };
let PROFILS = {};
V.publication = () => {
  const P = S.publication, c = S.cfg, r = pubReg(), fan = (c.origine || "").startsWith("fan");
  const opt = (id, val, libs) => `<select id="${id}">${Object.entries(libs).map(([k, t]) =>
    `<option value="${k}" ${val === k ? "selected" : ""}>${t}</option>`).join("")}</select>`;
  const coche = (id, on, lib) => `<label class="small" style="margin-right:14px"><input type="checkbox" id="${id}" ${on ? "checked" : ""}> ${lib}</label>`;
  const champ = (id, titre, txt, rows) => `<div class="row" style="margin-top:12px"><b>${titre}</b><div style="flex:1"></div>
    <button class="primary" data-cpy="${id}">📋 ${tr("Copier", "Copy")}</button></div>
    <textarea id="${id}" rows="${rows}" style="margin-top:6px">${esc(txt)}</textarea>`;
  const bloc = (id, titre, txt, rows) => `<div class="card">${champ(id, titre, txt, rows)}</div>`;
  const ROLES = {paroles: tr("Paroles", "Lyrics"), musique: tr("Musique", "Music"), interpretation: tr("Interprétation", "Performance"), clip: tr("Clip", "Video")};
  const BLOCS = {accroche: tr("Accroche", "Hook"), mention: tr("Mention / déclaration", "Notice / statement"), chapitres: tr("Chapitres", "Chapters"),
    paroles: tr("Paroles", "Lyrics"), credits: tr("Crédits", "Credits"), liens: tr("Liens", "Links"), hashtags: "Hashtags"};
  const cases = S.shots.filter(s => s.case);
  const vig = cases.find(s => s.id === r.vignette);
  const mention = (MENTIONS[c.langue] || MENTIONS.fr)[c.origine || "suno"] || "";
  const idees = P ? (P.miniatures && P.miniatures.length ? P.miniatures : [{idee: "", avec_texte: P.miniature, sans_texte: P.miniature_sans_texte}]) : [];
  return `
  <h2>8. ${tr("Publication YouTube", "YouTube publishing")}</h2><p class="lead">${tr("Claude rédige le titre, l'accroche et 3 idées de miniature; les chapitres, les paroles, la mention, les crédits et les liens sont ajoutés automatiquement, exacts.",
    "Claude writes the title, the hook and 3 thumbnail ideas; the chapters, the lyrics, the notice, the credits and the links are added automatically, exactly.")}</p>
  <div class="card"><h3>${tr("Informations", "Information")}</h3><div class="opts">
    <div class="opt"><label>${tr("Titre de la chanson", "Song title")}</label><input type="text" id="pub-titre" value="${esc(c.titre || "")}"></div>
    <div class="opt"><label>${tr("Artiste / groupe", "Artist / band")}</label><input type="text" id="pub-artiste" value="${esc(c.artiste || "")}"></div>
    <div class="opt"><label>${tr("Origine (mention)", "Origin (notice)")}</label>${opt("pub-origine", c.origine || "suno", ORIGINES)}</div>
    ${fan ? `<div class="opt"><label>${tr("Lien officiel de la chanson / de l'artiste", "Official link of the song / artist")}</label><input type="text" id="pub-off" value="${esc(r.lien_officiel)}" placeholder="https://…"></div>` : ""}
  </div>
  <div class="row" style="margin-top:12px"><label class="small">${tr("Profil", "Profile")}</label>
    <select id="pub-profil"><option value="">${tr("— choisir —", "— choose —")}</option></select>
    <button id="pub-charger">${tr("Charger", "Load")}</button>
    <button id="pub-enreg">💾 ${tr("Enregistrer comme profil…", "Save as profile…")}</button>
    <button id="pub-suppr">${tr("Supprimer", "Delete")}</button>
    <span class="muted small">${tr("origine, crédits, liens, rédaction et miniature, réutilisables d'un projet à l'autre", "origin, credits, links, writing and thumbnail, reusable from one project to another")}</span></div></div>

  <details class="card" open><summary><b>🎬 ${tr("Crédits et liens", "Credits and links")}</b> <span class="muted small">— ${tr("ajoutés tels quels à la description", "added as is to the description")}</span></summary><div class="opts" style="margin-top:10px">
    ${Object.entries(ROLES).map(([k, t]) => `<div class="opt"><label>${t}</label><input type="text" id="pub-cr-${k}" value="${esc(r.credits[k])}"></div>`).join("")}
  </div>
  <div style="margin-top:10px">${coche("pub-cs", r.clip_studio, tr("Mentionner « Clip réalisé avec Clip Studio » (lien GitHub)", "Mention “Video made with Clip Studio” (GitHub link)"))}</div>
  <label class="small" style="display:block;margin-top:10px">${tr("Liens (un par ligne, ex. « Spotify : https://… »)", "Links (one per line, e.g. “Spotify: https://…”)")}</label>
  <textarea id="pub-liens" rows="3">${esc(r.liens)}</textarea></details>

  <details class="card" open><summary><b>✍️ ${tr("Rédaction", "Writing")}</b></summary><div class="opts" style="margin-top:10px">
    <div class="opt"><label>${tr("Ton", "Tone")}</label>${opt("pub-ton", r.ton, {auto: tr("automatique (celui de la chanson)", "automatic (the song's)"), drole: tr("drôle", "funny"),
      serieux: tr("sérieux", "serious"), promo: "promo", quebecois: tr("québécois familier", "casual / colloquial")})}</div>
    <div class="opt"><label>${tr("Accroche", "Hook")}</label>${opt("pub-acc", r.accroche, {normale: tr("normale (2 à 3 phrases)", "normal (2 to 3 sentences)"), courte: tr("courte (1 phrase)", "short (1 sentence)")})}</div>
    <div class="opt"><label>Emojis</label>${coche("pub-emo", r.emojis, tr("dans l'accroche et les titres de blocs", "in the hook and the block headings"))}</div>
  </div>
  <label class="small" style="display:block;margin-top:10px">${tr("Blocs de la description", "Description blocks")}</label>
  <div>${Object.entries(BLOCS).map(([k, t]) => coche("pub-b-" + k, r.blocs[k], t)).join("")}</div></details>

  <details class="card" open><summary><b>🖼️ ${tr("Miniature", "Thumbnail")}</b> <span class="muted small">— ${tr("3 idées rédigées d'un coup", "3 ideas written at once")}</span></summary><div class="opts" style="margin-top:10px">
    <div class="opt"><label>${tr("Vignette de référence (1re idée)", "Reference image (1st idea)")}</label><select id="pub-vig"><option value="">${tr("aucune : Claude choisit", "none: Claude chooses")}</option>
      ${cases.map(s => `<option value="${s.id}" ${s.id === r.vignette ? "selected" : ""}>${s.id} — ${esc((s.texte || tr("ambiance", "ambiance")).slice(0, 50))}</option>`).join("")}</select>
      <img id="pub-vig-img" src="${vig ? file("cases/" + vig.id + ".png") : ""}" style="max-width:100%;margin-top:8px;border-radius:6px;${vig ? "" : "display:none"}"></div>
    <div class="opt"><label>${tr("Texte du bandeau", "Banner text")}</label><input type="text" id="pub-band" value="${esc(r.bandeau)}" placeholder="${esc(mention.toUpperCase())}"></div>
    <div class="opt"><label>${tr("Couleur du bandeau", "Banner color")}</label>${opt("pub-coul", r.bandeau_couleur, {rouge: tr("rouge", "red"), jaune: tr("jaune", "yellow"),
      noir: tr("noir", "black"), blanc: tr("blanc", "white"), bleu: tr("bleu", "blue")})}</div>
    <div class="opt"><label>${tr("Formats en plus du 16:9", "Formats in addition to 16:9")}</label><div>${coche("pub-f-carre", r.formats.includes("carre"), tr("carré 1:1", "square 1:1"))}${coche("pub-f-vertical", r.formats.includes("vertical"), tr("vertical 9:16", "vertical 9:16"))}</div></div>
  </div></details>

  <div class="card"><p class="small muted" style="margin:0 0 10px">${tr(`Textes rédigés en ${(c.langue || "fr") === "en" ? "anglais" : "français"} (langue de la chanson, étape 1).`, `Texts written in ${(c.langue || "fr") === "en" ? "English" : "French"} (language of the song, step 1).`)}</p>
  <div class="row"><input type="text" id="pub-consigne" placeholder="${tr("Consigne facultative : ex. miniature avec le disque d'or…", "Optional instruction: e.g. thumbnail with the gold record…")}" style="flex:1;min-width:260px">
    <button id="pub-save">💾 ${tr("Enregistrer les réglages", "Save the settings")}</button>
    ${CLAUDE ? `<button class="primary" id="pub-go">✨ ${P ? tr("Refaire avec Claude", "Redo with Claude") : tr("Rédiger avec Claude", "Write with Claude")}</button>`
      : `<span class="muted small">${tr("Claude Code introuvable (voir étape 3)", "Claude Code not found (see step 3)")}</span>`}</div></div>
  ${P ? `
    ${bloc("pub-t", tr("Titre", "Title"), P.titre, 2)}
    ${bloc("pub-d", "Description", P.description, 18)}
    ${idees.map((x, i) => `<details class="card" ${i ? "" : "open"}><summary><b>🖼️ ${tr("Miniature", "Thumbnail")} ${i + 1}</b>${x.idee ? ` <span class="muted small">— ${esc(x.idee)}</span>` : ""}</summary>
      ${champ(`pub-m${i}a`, tr("Avec texte (16:9)", "With text (16:9)"), x.avec_texte, 7)}
      ${x.sans_texte ? champ(`pub-m${i}b`, tr("Sans texte (16:9)", "Without text (16:9)"), x.sans_texte, 5) : ""}
      ${x.carre ? champ(`pub-m${i}c`, tr("Carrée 1:1", "Square 1:1"), x.carre, 5) : ""}
      ${x.vertical ? champ(`pub-m${i}v`, tr("Verticale 9:16", "Vertical 9:16"), x.vertical, 5) : ""}</details>`).join("")}
    <p class="small muted">${tr("Tu peux retoucher les textes ici avant de les copier (les modifications ne sont pas enregistrées).", "You can touch up the texts here before copying them (the changes are not saved).")}</p>` : ""}
  <div class="card"><h3>${tr("Avant de publier", "Before publishing")}</h3><ul class="small">
    <li>${tr("Vérifie l'orthographe du texte sur la miniature générée (sinon, génère la version sans texte).", "Check the spelling of the text on the generated thumbnail (otherwise, generate the version without text).")}</li>
    <li>${tr("Dans YouTube Studio, coche <b>« Contenu modifié ou synthétique »</b> (voix et images générées).", "In YouTube Studio, check <b>“Altered or synthetic content”</b> (generated voice and images).")}</li>
    ${fan ? `<li>${tr("Fan-made : YouTube peut revendiquer la vidéo (Content ID); les revenus éventuels vont alors aux ayants droit, et la vidéo peut être bloquée dans certains pays.", "Fan-made: YouTube may claim the video (Content ID); any revenue then goes to the rights holders, and the video may be blocked in some countries.")}</li>` : ""}
    <li>${tr("Suno : l'offre gratuite n'autorise pas l'usage commercial (monétisation); les offres payantes, oui.", "Suno: the free plan does not allow commercial use (monetization); paid plans do.")}</li>
    <li>${tr("Vérifie les chapitres à l'oreille : ils viennent du calage des paroles.", "Check the chapters by ear: they come from the lyrics alignment.")}</li></ul></div>`;
};
// réglages de l'étape 8 tels qu'affichés : {titre, artiste, origine, publication}
function pubLire() {
  const v = id => $("#" + id).value, ch = id => $("#" + id).checked;
  return {titre: v("pub-titre").trim(), artiste: v("pub-artiste").trim(), origine: v("pub-origine"),
    publication: {
      credits: Object.fromEntries(Object.keys(PUB_DEF.credits).map(k => [k, v("pub-cr-" + k).trim()])),
      clip_studio: ch("pub-cs"), liens: v("pub-liens"),
      lien_officiel: ($("#pub-off") ? v("pub-off") : pubReg().lien_officiel).trim(),
      ton: v("pub-ton"), accroche: v("pub-acc"), emojis: ch("pub-emo"),
      blocs: Object.fromEntries(Object.keys(PUB_DEF.blocs).map(k => [k, ch("pub-b-" + k)])),
      vignette: v("pub-vig") || null, bandeau: v("pub-band").trim(), bandeau_couleur: v("pub-coul"),
      formats: ["carre", "vertical"].filter(f => ch("pub-f-" + f))}};
}
async function pubSauver() {
  const d = pubLire(); Object.assign(S.cfg, d);
  await post(`/api/projet/${encodeURIComponent(nom())}/config`, d);
}
function pubProfils(choisi) {
  $("#pub-profil").innerHTML = `<option value="">${tr("— choisir —", "— choose —")}</option>` + Object.keys(PROFILS).sort()
    .map(n => `<option value="${esc(n)}" ${n === choisi ? "selected" : ""}>${esc(n)}</option>`).join("");
}
V.publication_bind = () => {
  document.querySelectorAll("[data-cpy]").forEach(b => b.onclick = () => copy($("#" + b.dataset.cpy).value));
  api("/api/profils").then(p => { PROFILS = p; pubProfils(); }).catch(() => {});
  // l'origine change le lien officiel, le bandeau par défaut et l'aide : réaffichage (sans perdre la saisie)
  $("#pub-origine").onchange = async () => { await pubSauver().catch(() => {}); renderStep(); };
  $("#pub-vig").onchange = e => { const img = $("#pub-vig-img");
    img.style.display = e.target.value ? "" : "none"; if (e.target.value) img.src = file("cases/" + e.target.value + ".png"); };
  $("#pub-save").onclick = async () => { await pubSauver(); toast(tr("Réglages enregistrés ✅", "Settings saved ✅")); };
  $("#pub-enreg").onclick = async () => {
    const n = prompt(tr("Nom du profil (ex. KPR, Fan-made) :", "Profile name (e.g. KPR, Fan-made):"), $("#pub-profil").value || ""); if (!n || !n.trim()) return;
    const d = pubLire(), {vignette, ...prof} = d.publication;            // la vignette est propre au projet
    try { PROFILS = await post("/api/profils", {nom: n.trim(), profil: {origine: d.origine, ...prof}}); pubProfils(n.trim());
      toast(tr("Profil enregistré ✅", "Profile saved ✅")); } catch (e) { toast(e.message, 5000); }
  };
  $("#pub-charger").onclick = async () => {
    const n = $("#pub-profil").value, prof = PROFILS[n]; if (!prof) return toast(tr("Choisis un profil", "Choose a profile"));
    const {origine, ...reste} = prof, d = pubLire();
    d.publication = {...PUB_DEF, ...reste, vignette: d.publication.vignette};
    if (origine) d.origine = origine;
    Object.assign(S.cfg, d); await post(`/api/projet/${encodeURIComponent(nom())}/config`, d);
    renderStep(); toast(tr(`Profil « ${n} » chargé`, `Profile “${n}” loaded`));
  };
  $("#pub-suppr").onclick = async () => {
    const n = $("#pub-profil").value; if (!n || !confirm(tr(`Supprimer le profil « ${n} » ?`, `Delete the profile “${n}”?`))) return;
    PROFILS = await post("/api/profils", {nom: n, profil: null}); pubProfils();
  };
  $("#pub-go") && ($("#pub-go").onclick = async () => {
    const d = pubLire();
    if (!d.titre || !d.artiste) return toast(tr("Indique le titre et l'artiste", "Enter the title and the artist"));
    await pubSauver();
    const cns = $("#pub-consigne").value.trim();
    run("publish", cns ? ["--consigne", cns.slice(0, 300)] : [], tr("Rédaction de la publication", "Writing the publishing texts"));
  });
};

// ------------------------------------------------------------------ démarrage
header();
$("#projet").onchange = refresh;
$("#nouveau").onclick = async () => {
  const n = prompt(tr("Nom du nouveau projet (lettres, chiffres, - et _ ; sans espaces) :", "Name of the new project (letters, digits, - and _; no spaces):")); if (!n) return;
  try { await post("/api/projets", {nom: n.trim()}); await loadProjects(n.trim()); go("projet"); toast(tr("Projet créé ✅", "Project created ✅")); }
  catch (e) { toast(e.message, 5000); }
};
$("#dossier").onclick = () => nom() && post(`/api/projet/${encodeURIComponent(nom())}/ouvrir?chemin=.`).catch(e => toast(e.message));
$("#jobhide").onclick = () => $("#job").classList.add("hide");
$("#jobstop").onclick = () => post(`/api/projet/${encodeURIComponent(nom())}/stop`);
api("/api/claude").then(r => { CLAUDE = r.chemin; if (["preparer", "descriptions", "planches", "videos", "publication"].includes(step)) renderStep(); }).catch(() => {});
loadProjects().then(async () => { const j = await api("/api/job").catch(() => null);
  if (j && j.running) { $("#job").classList.remove("hide"); pollJob(); } });
