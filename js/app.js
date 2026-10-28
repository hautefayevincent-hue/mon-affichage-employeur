// Questionnaire, enregistrement et espace client.
const C = window.CONFIG;
const params = new URLSearchParams(location.search);
const ESPACE_ID = params.get("id");
const BROUILLON = "pack_brouillon_v1";
let A = {};            // réponses
let etape = 0;
let client = null;     // { id, commande } une fois enregistré

const estPaye = () => !C.PAIEMENT_ACTIF || !!(client && client.paye);
const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const visible = (f) => !f.si || f.si(A);
const FIXES = ["diagnostic", "recap"];
const etapesVisibles = () => ETAPES.filter((e) => (FIXES.includes(e.id) && !(ESPACE_ID && e.id === "diagnostic")) || e.champs.some(visible) || e.vide);

function sauverBrouillon() { if (ESPACE_ID) return; try { localStorage.setItem(BROUILLON, JSON.stringify(A)); } catch (e) {} }
function lireBrouillon() { try { return JSON.parse(localStorage.getItem(BROUILLON) || "{}"); } catch (e) { return {}; } }

// ---------- rendu des champs ----------
function champHTML(f) {
  const v = A[f.k];
  const req = f.req ? ' <span class="req">*</span>' : "";
  const aide = f.aide ? `<p class="aide">${esc(f.aide)}</p>` : "";
  if (f.type === "titre") return `<h3 class="sous">${esc(f.l)}</h3>`;
  if (f.type === "ouinon") {
    return `<fieldset class="ouinon" data-k="${f.k}"><legend>${esc(f.l)}</legend><div class="choix">
      ${["oui", "non"].map((o) => `<label class="pill"><input type="radio" name="${f.k}" value="${o}" ${v === o ? "checked" : ""}>${o === "oui" ? "Oui" : "Non"}</label>`).join("")}
      </div>${aide}</fieldset>`;
  }
  if (f.type === "jours") {
    const j = v || {};
    return `<div class="champ"><label>${esc(f.l)}</label>${aide}<div class="tablewrap"><table class="saisie"><thead><tr><th>Jour</th>${COLS_JOURS.map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>
      ${JOURS.map((d) => `<tr><th>${d}</th>${COLS_JOURS.map((c, i) => `<td><input data-jour="${d}" data-i="${i}" value="${esc((j[d] || [])[i] || "")}" aria-label="${d} ${c}"></td>`).join("")}</tr>`).join("")}
      </tbody></table></div></div>`;
  }
  if (f.type === "table") {
    const rows = (v && v.length) ? v : [f.cols.map(() => "")];
    return `<div class="champ" data-table="${f.k}"><label>${esc(f.l)}</label>${aide}<div class="tablewrap"><table class="saisie"><thead><tr>${f.cols.map((c) => `<th>${esc(c)}</th>`).join("")}<th></th></tr></thead><tbody>
      ${rows.map((r, ri) => `<tr>${f.cols.map((c, ci) => `<td>${celluleHTML(f, r, ri, c, ci)}</td>`).join("")}<td><button type="button" class="lien suppr" data-r="${ri}" aria-label="Supprimer la ligne">✕</button></td></tr>`).join("")}
      </tbody></table></div><button type="button" class="btn-sec ajout">Ajouter une ligne</button></div>`;
  }
  const t = f.type === "number" ? "number" : f.type === "date" ? "date" : f.type === "email" ? "email" : "text";
  const input = f.type === "textarea"
    ? `<textarea id="f_${f.k}" data-k="${f.k}" rows="3">${esc(v || "")}</textarea>`
    : `<input id="f_${f.k}" data-k="${f.k}" type="${t}" value="${esc(v || "")}" ${f.ph ? `placeholder="${esc(f.ph)}"` : ""} ${t === "number" ? 'min="0" inputmode="numeric"' : ""}>`;
  return `<div class="champ"><label for="f_${f.k}">${esc(f.l)}${req}</label>${input}${aide}</div>`;
}

