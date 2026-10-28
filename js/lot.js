// Page revendeur : commande d'un lot de packs (paiement Lemon Squeezy, codes envoyés par courriel).
(function () {
  const C = window.CONFIG || {};
  const p = new URLSearchParams(location.search);
  const $ = (s) => document.querySelector(s);
  const etat = (t, err) => { const e = $("#lot-etat"); e.textContent = t; e.className = "etat" + (err ? " erreur" : ""); };
  document.addEventListener("DOMContentLoaded", () => {
    if (p.get("code")) $("#lot-code").value = p.get("code");
    if (p.get("paiement")) etat("Merci : votre paiement est enregistré. Vos codes vous sont envoyés par courriel dans les minutes qui suivent.");
    $("#lot-payer").addEventListener("click", async () => {
      const code = $("#lot-code").value.toUpperCase().replace(/[^A-Z0-9]/g, "");
      const q = parseInt($("#lot-qte").value, 10);
      if (!code) return etat("Indiquez votre identifiant revendeur.", true);
      if (!(q >= 1 && q <= 500)) return etat("Indiquez un nombre de packs entre 1 et 500.", true);
      $("#lot-payer").disabled = true; etat("Ouverture de la page de paiement sécurisé…");
      try {
        const r = await fetch(C.APPS_SCRIPT_URL, { method: "POST", body: JSON.stringify({ action: "lot", code: code, quantite: q }) });
        const j = await r.json();
        if (!j.ok) throw new Error(j.erreur || "Commande impossible.");
        location.href = j.url;
      } catch (e) { etat(e.message, true); $("#lot-payer").disabled = false; }
    });
  });
})();
