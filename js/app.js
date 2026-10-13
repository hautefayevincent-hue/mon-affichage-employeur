// Questionnaire, enregistrement et espace client.
const C = window.CONFIG;
const params = new URLSearchParams(location.search);
const ESPACE_ID = params.get("id");
const BROUILLON = "pack_brouillon_v1";
let A = {};            // réponses
let etape = 0;
let client = null;     // { id, commande } une fois enregistré

const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const visible = (f) => !f.si || f.si(A);
const etapesVisibles = () => ETAPES.filter((e) => e.id === "recap" || e.champs.some(visible) || e.vide);

function sauverBrouillon() { if (ESPACE_ID) return; try { localStorage.setItem(BROUILLON, JSON.stringify(A)); } catch (e) {} }
function lireBrouillon() { try { return JSON.parse(localStorage.getItem(BROUILLON) || "{}"); } catch (e) { return {}; } }

// ---------- rendu des champs ----------
function champHTML(f) {
  const v = A[f.k];
  const req = f.req ? ' <span class="req">*</span>' : "";
  const aide = f.aide ? `<p class="aide">${esc(f.aide)}</p>` : "";
  if (f.type === "titre") return `<h3 class="sous">${esc(f.l)}</h3>`;
  if (f.type === "ouinon") {
    return `<fieldset class="ouinon" data-k="${f.k}"><legend>${esc(f.l)}</legend>
      ${["oui", "non"].map((o) => `<label class="pill"><input type="radio" name="${f.k}" value="${o}" ${v === o ? "checked" : ""}> ${o === "oui" ? "Oui" : "Non"}</label>`).join("")}
      ${aide}</fieldset>`;
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
function rendre(scroll = true) {
  const ets = etapesVisibles();
  etape = Math.min(etape, ets.length - 1);
  const e = ets[etape];
  $("#progression").innerHTML = ets.map((x, i) => `<li class="${i < etape ? "fait" : i === etape ? "actif" : ""}">${esc(x.titre)}</li>`).join("");
  $("#compteur").textContent = `Étape ${etape + 1} sur ${ets.length}`;
  const zone = $("#etape");
  if (e.id === "recap") { rendreRecap(zone); }
  else {
    const ch = e.champs.filter(visible);
    zone.innerHTML = `<h2>${esc(e.titre)}</h2>${e.intro ? `<p class="intro">${esc(e.intro)}</p>` : ""}
      ${ch.length ? ch.map(champHTML).join("") : `<p class="intro">${esc(e.vide || "")}</p>`}`;
    lierChamps(zone);
  }
  $("#prec").hidden = etape === 0;
  $("#suiv").hidden = e.id === "recap";
  $("#erreurs").textContent = "";
  if (scroll) window.scrollTo({ top: 0, behavior: "smooth" });
}

function manquants(e) {
  return e.champs.filter(visible).filter((f) => {
    if (f.type === "ouinon") return !A[f.k];
    return f.req && !String(A[f.k] || "").trim();
  });
}

function suivant() {
  const e = etapesVisibles()[etape];
  const m = manquants(e);
  if (m.length) {
    $("#erreurs").textContent = "À compléter : " + m.map((f) => f.l).join(" · ");
    const first = $(`[data-k="${m[0].k}"]`); if (first) first.focus?.();
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
  // situation : réponses non affichées = non
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

// ---------- récapitulatif et génération ----------
async function rendreRecap(zone) {
  zone.innerHTML = `<h2>Votre pack</h2><p class="intro">Préparation de la liste des documents…</p>`;
  let docs;
  try { docs = await documentsDus(donneesPack()); }
  catch (e) { zone.innerHTML = `<h2>Votre pack</h2><p class="erreur">Le générateur n'a pas pu démarrer : ${esc(e.message)}</p>`; return; }
  const socle = docs.filter((d) => d[0] === "01_Socle"), sit = docs.filter((d) => d[0] !== "01_Socle");
  const nom = (n) => { const k = n.split("_")[0]; return esc(k + " · " + (TITRES[k] || n)); };
  const regs = docs.map((d) => d[1].split("_")[0]).filter((n) => REGISTRES[n]);
  zone.innerHTML = `<h2>Votre pack</h2>
    <p class="intro">${docs.length} documents pour <b>${esc(A.raison || "")}</b>, plus le panneau récapitulatif A3 et le pack complet en un seul PDF.</p>
    <div class="deuxcol"><div><h3 class="sous">Socle</h3><ul class="docs">${socle.map((d) => `<li>${nom(d[1])}</li>`).join("")}</ul></div>
    <div><h3 class="sous">Documents complémentaires</h3><ul class="docs">${sit.length ? sit.map((d) => `<li>${nom(d[1])}</li>`).join("") : "<li>Aucun document supplémentaire</li>"}</ul></div></div>
    ${ESPACE_ID ? "" : `<label class="cgv"><input type="checkbox" id="cgv"><span>J'accepte les <a href="cgv.html" target="_blank">conditions générales de vente</a> je demande la fourniture immédiate du pack et je reconnais perdre mon droit de rétractation dès son téléchargement.</span></label>`}
    <div class="actions-recap"><button class="btn" id="generer">${ESPACE_ID ? "Télécharger le pack à jour" : C.PAIEMENT_ACTIF ? `Payer ${esc(C.PRIX_HT)} € HT et recevoir le pack` : "Générer mon pack"}</button></div>
    ${ESPACE_ID && regs.length ? `<div class="encart"><h3 class="sous">Feuillets supplémentaires de registres</h3>
      <p class="aide">Les feuillets sont à numéroter à la suite des précédents.</p>
      <div class="regs">${regs.map((n) => `<label class="pill"><input type="checkbox" value="${n}"> ${esc(REGISTRES[n])}</label>`).join("")}</div>
      <button class="btn-sec" id="feuillets">Télécharger les feuillets</button></div>` : ""}
    <p id="etat" class="etat" role="status"></p>`;
  $("#generer").addEventListener("click", () => generer(docs));
  $("#feuillets")?.addEventListener("click", async () => {
    const n = [...zone.querySelectorAll(".regs input:checked")].map((i) => i.value);
    if (!n.length) return etat("Cochez au moins un registre.");
    etat("Préparation des feuillets…");
    telecharger(await genererFeuillets(donneesPack(), n), "Feuillets_registres.pdf"); etat("Feuillets téléchargés.");
  });
}
function etat(t, err) { const e = $("#etat"); if (e) { e.textContent = t; e.className = "etat" + (err ? " erreur" : ""); } }

async function generer(docs) {
  if (!ESPACE_ID && !$("#cgv").checked) return etat("Merci d'accepter les conditions générales de vente.", true);
  const btn = $("#generer"); btn.disabled = true;
  try {
    const numeros = docs.map((d) => d[1].split("_")[0]);
    if (C.APPS_SCRIPT_URL) {
      etat("Enregistrement de votre commande…");
      const r = await appel({ action: client ? "update" : "save", id: client?.id, email: A.email, reponses: A, documents: numeros });
      if (r) client = { id: r.id, commande: r.commande };
    }
    etat("Fabrication des documents…");
    const blob = await genererPack(donneesPack());
    telecharger(blob, "Pack_affichages_obligatoires.zip");
    if (C.APPS_SCRIPT_URL && client) { appel({ action: "log", id: client.id }).catch(() => {}); }
    etat(client && !ESPACE_ID ? "Pack téléchargé. Votre lien personnel vient de vous être envoyé par courriel." : "Pack téléchargé.");
    if (!ESPACE_ID) { try { localStorage.removeItem(BROUILLON); } catch (e) {} }
  } catch (e) { etat("Erreur : " + e.message, true); }
  btn.disabled = false;
}

// ---------- démarrage ----------
async function demarrer() {
  document.querySelectorAll("[data-nom]").forEach((el) => (el.textContent = C.NOM_COMMERCIAL));
  chargerGenerateur();   // en tâche de fond pendant la saisie
  $("#prec").addEventListener("click", () => { etape--; rendre(); });
  $("#suiv").addEventListener("click", suivant);
  if (ESPACE_ID) {
    $("#titre-page").textContent = "Votre espace";
    try {
      const j = await chargerClient(ESPACE_ID);
      A = j.reponses || {}; client = { id: ESPACE_ID, commande: j.commande };
      $("#bandeau").innerHTML = `Commande n° <b>${esc(j.commande)}</b> · ${esc(A.raison || "")}. Vos réponses sont modifiables : vos documents seront régénérés avec les textes en vigueur.`;
      $("#bandeau").hidden = false;
      etape = etapesVisibles().length - 1;
    } catch (e) { $("#etape").innerHTML = `<p class="erreur">${esc(e.message)}</p>`; return; }
  } else {
    A = lireBrouillon();
  }
  rendre(false);
}
document.addEventListener("DOMContentLoaded", demarrer);