function celluleHTML(f, r, ri, c, ci) {
  const v = r[ci] || "";
  const ch = f.choix && f.choix[ci];
  if (ch) return `<select data-r="${ri}" data-c="${ci}" aria-label="${esc(c)}"><option value="">Choisir</option>${ch.map((o) => `<option ${o === v ? "selected" : ""}>${esc(o)}</option>`).join("")}</select>`;
  return `<input data-r="${ri}" data-c="${ci}" value="${esc(v)}" aria-label="${esc(c)}">`;
}

function lireTable(box) {
  return [...box.querySelectorAll("tbody tr")].map((tr) => [...tr.querySelectorAll("input, select")].map((i) => i.value.trim()))
    .filter((r) => r.some((x) => x));
}

function lierChamps(root) {
  root.querySelectorAll("[data-k]").forEach((el) => {
    if (el.tagName === "FIELDSET") {
      el.querySelectorAll("input").forEach((r) => r.addEventListener("change", () => { A[el.dataset.k] = r.value; sauverBrouillon(); rendre(false); }));
    } else {
      el.addEventListener("input", () => { A[el.dataset.k] = el.value.trim(); sauverBrouillon(); });
      if (el.dataset.k === "effectif") el.addEventListener("change", () => rendre(false));
    }
  });
  root.querySelectorAll("input[data-jour]").forEach((el) => el.addEventListener("input", () => {
    const j = A.hc_jours || (A.hc_jours = {});
    const row = j[el.dataset.jour] || (j[el.dataset.jour] = ["", "", "", "", ""]);
    row[+el.dataset.i] = el.value.trim(); sauverBrouillon();
  }));
  root.querySelectorAll("[data-table]").forEach((box) => {
    const k = box.dataset.table;
    box.querySelectorAll("tbody input, tbody select").forEach((i) => i.addEventListener(i.tagName === "SELECT" ? "change" : "input", () => { A[k] = lireTable(box); sauverBrouillon(); }));
    $(".ajout", box).addEventListener("click", () => {
      const f = ETAPES.flatMap((e) => e.champs).find((x) => x.k === k);
      A[k] = lireTable(box); A[k].push(f.cols.map(() => "")); rendre(false);
    });
    box.querySelectorAll(".suppr").forEach((b) => b.addEventListener("click", () => {
      const rows = [...box.querySelectorAll("tbody tr")].map((tr) => [...tr.querySelectorAll("input, select")].map((i) => i.value.trim()));
      rows.splice(+b.dataset.r, 1); A[k] = rows.filter((r) => r.some((x) => x)); sauverBrouillon(); rendre(false);
    }));
  });
}

// ---------- étapes ----------
const ICON_OK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>';
let docsCourants = null;   // liste calculée par le générateur
let docsCle = "";

function nomDoc(n) { const k = n.split("_")[0]; return TITRES[k] || n; }
function numDoc(n) { return n.split("_")[0]; }

async function majDocs() {
  const d = donneesPack();
  const cle = JSON.stringify(d, Object.keys(d).filter((k) => /^s_|^effectif$/.test(k)).sort());
  if (docsCourants && cle === docsCle) return docsCourants;
  docsCourants = await documentsDus(d); docsCle = cle;
  return docsCourants;
}

async function majResume(visibleListe) {
  const box = $("#resume");
  if (!visibleListe) { box.innerHTML = `<h3>Votre pack</h3><p class="vide">La liste des documents s'affiche après l'étude.</p>`; return; }
  box.innerHTML = `<h3>Votre pack</h3><p class="chargement">Calcul en cours</p>`;
  try {
    const docs = await majDocs();
    const sit = docs.filter((d) => d[0] !== "01_Socle").length;
    box.innerHTML = `<h3>Votre pack</h3><div class="compte">${docs.length} <small>documents</small></div>
      <p class="aide">${docs.length - sit} au socle, ${sit} liés à votre situation, plus le panneau A3.</p>
      <ul>${docs.map((d) => `<li class="${d[0] !== "01_Socle" ? "plus" : ""}"><span>${esc(numDoc(d[1]))}</span>${esc(nomDoc(d[1]))}</li>`).join("")}</ul>`;
  } catch (e) { box.innerHTML = `<h3>Votre pack</h3><p class="vide">Liste indisponible pour le moment.</p>`; }
}

