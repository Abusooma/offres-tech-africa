"""Source : sites carrières SAP SuccessFactors (UNESCO, Union africaine).

Les listes d'offres de ces sites sont chargées en JavaScript. On passe donc par :
1. le sitemap public (sitemap.xml), qui liste toutes les offres ouvertes ;
2. un premier tri sur le titre, lisible dans l'adresse de l'offre ;
3. la fiche de chaque offre retenue, dont le contenu est dans le HTML.
Le robots.txt de ces sites interdit /services/, pas le sitemap ni les fiches.
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import unquote

from bs4 import BeautifulSoup

import filtres

SITES = [
    {
        "sigle": "UNESCO",
        "nom": "UNESCO",
        "url": "https://careers.unesco.org",
        # Libellés des champs sur la fiche, du plus précis au plus général.
        "lieu": ["Work location", "Duty Station"],
        "cloture": ["Application deadline"],
        "publication": ["Posting Start Date", "Date posted"],
        "niveau": ["Grade", "Level"],
        "ordre_date": "jour/mois",   # 23/11/26 = 23 novembre 2026
    },
    {
        "sigle": "UA",
        "nom": "Union africaine",
        "url": "https://jobs.au.int",
        "lieu": ["Job Location (country)", "Location"],
        "cloture": ["End Date"],
        "publication": ["Posting Start Date"],
        "niveau": ["Job Grade"],
        "ordre_date": "mois/jour",   # 11/18/26 = 18 novembre 2026
    },
]

PAUSE = 2.0
_NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


# ---------------------------------------------------------------- Sitemap

def lire_sitemap(xml: str) -> list[str]:
    racine = ET.fromstring(xml)
    liens = [loc.text.strip() for loc in racine.iterfind(".//s:loc", _NS) if loc.text]
    if not liens:  # sitemap sans espace de noms
        liens = [loc.text.strip() for loc in racine.iter("loc") if loc.text]
    return [l for l in liens if "/job/" in l]


def titre_depuis_lien(lien: str) -> str:
    """'.../job/Dakar-ICT-Officer-%28Data%29/1379/' -> 'Dakar ICT Officer (Data)'."""
    morceaux = lien.rstrip("/").split("/")
    slug = morceaux[-2] if len(morceaux) >= 2 else ""
    return unquote(slug).replace("-", " ")


# ------------------------------------------------------------------ Fiche

def lire_date_fiche(texte: str, ordre: str) -> str:
    texte = re.sub(r"\s+", " ", texte or "").strip()
    texte = re.sub(r"\s*\(.*$", "", texte)  # retire "(Midnight Paris Time)" etc.
    formats = ["%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y", "%Y-%m-%d"]
    formats += ["%d/%m/%y", "%d/%m/%Y"] if ordre == "jour/mois" else ["%m/%d/%y", "%m/%d/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(texte, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def champ(lignes: list[str], libelles: list[str]) -> str:
    """Cherche 'Libellé : valeur' (sur la même ligne ou la suivante)."""
    for libelle in libelles:
        motif = re.compile(rf"^\s*{re.escape(libelle)}[^:]*:\s*(.*)$", re.IGNORECASE)
        for i, ligne in enumerate(lignes):
            trouve = motif.match(ligne)
            if not trouve:
                continue
            valeur = trouve.group(1).strip()
            if not valeur:
                valeur = next((l.strip() for l in lignes[i + 1:i + 3] if l.strip()), "")
            if valeur:
                return valeur
    return ""


def _ville(lignes: list[str]) -> str:
    """Première partie d'un champ de lieu qui n'est pas juste un nom de pays."""
    for libelle in ["Duty Station", "Work location", "Location"]:
        valeur = champ(lignes, [libelle])
        premier = valeur.split(",")[0].strip()
        if premier and not filtres.pays_depuis_nom(premier):
            return premier
    return ""


def analyser_fiche(site: dict, lien: str, html: str) -> dict | None:
    soupe = BeautifulSoup(html, "html.parser")
    og = soupe.find("meta", attrs={"property": "og:title"})
    h1 = soupe.find("h1")
    titre = (og.get("content") if og else "") or (h1.get_text(" ", strip=True) if h1 else "")
    titre = titre.strip() or titre_depuis_lien(lien)

    lignes = [l for l in soupe.get_text("\n").splitlines() if l.strip()]
    lieu = champ(lignes, site["lieu"])
    pays = filtres.pays_depuis_lieu(lieu) or filtres.pays_depuis_lieu(titre_depuis_lien(lien).split(" ")[0])
    if not pays or not filtres.est_tech(titre):
        return None

    identifiant = re.search(r"/(\d+)/?$", lien)
    return {
        "id": f"{site['sigle'].lower()}-{identifiant.group(1) if identifiant else lien}",
        "titre": titre,
        "organisation": site["sigle"],
        "organisation_nom": site["nom"],
        "pays": pays,
        "ville": _ville(lignes),
        "categorie": "",
        "niveau": champ(lignes, site["niveau"]),
        "date_publication": lire_date_fiche(champ(lignes, site["publication"]), site["ordre_date"]),
        "date_cloture": lire_date_fiche(champ(lignes, site["cloture"]), site["ordre_date"]),
        "url": lien,
        "source": site["url"].split("//")[1],
    }


# --------------------------------------------------------------- Collecte

def collecter_site(session, site: dict) -> list[dict]:
    reponse = session.get(f"{site['url']}/sitemap.xml", timeout=60)
    reponse.raise_for_status()
    liens = lire_sitemap(reponse.text)
    candidats = [l for l in liens if filtres.est_tech(titre_depuis_lien(l))]

    offres = []
    for lien in candidats:
        time.sleep(PAUSE)
        fiche = session.get(lien, timeout=60)
        fiche.raise_for_status()
        offre = analyser_fiche(site, lien, fiche.text)
        if offre:
            offres.append(offre)
    print(f"  {site['sigle']} : {len(liens)} offres dans le sitemap, "
          f"{len(candidats)} fiches ouvertes, {len(offres)} retenues")
    return offres


def collecter(session) -> list[dict]:
    offres, erreurs = [], []
    for site in SITES:
        try:
            offres.extend(collecter_site(session, site))
        except Exception as erreur:  # un site en panne ne bloque pas l'autre
            print(f"  {site['sigle']} : échec ({erreur})")
            erreurs.append(site["sigle"])
    if len(erreurs) == len(SITES):
        raise RuntimeError("aucun site SuccessFactors n'a répondu")
    return offres
