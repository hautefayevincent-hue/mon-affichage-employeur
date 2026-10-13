# -*- coding: utf-8 -*-
"""Textes légaux chargés depuis les extraits Légifrance (MCP OpenLegi / API PISTE), relevés le 12/10/2026.
Seule correction appliquée : nettoyage des espaces parasites de l'API (« l' article », « L. 3211-1 , »)."""
import re, glob, os
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sorted(glob.glob(os.path.join(HERE, "legi_*.md")) + glob.glob(os.path.join(HERE, "..", "legi_*.md")))
ART = {}; META = {}
for f in SRC:
    txt = open(f, encoding="utf-8").read()
    for m in re.finditer(r"^## Article (\S+) du (code [^\n]+)\n(.*?)```text\n(.*?)\n```", txt, re.S | re.M):
        num, code, head, body = m.group(1), m.group(2), m.group(3), m.group(4)
        link = re.search(r"Lien : (\S+)", head); since = re.search(r"En vigueur depuis : ([0-9/]+)", head)
        ART[num] = body
        META[num] = dict(code=code, lien=link.group(1) if link else "", depuis=since.group(1) if since else "")

def clean(s):
    s = re.sub(r"\s+([,.])(?=\s|$)", r"\1", s)
    s = s.replace("l' article", "l'article").replace("l 'article", "l'article").replace("d' article", "d'article")
    s = re.sub(r"(\d) e classe", r"\1e classe", s).replace("1 er ", "1er ")
    s = re.sub(r"\[\.\.\.\]\n?", "", s)
    return s

def paras(num):
    return [clean(p) for p in ART[num].split("\n") if p.strip()]

CP_222_33 = paras("222-33")
CP_222_33_2 = paras("222-33-2")
CP_225_1 = paras("225-1"); CP_225_1_1 = paras("225-1-1"); CP_225_1_2 = paras("225-1-2")
CP_225_2 = paras("225-2"); CP_225_3 = paras("225-3"); CP_225_4 = paras("225-4")
CT_L3221 = [("Article L. 3221-%d" % i, paras("L3221-%d" % i)) for i in range(1, 8)]

if __name__ == "__main__":
    print(len(ART), "articles chargés")
    for k in ["222-33", "225-4", "L3221-7", "R3515-2"]:
        print(k, META[k]["depuis"], paras(k)[:1])
