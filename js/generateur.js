// Générateur du pack exécuté dans le navigateur (Python + reportlab via Pyodide).
// Aucune donnée n'est envoyée à un serveur pour fabriquer les PDF.
const PY_FILES = ["build.py", "textes.py", "modele_espace_sans_tabac.png", "modele_emplacement_fumeur.png",
  "legi_222_33.md", "legi_penal_csp.md", "legi_travail_1.md", "legi_travail_2.md"];
const GEN_DIR = "/home/pyodide/gen";
let _pyReady = null;

function chargerGenerateur(base) {
  if (_pyReady) return _pyReady;
  base = base || "./";
  _pyReady = (async () => {
    const py = await loadPyodide({ indexURL: base + "pyodide/" });
    await py.loadPackage(["pillow", "charset-normalizer"]);
    const whl = await (await fetch(base + "wheels/reportlab-5.0.1-py3-none-any.whl")).arrayBuffer();
    py.unpackArchive(whl, "wheel", { extractDir: "/lib/python3.12/site-packages" });
    py.FS.mkdirTree(GEN_DIR);
    await Promise.all(PY_FILES.map(async (f) => {
      const r = await fetch(base + "py/" + f, { cache: "no-cache" });
      if (!r.ok) throw new Error("Fichier manquant : " + f);
      py.FS.writeFile(GEN_DIR + "/" + f, new Uint8Array(await r.arrayBuffer()));
    }));
    py.runPython(`import sys, os\nsys.path.insert(0, "${GEN_DIR}")\nos.chdir("${GEN_DIR}")\nimport build`);
    return py;
  })();
  return _pyReady;
}

async function documentsDus(data) {
  const py = await chargerGenerateur();
  py.globals.set("DATA_JSON", JSON.stringify(data));
  const res = py.runPython(`import json\njson.dumps(build.liste_documents(json.loads(DATA_JSON)))`);
  return JSON.parse(res);
}

async function genererPack(data) {
  const py = await chargerGenerateur();
  py.globals.set("DATA_JSON", JSON.stringify(data));
  const path = py.runPython(`import shutil, os\nshutil.rmtree("/tmp/pack", ignore_errors=True); os.makedirs("/tmp/pack")\nbuild.build_client(DATA_JSON, "/tmp/pack")`);
  return new Blob([py.FS.readFile(path)], { type: "application/zip" });
}

async function genererFeuillets(data, numeros) {
  const py = await chargerGenerateur();
  py.globals.set("DATA_JSON", JSON.stringify(data));
  py.globals.set("NUMS", JSON.stringify(numeros));
  const path = py.runPython(`import json, os\nos.makedirs("/tmp/feuillets", exist_ok=True)\nbuild.build_registres(DATA_JSON, "/tmp/feuillets", json.loads(NUMS))`);
  return new Blob([py.FS.readFile(path)], { type: "application/pdf" });
}

function telecharger(blob, nom) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = nom;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 10000);
}
