"""Source : flux RSS public du portail carrières de l'ONU (careers.un.org/jobfeed)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime

import filtres

URL = "https://careers.un.org/jobfeed"

# Noms courts pour les entités les plus fréquentes.
SIGLES = {
    "United Nations Environment Programme": "PNUE",
    "Economic Commission for Africa": "CEA",
    "Office for the Coordination of Humanitarian Affairs": "OCHA",
    "United Nations Human Settlements Programme": "ONU-Habitat",
    "United Nations Office at Nairobi": "ONUN",
    "Office of Information and Communications Technology": "OICT",
    "Department of Operational Support": "DOS",
    "Department of Peace Operations": "DPO",
    "Office of the High Commissioner for Human Rights": "HCDH",
    "United Nations Office on Drugs and Crime": "ONUDC",
    "Office of Internal Oversight Services": "BSCI",
    "United Nations Development Programme": "PNUD",
    "United Nations Children's Fund": "UNICEF",
    "Department of Safety and Security": "DSS",
    "Office of Legal Affairs": "OLA",
}


def _champs_description(description: str) -> dict[str, str]:
    """Transforme 'Level : P-3 <br> Duty Station : NAIROBI <br> ...' en dictionnaire."""
    champs = {}
    for morceau in re.split(r"<br\s*/?>", description):
        if ":" in morceau:
            cle, _, valeur = morceau.partition(":")
            champs[cle.strip()] = valeur.strip()
    return champs


def _date(texte: str) -> str:
    """'06/27/2026 23:59:59 PM (New York time)' -> '2026-06-27'."""
    try:
        return datetime.strptime(texte.split()[0], "%m/%d/%Y").date().isoformat()
    except (ValueError, IndexError):
        return ""


def analyser(xml: str) -> list[dict]:
    offres = []
    for item in ET.fromstring(xml).iter("item"):
        titre = (item.findtext("title") or "").strip()
        lien = (item.findtext("link") or "").strip()
        champs = _champs_description(item.findtext("description") or "")

        lieu = champs.get("Duty Station", "")
        pays = filtres.pays_depuis_ville(lieu)
        famille = champs.get("Job Family", "")
        if not pays or not filtres.est_tech(titre, famille):
            continue

        departement = champs.get("Department/Office", "")
        offres.append({
            "id": f"un-{champs.get('Job ID') or lien.rsplit('/', 1)[-1].split('?')[0]}",
            "titre": titre,
            "organisation": SIGLES.get(departement, departement or "ONU"),
            "organisation_nom": departement,
            "pays": pays,
            "ville": lieu.split("-")[0].title(),
            "categorie": famille,
            "niveau": champs.get("Level", ""),
            "date_publication": _date(champs.get("Posted Date", "")),
            "date_cloture": _date(champs.get("Deadline", "")),
            "url": lien,
            "source": "careers.un.org",
        })
    return offres


def collecter(session) -> list[dict]:
    reponse = session.get(URL, timeout=60)
    reponse.raise_for_status()
    return analyser(reponse.text)
