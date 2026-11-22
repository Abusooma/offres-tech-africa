"""Source : Banque africaine de développement (afdb.org).

Deux pages publiques : les postes et les consultances.
Le robots.txt de afdb.org demande 10 secondes entre deux requêtes.
"""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import filtres
from sources.tableaux_html import colonne, lire_date, lire_tableau

PAGES = [
    "https://www.afdb.org/en/about-careers/current-vacancies",
    "https://www.afdb.org/en/about-us/careers/current-vacancies/consultants",
]
FLUX_RSS = [
    "https://www.afdb.org/en/about-us/careers/current-vacancies/rss/",
    "https://www.afdb.org/en/about-us/careers/current-vacancies/consultants/rss",
]
PAUSE = 10

# Appels à manifestation d'intérêt destinés aux cabinets, pas à des candidats individuels.
_CABINETS = re.compile(r"consulting firms|pre-?qualification|firm consultant", re.IGNORECASE)


def analyser_ligne(ligne: dict) -> dict | None:
    titre = ligne["_titre"]
    type_poste = colonne(ligne, "consultant type", "type")
    if not filtres.est_tech(titre) or _CABINETS.search(f"{titre} {type_poste}"):
        return None
    lieu = colonne(ligne, "location")
    identifiant = re.search(r"-(\d+)/?$", ligne["_lien"])
    return {
        "id": f"afdb-{identifiant.group(1) if identifiant else ligne['_lien']}",
        "titre": titre,
        "organisation": "BAD",
        "organisation_nom": "Banque africaine de développement",
        # Les consultances n'indiquent pas de lieu : on ne l'invente pas.
        "pays": filtres.pays_depuis_lieu(lieu) or "",
        "ville": lieu.split(",")[0].strip() if lieu else "",
        "categorie": type_poste,
        "niveau": colonne(ligne, "grade") or type_poste,
        "date_publication": lire_date(colonne(ligne, "publication")),
        "date_cloture": lire_date(colonne(ligne, "closing")),
        "url": ligne["_lien"],
        "source": "afdb.org",
    }


def analyser_rss(xml: str) -> list[dict]:
    """Solution de repli : le flux RSS donne le titre, le lien et la date de publication,
    mais ni le lieu ni la date de clôture."""
    offres = []
    for item in ET.fromstring(xml).iter("item"):
        titre = (item.findtext("title") or "").strip()
        lien = (item.findtext("link") or "").strip()
        if not titre or not lien or not filtres.est_tech(titre) or _CABINETS.search(titre):
            continue
        identifiant = re.search(r"-(\d+)/?$", lien)
        try:
            publication = parsedate_to_datetime(item.findtext("pubDate") or "").date().isoformat()
        except (TypeError, ValueError):
            publication = ""
        offres.append({
            "id": f"afdb-{identifiant.group(1) if identifiant else lien}",
            "titre": titre,
            "organisation": "BAD",
            "organisation_nom": "Banque africaine de développement",
            "pays": "",
            "ville": "",
            "categorie": "",
            "niveau": "Consultant" if "/consultants/" in lien else "",
            "date_publication": publication,
            "date_cloture": "",
            "url": lien,
            "source": "afdb.org (RSS)",
        })
    return offres


def _par_pages(session) -> list[dict]:
    offres = []
    for numero, url in enumerate(PAGES):
        if numero:
            time.sleep(PAUSE)
        reponse = session.get(url, timeout=60)
        reponse.raise_for_status()
        lignes = lire_tableau(reponse.text, url)
        retenues = [o for o in map(analyser_ligne, lignes) if o]
        print(f"  BAD : {len(lignes)} offres lues sur {url.rsplit('/', 1)[-1]}, {len(retenues)} retenues")
        offres.extend(retenues)
    return offres


def _par_rss(session) -> list[dict]:
    offres = []
    for numero, url in enumerate(FLUX_RSS):
        time.sleep(PAUSE)
        reponse = session.get(url, timeout=60)
        reponse.raise_for_status()
        retenues = analyser_rss(reponse.text)
        print(f"  BAD (RSS) : {len(retenues)} offres retenues")
        offres.extend(retenues)
    return offres


def collecter(session) -> list[dict]:
    try:
        return _par_pages(session)
    except Exception as erreur:
        print(f"  BAD : pages refusées ({erreur}), essai du flux RSS")
        return _par_rss(session)
