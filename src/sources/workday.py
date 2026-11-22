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

TAILLE_PAGE = 20          # maximum accepté par Workday
PAUSE = 3.0               # secondes entre deux requêtes
ESSAIS = 3                # tentatives si le site répond 429 (trop de requêtes)
ATTENTE_429 = 60          # secondes d'attente par défaut après un 429


class TropDeRequetes(Exception):
    pass


def _requete(session, methode: str, url: str, **kwargs) -> dict:
    """Envoie la requête, attend et réessaie si le site demande de ralentir."""
    for essai in range(1, ESSAIS + 1):
        reponse = session.request(methode, url, headers={"Accept": "application/json"}, timeout=60, **kwargs)
        if reponse.status_code != 429:
            reponse.raise_for_status()
            time.sleep(PAUSE)
            return reponse.json()
        if essai == ESSAIS:
            raise TropDeRequetes(f"429 persistant après {ESSAIS} essais sur {url}")
        attente = int(reponse.headers.get("Retry-After", ATTENTE_429 * essai))
        print(f"  429 reçu, nouvel essai dans {attente} s")
        time.sleep(attente)
    return {}


def _base(site: dict) -> str:
    return f"https://{site['hote']}/wday/cxs/{site['tenant']}/{site['site']}"


def _lister(session, site: dict) -> list[dict]:
    """Parcourt toutes les offres du site, sans recherche, page par page."""
    resultats, offset = [], 0
    while True:
        contenu = _requete(
            session, "POST", f"{_base(site)}/jobs",
            json={"appliedFacets": {}, "limit": TAILLE_PAGE, "offset": offset, "searchText": ""},
        )
        page = contenu.get("jobPostings", [])
        resultats.extend(page)
        offset += len(page)
        if not page or offset >= contenu.get("total", 0):
            return resultats


def _detail(session, site: dict, chemin: str) -> dict:
    return _requete(session, "GET", f"{_base(site)}{chemin}").get("jobPostingInfo", {})


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
        annonces = _lister(session, site)
        # Tri sur le titre d'abord : on n'ouvre que les fiches qui ressemblent à de la tech.
        chemins = sorted({
            a["externalPath"] for a in annonces
            if a.get("externalPath") and filtres.est_tech(a.get("title", ""))
        })
        print(f"  {site['sigle']} : {len(annonces)} offres au total, {len(chemins)} à vérifier")
        for chemin in chemins:
            offre = analyser_detail(site, chemin, _detail(session, site, chemin))
            if offre:
                offres.append(offre)
    return offres
