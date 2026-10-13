// Éléments communs à toutes les pages : prix, contact, visionneuse d'aperçus, mesure d'audience.
(function () {
  const C = window.CONFIG || {};
  document.querySelectorAll("[data-prix]").forEach((e) => (e.textContent = C.PRIX_HT));
  document.querySelectorAll("[data-contact]").forEach((e) => {
    e.textContent = C.CONTACT;
    if (e.tagName === "A" && C.CONTACT && C.CONTACT.indexOf("@") > 0) e.href = "mailto:" + C.CONTACT;
  });

  // Visionneuse
  const boutons = document.querySelectorAll("[data-zoom]");
  if (boutons.length) {
    const lb = document.createElement("div");
    lb.className = "lightbox"; lb.setAttribute("role", "dialog"); lb.setAttribute("aria-label", "Aperçu du document");
    lb.innerHTML = '<img alt="">';
    document.body.appendChild(lb);
    const fermer = () => lb.classList.remove("ouvert");
    lb.addEventListener("click", fermer);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") fermer(); });
    boutons.forEach((b) => b.addEventListener("click", () => {
      const img = lb.querySelector("img"); img.src = b.dataset.zoom; img.alt = b.dataset.alt || "";
      lb.classList.add("ouvert");
    }));
  }

  // Mesure d'audience sans cookie (GoatCounter), active seulement si un code est renseigné dans config.js
  if (C.GOATCOUNTER) {
    const s = document.createElement("script");
    s.async = true; s.src = "https://gc.zgo.at/count.js";
    s.dataset.goatcounter = "https://" + C.GOATCOUNTER + ".goatcounter.com/count";
    document.body.appendChild(s);
  }
})();