function rendre(scroll = true) {
  const ets = etapesVisibles();
  etape = Math.max(0, Math.min(etape, ets.length - 1));
  const e = ets[etape];
  $("#barre").style.width = Math.round((etape / (ets.length - 1)) * 100) + "%";
  $("#nom-etape").textContent = e.titre;
  $("#compteur").textContent = `Étape ${etape + 1} sur ${ets.length}`;
  const zone = $("#etape");
  const iDiag = ets.findIndex((x) => x.id === "diagnostic");
  majResume(ESPACE_ID || (iDiag >= 0 && etape >= iDiag));
  if (e.id === "recap") rendreRecap(zone);
  else if (e.id === "diagnostic") rendreDiagnostic(zone);
  else {
    const ch = e.champs.filter(visible);
    zone.innerHTML = `<h2>${esc(e.titre)}</h2>${e.intro ? `<p class="intro">${esc(e.intro)}</p>` : ""}
      ${ch.length ? ch.map(champHTML).join("") : `<p class="intro">${esc(e.vide || "")}</p>`}`;
    lierChamps(zone);
  }
  $("#prec").hidden = etape === 0;
  $("#suiv").hidden = e.id === "recap";
  $("#suiv").textContent = e.bouton || "Continuer";
  $(".nav-etapes").hidden = false;
  $("#erreurs").textContent = "";
  if (scroll) window.scrollTo({ top: 0, behavior: "smooth" });
}

function manquants(e) {
  return e.champs.filter(visible).filter((f) => {
    if (f.type === "ouinon") return !A[f.k];
    if (f.type === "email") return !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(A[f.k] || "");
    return f.req && !String(A[f.k] || "").trim();
  });
}

function suivant() {
  const e = etapesVisibles()[etape];
  const m = manquants(e);
  if (m.length) {
    $("#erreurs").textContent = "À compléter : " + m.map((f) => f.l).join(" · ");
    const first = $(`[data-k="${m[0].k}"]`); if (first && first.focus) first.focus();
    return;
  }
  etape++; rendre();
}

// ---------- données envoyées au générateur ----------
function frDate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || ""); return m ? `${m[3]}/${m[2]}/${m[1]}` : (iso || "");
}
function donneesPack() {
  const champs = ETAPES.flatMap((e) => e.champs);
  const d = {};
  champs.forEach((f) => {
    if (f.type === "titre") return;
    if (!visible(f)) return;
    let v = A[f.k];
    if (f.type === "date") v = frDate(v);
    if (v !== undefined) d[f.k] = v;
  });
  champs.filter((f) => f.type === "ouinon").forEach((f) => { if (!d[f.k]) d[f.k] = "non"; });
  d.s_incendie = incendie(A) ? "oui" : "non";
  if (d.hc_jours) {
    const j = {}; Object.entries(d.hc_jours).forEach(([k, r]) => { if (r.some((x) => x)) j[k] = r; }); d.hc_jours = j;
  }
  if (Array.isArray(d.equipes) && d.equipes.length === 1) { d.eq1 = d.equipes[0][0]; d.eq1c = d.equipes[0][3]; }
  const now = new Date();
  d.date = now.toLocaleDateString("fr-FR");
  d.commande = client ? client.commande : "ESSAI-" + now.getTime().toString().slice(-6);
  return d;
}

