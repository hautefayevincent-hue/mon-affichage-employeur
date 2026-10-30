// Formulaire d'inscription du programme partenaires.
(function () {
  const C = window.CONFIG || {};
  const $ = (s) => document.querySelector(s);
  const etat = (t, err) => { const e = $("#pt-etat"); e.textContent = t; e.className = "etat" + (err ? " erreur" : ""); };
  document.addEventListener("DOMContentLoaded", () => {
    const f = $("#form-partenaire"); if (!f) return;
    const sel = $("#pt-profession");
    const adapter = () => {
      const comptable = /comptable/i.test(sel.value);
      const contenu = /contenu/i.test(sel.value);
      const r = f.querySelector('input[value="Recommandation"]');
      const v = f.querySelector('input[value="Revente"]');
      [[r, comptable], [v, contenu]].forEach(([el, off]) => {
        el.disabled = off; if (off && el.checked) el.checked = false;
        el.parentElement.style.opacity = off ? .45 : 1;
      });
    };
    sel.addEventListener("change", adapter);
    const profil = new URLSearchParams(location.search).get("profil");
    if (profil) {
      const o = [...sel.options].find((x) => x.value === profil || x.text === profil);
      if (o) { sel.value = o.value; adapter(); }
    }
    f.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const v = (id) => $(id).value.trim();
      const formule = (f.querySelector('input[name="formule"]:checked') || {}).value || "";
      const d = { action: "partenaire", structure: v("#pt-structure"), contact: v("#pt-contact"), email: v("#pt-email"), telephone: v("#pt-tel"),
                  profession: v("#pt-profession"), siret: v("#pt-siret").replace(/\s/g, ""), formule: formule, message: v("#pt-message"), conditions: $("#pt-conditions").checked };
      if (!d.structure || !d.contact || !d.profession || !formule) return etat("Merci de remplir les champs marqués d'une étoile.", true);
      if (!/^\d{14}$/.test(d.siret)) return etat("Indiquez votre SIRET : 14 chiffres.", true);
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(d.email)) return etat("Indiquez une adresse e-mail valide.", true);
      if (!d.conditions) return etat("Merci d'accepter les conditions du programme partenaires.", true);
      $("#pt-envoyer").disabled = true; etat("Envoi de votre demande…");
      try {
        const r = await fetch(C.APPS_SCRIPT_URL, { method: "POST", body: JSON.stringify(d) });
        const j = await r.json();
        if (!j.ok) throw new Error(j.erreur || "Envoi impossible.");
        f.innerHTML = '<h3>Merci, c'est reçu.</h3><p>Vous allez recevoir un mail de confirmation, puis vos accès une fois la demande validée.</p>';
      } catch (e) { etat(e.message, true); $("#pt-envoyer").disabled = false; }
    });
  });
})();
