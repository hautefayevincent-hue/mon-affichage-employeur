# -*- coding: utf-8 -*-
"""Génération du pack socle : affichages et registres obligatoires employeur.
Usage : python build.py <dossier_sortie>
Produit deux versions : vierge (à remplir) et exemple (entreprise fictive)."""
import sys, os
from reportlab.lib.pagesizes import A4, A3, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
                                Table, TableStyle, PageBreak, NextPageTemplate, Flowable, KeepTogether)
from reportlab.pdfgen import canvas as rl_canvas
import textes as T
import html as _html

def _raw(x):
    return _html.unescape(x) if isinstance(x, str) else x

VERSION = "Version 2026-10"
ASOF = "Textes en vigueur au 16 octobre 2026"
NAVY = colors.HexColor("#1F3A5F")
INK = colors.HexColor("#1A1A1A")
GREY = colors.HexColor("#5A6270")
LIGHT = colors.HexColor("#EEF2F7")
RULE = colors.HexColor("#B8C2CF")
RED = colors.HexColor("#B42318")
FILL = colors.HexColor("#0B4A8B")

# ---------- styles ----------
def S(name, **kw):
    base = dict(fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK)
    base.update(kw)
    return ParagraphStyle(name, **base)

ST = {
    "title": S("title", fontName="Helvetica-Bold", fontSize=19, leading=23, textColor=NAVY, spaceAfter=2),
    "basis": S("basis", fontSize=9, leading=12, textColor=GREY, spaceAfter=8),
    "h2": S("h2", fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=NAVY, spaceBefore=8, spaceAfter=4),
    "h3": S("h3", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=INK, spaceBefore=5, spaceAfter=2),
    "body": S("body", alignment=TA_JUSTIFY),
    "small": S("small", fontSize=8, leading=10.5, textColor=GREY),
    "legal": S("legal", fontSize=8.2, leading=10.6, alignment=TA_JUSTIFY),
    "legalh": S("legalh", fontName="Helvetica-Bold", fontSize=8.6, leading=11, textColor=NAVY, spaceBefore=5, spaceAfter=1),
    "cell": S("cell", fontSize=8.2, leading=10.2),
    "cellb": S("cellb", fontName="Helvetica-Bold", fontSize=8.2, leading=10.2, textColor=colors.white),
    "big": S("big", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=INK),
    "center": S("center", alignment=TA_CENTER),
}

class Ctx:
    blank = True
    data = {}
    meta = ("", "")  # (numéro, titre court)

def v(key, width_chars=40):
    """Champ : valeur (exemple), ligne pointillée (vierge) ou étiquette colorée (gabarit)."""
    if getattr(Ctx, "gabarit", False):
        lab = LABELS.get(key, key)
        col = "#CFE3FF" if key in COND else "#FFE38A"
        return '<span backColor="%s"><font color="#3A2A00">&nbsp;[%s]&nbsp;</font></span>' % (col, lab)
    if Ctx.blank:
        return '<font color="#8A94A3">' + "." * width_chars + "</font>"
    val = Ctx.data.get(key, "")
    return '<font color="#0B4A8B"><b>%s</b></font>' % val

class NoSign(Flowable):
    def __init__(self, d=46*mm):
        super().__init__(); self.d = d; self.width = W_P; self.height = d
    def draw(self):
        c = self.canv; r = self.d / 2; cx = self.width / 2; cy = r
        c.setFillColor(colors.HexColor("#5A6270")); c.rect(cx - r*0.62, cy - 3*mm, r*1.05, 6*mm, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#E67E22")); c.rect(cx + r*0.43, cy - 3*mm, r*0.2, 6*mm, stroke=0, fill=1)
        c.setStrokeColor(RED); c.setLineWidth(5*mm/3); c.circle(cx, cy, r - 2*mm, stroke=1, fill=0)
        import math
        a = math.radians(45); rr = r - 2*mm
        c.line(cx - rr*math.cos(a), cy + rr*math.sin(a), cx + rr*math.cos(a), cy - rr*math.sin(a))

class Meta(Flowable):
    """Marque le document courant pour l'en-tête et le pied de page."""
    def __init__(self, num, short, kind="AFFICHAGE OBLIGATOIRE"):
        super().__init__(); self.num, self.short, self.kind = num, short, kind
        self.width = self.height = 0
    def draw(self):
        Ctx.meta = (self.num, self.short); Ctx.kind = self.kind

def P(txt, st="body"): return Paragraph(txt, ST[st])

import re as _re
def parse_h(x):
    """'8 h 30', '8h30', '17:30', '8 h' -> minutes ; None si illisible."""
    t = _html.unescape(str(x or "")).strip().lower().replace("heures", "h").replace("heure", "h")
    m = _re.fullmatch(r"(\d{1,2})\s*(?:h|:)\s*(\d{1,2})?\s*(?:min)?", t)
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2) or 0)

def _span(x):
    parts = _re.split(r"\s*[-–à]\s*", _html.unescape(str(x or "")).strip())
    if len(parts) != 2:
        return None
    a, b = parse_h(parts[0]), parse_h(parts[1])
    return (b - a) if a is not None and b is not None and b > a else None

def duree_jour(r):
    """r = [début, fin, repos (début - fin), reprise - fin, durée] -> minutes travaillées ou None."""
    a, b = parse_h(r[0]), parse_h(r[1])
    if a is None or b is None or b <= a:
        return None
    tot = b - a
    rep = _span(r[3]) if len(r) > 3 else None
    if rep:
        return tot + rep
    pause = _span(r[2]) if len(r) > 2 else None
    return tot - pause if pause else tot

def fmt_h(m):
    h, mi = divmod(int(m), 60)
    return "%d h" % h if not mi else "%d h %02d" % (h, mi)

def field_table(rows, colw=(62*mm, None), total=174*mm):
    data = [[P("<b>%s</b>" % a, "cell"), P(b, "cell")] for a, b in rows]
    w2 = total - colw[0]
    t = Table(data, colWidths=[colw[0], w2])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
    ]))
    return t

def grid(header, rows, widths, nblank=0, font=8, rowh=None):
    data = [[P(h, "cellb") for h in header]]
    for r in rows:
        data.append([P(c, "cell") for c in r])
    for _ in range(nblank):
        data.append(["" for _ in header])
    t = Table(data, colWidths=widths, repeatRows=1, rowHeights=None)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if rowh:
        for i in range(1 + len(rows), 1 + len(rows) + nblank):
            style.append(("TOPPADDING", (0, i), (-1, i), rowh))
    t.setStyle(TableStyle(style))
    return t

def legal_block(title, paras, num=None):
    items = [P(title, "legalh")] + [P(p, "legal") for p in paras]
    if num and num in T.META and T.META[num]["depuis"]:
        items.append(P("Version en vigueur depuis le %s · source : Légifrance" % T.META[num]["depuis"], "small"))
    return items

def boxed(flows, bg=LIGHT, width=174*mm):
    t = Table([[flows]], colWidths=[width])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return t

def register_line(width):
    return field_table([("Établissement", v("raison", 60)), ("SIRET", v("siret", 30)),
                        ("Feuillet n°", '<font color="#8A94A3">..........</font>')], total=width)

def rappel(txt):
    return P("<b>Rappel :</b> " + txt, "small")

def establishment_line(width=174*mm):
    return field_table([("Établissement", v("raison", 60)), ("Adresse", v("adresse", 70)), ("SIRET", v("siret", 30))],
                       total=width)

def head(num, short, title, basis, kind="AFFICHAGE OBLIGATOIRE"):
    return [Meta(num, short, kind), P(title, "title"), P(basis, "basis")]

def signature_block(width=174*mm):
    return field_table([("Fait à", v("ville", 30)), ("Le", v("date", 20)),
                        ("Nom et qualité du signataire", v("signataire", 50)), ("Signature", "" if not Ctx.blank else ("Signature manuscrite de l'employeur" if getattr(Ctx, "gabarit", False) else v("x", 30)))],
                       total=width)

# ---------- page décor ----------
def deco(c, doc, pagesize):
    W, H = pagesize
    num, short = Ctx.meta
    c.saveState()
    c.setFillColor(NAVY); c.rect(0, H - 14*mm, W, 14*mm, stroke=0, fill=1)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 8.5)
    c.drawString(18*mm, H - 8.8*mm, getattr(Ctx, "kind", "AFFICHAGE OBLIGATOIRE"))
    c.setFont("Helvetica", 8.5)
    c.drawRightString(W - 18*mm, H - 8.8*mm, "Document %s  ·  %s" % (num, short))
    c.setStrokeColor(RULE); c.setLineWidth(0.5); c.line(18*mm, 13*mm, W - 18*mm, 13*mm)
    c.setFillColor(GREY); c.setFont("Helvetica", 7.2)
    c.drawString(18*mm, 9*mm, "%s  ·  %s" % (ASOF, VERSION))
    c.drawRightString(W - 18*mm, 9*mm, "Page %d" % doc.page)
    lic = None
    if getattr(Ctx, "gabarit", False):
        lic = "Document établi pour [Raison sociale] · commande n° [N° de commande]"
    elif Ctx.data.get("commande"):
        lic = "Document établi pour %s · commande n° %s · usage réservé à cet établissement" % (_raw(Ctx.data["raison"]), _raw(Ctx.data["commande"]))
    if lic:
        c.setFont("Helvetica", 6.8); c.setFillColor(GREY); c.drawCentredString(W / 2, 5*mm, lic)
    if not Ctx.blank and not getattr(Ctx, "client", False):
        c.setFillColor(colors.HexColor("#C0392B")); c.setFont("Helvetica-Bold", 7.2)
        c.drawRightString(W - 34*mm, 9*mm, "EXEMPLE  ·  DONNÉES FICTIVES")
    c.restoreState()