// ---------- serveur Apps Script ----------
async function appel(payload) {
  if (!C.APPS_SCRIPT_URL) return null;
  const r = await fetch(C.APPS_SCRIPT_URL, { method: "POST", body: JSON.stringify(payload) });
  const j = await r.json();
  if (!j.ok) throw new Error(j.erreur || "Erreur d'enregistrement");
  return j;
}
async function chargerClient(id) {
  const r = await fetch(C.APPS_SCRIPT_URL + "?action=get&id=" + encodeURIComponent(id));
  const j = await r.json();
  if (!j.ok) throw new Error(j.erreur || "Lien introuvable");
  return j;
}

// ---------- résultat du diagnostic ----------
function listeDocs(docs) {
  const socle = docs.filter((d) => d[0] === "01_Socle"), sit = docs.filter((d) => d[0] !== "01_Socle");
  const li = (d) => `<li><span>${esc(numDoc(d[1]))}</span>${esc(nomDoc(d[1]))}</li>`;
  return `<div class="deuxcol"><div><h3 class="sous">Socle applicable à tout employeur</h3><ul class="docs">${socle.map(li).join("")}</ul></div>
    <div><h3 class="sous">Liés à votre situation</h3><ul class="docs">${sit.length ? sit.map(li).join("") : "<li>Aucun document supplémentaire</li>"}</ul></div></div>`;
}

async function rendreDiagnostic(zone) {
  zone.innerHTML = `<h2>Documents correspondant à vos réponses</h2><p class="chargement">Analyse de vos réponses</p>`;
  let docs;
  try { docs = await majDocs(); }
  catch (e) { zone.innerHTML = `<h2>Documents correspondant à vos réponses</h2><p class="erreur">La liste n'a pas pu être établie. Rechargez la page puis réessayez.</p>`; return; }
  const sit = docs.filter((d) => d[0] !== "01_Socle").length;
  zone.innerHTML = `<h2>Documents correspondant à vos réponses</h2>
    <div class="resultat"><div class="chiffre">${docs.length}</div>
      <p style="margin:6px 0 0"><b>affichages, registres et documents</b> sont applicables à ${esc(A.raison || "votre établissement")} : ${docs.length - sit} au titre du socle et ${sit} au titre de sa situation.</p></div>
    ${listeDocs(docs)}
    <p class="aide">Liste établie automatiquement à partir de vos réponses et des textes en vigueur. Information générale, qui ne constitue pas une consultation juridique.</p>
    <h3 class="sous">Recevoir ces documents remplis</h3>
    <p class="intro" style="margin-bottom:0">Renseignez les informations propres à l'établissement : coordonnées des services, horaires, congés, document unique. Elles sont reportées sur chaque document du pack, que vous téléchargez à la fin du questionnaire.</p>`;
  if (!A._prospect && C.APPS_SCRIPT_URL && !ESPACE_ID) {
    A._prospect = true; sauverBrouillon();
    appel({ action: "lead", email: A.email, raison: A.raison, effectif: A.effectif, documents: docs.map((d) => numDoc(d[1])) }).catch(() => {});
  }
}

