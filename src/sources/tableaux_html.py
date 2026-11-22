"""Lecture des tableaux d'offres en HTML (SuccessFactors, Drupal...).

Les colonnes sont repérées par le texte de leur en-tête, pas par leur position,
pour résister aux petits changements de mise en page.
"""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

FORMATS_DATE = [
    "%d %b %Y", "%d %B %Y", "%d-%b-%Y", "%d/%m/%Y", "%b %d, %Y", "%B %d, %Y", "%Y-%m-%d",
]


def lire_date(texte: str) -> str:
    """'21 Nov 2026', '31/12/2026', '16-Nov-2026'... -> '2026-11-21'. Chaîne vide si illisible."""
    texte = re.sub(r"\s+", " ", texte or "").strip()
    for fmt in FORMATS_DATE:
        try:
            return datetime.strptime(texte, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def _texte(element) -> str:
    return re.sub(r"\s+", " ", element.get_text(" ", strip=True)) if element else ""


def lire_tableau(html: str, url_base: str) -> list[dict]:
    """Renvoie une liste de lignes {en-tête en minuscules: texte}, plus '_titre' et '_lien'."""
    soupe = BeautifulSoup(html, "html.parser")
    tableaux = [t for t in soupe.find_all("table") if t.find("a", href=True)]
    if not tableaux:
        return []
    tableau = max(tableaux, key=lambda t: len(t.find_all("tr")))

    entetes = [_texte(th).lower() for th in tableau.find_all("th")]
    lignes = []
    for tr in tableau.find_all("tr"):
        cellules = tr.find_all("td", recursive=False)
        if not cellules:
            continue
        lien = tr.select_one("a.jobTitle-link") or tr.find("a", href=True)
        if not lien:
            continue
        ligne = {"_titre": _texte(lien), "_lien": urljoin(url_base, lien["href"])}
        # La première cellule de SuccessFactors répète tout pour mobile : on ne la lit pas.
        for entete, cellule in zip(entetes, cellules):
            ligne[entete] = _texte(cellule)
        lignes.append(ligne)
    return lignes


def colonne(ligne: dict, *mots: str, sauf: tuple[str, ...] = ()) -> str:
    """Valeur de la première colonne dont l'en-tête contient un des mots."""
    for entete, valeur in ligne.items():
        if entete.startswith("_"):
            continue
        if any(m in entete for m in mots) and not any(s in entete for s in sauf):
            return valeur
    return ""