def make_doc(path, pagesize=A4):
    doc = BaseDocTemplate(path, pagesize=pagesize, leftMargin=18*mm, rightMargin=18*mm,
                          topMargin=22*mm, bottomMargin=18*mm, title="Pack affichages et registres obligatoires",
                          author="Pack affichage obligatoire")
    pw, ph = A4
    lw, lh = landscape(A4)
    fp = Frame(18*mm, 18*mm, pw - 36*mm, ph - 40*mm, id="p", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    fl = Frame(18*mm, 18*mm, lw - 36*mm, lh - 40*mm, id="l", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([
        PageTemplate(id="P", frames=[fp], pagesize=A4, onPageEnd=lambda c, d: deco(c, d, A4)),
        PageTemplate(id="L", frames=[fl], pagesize=landscape(A4), onPageEnd=lambda c, d: deco(c, d, landscape(A4))),
        PageTemplate(id="N", frames=[Frame(15*mm, 12*mm, pw - 30*mm, ph - 24*mm, id="n", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], pagesize=A4),
    ])
    return doc

W_P = 174*mm
W_L = landscape(A4)[0] - 36*mm

# ---------- documents ----------
def doc01():
    f = head("01", "Coordonnées obligatoires", "Coordonnées des services à contacter",
             "Articles D. 4711-1 et D. 1151-1 du code du travail")
    f += [establishment_line(), Spacer(1, 8)]
    f += [P("Inspection du travail", "h2"),
          field_table([("Service (unité de contrôle)", v("it_service", 60)), ("Adresse", v("it_adresse", 70)),
                       ("Téléphone", v("it_tel", 25)), ("Nom de l'inspecteur compétent", v("it_agent", 45))])]
    f += [P("Service de prévention et de santé au travail", "h2"),
          field_table([("Médecin du travail ou service compétent", v("spst_nom", 60)), ("Adresse", v("spst_adresse", 70)),
                       ("Téléphone", v("spst_tel", 25)), ("Médecin du travail", v("spst_medecin", 45))])]
    f += [P("Services de secours d'urgence", "h2"),
          grid(["Service", "Numéro d'appel"],
               [["SAMU · urgence médicale", "<b>15</b>"], ["Police secours", "<b>17</b>"],
                ["Sapeurs-pompiers", "<b>18</b>"], ["Numéro d'urgence européen", "<b>112</b>"],
                ["Urgences pour les personnes sourdes, malentendantes ou aphasiques (SMS, fax, application)", "<b>114</b>"],
                ["Centre de secours le plus proche (facultatif)", v("secours_local", 40)]],
               [120*mm, 54*mm])]
    f += [P("Défenseur des droits", "h2"),
          field_table([("Adresse postale", "Défenseur des droits, Libre réponse 71120, 75342 Paris Cedex 07"), ("Accueil téléphonique", "<b>09 69 39 00 00</b>"),
                       ("Site internet", "www.defenseurdesdroits.fr"),
                       ("Mission", "Lutte contre les discriminations et promotion de l'égalité ; toute personne s'estimant victime d'une discrimination peut le saisir gratuitement.")])]
    return f

def doc02():
    f = head("02", "Horaires collectifs", "Horaire collectif de travail",
             "Articles L. 3171-1 et D. 3171-1 à D. 3171-7 du code du travail")
    f += [establishment_line(), Spacer(1, 6)]
    f += [field_table([("Service ou atelier concerné", v("hc_service", 50)), ("Durée hebdomadaire de travail", v("hc_duree", 15) + " heures"),
                       ("Date d'entrée en vigueur", v("hc_date", 20))])]
    f += [P("Répartition de la durée du travail", "h2")]
    days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    rows = []
    for d in days:
        if getattr(Ctx, "gabarit", False):
            rows.append([d, v("h_debut"), v("h_fin"), v("h_repos"), v("h_reprise"), v("h_duree")])
        elif Ctx.blank:
            rows.append([d, "", "", "", "", ""])
        else:
            r = list(Ctx.data.get("hc_jours", {}).get(d, ["Repos", "", "", "", ""]))
            r += [""] * (5 - len(r))
            if not str(r[4]).strip():
                m = duree_jour(r)
                if m: r[4] = fmt_h(m)
            rows.append([d] + r)
    if not Ctx.blank and not getattr(Ctx, "gabarit", False):
        tot = sum(parse_h(x[5]) or 0 for x in rows)
        if tot: rows.append(["<b>Total de la semaine</b>", "", "", "", "", "<b>%s</b>" % fmt_h(tot)])
    t = grid(["Jour", "Début", "Fin", "Repos (début - fin)", "Reprise - fin", "Durée du jour"], rows,
             [30*mm, 25*mm, 25*mm, 36*mm, 33*mm, 25*mm])
    if Ctx.blank:
        t.setStyle(TableStyle([("TOPPADDING", (0, 1), (-1, -1), 9), ("BOTTOMPADDING", (0, 1), (-1, -1), 9)]))
    f += [t]
    f += [P("Organisation en équipes successives", "h2")]
    if getattr(Ctx, "gabarit", False):
        er = [[v("eq_nom"), v("eq_jours"), v("eq_horaires"), v("eq_compo")]]
    elif Ctx.blank:
        er = []
    else:
        er = Ctx.data.get("equipes", [])
    t2 = grid(["Équipe", "Jours", "Horaires (début - fin, repos)", "Composition nominative, y compris salariés intérimaires"], er,
              [26*mm, 34*mm, 44*mm, 70*mm], nblank=max(0, 3 - len(er)), rowh=6)
    f += [t2, Spacer(1, 4), rappel("la composition nominative de chaque équipe, y compris les salariés intérimaires, est indiquée par un tableau affiché ou par un registre tenu à jour (article D. 3171-7). Un double de l'horaire collectif et de ses rectifications est préalablement adressé à l'agent de contrôle de l'inspection du travail ; toute modification donne lieu, avant son application, à une rectification affichée (article D. 3171-4).")]
    f += [Spacer(1, 6), signature_block()]
    return f

def doc02b():
    f = [NextPageTemplate("P"), PageBreak()]
    f += head("02b", "Aménagement du temps de travail", "Programme de la durée du travail sur plusieurs semaines",
              "Articles L. 3121-41 et D. 3171-5 du code du travail")
    f += [establishment_line(), Spacer(1, 6),
          field_table([("Accord ou décision applicable", v("am_accord", 60)), ("Nombre de semaines de la période de référence", v("am_semaines", 10)),
                       ("Début de la période de référence", v("am_debut", 20))])]
    rows = [[v("am_sem"), v("am_horaire"), v("am_duree")]] if getattr(Ctx, "gabarit", False) else ([] if Ctx.blank else [list(r) for r in Ctx.data.get("am_programme", [])])
    f += [P("Horaire de travail et répartition de la durée du travail pour chaque semaine", "h2"),
          grid(["Semaine", "Horaire et répartition de la durée du travail", "Durée de la semaine"], rows,
               [36*mm, 104*mm, 34*mm], nblank=max(0, 6 - len(rows)), rowh=6),
          Spacer(1, 4), rappel("l'affichage indique le nombre de semaines que comporte la période de référence et, pour chaque semaine incluse dans cette période, l'horaire de travail et la répartition de la durée du travail. Les changements de durée ou d'horaire de travail sont communiqués aux salariés en respectant un délai de prévenance de sept jours ouvrés, sauf stipulation contraire de l'accord (article D. 3171-5).")]
    f += [Spacer(1, 6), signature_block()]
    return f

def doc03():
    f = head("03", "Accès au document unique", "Accès au document unique d'évaluation des risques professionnels",
             "Articles R. 4121-1 à R. 4121-4 du code du travail")
    f += [establishment_line(), Spacer(1, 8)]
    f += [P("Le document unique d'évaluation des risques professionnels de l'établissement est à la disposition de chaque travailleur. Il peut être consulté selon les voies d'accès ci-dessous.", "body"), Spacer(1, 8)]
    acc = Table([[P("<b>VOIES D'ACCÈS</b>", "cellb"), ""],
                 [P("<b>1. Sur place</b>", "big"), P("Lieu : " + v("du_lieu", 50) + "<br/>Jours et horaires : " + v("du_horaires", 40), "body")],
                 [P("<b>2. Sur demande</b>", "big"), P("Auprès de : " + v("du_contact", 40) + "<br/>Contact : " + v("du_contact_tel", 40), "body")],
                 [P("<b>3. En ligne</b>", "big"), P("Accès numérique : " + v("du_num", 50), "body")]],
                colWidths=[46*mm, 128*mm])
    acc.setStyle(TableStyle([("SPAN", (0, 0), (-1, 0)), ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                             ("BACKGROUND", (0, 1), (0, -1), LIGHT), ("BOX", (0, 0), (-1, -1), 1.2, NAVY),
                             ("LINEBELOW", (0, 1), (-1, -2), 0.5, RULE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("TOPPADDING", (0, 1), (-1, -1), 10), ("BOTTOMPADDING", (0, 1), (-1, -1), 10), ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    f += [acc, Spacer(1, 8), field_table([("Date de la dernière mise à jour", v("du_maj", 20))])]
    f += [Spacer(1, 6), rappel("dans les établissements dotés d'un règlement intérieur, le présent avis est affiché au même emplacement que celui réservé au règlement intérieur (article R. 4121-4).")]
    return f

def official_model(png, w_mm=180):
    from reportlab.platypus import Image as RLImage
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(png).getSize()
    w = w_mm*mm; h = w * ih / iw
    maxh = 262*mm
    if h > maxh: h = maxh; w = h * iw / ih
    im = RLImage(png, width=w, height=h); im.hAlign = "CENTER"
    return im

def doc04():
    here = os.path.dirname(os.path.abspath(__file__))
    f = [NextPageTemplate("N"), PageBreak(), Meta("04", "Interdiction de fumer", "AFFICHAGE OBLIGATOIRE"),
         Spacer(1, 4*mm), official_model(os.path.join(here, "modele_espace_sans_tabac.png"))]
    f += [NextPageTemplate("N"), PageBreak(), Meta("04", "Interdiction de vapoter", "AFFICHAGE OBLIGATOIRE"), AfficheVapotage()]
    return f

class AfficheVapotage(Flowable):
    """Signalisation de l'interdiction de vapoter (art. R. 3513-3 CSP : aucun modèle officiel imposé)."""
    def wrap(self, aw, ah):
        self.w, self.h = aw, ah - 2
        return self.w, self.h
    def draw(self):
        c, W, H = self.canv, self.w, self.h
        cx = W / 2
        # bandeau haut
        c.setFillColor(NAVY); c.rect(0, H - 34*mm, W, 34*mm, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 34)
        c.drawCentredString(cx, H - 22*mm, "ESPACE SANS VAPOTAGE")
        # panneau d'interdiction
        cy, r = H - 112*mm, 62*mm
        c.setFillColor(colors.white); c.setStrokeColor(RED); c.setLineWidth(11*mm)
        c.circle(cx, cy, r - 5.5*mm, stroke=1, fill=1)
        # cigarette électronique (stylo) inclinée
        c.saveState(); c.translate(cx - 4*mm, cy - 6*mm); c.rotate(20)
        body = colors.HexColor("#3B4452")
        c.setFillColor(body); c.setStrokeColor(body); c.setLineWidth(0.5)
        c.roundRect(-38*mm, -6*mm, 62*mm, 12*mm, 3*mm, stroke=0, fill=1)          # corps
        c.setFillColor(colors.HexColor("#9AA4B1"))
        c.roundRect(24*mm, -4.5*mm, 12*mm, 9*mm, 2*mm, stroke=0, fill=1)          # réservoir
        c.setFillColor(colors.HexColor("#1A1F27"))
        c.roundRect(36*mm, -2.6*mm, 8*mm, 5.2*mm, 1.6*mm, stroke=0, fill=1)        # embout
        c.setFillColor(colors.HexColor("#6FA8DC")); c.circle(-28*mm, 0, 1.6*mm, stroke=0, fill=1)  # bouton
        # vapeur
        c.setStrokeColor(colors.HexColor("#A8B3C2")); c.setLineWidth(2.6*mm); c.setLineCap(1)
        for dy, k in ((0, 1.0), (7*mm, 0.8), (-7*mm, 0.8)):
            pth = c.beginPath(); x0 = 47*mm
            pth.moveTo(x0, dy); pth.curveTo(x0 + 6*mm*k, dy + 8*mm, x0 + 10*mm*k, dy - 8*mm, x0 + 16*mm*k, dy + 2*mm)
            c.drawPath(pth, stroke=1, fill=0)
        c.restoreState()
        # barre d'interdiction
        c.setStrokeColor(RED); c.setLineWidth(11*mm); c.setLineCap(0)
        import math
        a = math.radians(45); d = r - 9*mm
        c.line(cx - d*math.cos(a), cy + d*math.sin(a), cx + d*math.cos(a), cy - d*math.sin(a))
        # textes
        c.setFillColor(RED); c.setFont("Helvetica-Bold", 44)
        c.drawCentredString(cx, cy - r - 22*mm, "INTERDIT DE VAPOTER")
        c.setFillColor(INK); c.setFont("Helvetica", 15)
        c.drawCentredString(cx, cy - r - 36*mm, "Il est interdit de vapoter dans les lieux de travail")
        c.drawCentredString(cx, cy - r - 44*mm, "fermés et couverts à usage collectif.")
        c.setFillColor(GREY); c.setFont("Helvetica", 8.5)
        c.drawCentredString(cx, 4*mm, "Articles L. 3513-6, R. 3513-2 et R. 3513-3 du code de la santé publique")

def doc04b():
    here = os.path.dirname(os.path.abspath(__file__))
    return [NextPageTemplate("N"), PageBreak(), Meta("04b", "Emplacement fumeur", "AFFICHAGE OBLIGATOIRE"),
            Spacer(1, 4*mm), official_model(os.path.join(here, "modele_emplacement_fumeur.png"))]

def doc05():
    f = head("05", "Égalité et non-discrimination", "Égalité de rémunération entre les femmes et les hommes",
             "Article R. 3221-2 du code du travail", "INFORMATION OBLIGATOIRE")
    f += [establishment_line(), Spacer(1, 4)]
    for title, paras in T.CT_L3221:
        f += legal_block(title + " du code du travail", paras, title.replace("Article ", "").replace(". ", ""))
    f += [PageBreak()]
    f += head("05", "Égalité et non-discrimination", "Lutte contre les discriminations",
              "Article L. 1142-6 du code du travail", "INFORMATION OBLIGATOIRE")
    f += legal_block("Article 225-1 du code pénal", T.CP_225_1, "225-1")
    f += legal_block("Article 225-1-1 du code pénal", T.CP_225_1_1, "225-1-1")
    f += legal_block("Article 225-1-2 du code pénal", T.CP_225_1_2, "225-1-2")
    f += legal_block("Article 225-2 du code pénal", T.CP_225_2, "225-2")
    f += legal_block("Article 225-3 du code pénal", T.CP_225_3, "225-3")
    f += legal_block("Article 225-4 du code pénal", T.CP_225_4, "225-4")
    f += [Spacer(1, 6), boxed([P("Toute personne qui s'estime victime d'une discrimination peut saisir gratuitement le <b>Défenseur des droits</b> : <b>09 69 39 00 00</b> · www.defenseurdesdroits.fr · Libre réponse 71120, 75342 Paris Cedex 07", "body")]),
          Spacer(1, 4), rappel("les textes relatifs à l'égalité de rémunération sont portés à la connaissance des personnes ayant accès aux lieux de travail ainsi qu'aux candidats à l'embauche ; les textes relatifs aux discriminations le sont également dans les locaux ou à la porte des locaux où se fait l'embauche (articles R. 3221-2 et L. 1142-6).")]
    return f

def doc06():
    f = head("06", "Harcèlement", "Harcèlement moral et harcèlement sexuel",
             "Articles L. 1152-4, L. 1153-5 et D. 1151-1 du code du travail", "INFORMATION OBLIGATOIRE")
    f += [establishment_line(), Spacer(1, 2)]
    f += [P("Harcèlement moral", "h2")]
    f += legal_block("Article 222-33-2 du code pénal", T.CP_222_33_2, "222-33-2")
    f += [P("Harcèlement sexuel", "h2")]
    f += legal_block("Article 222-33 du code pénal", T.CP_222_33, "222-33")
    f += [P("Actions contentieuses civiles et pénales ouvertes en matière de harcèlement sexuel", "h2"),
          P("<b>Action civile</b> : la victime peut saisir le conseil de prud'hommes afin d'obtenir réparation du préjudice subi et l'annulation de toute mesure prise à son encontre en raison des faits (articles L. 1153-2 à L. 1153-4 du code du travail). <b>Action pénale</b> : elle peut déposer plainte auprès des services de police ou de gendarmerie, ou saisir directement par écrit le procureur de la République.", "legal")]
    f += [P("Contacts", "h2"),
          field_table([("Médecin du travail", v("spst_medecin", 30) + " · " + v("spst_adresse", 40) + " · " + v("spst_tel", 15)),
                       ("Inspection du travail", v("it_agent", 30) + " · " + v("it_adresse", 40) + " · " + v("it_tel", 15)),
                       ("Défenseur des droits", "Libre réponse 71120, 75342 Paris Cedex 07 · 09 69 39 00 00 · www.defenseurdesdroits.fr"),
                       ("Référent du CSE (s'il existe)", v("ref_cse", 30) + " · " + v("ref_cse_coord", 40)),
                       ("Référent de l'employeur (250 salariés et plus)", v("ref_emp", 30) + " · " + v("ref_emp_coord", 40))])]
    f += [Spacer(1, 4), rappel("les textes relatifs au harcèlement sexuel sont également portés à la connaissance des personnes dans les locaux ou à la porte des locaux où se fait l'embauche (article L. 1153-5).")]
    return f

def doc07():
    f = head("07", "Conventions et accords", "Avis relatif aux conventions et accords collectifs applicables",
             "Articles R. 2262-1 à R. 2262-3 du code du travail", "INFORMATION OBLIGATOIRE")
    f += [establishment_line(), Spacer(1, 8)]
    f += [field_table([("Convention collective applicable", v("cc_nom", 60)), ("Identifiant (IDCC)", v("cc_idcc", 10)),
                       ("Accords nationaux interprofessionnels", "Accords nationaux interprofessionnels applicables à l'entreprise"),
                       ("Accords d'entreprise ou d'établissement", v("accords", 70)),
                       ("Lieu où les textes sont tenus à disposition", v("cc_lieu", 60)),
                       ("Modalités de consultation pendant le temps de présence", v("cc_modalites", 60))])]
    f += [Spacer(1, 8), P("Un exemplaire à jour de la convention collective applicable est tenu à la disposition des salariés sur le lieu de travail. Les salariés peuvent en prendre connaissance pendant leur temps de présence sur le lieu de travail, dans les conditions précisées ci-dessus.", "body")]
    return f

def doc08():
    f = head("08", "Congés payés", "Congés payés : période de prise et ordre des départs",
             "Articles L. 3141-13 à L. 3141-16, D. 3141-5 et D. 3141-6 du code du travail", "INFORMATION OBLIGATOIRE")
    f += [establishment_line(), Spacer(1, 8)]
    f += [field_table([("Période de référence pour l'acquisition des congés", "du " + v("cp_debut", 18) + " au " + v("cp_fin", 18)),
                       ("Période de prise du congé principal", "du " + v("cp_p_debut", 18) + " au " + v("cp_p_fin", 18)),
                       ("Fermeture de l'établissement (le cas échéant)", v("cp_fermeture", 50)),
                       ("Critères retenus pour fixer l'ordre des départs", v("cp_criteres", 70)),
                       ("Caisse de congés payés (le cas échéant)", v("cp_caisse", 60))])]
    f += [Spacer(1, 4), rappel("la période de prise des congés est portée à la connaissance des salariés au moins deux mois avant son ouverture (article D. 3141-5). L'ordre des départs est communiqué, par tout moyen, à chaque salarié un mois avant son départ (article D. 3141-6).")]
    f += [Spacer(1, 6), signature_block()]
    return f

def doc09():
    f = head("09", "Premiers secours", "Organisation des premiers secours",
             "Articles R. 4224-14 à R. 4224-16 du code du travail", "DOCUMENT OBLIGATOIRE")
    f += [establishment_line(), Spacer(1, 6)]
    f += [field_table([("Date de l'avis du médecin du travail", v("ps_avis", 20)),
                       ("Emplacement du matériel de premiers secours", v("ps_lieu", 60)),
                       ("Sauveteur(s) secouriste(s) du travail (le cas échéant)", v("ps_sst", 60)),
                       ("Emplacement du défibrillateur (le cas échéant)", v("ps_dae", 50)),
                       ("Personne à prévenir dans l'établissement", v("ps_contact", 50))])]
    f += [P("Conduite à tenir en cas d'accident", "h2")]
    steps = [("1. Protéger", "Supprimer ou isoler le danger pour éviter un sur-accident, sans se mettre en danger."),
             ("2. Examiner", "Vérifier si la victime répond, respire, saigne abondamment."),
             ("3. Alerter", "Appeler le <b>15</b> (SAMU), le <b>18</b> (pompiers) ou le <b>112</b>. Indiquer : l'adresse précise, la nature de l'accident, le nombre de victimes et leur état, les gestes déjà effectués. Ne pas raccrocher le premier."),
             ("4. Secourir", "Pratiquer les gestes de premiers secours adaptés, dans la limite de sa formation, jusqu'à l'arrivée des secours.")]
    f += [grid(["Étape", "Action"], [[a, b] for a, b in steps], [32*mm, 142*mm])]
    f += [Spacer(1, 4), rappel("les mesures de premiers secours sont prises après avis du médecin du travail et consignées dans un document tenu à la disposition de l'inspection du travail (article R. 4224-16).")]
    return f

def registre_cover(num, short, title, basis, intro, kind):
    f = [NextPageTemplate("P"), PageBreak()] if False else []
    f += head(num, short, title, basis, kind)
    f += [establishment_line(), Spacer(1, 8), P(intro, "body"), Spacer(1, 8)]
    return f

def doc10():
    f = [NextPageTemplate("L"), PageBreak()]
    f += head("10", "Registre unique du personnel", "Registre unique du personnel",
              "Articles L. 1221-13, L. 1221-15, D. 1221-23 à D. 1221-27 et R. 1221-26 du code du travail", "REGISTRE OBLIGATOIRE")
    f += [register_line(W_L), Spacer(1, 4),
          rappel("les noms et prénoms de tous les salariés sont inscrits dans l'ordre des embauches, au moment de l'embauche et de façon indélébile. Les mentions sont conservées cinq ans à compter de la date de départ du salarié ou du stagiaire. Une copie des titres de travail des salariés étrangers est annexée au registre."), Spacer(1, 4)]
    hdr = ["N°", "Nom et prénoms", "Nationalité", "Date de naissance", "Sexe", "Emploi", "Qualification", "Date d'entrée", "Date de sortie",
           "Type de contrat (CDD, temps partiel, apprentissage, professionnalisation)", "Date d'autorisation d'embauche ou de licenciement (si requise)",
           "Salarié temporaire : nom et adresse de l'entreprise de travail temporaire · Salarié mis à disposition par un groupement d'employeurs : nom et adresse du groupement", "Salarié étranger : type et n° d'ordre du titre de travail"]
    wd = [7, 28, 16, 16, 9, 20, 20, 15, 15, 28, 22, 34, 28]
    s = sum(wd); wd = [W_L * x / s for x in wd]
    rows = []
    if not Ctx.blank:
        rows = Ctx.data.get("rup", [])
    f += [grid(hdr, rows, wd, nblank=8 - len(rows), rowh=10)]
    f += [PageBreak()]
    f += head("10", "Registre unique du personnel", "Registre unique du personnel : stagiaires et volontaires",
              "Article L. 1221-13 du code du travail : partie distincte du registre", "REGISTRE OBLIGATOIRE")
    hdr2 = ["N°", "Nom et prénoms", "Statut (stagiaire, service civique)", "Date d'arrivée", "Date de départ", "Nom du tuteur", "Lieu de présence"]
    wd2 = [8, 50, 40, 25, 25, 45, 50]; s = sum(wd2); wd2 = [W_L * x / s for x in wd2]
    f += [grid(hdr2, [], wd2, nblank=11, rowh=10)]
    return f

def doc11():
    f = [NextPageTemplate("L"), PageBreak()]
    f += head("11", "Document unique", "Document unique d'évaluation des risques professionnels : trame à compléter",
              "Articles L. 4121-1 à L. 4121-3-1 et R. 4121-1 à R. 4121-4 du code du travail", "TRAME À COMPLÉTER")
    f += [establishment_line(W_L), Spacer(1, 6),
          field_table([("Activité de l'établissement", v("activite", 60)), ("Effectif", v("effectif", 10)),
                       ("Personne chargée de l'évaluation", v("du_contact", 45)), ("Date de l'évaluation", '<font color="#8A94A3">....................</font>')], total=W_L)]
    f += [Spacer(1, 4), rappel("cette trame ne constitue pas l'évaluation des risques. Le document unique n'est établi qu'une fois l'inventaire des risques de chaque unité de travail réalisé et consigné.")]
    f += [P("Rappel des obligations", "h2"),
          grid(["Point", "Règle"],
               [["Contenu", "Inventaire des risques identifiés dans chaque unité de travail et résultats de leur évaluation."],
                ["Mise à jour", "Au moins chaque année dans les entreprises d'au moins onze salariés ; dans tous les cas lors de toute décision d'aménagement important modifiant les conditions de santé et de sécurité ou les conditions de travail, et lorsqu'une information supplémentaire intéressant l'évaluation d'un risque est portée à la connaissance de l'employeur."],
                ["Prévention", "Moins de 50 salariés : actions de prévention et de protection consignées dans le document unique. 50 salariés et plus : programme annuel de prévention des risques professionnels et d'amélioration des conditions de travail."],
                ["Conservation", "Le document et ses versions successives sont conservés pendant au moins quarante ans."],
                ["Transmission", "Le document est transmis au service de prévention et de santé au travail à chaque mise à jour."]],
               [36*mm, W_L - 36*mm])]
    f += [P("Historique des versions", "h2"),
          grid(["Version", "Date", "Motif de la mise à jour", "Rédacteur"], [], [24*mm, 34*mm, W_L - 118*mm, 60*mm], nblank=3, rowh=7)]
    f += [NextPageTemplate("L"), PageBreak()]
    f += head("11", "Document unique", "Évaluation des risques par unité de travail",
              "Article R. 4121-1 du code du travail", "TRAME À COMPLÉTER")
    hdr = ["Unité de travail", "Danger identifié", "Risque et situation d'exposition", "Gravité (1-4)", "Probabilité (1-4)", "Niveau de risque",
           "Mesures de prévention existantes", "Actions à mettre en œuvre", "Responsable", "Échéance"]
    wd = [26, 26, 34, 13, 15, 14, 34, 34, 20, 16]; s = sum(wd); wd = [W_L * x / s for x in wd]
    f += [grid(hdr, [], wd, nblank=9, rowh=12)]
    f += [Spacer(1, 4), P("Cotation fournie : gravité 1 (faible) à 4 (très grave) ; probabilité 1 (rare) à 4 (très fréquent) ; niveau de risque = gravité × probabilité.", "small")]
    return f

def simple_register(num, short, title, basis, intro, hdr, wd, n=8, kind="REGISTRE OBLIGATOIRE"):
    f = [NextPageTemplate("L"), PageBreak()]
    f += head(num, short, title, basis, kind)
    f += [register_line(W_L), Spacer(1, 4), rappel(intro[0].lower() + intro[1:]), Spacer(1, 4)]
    s = sum(wd); wd = [W_L * x / s for x in wd]
    f += [grid(hdr, [], wd, nblank=n, rowh=11)]
    return f

def doc12():
    return simple_register("12", "Registre des vérifications", "Registre de sécurité : vérifications et contrôles périodiques",
        "Articles L. 4711-1 à L. 4711-5 et R. 4226-14 à R. 4226-21 du code du travail",
        "Le registre consigne les vérifications et contrôles périodiques des installations et équipements (installations électriques, moyens de lutte contre l'incendie, équipements de travail soumis à vérification). Les rapports établis par les organismes ou personnes chargés des vérifications y sont annexés. Il est tenu à la disposition de l'inspection du travail et des membres du comité social et économique.",
        ["Date", "Installation ou équipement vérifié", "Nature de la vérification", "Organisme ou personne ayant vérifié", "Résultat et observations", "Mesures prises pour lever les observations", "Date de levée", "Visa"],
        [18, 40, 30, 36, 40, 40, 18, 16])

def doc13():
    return simple_register("13", "Danger grave et imminent", "Registre des dangers graves et imminents",
        "Articles L. 4131-2, L. 4132-2 et D. 4132-1 à D. 4132-2 du code du travail",
        "L'avis du représentant du personnel au comité social et économique qui constate qu'il existe une cause de danger grave et imminent (article L. 4131-2) est consigné sur le présent registre. Il est daté et signé et indique les postes de travail concernés, la nature et la cause du danger et le nom des travailleurs exposés. Les pages sont numérotées et authentifiées par le tampon du comité. Le registre est tenu, sous la responsabilité de l'employeur, à la disposition des représentants du personnel au comité.",
        ["Date et heure", "Poste de travail concerné", "Nature et cause du danger", "Nom des travailleurs exposés", "Nom et signature du représentant au CSE", "Mesures prises par l'employeur", "Signature de l'employeur"],
        [20, 34, 44, 38, 34, 50, 22])

def doc14():
    return simple_register("14", "Alertes santé et environnement", "Registre des alertes en matière de santé publique et d'environnement",
        "Articles L. 4133-1 à L. 4133-4 et D. 4133-1 à D. 4133-3 du code du travail",
        "L'alerte donnée par un travailleur ou par un représentant du personnel, lorsque les produits ou procédés de fabrication utilisés ou mis en œuvre par l'établissement font peser un risque grave sur la santé publique ou l'environnement, est consignée par écrit, datée et signée. Les pages sont numérotées et le registre est tenu à la disposition des représentants du personnel.",
        ["Date", "Produits ou procédés de fabrication en cause", "Risque grave pour la santé publique ou l'environnement", "Conséquences potentielles", "Toute autre information utile", "Nom et signature de l'auteur de l'alerte", "Suite donnée par l'employeur"],
        [18, 40, 42, 36, 36, 32, 38])

# ---------- panneau A3 ----------
def _fit(c, txt, font, size, width, mini=7):
    """Réduit la police pour que le texte tienne dans la largeur ; tronque en dernier recours."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    while size > mini and stringWidth(txt, font, size) > width:
        size -= 0.5
    while txt and stringWidth(txt, font, size) > width:
        txt = txt[:-2] + "…"
    c.setFont(font, size); _fit.txt = txt

def panneau(path):
    c = rl_canvas.Canvas(path, pagesize=A3)
    W, H = A3
    m = 15*mm
    c.setFillColor(NAVY); c.rect(0, H - 34*mm, W, 34*mm, stroke=0, fill=1)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 26)
    c.drawString(m, H - 18*mm, "AFFICHAGES OBLIGATOIRES")
    c.setFont("Helvetica", 11)
    raison = "[Raison sociale]" if getattr(Ctx, "gabarit", False) else ("............................................................" if Ctx.blank else _raw(Ctx.data["raison"]))
    c.drawString(m, H - 27*mm, "Établissement : " + raison)
    c.drawRightString(W - m, H - 27*mm, ASOF)
    cols = 2; gap = 8*mm; cw = (W - 2*m - gap) / 2
    blocks = [
        ("Inspection du travail", [("Service", "it_service"), ("Adresse", "it_adresse"), ("Téléphone", "it_tel"), ("Agent de contrôle", "it_agent")], "Art. D. 4711-1 C. trav."),
        ("Santé au travail", [("Organisme", "spst_nom"), ("Adresse", "spst_adresse"), ("Téléphone", "spst_tel"), ("Médecin du travail", "spst_medecin")], "Art. D. 4711-1 C. trav."),
        ("Secours d'urgence", [("SAMU", "=15"), ("Police secours", "=17"), ("Pompiers", "=18"), ("Urgence européen", "=112"), ("Sourds et malentendants", "=114")], "Art. D. 4711-1 C. trav."),
        ("Défenseur des droits", [("Adresse", "=Libre réponse 71120, 75342 Paris Cedex 07"), ("Téléphone", "=09 69 39 00 00"), ("Site", "=www.defenseurdesdroits.fr")], "Art. D. 1151-1 C. trav."),
        ("Horaire collectif", [("Durée hebdomadaire", "hc_duree"), ("Horaires", "hc_resume"), ("Repos hebdomadaire", "repos")], "Art. L. 3171-1 C. trav. · détail : document 02"),
        ("Congés payés", [("Congé principal", "cp_resume"), ("Critères des départs", "cp_criteres")], "Art. D. 3141-5 et D. 3141-6 C. trav. · document 08"),
        ("Convention collective", [("Intitulé", "cc_nom"), ("IDCC", "cc_idcc"), ("Consultation", "cc_lieu")], "Art. R. 2262-3 C. trav. · document 07"),
        ("Document unique", [("Lieu de consultation", "du_lieu"), ("Contact", "du_contact")], "Art. R. 4121-4 C. trav. · document 03"),
        ("Harcèlement", [("Référent CSE", "ref_cse"), ("Référent employeur", "ref_emp")], "Art. L. 1152-4, L. 1153-5 C. trav. · textes : document 06"),
        ("Égalité et discriminations", [("Textes affichés", "=L. 3221-1 à 7 C. trav. · 225-1 à 4 C. pén."), ("Défenseur des droits", "=09 69 39 00 00")], "Art. R. 3221-2, L. 1142-6 C. trav. · document 05"),
    ]
    x0 = [m, m + cw + gap]; y = [H - 42*mm, H - 42*mm]
    for i, (title, fields, ref) in enumerate(blocks):
        col = 0 if y[0] >= y[1] else 1
        bh = 12*mm + len(fields) * 9*mm + 7*mm
        x = x0[col]; top = y[col]
        c.setStrokeColor(RULE); c.setFillColor(colors.white); c.roundRect(x, top - bh, cw, bh, 3*mm, stroke=1, fill=1)
        c.setFillColor(LIGHT); c.roundRect(x, top - 11*mm, cw, 11*mm, 3*mm, stroke=0, fill=1)
        c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 13); c.drawString(x + 5*mm, top - 7.5*mm, title)
        yy = top - 19*mm
        for lab, key in fields:
            c.setFillColor(GREY); c.setFont("Helvetica", 9); c.drawString(x + 5*mm, yy, lab)
            if key.startswith("="):
                c.setFillColor(INK); _fit(c, key[1:], "Helvetica-Bold", 11, cw - 53*mm); c.drawString(x + 48*mm, yy, _fit.txt)
            elif getattr(Ctx, "gabarit", False):
                c.setFillColor(colors.HexColor("#CFE3FF" if key in COND else "#FFE38A")); c.rect(x + 47*mm, yy - 2.2*mm, cw - 52*mm, 6*mm, stroke=0, fill=1)
                c.setFillColor(colors.HexColor("#3A2A00")); c.setFont("Helvetica", 8.5); c.drawString(x + 48.5*mm, yy, "[" + LABELS.get(key, key) + "]")
            elif Ctx.blank:
                c.setStrokeColor(colors.HexColor("#8A94A3")); c.setDash(1, 2); c.line(x + 48*mm, yy - 1, x + cw - 5*mm, yy - 1); c.setDash()
            else:
                c.setFillColor(FILL); _fit(c, _raw(str(Ctx.data.get(key, ""))), "Helvetica-Bold", 10.5, cw - 53*mm); c.drawString(x + 48*mm, yy, _fit.txt)
            yy -= 9*mm
        c.setFillColor(GREY); c.setFont("Helvetica-Oblique", 7.5); c.drawString(x + 5*mm, top - bh + 3.5*mm, ref)
        y[col] = top - bh - 6*mm
    # tabac band
    yb = min(y) - 4*mm
    c.setFillColor(RED); c.roundRect(m, yb - 22*mm, W - 2*m, 22*mm, 3*mm, stroke=0, fill=1)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(W / 2, yb - 11*mm, "INTERDICTION DE FUMER ET DE VAPOTER")
    c.setFont("Helvetica", 9.5)
    c.drawCentredString(W / 2, yb - 18*mm, "Art. R. 3512-2 et L. 3513-6 C. santé publ. · Tabac info service : 39 89 · Signalétique réglementaire : document 04")
    c.setFillColor(GREY); c.setFont("Helvetica", 7.5)
    c.drawString(m, 10*mm, ASOF + "  ·  " + VERSION)
    if not Ctx.blank and not getattr(Ctx, "gabarit", False) and not getattr(Ctx, "client", False):
        c.setFillColor(colors.HexColor("#C0392B")); c.setFont("Helvetica-Bold", 8); c.drawRightString(W - m, 10*mm, "EXEMPLE · DONNÉES FICTIVES")
    c.showPage(); c.save()

# ---------- données fictives ----------
EXEMPLE = {
    "raison": "ATELIER EXEMPLE SARL (fictif)", "adresse": "12 rue de l'Exemple, 77000 Ville-Exemple", "siret": "000 000 000 00000",
    "it_service": "DREETS · Unité de contrôle n° 0 (fictif)", "it_adresse": "1 avenue Fictive, 77000 Ville-Exemple", "it_tel": "01 00 00 00 00", "it_agent": "Mme Exemple",
    "spst_nom": "Service de santé au travail Exemple", "spst_adresse": "3 place Fictive, 77000 Ville-Exemple", "spst_tel": "01 00 00 00 01", "spst_medecin": "Dr Exemple",
    "secours_local": "Centre de secours de Ville-Exemple",
    "hc_service": "Personnel administratif", "hc_duree": "35", "hc_date": "01/11/2026",
    "hc_jours": {"Lundi": ["8 h 30", "17 h 30", "12 h 30 - 13 h 30", "", "8 h"], "Mardi": ["8 h 30", "17 h 30", "12 h 30 - 13 h 30", "", "8 h"],
                 "Mercredi": ["8 h 30", "17 h 30", "12 h 30 - 13 h 30", "", "8 h"], "Jeudi": ["8 h 30", "17 h 30", "12 h 30 - 13 h 30", "", "8 h"],
                 "Vendredi": ["8 h 30", "11 h 30", "", "", "3 h"]},
    "hc_resume": "Lun.-jeu. 8 h 30-17 h 30, ven. 8 h 30-11 h 30", "repos": "Samedi et dimanche",
    "eq1": "Sans objet", "eq1c": "Sans objet",
    "ville": "Ville-Exemple", "date": "15/10/2026", "signataire": "M. Exemple, gérant", "x": "",
    "du_lieu": "Bureau de la direction, armoire « Sécurité »", "du_horaires": "Du lundi au vendredi, 9 h - 12 h", "du_contact": "M. Exemple, gérant",
    "du_num": "Sur demande à l'adresse rh@exemple.invalid", "du_maj": "15/10/2026",
    "ref_cse": "Sans objet (pas de CSE)", "ref_emp": "Sans objet (moins de 250 salariés)", "ref_cse_coord": "sans objet", "ref_emp_coord": "sans objet",
    "am_accord": "Accord d'entreprise du 01/09/2026 (exemple)", "am_semaines": "4", "am_debut": "02/11/2026",
    "am_programme": [["Semaine 1", "Lundi au vendredi, 8 h - 12 h et 13 h - 17 h", "40 h"], ["Semaine 2", "Lundi au vendredi, 8 h - 12 h et 13 h - 16 h", "35 h"],
                     ["Semaine 3", "Lundi au jeudi, 8 h - 12 h et 13 h - 16 h", "28 h"], ["Semaine 4", "Lundi au vendredi, 8 h - 12 h et 13 h - 17 h", "40 h"]],
    "ev_alerte": "Alarme sonore à l'accueil", "ev_sorties": "Porte principale et issue de secours de l'atelier", "ev_responsable": "M. Exemple, gérant",
    "ev_appel": "Mme Exemple-Deux", "ev_rassemblement": "Parking devant l'entrée", "ev_aide": "Accompagnement par un collègue désigné",
    "ri_date": "01/03/2026", "ri_lieu": "Panneau d'affichage de la salle de pause",
    "vi_zones": "Entrée et zone de stockage", "vi_finalite": "Sécurité des biens et des personnes", "vi_responsable": "ATELIER EXEMPLE SARL (fictif)",
    "vi_duree": "30 jours", "vi_contact": "direction@exemple.invalid",
    "cc_nom": "Convention collective nationale (exemple)", "cc_idcc": "0000", "accords": "Aucun accord d'entreprise",
    "cc_lieu": "Bureau de la direction", "cc_modalites": "Sur simple demande, pendant le temps de travail",
    "cp_debut": "01/05/2026", "cp_fin": "30/04/2027", "cp_p_debut": "01/05/2027", "cp_p_fin": "31/10/2027",
    "cp_fermeture": "Du 10 au 23 août 2027", "cp_criteres": "Situation de famille, ancienneté, activité chez un autre employeur", "cp_caisse": "Sans objet",
    "cp_resume": "Du 1er mai au 31 octobre",
    "ps_avis": "01/10/2026", "ps_lieu": "Trousse de secours à l'accueil", "ps_sst": "Mme Exemple-Deux (SST)", "ps_dae": "Sans objet", "ps_contact": "M. Exemple, gérant",
    "activite": "Atelier de fabrication (exemple)", "effectif": "6",
    "commande": "EX-0001",
    "du_contact_tel": "01 00 00 00 02 · direction@exemple.invalid",
    "equipes": [["Équipe A", "Lundi au vendredi", "6 h - 13 h, pause 9 h 30 - 9 h 50", "EXEMPLE Jean, EXEMPLE Paul"],
                ["Équipe B", "Lundi au vendredi", "13 h - 20 h, pause 16 h 30 - 16 h 50", "EXEMPLE Marie, EXEMPLE Léa (intérimaire)"]],
    "repos_blocs": [["Service vente", "Lundi", "0 h - 24 h", "Un autre jour que le dimanche"]],
    "rup": [["1", "EXEMPLE Jean", "Française", "01/01/1990", "M", "Technicien", "Ouvrier qualifié", "01/03/2024", "", "CDI temps plein", "", ""],
            ["2", "EXEMPLE Marie", "Française", "02/02/1995", "F", "Assistante", "Employée", "01/09/2025", "", "CDD temps partiel", "", ""]],
}

def build(outdir, blank):
    Ctx.blank = blank; Ctx.data = {} if blank else EXEMPLE
    suffix = "vierge" if blank else "exemple"
    path = os.path.join(outdir, "Pack_socle_%s.pdf" % suffix)
    doc = make_doc(path)
    story = []
    for i, fn in enumerate([doc01, doc02, doc03, doc04, doc05, doc06, doc07, doc08, doc09]):
        if i: story.append(PageBreak())
        story += fn()
    for fn in [doc10, doc11, doc12, doc13, doc14]:
        story += fn()
    doc.build(story)
    panneau(os.path.join(outdir, "Panneau_recapitulatif_A3_%s.pdf" % suffix))
    return path


# ====================== LOT 2 : documents selon la situation ======================
def doc16():
    f = head("16", "Repos hebdomadaire", "Repos hebdomadaire collectif",
             "Article R. 3172-1 du code du travail", "INFORMATION OBLIGATOIRE")
    f += [establishment_line(), Spacer(1, 8)]
    f += [P("Jours et heures de repos collectif attribués aux salariés ne bénéficiant pas du repos hebdomadaire la journée entière du dimanche :", "body"), Spacer(1, 6)]
    rows = [[v("rh_service"), v("rh_jour"), v("rh_heures"), v("rh_modalite")]] if getattr(Ctx, "gabarit", False) else ([] if Ctx.blank else Ctx.data.get("repos_blocs", []))
    f += [grid(["Salariés ou service concernés", "Jour(s) de repos", "Heures (début - fin)", "Modalité"], rows,
               [52*mm, 38*mm, 36*mm, 48*mm], nblank=max(0, 5 - len(rows)), rowh=8)]
    f += [Spacer(1, 4), rappel("ces jours et heures de repos, ainsi que leurs modalités de communication aux salariés, sont communiqués au préalable à l'agent de contrôle de l'inspection du travail (article R. 3172-1).")]
    f += [Spacer(1, 6), signature_block()]
    return f

def doc16b():
    return simple_register("16b", "Repos hebdomadaire individuel", "Registre du repos hebdomadaire non collectif",
        "Article R. 3172-2 du code du travail",
        "Lorsque le repos hebdomadaire n'est pas donné collectivement à tous les salariés, le présent registre indique les noms des salariés soumis à un régime de repos particulier, ce régime, et pour chaque salarié le jour et, le cas échéant, les fractions de journée choisis pour le repos. Il est tenu constamment à jour et à la disposition de l'agent de contrôle de l'inspection du travail.",
        ["Nom et prénom du salarié", "Régime de repos hebdomadaire", "Jour de repos", "Fraction(s) de journée", "Date de mise à jour", "Observations"],
        [50, 50, 28, 34, 24, 50])

def doc17():
    f = [NextPageTemplate("L"), PageBreak()]
    f += head("17", "Décompte de la durée du travail", "Décompte individuel de la durée du travail",
              "Article D. 3171-8 du code du travail", "DOCUMENT OBLIGATOIRE")
    f += [register_line(W_L), Spacer(1, 4),
          field_table([("Salarié", v("dt_salarie", 40)), ("Semaine du", v("dt_semaine", 20))], total=W_L),
          Spacer(1, 4), rappel("pour les salariés ne travaillant pas selon l'horaire collectif affiché, la durée du travail est décomptée chaque jour par l'enregistrement des heures de début et de fin de chaque période de travail, ou par le relevé du nombre d'heures accomplies, et récapitulée chaque semaine."), Spacer(1, 4)]
    hdr = ["Jour", "Début (matin)", "Fin (matin)", "Début (après-midi)", "Fin (après-midi)", "Heures accomplies", "Observations"]
    days = [["Lundi"] + [""] * 6, ["Mardi"] + [""] * 6, ["Mercredi"] + [""] * 6, ["Jeudi"] + [""] * 6,
            ["Vendredi"] + [""] * 6, ["Samedi"] + [""] * 6, ["Dimanche"] + [""] * 6, ["<b>Total de la semaine</b>"] + [""] * 6]
    wd = [30, 25, 25, 25, 25, 25, 60]; s_ = sum(wd); wd = [W_L * x / s_ for x in wd]
    t = grid(hdr, days, wd); t.setStyle(TableStyle([("TOPPADDING", (0, 1), (-1, -1), 7), ("BOTTOMPADDING", (0, 1), (-1, -1), 7)]))
    f += [t, Spacer(1, 8), field_table([("Visa du salarié", ""), ("Visa de l'employeur", "")], total=W_L)]
    return f

def doc18():
    f = [NextPageTemplate("P"), PageBreak()]
    f += head("18", "Consigne de sécurité incendie", "Consigne de sécurité incendie",
              "Articles R. 4227-34 et R. 4227-37 à R. 4227-40 du code du travail")
    f += [establishment_line(), Spacer(1, 4), field_table([("Local ou zone concerné", v("ci_local", 50))])]
    f += [Spacer(1, 6), boxed([P('<font size="11"><b>EN CAS D\'INCENDIE : SAPEURS-POMPIERS 18 · URGENCE 112</b></font>', "center"),
                               P("Service de secours de premier appel : " + v("ci_secours", 50), "center")], bg=colors.HexColor("#FBE9E7"))]
    rows = [("1° Matériel d'extinction et de secours dans le local ou à ses abords", v("ci_materiel", 60)),
            ("2° Personnes chargées de mettre ce matériel en action", v("ci_equipiers", 60)),
            ("3° Personnes chargées de diriger l'évacuation des travailleurs et du public", v("ci_evac", 60)),
            ("4° Mesures liées à la présence de personnes handicapées (espaces d'attente sécurisés)", v("ci_handicap", 60)),
            ("5° Moyens d'alerte", v("ci_alerte", 50)),
            ("6° Personnes chargées d'aviser les sapeurs-pompiers", v("ci_appel", 50)),
            ("7° Adresse et numéro d'appel du service de secours de premier appel", v("ci_secours", 50)),
            ("Point de rassemblement", v("ci_rassemblement", 40))]
    f += [Spacer(1, 6), field_table(rows, colw=(78*mm, None))]
    f += [Spacer(1, 6), boxed([P("<b>8° Toute personne apercevant un début d'incendie doit donner l'alarme et mettre en œuvre les moyens de premier secours, sans attendre l'arrivée des travailleurs spécialement désignés.</b>", "body")])]
    f += [Spacer(1, 4), rappel("la consigne de sécurité incendie est communiquée à l'inspection du travail (article R. 4227-40).")]
    return f

def doc18b():
    f = [NextPageTemplate("P"), PageBreak()]
    f += head("18b", "Instructions d'évacuation", "Instructions d'évacuation",
              "Articles R. 4227-37 et R. 4141-3-1 du code du travail", "INFORMATION OBLIGATOIRE")
    f += [establishment_line(), Spacer(1, 4)]
    f += [Spacer(1, 2), boxed([P('<font size="11"><b>EN CAS D\'INCENDIE OU D\'ALERTE : SAPEURS-POMPIERS 18 · URGENCE 112</b></font>', "center")], bg=colors.HexColor("#FBE9E7"))]
    f += [Spacer(1, 6), field_table([("Signal ou moyen d'alerte", v("ev_alerte", 50)),
                                     ("Sorties et cheminement à emprunter", v("ev_sorties", 60)),
                                     ("Personne qui dirige l'évacuation", v("ev_responsable", 50)),
                                     ("Personne qui appelle les secours", v("ev_appel", 50)),
                                     ("Point de rassemblement", v("ev_rassemblement", 50)),
                                     ("Aide aux personnes à mobilité réduite", v("ev_aide", 60))], colw=(70*mm, None))]
    f += [P("Conduite à tenir", "h2"),
          grid(["Étape", "Action"], [["1. Alerter", "Donner l'alarme et prévenir la personne qui dirige l'évacuation."],
                                     ["2. Évacuer", "Quitter les lieux calmement par les sorties indiquées, sans revenir en arrière ni utiliser d'ascenseur ; fermer les portes derrière soi."],
                                     ["3. Se rassembler", "Rejoindre le point de rassemblement et y rester jusqu'à l'autorisation de réintégrer les locaux."],
                                     ["4. Signaler", "Signaler toute personne absente ou restée à l'intérieur."]], [32*mm, 142*mm])]
    f += [Spacer(1, 4), rappel("des instructions permettant d'assurer l'évacuation des personnes présentes sont établies dans les établissements qui ne sont pas soumis à la consigne de sécurité incendie (article R. 4227-37). Les travailleurs reçoivent une information sur ces instructions (article R. 4141-3-1).")]
    return f

def doc19():
    return simple_register("19", "Exercices incendie", "Registre des essais, visites et exercices incendie",
        "Article R. 4227-39 du code du travail",
        "Les exercices au cours desquels les travailleurs apprennent à reconnaître le signal sonore d'alarme générale, à localiser et utiliser les espaces d'attente sécurisés, à se servir des moyens de premier secours et à exécuter les manœuvres nécessaires, ainsi que les essais et visites périodiques du matériel, ont lieu au moins tous les six mois. Le registre est tenu à la disposition de l'inspection du travail.",
        ["Date", "Nature (exercice, essai, visite)", "Matériel ou zone concernés", "Participants", "Durée de l'évacuation", "Observations", "Mesures correctives", "Visa"],
        [18, 30, 34, 34, 20, 44, 40, 16])

def doc20():
    f = [NextPageTemplate("P"), PageBreak()]
    f += head("20", "Notice de poste", "Notice de poste : agents chimiques dangereux",
              "Article R. 4412-39 du code du travail", "DOCUMENT OBLIGATOIRE")
    f += [establishment_line(), Spacer(1, 4)]
    f += [field_table([("Poste ou situation de travail", v("np_poste", 50)), ("Agents chimiques dangereux utilisés", v("np_agents", 60)),
                       ("Risques auxquels le travail expose", v("np_risques", 60)), ("Dispositions prises pour les éviter", v("np_dispositions", 60)),
                       ("Règles d'hygiène applicables", v("np_hygiene", 60)), ("Équipements de protection collective", v("np_epc", 50)),
                       ("Équipements de protection individuelle", v("np_epi", 50)), ("Conduite à tenir en cas d'accident", v("np_accident", 60)),
                       ("Date d'actualisation", v("np_date", 20))], colw=(70*mm, None))]
    f += [Spacer(1, 6), rappel("la notice de poste est actualisée en tant que de besoin ; les fiches de données de sécurité des produits sont tenues à la disposition des travailleurs.")]
    return f

def doc21():
    f = head("21", "Membres du CSE", "Liste nominative des membres du comité social et économique",
             "Article R. 2314-22 du code du travail")
    f += [establishment_line(), Spacer(1, 6)]
    if getattr(Ctx, "gabarit", False):
        rows = [[v("cse_nom"), v("cse_qualite"), v("cse_emplacement"), v("cse_commission")]]
    elif Ctx.blank:
        rows = []
    else:
        rows = [list(r) for r in Ctx.data.get("cse_membres", [])]
    f += [grid(["Nom et prénom", "Qualité (titulaire, suppléant)", "Emplacement de travail habituel", "Commission(s)"], rows,
               [50*mm, 36*mm, 52*mm, 36*mm], nblank=max(0, 8 - len(rows)), rowh=8)]
    f += [Spacer(1, 6), field_table([("Référent harcèlement sexuel et agissements sexistes", v("ref_cse", 50)),
                                     ("Date des dernières élections", v("cse_date", 20)), ("Fin des mandats", v("cse_fin", 20))])]
    return f

def doc22():
    f = [PageBreak()]
    f += head("22", "Élections du CSE", "Élections des membres du comité social et économique",
              "Articles L. 2314-4 et L. 2314-9 du code du travail", "INFORMATION OBLIGATOIRE")
    f += [establishment_line(), Spacer(1, 8)]
    f += [P("Organisation des élections", "h2"),
          P("Le personnel est informé de l'organisation des élections des membres de la délégation du personnel au comité social et économique.", "body"), Spacer(1, 6),
          field_table([("Date de diffusion de la présente information", v("el_diffusion", 20)),
                       ("Date envisagée pour le premier tour", v("el_tour1", 20)),
                       ("Lieu et modalités du scrutin", v("el_lieu", 50))]),
          Spacer(1, 4), rappel("le premier tour se tient au plus tard le quatre-vingt-dixième jour suivant la diffusion de la présente information.")]
    if not (getattr(Ctx, "client", False) and str(Ctx.data.get("s_cse", "")).lower() == "oui"):
        f += [P("Procès-verbal de carence", "h2"),
              P("En l'absence de candidat aux élections, le procès-verbal de carence est porté à la connaissance du personnel.", "body"), Spacer(1, 4),
              field_table([("Date du procès-verbal de carence", v("el_carence", 20)),
                           ("Date de transmission à l'inspection du travail et au prestataire du ministère", v("el_transmission", 20))]),
              Spacer(1, 4), rappel("le procès-verbal de carence est porté à la connaissance des salariés par tout moyen permettant de lui conférer date certaine. Il est transmis dans les quinze jours, sur le formulaire homologué, à l'agent de contrôle de l'inspection du travail et au prestataire agissant pour le compte du ministre chargé du travail (articles L. 2314-9 et R. 2314-22).")]
    f += [Spacer(1, 6), signature_block()]
    return f

def doc23():
    return simple_register("23", "Demandes des membres du CSE", "Registre spécial des demandes des membres du CSE et des réponses de l'employeur",
        "Article L. 2315-22 du code du travail (entreprises de moins de cinquante salariés)",
        "Les membres de la délégation du personnel remettent à l'employeur une note écrite exposant l'objet de leurs demandes deux jours ouvrables avant la réunion. L'employeur, président du comité, y répond par écrit au plus tard dans les six jours ouvrables suivant la réunion. Les demandes et les réponses motivées sont transcrites sur le présent registre ou y sont annexées. Le registre est tenu à la disposition des salariés un jour ouvrable par quinzaine, en dehors de leur temps de travail, ainsi qu'à celle de l'agent de contrôle de l'inspection du travail et des membres du comité.",
        ["Date de la réunion", "Date de remise de la note", "Objet des demandes", "Membre(s) concerné(s)", "Réponse motivée de l'employeur", "Date de la réponse"],
        [20, 20, 62, 30, 74, 20])

def doc24():
    f = [NextPageTemplate("P"), PageBreak()]
    f += head("24", "Index égalité", "Index de l'égalité professionnelle entre les femmes et les hommes",
              "Articles L. 1142-8 et D. 1142-4 du code du travail (entreprises d'au moins cinquante salariés, sans site internet)", "INFORMATION OBLIGATOIRE")
    f += [establishment_line(), Spacer(1, 6)]
    f += [field_table([("Année de calcul", v("ix_annee", 10)), ("Note globale (sur 100)", v("ix_note", 10)),
                       ("Résultats par indicateur", v("ix_indicateurs", 60)),
                       ("Mesures de correction et objectifs de progression", v("ix_mesures", 60))])]
    f += [Spacer(1, 4), rappel("les résultats sont publiés sur le site internet de l'entreprise lorsqu'il en existe un ; à défaut, ils sont portés à la connaissance des salariés par tout moyen (article D. 1142-4).")]
    return f

def doc25():
    f = head("25", "Lanceurs d'alerte", "Procédure de recueil et de traitement des signalements",
             "Loi n° 2016-1691 du 9 décembre 2016, article 8 · Décret n° 2022-1284 du 3 octobre 2022, articles 5 et 8 (entreprises d'au moins cinquante salariés)", "INFORMATION OBLIGATOIRE")
    f += [establishment_line(), Spacer(1, 6)]
    f += [field_table([("Personne ou service chargé de recueillir les signalements", v("la_referent", 50)),
                       ("Canal de signalement (adresse, courriel, plateforme)", v("la_canal", 60)),
                       ("Accès à la procédure complète", v("la_procedure", 50))])]
    f += [Spacer(1, 6), boxed([P("<b>Signalement externe</b> : tout lanceur d'alerte peut également adresser un signalement externe à l'autorité compétente désignée par le décret n° 2022-1284, au Défenseur des droits, à l'autorité judiciaire ou à une institution, un organe ou un organisme de l'Union européenne compétent. Le Défenseur des droits oriente les lanceurs d'alerte : 09 69 39 00 00 · www.defenseurdesdroits.fr", "body")])]
    return f

def doc26():
    f = head("26", "Participation", "Information sur l'accord de participation",
             "Article D. 3323-12 du code du travail (entreprises d'au moins cinquante salariés)", "INFORMATION OBLIGATOIRE")
    f += [establishment_line(), Spacer(1, 6)]
    f += [field_table([("Intitulé et date de l'accord", v("pa_accord", 50)), ("Organisme gestionnaire", v("pa_gestion", 40)),
                       ("Modalités de calcul et de répartition", v("pa_calcul", 60)), ("Lieu où l'accord peut être consulté", v("pa_lieu", 50))])]
    f += [Spacer(1, 4), rappel("cette information est affichée à défaut d'un autre moyen d'information prévu par l'accord (article D. 3323-12).")]
    return f

def doc27():
    return simple_register("27", "Accidents bénins", "Registre des accidents du travail bénins",
        "Articles L. 441-4 et D. 441-1 à D. 441-4 du code de la sécurité sociale",
        "Sont inscrits, dans les quarante-huit heures non compris les dimanches et jours fériés, les accidents du travail n'entraînant ni arrêt de travail ni soins médicaux pris en charge par la sécurité sociale. La victime signe le registre en face des indications portées par l'employeur ; le médecin du travail peut le consulter. L'employeur informe sans délai la CARSAT de la tenue du registre et le conserve cinq ans à compter de la fin de l'exercice considéré. La tenue du registre suppose la présence permanente d'un médecin, d'un pharmacien, d'un infirmier diplômé d'État ou d'une personne titulaire du diplôme de sauveteur secouriste du travail, l'existence d'un poste de secours d'urgence et le respect des obligations relatives au comité social et économique (article D. 441-1).",
        ["Nom de la victime", "Date et heure", "Lieu", "Circonstances", "Nature et siège des lésions", "Soins donnés · visa du donneur de soins", "Témoins", "Signature de la victime"],
        [30, 20, 24, 44, 32, 36, 24, 22])

def doc28():
    f = [NextPageTemplate("P"), PageBreak()]
    f += head("28", "Règlement intérieur", "Avis relatif au règlement intérieur",
              "Articles L. 1311-2, L. 1321-1 et R. 1321-1 du code du travail (entreprises d'au moins cinquante salariés)", "INFORMATION OBLIGATOIRE")
    f += [establishment_line(), Spacer(1, 6),
          field_table([("Date d'entrée en vigueur du règlement intérieur", v("ri_date", 20)),
                       ("Lieu où le règlement intérieur peut être consulté", v("ri_lieu", 60))])]
    f += [Spacer(1, 6), P("Le règlement intérieur fixe les mesures d'application de la réglementation en matière de santé et de sécurité dans l'établissement, les règles générales et permanentes relatives à la discipline, la nature et l'échelle des sanctions, ainsi que les dispositions relatives aux droits de la défense des salariés et aux harcèlements moral et sexuel et aux agissements sexistes.", "body")]
    f += [Spacer(1, 4), rappel("le règlement intérieur est porté, par tout moyen, à la connaissance des personnes ayant accès aux lieux de travail ou aux locaux où se fait l'embauche (article R. 1321-1). L'avis d'accès au document unique est affiché au même emplacement (article R. 4121-4).")]
    return f

def doc29():
    f = [NextPageTemplate("P"), PageBreak()]
    f += head("29", "Vidéosurveillance", "Information sur le dispositif de vidéosurveillance",
              "Article L. 1222-4 du code du travail · article 13 du règlement (UE) 2016/679", "INFORMATION OBLIGATOIRE")
    f += [establishment_line(), Spacer(1, 6),
          boxed([P('<font size="14"><b>ÉTABLISSEMENT PLACÉ SOUS VIDÉOSURVEILLANCE</b></font>', "center")], bg=colors.white)]
    f += [Spacer(1, 6), field_table([("Zones filmées", v("vi_zones", 60)), ("Finalité du dispositif", v("vi_finalite", 60)),
                                     ("Responsable du dispositif", v("vi_responsable", 50)),
                                     ("Durée de conservation des images", v("vi_duree", 20)),
                                     ("Contact pour exercer ses droits (accès, effacement, limitation, opposition)", v("vi_contact", 50))], colw=(78*mm, None))]
    f += [Spacer(1, 6), P("Toute personne filmée dispose d'un droit d'accès aux images la concernant. Elle peut introduire une réclamation auprès de la Commission nationale de l'informatique et des libertés (CNIL) · www.cnil.fr.", "body")]
    f += [Spacer(1, 4), rappel("aucune information concernant personnellement un salarié ne peut être collectée par un dispositif qui n'a pas été porté préalablement à sa connaissance (article L. 1222-4).")]
    return f

# ====================== libellés des champs ======================
LABELS = {
 "eq_nom": "Équipe", "eq_jours": "Jours", "eq_horaires": "Horaires", "eq_compo": "Noms des salariés de l'équipe", "du_contact_tel": "Téléphone ou courriel",
 "raison": "Raison sociale", "adresse": "Adresse de l'établissement", "siret": "SIRET",
 "it_service": "Unité de contrôle de l'inspection", "it_adresse": "Adresse de l'inspection", "it_tel": "Téléphone inspection", "it_agent": "Nom de l'inspecteur",
 "spst_nom": "Médecin / service de santé au travail", "spst_adresse": "Adresse service santé", "spst_tel": "Téléphone service santé", "spst_medecin": "Nom du médecin du travail",
 "secours_local": "Centre de secours local", "hc_service": "Service concerné", "hc_duree": "Durée hebdo", "hc_date": "Date d'effet",
 "h_debut": "début", "h_fin": "fin", "h_repos": "pause", "h_reprise": "reprise-fin", "h_duree": "durée",
 "hc_resume": "Résumé des horaires", "repos": "Jour(s) de repos", "eq1": "Équipe", "eq1c": "Composition de l'équipe",
 "ville": "Ville", "date": "Date", "signataire": "Signataire", "x": "",
 "du_lieu": "Lieu de consultation du DUERP", "du_horaires": "Horaires de consultation", "du_contact": "Personne à contacter", "du_num": "Accès numérique", "du_maj": "Date de mise à jour",
 "ref_cse": "Référent harcèlement CSE", "ref_emp": "Référent employeur (≥ 250)", "ref_cse_coord": "Adresse et téléphone du référent CSE", "ref_emp_coord": "Adresse et téléphone du référent employeur",
 "am_accord": "Accord applicable", "am_semaines": "Nombre de semaines", "am_debut": "Début de la période", "am_sem": "Semaine", "am_horaire": "Horaire de la semaine", "am_duree": "Durée",
 "ev_alerte": "Moyen d'alerte", "ev_sorties": "Sorties à emprunter", "ev_responsable": "Personne qui dirige l'évacuation", "ev_appel": "Personne qui appelle les secours",
 "ev_rassemblement": "Point de rassemblement", "ev_aide": "Aide aux personnes à mobilité réduite",
 "ri_date": "Date d'entrée en vigueur", "ri_lieu": "Lieu de consultation du règlement",
 "vi_zones": "Zones filmées", "vi_finalite": "Finalité", "vi_responsable": "Responsable du dispositif", "vi_duree": "Durée de conservation", "vi_contact": "Contact pour exercer ses droits",
 "cc_nom": "Convention collective", "cc_idcc": "IDCC", "accords": "Accords d'entreprise", "cc_lieu": "Lieu de consultation", "cc_modalites": "Modalités de consultation",
 "cp_debut": "Début période", "cp_fin": "Fin période", "cp_p_debut": "Début congé principal", "cp_p_fin": "Fin congé principal",
 "cp_fermeture": "Fermeture annuelle", "cp_criteres": "Critères ordre des départs", "cp_caisse": "Caisse de congés payés", "cp_resume": "Période de prise",
 "ps_avis": "Date de l'avis du médecin du travail", "ps_lieu": "Emplacement trousse de secours", "ps_sst": "Sauveteur secouriste", "ps_dae": "Emplacement défibrillateur", "ps_contact": "Personne à prévenir",
 "activite": "Activité", "effectif": "Effectif",
 "rh_service": "Salariés concernés", "rh_jour": "Jour de repos", "rh_heures": "Heures de repos", "rh_modalite": "Modalité retenue",
 "dt_salarie": "Nom du salarié", "dt_semaine": "Semaine",
 "ci_local": "Local", "ci_secours": "Centre de secours de premier appel", "ci_materiel": "Extincteurs, RIA, alarme", "ci_equipiers": "Équipiers d'intervention",
 "ci_evac": "Guides et serre-files", "ci_handicap": "Espaces d'attente sécurisés", "ci_alerte": "Moyen d'alerte", "ci_appel": "Personne qui appelle le 18", "ci_rassemblement": "Point de rassemblement",
 "np_poste": "Poste", "np_agents": "Produits utilisés", "np_risques": "Risques", "np_dispositions": "Mesures prises", "np_hygiene": "Règles d'hygiène",
 "np_epc": "Protections collectives", "np_epi": "Protections individuelles", "np_accident": "Conduite en cas d'accident", "np_date": "Date",
 "cse_nom": "Nom du membre", "cse_qualite": "Titulaire / suppléant", "cse_emplacement": "Emplacement de travail", "cse_commission": "Commission",
 "cse_date": "Date des élections", "cse_fin": "Fin des mandats",
 "el_diffusion": "Date de diffusion", "el_tour1": "Date du 1er tour", "el_lieu": "Lieu du scrutin", "el_carence": "Date du PV de carence", "el_transmission": "Date d'envoi à l'inspection",
 "ix_annee": "Année", "ix_note": "Note /100", "ix_indicateurs": "Résultats par indicateur", "ix_site": "Adresse web de publication", "ix_mesures": "Mesures de correction",
 "la_referent": "Référent signalements", "la_canal": "Canal de signalement", "la_procedure": "Lien vers la procédure",
 "pa_accord": "Accord de participation", "pa_gestion": "Organisme gestionnaire", "pa_calcul": "Modalités de calcul", "pa_lieu": "Lieu de consultation",
}
COND = {"ref_cse_coord", "ref_emp_coord", "eq_nom", "eq_jours", "eq_horaires", "eq_compo", "secours_local", "eq1", "eq1c", "ref_cse", "ref_emp", "cp_fermeture", "cp_caisse", "ps_dae", "du_num", "accords", "repos"}

DOCS = [("01_Socle", "01_Coordonnees_obligatoires", doc01, "P"), ("01_Socle", "02_Horaire_collectif", doc02, "P"),
        ("01_Socle", "03_Acces_document_unique", doc03, "P"), ("01_Socle", "04_Interdiction_fumer_vapoter", doc04, "N"),
        ("01_Socle", "05_Egalite_et_discriminations", doc05, "P"), ("01_Socle", "06_Harcelement", doc06, "P"),
        ("01_Socle", "07_Conventions_et_accords", doc07, "P"), ("01_Socle", "08_Conges_payes", doc08, "P"),
        ("01_Socle", "09_Premiers_secours", doc09, "P"), ("01_Socle", "10_Registre_unique_du_personnel", doc10, "L"),
        ("01_Socle", "11_Trame_document_unique_DUERP", doc11, "L"), ("01_Socle", "12_Registre_de_securite", doc12, "L"),
        ("01_Socle", "14_Registre_alertes_sante_environnement", doc14, "L"),
        ("02_Selon_situation", "02b_Amenagement_temps_de_travail", doc02b, "P"),
        ("02_Selon_situation", "04b_Emplacement_fumeur", doc04b, "N"), ("02_Selon_situation", "13_Registre_danger_grave_imminent", doc13, "L"),
        ("02_Selon_situation", "16_Repos_hebdomadaire", doc16, "P"), ("02_Selon_situation", "16b_Registre_repos_hebdomadaire", doc16b, "L"),
        ("02_Selon_situation", "17_Decompte_duree_du_travail", doc17, "L"),
        ("02_Selon_situation", "18_Consigne_securite_incendie", doc18, "P"), ("02_Selon_situation", "18b_Instructions_evacuation", doc18b, "P"),
        ("02_Selon_situation", "19_Registre_exercices_incendie", doc19, "L"),
        ("02_Selon_situation", "20_Notice_de_poste_chimique", doc20, "P"), ("02_Selon_situation", "21_Liste_membres_CSE", doc21, "P"),
        ("02_Selon_situation", "22_Elections_CSE_et_carence", doc22, "P"), ("02_Selon_situation", "23_Registre_questions_CSE", doc23, "L"),
        ("02_Selon_situation", "24_Index_egalite", doc24, "P"), ("02_Selon_situation", "25_Lanceurs_alerte", doc25, "P"),
        ("02_Selon_situation", "26_Accord_participation", doc26, "P"), ("02_Selon_situation", "27_Registre_accidents_benins", doc27, "L"),
        ("02_Selon_situation", "28_Reglement_interieur", doc28, "P"), ("02_Selon_situation", "29_Videosurveillance", doc29, "P")]

def strip_lead(story):
    while story and (isinstance(story[0], (NextPageTemplate, PageBreak))):
        story = story[1:]
    return story

def make_doc_first(path, first):
    doc = make_doc(path)
    if first == "L":
        doc.pageTemplates = [doc.pageTemplates[1], doc.pageTemplates[0], doc.pageTemplates[2]]
    elif first == "N":
        doc.pageTemplates = [doc.pageTemplates[2], doc.pageTemplates[0], doc.pageTemplates[1]]
    return doc

def set_mode(mode, data=None):
    Ctx.gabarit = (mode == "gabarit"); Ctx.client = (mode == "client")
    Ctx.blank = mode not in ("exemple", "client")
    Ctx.data = EXEMPLE if mode == "exemple" else (data or {})

def legend():
    return [Meta("00", "Mode d'emploi", "GABARIT DU PACK"), P("Gabarit : zones à remplir par le client", "title"),
            P("Chaque zone colorée est remplie automatiquement à partir du questionnaire. Le reste du document est fixe.", "basis"),
            grid(["Couleur", "Signification"],
                 [['<span backColor="#FFE38A">&nbsp;[Champ]&nbsp;</span>', "Renseignement obligatoire, saisi une fois dans le questionnaire"],
                  ['<span backColor="#CFE3FF">&nbsp;[Champ]&nbsp;</span>', "Renseignement demandé seulement si la situation l'impose (CSE, caisse de congés, fermeture, défibrillateur…)"],
                  ["Tableaux vierges", "Registres complétés à la main par l'employeur au fil de l'eau (embauches, exercices, alertes…)"],
                  ["Texte noir", "Contenu fixe : textes légaux et mentions obligatoires, en vigueur à la date indiquée en pied de page"]],
                 [40*mm, 134*mm])]

def build_all(outdir):
    import zipfile, shutil
    root = os.path.join(outdir, "Pack_affichages_obligatoires_2026-10")
    if os.path.exists(root): shutil.rmtree(root)
    for mode, sub in [("vierge", "Version_vierge_a_remplir"), ("exemple", "Version_exemple_entreprise_fictive"), ("gabarit", "Gabarit_champs_en_couleur")]:
        set_mode(mode)
        for folder, name, fn, first in DOCS:
            d = os.path.join(root, sub, folder); os.makedirs(d, exist_ok=True)
            doc = make_doc_first(os.path.join(d, name + ".pdf"), first)
            doc.build(strip_lead(fn()))
        panneau(os.path.join(root, sub, "00_Panneau_recapitulatif_A3.pdf"))
        # document unique regroupant tout
        doc = make_doc(os.path.join(root, sub, "Pack_complet_%s.pdf" % mode))
        story = legend() if mode == "gabarit" else []
        for i, (folder, name, fn, first) in enumerate(DOCS):
            part = fn()
            if story or i:
                if not (part and isinstance(part[0], (NextPageTemplate, PageBreak))):
                    story += [NextPageTemplate("P"), PageBreak()]
            elif first == "L":
                part = strip_lead(part)
            story += part
        doc.build(story)
    for extra in ["Textes_obligatoires_et_presentation.md", "Sources_Legifrance_12-10-2026.md", "Champs_questionnaire.csv"]:
        src = os.path.join(outdir, extra)
        if os.path.exists(src): shutil.copy(src, root)
    z = os.path.join(outdir, "Pack_affichages_obligatoires_2026-10.zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for dp, _, fs in os.walk(root):
            for fn_ in fs:
                full = os.path.join(dp, fn_); zf.write(full, os.path.relpath(full, outdir))
    return z

if __name__ == "__main__":
    print(build_all(sys.argv[1]))


# ====================== MODE CLIENT : pack personnalisé ======================
# Seuils d'effectif repris des textes : CSE dès 11 salariés pendant 12 mois consécutifs (L. 2311-2),
# registre spécial des demandes CSE sous 50 (L. 2315-22), index égalité sans site internet (D. 1142-4),
# lanceurs d'alerte et participation dès 50, règlement intérieur 12 mois après le seuil de 50 (L. 1311-2),
# référent harcèlement employeur dès 250 (L. 1153-5-1). Registre DGI seulement avec CSE (D. 4132-1).
# Consigne incendie (R. 4227-34) ou, à défaut, instructions d'évacuation (R. 4227-37).
SOCLE = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "14"]

def _num(name):
    return name.split("_")[0]

def _int(x):
    try:
        return int(str(x).strip())
    except Exception:
        return 0

def selection(d):
    """Liste des numéros de documents dus selon la situation déclarée."""
    eff = _int(d.get("effectif"))
    oui = lambda k: str(d.get(k, "")).lower() in ("oui", "true", "1")
    non = lambda k: str(d.get(k, "")).lower() in ("non", "false", "0")
    sel = list(SOCLE)
    if oui("s_amenagement"): sel.append("02b")
    if oui("s_fumoir"): sel.append("04b")
    if oui("s_cse"): sel.append("13")
    hors_dimanche = non("s_repos_dimanche") if "s_repos_dimanche" in d else oui("s_repos_hors_dimanche")
    if hors_dimanche: sel.append("16")
    if oui("s_repos_individuel"): sel.append("16b")
    if oui("s_horaires_individuels"): sel.append("17")
    if oui("s_incendie"): sel += ["18", "19"]
    else: sel.append("18b")
    if oui("s_chimique"): sel.append("20")
    if oui("s_cse"): sel.append("21")
    seuil11 = eff >= 11 and (oui("s_11_12mois") if "s_11_12mois" in d else True)
    if seuil11: sel.append("22")
    if oui("s_cse") and eff < 50: sel.append("23")
    if eff >= 50 and not oui("s_site"): sel.append("24")
    if eff >= 50: sel.append("25")
    if eff >= 50 or oui("s_participation"): sel.append("26")
    if oui("s_accidents_benins") and oui("s_ab_soignant") and oui("s_ab_poste") and (eff < 11 or oui("s_cse")): sel.append("27")
    if eff >= 50 and oui("s_50_12mois"): sel.append("28")
    if oui("s_video"): sel.append("29")
    return sel

def liste_documents(d):
    sel = set(selection(d))
    return [(folder, name) for folder, name, fn, first in DOCS if _num(name) in sel]

def _esc(o):
    if isinstance(o, str):
        return _html.escape(o, quote=False)
    if isinstance(o, list):
        return [_esc(x) for x in o]
    if isinstance(o, dict):
        return {k: _esc(x) for k, x in o.items()}
    return o

def _defaults(d):
    """Mentions par défaut des champs conditionnels non concernés."""
    eff = _int(d.get("effectif"))
    oui = lambda k: str(d.get(k, "")).lower() in ("oui", "true", "1")
    so = "Sans objet"
    if not oui("s_cse"): d["ref_cse"] = "Sans objet (pas de CSE)"
    if not oui("s_cse"): d["ref_cse_coord"] = "sans objet"
    if eff < 250: d["ref_emp"] = "Sans objet (moins de 250 salariés)"; d["ref_emp_coord"] = "sans objet"
    for k in ["secours_local", "du_num", "accords", "cp_fermeture", "cp_caisse", "ps_dae", "ps_sst", "eq1", "eq1c"]:
        if not str(d.get(k, "")).strip(): d[k] = so
    if not d.get("repos"): d["repos"] = "Dimanche"
    if not str(d.get("ps_avis", "")).strip(): d["ps_avis"] = "...................."
    d.setdefault("hc_jours", {}); d.setdefault("equipes", []); d.setdefault("repos_blocs", [])
    d.setdefault("cse_membres", []); d.setdefault("am_programme", []); d["rup"] = []   # aucune donnée salarié : registre remis vierge
    return d

def build_client(data, outdir, nom_pack="Pack_affichages_obligatoires"):
    """Construit le pack du client et renvoie le chemin du zip."""
    import zipfile, shutil, json
    if isinstance(data, str):
        data = json.loads(data)
    d = _esc(_defaults(dict(data)))
    sel = set(selection(data))
    set_mode("client", d)
    root = os.path.join(outdir, nom_pack)
    if os.path.exists(root): shutil.rmtree(root)
    chosen = [x for x in DOCS if _num(x[1]) in sel]
    for folder, name, fn, first in chosen:
        dd = os.path.join(root, folder); os.makedirs(dd, exist_ok=True)
        doc = make_doc_first(os.path.join(dd, name + ".pdf"), first)
        doc.build(strip_lead(fn()))
    panneau(os.path.join(root, "00_Panneau_recapitulatif_A3.pdf"))
    doc = make_doc(os.path.join(root, "Pack_complet.pdf"))
    story = []
    for i, (folder, name, fn, first) in enumerate(chosen):
        part = fn()
        if i:
            if not (part and isinstance(part[0], (NextPageTemplate, PageBreak))):
                story += [NextPageTemplate("P"), PageBreak()]
        elif first == "L":
            part = strip_lead(part)
        elif first == "N":
            part = strip_lead(part); doc.pageTemplates = [doc.pageTemplates[2], doc.pageTemplates[0], doc.pageTemplates[1]]
        story += part
    doc.build(story)
    z = os.path.join(outdir, nom_pack + ".zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for dp, _, fs in os.walk(root):
            for fn_ in sorted(fs):
                full = os.path.join(dp, fn_); zf.write(full, os.path.relpath(full, outdir))
    return z

def build_registres(data, outdir, numeros):
    """Feuillets supplémentaires de registres (espace client)."""
    import json
    if isinstance(data, str):
        data = json.loads(data)
    d = _esc(_defaults(dict(data)))
    set_mode("client", d)
    chosen = [x for x in DOCS if _num(x[1]) in set(numeros)]
    path = os.path.join(outdir, "Feuillets_registres.pdf")
    doc = make_doc(path)
    doc.pageTemplates = [doc.pageTemplates[1], doc.pageTemplates[0], doc.pageTemplates[2]]
    story = []
    for i, (folder, name, fn, first) in enumerate(chosen):
        part = fn()
        story += strip_lead(part) if i == 0 else part
    doc.build(story)
    return path
