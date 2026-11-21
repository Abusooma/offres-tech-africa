"""Source : sites carrières Workday (UNHCR).

On utilise l'API JSON que le site carrière appelle lui-même pour afficher les offres.
Le robots.txt de unhcr.wd3.myworkdayjobs.com autorise la partie /External/.
"""

from __future__ import annotations

import time

import filtres

# Organisations sur Workday. Pour en ajouter une : hôte, tenant et nom du site
# se lisent dans l'URL de leur page carrière.
SITES = [
    {
        "sigle": "HCR",
        "nom": "UNHCR - Haut Commissariat des Nations unies pour les réfugiés",
        "hote": "unhcr.wd3.myworkdayjobs.com",
        "tenant": "unhcr",
        "site": "External",
    },
]

RECHERCHES = ["ICT", "data", "information management", "developer", "software", "digital", "GIS", "network"]
TAILLE_PAGE = 20          # maximum accepté par Workday
PAUSE = 1.0               # secondes entre deux requêtes, pour rester discret


def _base(site: dict) -> str:
    return f"https://{site['hote']}/wday/cxs/{site['tenant']}/{site['site']}"


def _chercher(session, site: dict, texte: str) -> list[dict]:
    resultats, offset = [], 0
    while True:
        reponse = session.post(
            f"{_base(site)}/jobs",
            json={"appliedFacets": {}, "limit": TAILLE_PAGE, "offset": offset, "searchText": texte},
            timeout=60,
        )
        reponse.raise_for_status()
        contenu = reponse.json()
        page = contenu.get("jobPostings", [])
        resultats.extend(page)
        offset += len(page)
        time.sleep(PAUSE)
        if not page or offset >= contenu.get("total", 0):
            return resultats


def _detail(session, site: dict, chemin: str) -> dict:
    reponse = session.get(f"{_base(site)}{chemin}", timeout=60)
    reponse.raise_for_status()
    time.sleep(PAUSE)
    return reponse.json().get("jobPostingInfo", {})


def analyser_detail(site: dict, chemin: str, info: dict) -> dict | None:
    titre = info.get("title", "").strip()
    pays_en = (info.get("country") or {}).get("descriptor", "")
    pays = filtres.pays_depuis_nom(pays_en) or filtres.pays_depuis_ville(info.get("location", ""))
    if not pays or not filtres.est_tech(titre):
        return None
    return {
        "id": f"{site['tenant']}-{info.get('jobReqId') or chemin.rsplit('_', 1)[-1]}",
        "titre": titre,
        "organisation": site["sigle"],
        "organisation_nom": site["nom"],
        "pays": pays,
        "ville": info.get("location", ""),
        "categorie": "",
        "niveau": info.get("timeType", ""),
        "date_publication": (info.get("startDate") or "")[:10],
        "date_cloture": (info.get("endDate") or "")[:10],
        "url": info.get("externalUrl") or f"https://{site['hote']}/en-US/{site['site']}{chemin}",
        "source": site["hote"],
    }


def collecter(session) -> list[dict]:
    offres = []
    for site in SITES:
        chemins = set()
        for texte in RECHERCHES:
            for annonce in _chercher(session, site, texte):
                # Premier tri sur le titre pour ne pas ouvrir chaque fiche inutilement.
                if annonce.get("externalPath") and filtres.est_tech(annonce.get("title", "")):
                    chemins.add(annonce["externalPath"])
        for chemin in sorted(chemins):
            offre = analyser_detail(site, chemin, _detail(session, site, chemin))
            if offre:
                offres.append(offre)
    return offres