// ---------- récapitulatif et génération ----------
async function rendreRecap(zone) {
  zone.innerHTML = `<h2>Récapitulatif</h2><p class="chargement">Préparation de la liste des documents</p>`;
  let docs;
  try { docs = await majDocs(); }
  catch (e) { zone.innerHTML = `<h2>Récapitulatif</h2><p class="erreur">Le générateur n'a pas pu démarrer. Rechargez la page puis réessayez.</p>`; return; }
  const regs = docs.map((d) => numDoc(d[1])).filter((n) => REGISTRES[n]);
  const payeOk = ESPACE_ID && estPaye();
  const libelle = payeOk ? "Télécharger le pack à jour" : C.PAIEMENT_ACTIF ? `Payer ${esc(C.PRIX_HT)} € HT et recevoir le pack` : "Télécharger mon pack";
  zone.innerHTML = `<h2>Récapitulatif</h2>
    <p class="intro">${docs.length} documents établis pour <b>${esc(A.raison || "")}</b>, avec le panneau récapitulatif A3 et le pack complet en un seul PDF.</p>
    ${listeDocs(docs)}
    ${payeOk ? "" : `<div class="encart-paiement">
      ${C.PAIEMENT_ACTIF ? `<label class="champ-paiement" for="email-paiement">Adresse e-mail de réception du pack et de la facture</label>
      <input type="email" id="email-paiement" autocomplete="email" value="${esc(A.email || "")}" placeholder="vous@entreprise.fr">
      <p class="aide">Votre lien personnel et la facture sont envoyés à cette adresse.</p>` : ""}
      <label class="cgv"><input type="checkbox" id="cgv"><span>J'accepte les <a href="cgv.html" target="_blank">conditions générales de vente</a>. Je demande la fourniture immédiate du pack et reconnais perdre mon droit de rétractation dès son téléchargement.</span></label></div>`}
    <div class="actions-recap"><button class="btn btn-lg" id="generer">${libelle}</button></div>
    ${payeOk && regs.length ? `<div class="encart"><h3 class="sous">Feuillets supplémentaires de registres</h3>
      <p class="aide">Numérotez les nouveaux feuillets à la suite des précédents.</p>
      <div class="regs">${regs.map((n) => `<label class="pill"><input type="checkbox" value="${n}"> ${esc(REGISTRES[n])}</label>`).join("")}</div>
      <button class="btn-sec" id="feuillets">Télécharger les feuillets</button></div>` : ""}
    <p id="etat" class="etat" role="status"></p>`;
  $("#generer").addEventListener("click", () => generer(docs));
  const bf = $("#feuillets");
  if (bf) bf.addEventListener("click", async () => {
    const n = [...zone.querySelectorAll(".regs input:checked")].map((i) => i.value);
    if (!n.length) return etat("Cochez au moins un registre.", true);
    etat("Préparation des feuillets…");
    telecharger(await genererFeuillets(donneesPack(), n), "Feuillets_registres.pdf"); etat("Feuillets téléchargés.");
  });
}
function etat(t, err) { const e = $("#etat"); if (e) { e.textContent = t; e.className = "etat" + (err ? " erreur" : ""); } }

let dernierPack = null;
async function generer(docs) {
  const em = $("#email-paiement");
  if (em) {
    const v = em.value.trim();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) { em.focus(); return etat("Indiquez une adresse e-mail valide pour recevoir le pack.", true); }
    A.email = v; sauverBrouillon();
  }
  const cgv = $("#cgv");
  if (cgv && !cgv.checked) return etat("Veuillez accepter les conditions générales de vente.", true);
  const btn = $("#generer"); btn.disabled = true;
  try {
    const numeros = docs.map((d) => numDoc(d[1]));
    if (C.APPS_SCRIPT_URL) {
      etat("Enregistrement de votre commande…");
      const r = await appel({ action: client ? "update" : "save", id: client && client.id, email: A.email, reponses: A, documents: numeros });
      if (r) client = { id: r.id, commande: r.commande, paye: client && client.paye ? true : !!r.paye };
    }
    if (C.PAIEMENT_ACTIF && !estPaye()) {
      if (!client) throw new Error("le paiement nécessite l'enregistrement de la commande.");
      etat("Ouverture de la page de paiement sécurisé…");
      const p = await appel({ action: "payer", id: client.id });
      if (p && p.paye) { client.paye = true; }
      else { if (!ESPACE_ID) { try { localStorage.removeItem(BROUILLON); } catch (e) {} } window.location.href = p.url; return; }
    }
    etat("Fabrication des documents…");
    dernierPack = await genererPack(donneesPack());
    telecharger(dernierPack, "Pack_affichages_obligatoires.zip");
    if (C.APPS_SCRIPT_URL && client) appel({ action: "log", id: client.id }).catch(() => {});
    if (!ESPACE_ID) { try { localStorage.removeItem(BROUILLON); } catch (e) {} }
    rendreFin(docs.length);
  } catch (e) { etat("La fabrication a échoué : " + e.message, true); btn.disabled = false; }
}

function rendreFin(n) {
  const zone = $("#etape");
  $(".nav-etapes").hidden = true;
  $("#barre").style.width = "100%";
  $("#nom-etape").textContent = "Pack téléchargé";
  $("#compteur").textContent = "";
  const lien = client && !ESPACE_ID
    ? `<li>Conservez le courriel envoyé à <b>${esc(A.email || "")}</b> : son lien ouvre votre espace client, où vous retrouvez vos réponses, vos documents à jour et des feuillets supplémentaires de registres.</li>` : "";
  zone.innerHTML = `<div class="fin"><div class="ok-badge">${ICON_OK}</div>
    <h2>Votre pack est prêt</h2>
    <p class="intro">Le téléchargement du fichier <b>Pack_affichages_obligatoires.zip</b> a démarré. Il contient ${n} documents, le pack complet et le panneau récapitulatif.</p>
    <h3 class="sous">Étapes suivantes</h3>
    <ol>
      <li>Imprimez les documents au format A4 et le panneau récapitulatif au format A3.</li>
      <li>Affichez-les dans les locaux de travail, à un emplacement accessible à l'ensemble du personnel.</li>
      <li>Rangez les registres et le document unique dans un endroit connu, et tenez-les à jour.</li>
      ${lien}
    </ol>
    <div class="actions-recap"><a class="btn" href="index.html">Retour à l'accueil</a>
      <button class="btn-sec" id="retelecharger">Télécharger à nouveau</button></div></div>`;
  $("#retelecharger").addEventListener("click", () => dernierPack && telecharger(dernierPack, "Pack_affichages_obligatoires.zip"));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ---------- démarrage ----------
async function demarrer() {
  chargerGenerateur();   // en tâche de fond pendant la saisie
  $("#prec").addEventListener("click", () => { etape--; rendre(); });
  $("#suiv").addEventListener("click", suivant);
  if (ESPACE_ID) {
    $("#titre-page").textContent = "Votre espace client";
    $("#sous-titre").textContent = "Vos réponses sont enregistrées. Modifiez-les si besoin : vos documents sont régénérés avec les textes en vigueur.";
    try {
      if (!C.APPS_SCRIPT_URL) throw new Error("Espace client indisponible pour le moment.");
      const j = await chargerClient(ESPACE_ID);
      A = j.reponses || {}; client = { id: ESPACE_ID, commande: j.commande, paye: j.paye !== false };
      if (!client.paye && params.get("paiement")) {
        $("#etape").innerHTML = `<p class="chargement">Confirmation de votre paiement</p>`;
        for (let i = 0; i < 10 && !client.paye; i++) {
          try { const v = await appel({ action: "verifier", id: ESPACE_ID }); client.paye = !!(v && v.paye); } catch (e) {}
          if (!client.paye) await new Promise((ok) => setTimeout(ok, 3000));
        }
        if (!client.paye) $("#sous-titre").textContent = "Votre paiement n'est pas encore confirmé. Rechargez cette page dans une minute ; le lien vous est aussi envoyé par courriel dès la confirmation.";
      }
      $("#bandeau").innerHTML = `Commande n° <b>${esc(j.commande)}</b> · ${esc(A.raison || "")}`;
      $("#bandeau").hidden = false;
      etape = etapesVisibles().length - 1;
    } catch (e) { $("#etape").innerHTML = `<p class="erreur">${esc(e.message)}</p>`; $(".nav-etapes").hidden = true; return; }
  } else {
    A = lireBrouillon();
  }
  rendre(false);
}
document.addEventListener("DOMContentLoaded", demarrer);
