"""Collecte quotidienne des offres d'emploi tech des organisations internationales en Afrique.

Sources : flux RSS de careers.un.org (Secrétariat de l'ONU) et site carrière Workday du HCR.
Usage :  python src/collect.py
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
import affichage  # noqa: E402
from sources import USER_AGENT, un_careers, workday  # noqa: E402

SOURCES = {
    "careers.un.org": un_careers.collecter,
    "Workday (HCR)": workday.collecter,
}

RACINE = Path(__file__).resolve().parent.parent
FICHIER_OFFRES = RACINE / "data" / "offres.csv"
FICHIER_STATS = RACINE / "data" / "stats_journalieres.csv"
FICHIER_README = RACINE / "README.md"
FICHIER_MESSAGE = RACINE / ".commit_msg"

COLONNES = [
    "id", "titre", "organisation", "organisation_nom", "pays", "ville", "categorie",
    "niveau", "date_publication", "date_cloture", "url", "source", "vue_le", "derniere_vue",
]

DEBUT_TABLE = "<!-- OFFRES:DEBUT -->"
FIN_TABLE = "<!-- OFFRES:FIN -->"


# ------------------------------------------------------------ Fichiers

def lire_csv(chemin: Path) -> list[dict]:
    if not chemin.exists():
        return []
    with chemin.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def ecrire_csv(chemin: Path, lignes: list[dict], colonnes: list[str]) -> None:
    chemin.parent.mkdir(exist_ok=True)
    with chemin.open("w", encoding="utf-8", newline="") as f:
        ecrivain = csv.DictWriter(f, fieldnames=colonnes, extrasaction="ignore")
        ecrivain.writeheader()
        ecrivain.writerows(lignes)


# ---------------------------------------------------------- Traitement

def est_ouverte(offre: dict, aujourdhui: date) -> bool:
    cloture = offre.get("date_cloture")
    if not cloture:
        return True
    return datetime.strptime(cloture, "%Y-%m-%d").date() >= aujourdhui


def fusionner(existantes: dict[str, dict], collectees: list[dict], jour: str) -> tuple[dict, list[dict]]:
    """Ajoute les nouvelles offres, met à jour les anciennes. Renvoie (toutes, nouvelles)."""
    toutes = dict(existantes)
    nouvelles = []
    for offre in collectees:
        if offre["id"] in toutes:
            toutes[offre["id"]] = {**offre, "vue_le": toutes[offre["id"]]["vue_le"], "derniere_vue": jour}
        else:
            toutes[offre["id"]] = {**offre, "vue_le": jour, "derniere_vue": jour}
            nouvelles.append(toutes[offre["id"]])
    return toutes, nouvelles


def ligne_stats(jour: str, ouvertes: list[dict], nouvelles: list[dict]) -> dict:
    top = Counter(o["organisation"] for o in ouvertes).most_common(1)
    return {
        "date": jour,
        "offres_ouvertes": len(ouvertes),
        "nouvelles_offres": len(nouvelles),
        "organisations": len({o["organisation"] for o in ouvertes}),
        "pays": len({o["pays"] for o in ouvertes}),
        "organisation_top": top[0][0] if top else "",
    }


# -------------------------------------------------------------- Sorties

def mettre_a_jour_readme(table: str) -> None:
    texte = FICHIER_README.read_text(encoding="utf-8")
    debut = texte.index(DEBUT_TABLE) + len(DEBUT_TABLE)
    fin = texte.index(FIN_TABLE)
    FICHIER_README.write_text(texte[:debut] + "\n" + table + "\n" + texte[fin:], encoding="utf-8")


def message_commit(jour: str, nouvelles: list[dict], ouvertes: list[dict]) -> str:
    if not nouvelles:
        return f"data: aucune nouvelle offre le {jour}, {len(ouvertes)} offres ouvertes"
    orgs = [org for org, _ in Counter(o["organisation"] for o in nouvelles).most_common(3)]
    s = "s" if len(nouvelles) > 1 else ""
    return f"data: {len(nouvelles)} nouvelle{s} offre{s} tech le {jour} ({', '.join(orgs)})"


# ----------------------------------------------------------------- Main

def main() -> int:
    aujourdhui = date.today()
    jour = aujourdhui.isoformat()

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    collectees, echecs = [], []
    for nom, collecter in SOURCES.items():
        try:
            offres = collecter(session)
            print(f"{nom} : {len(offres)} offres tech en Afrique")
            collectees.extend(offres)
        except Exception as erreur:  # une source en panne ne doit pas bloquer les autres
            print(f"{nom} : échec ({erreur})", file=sys.stderr)
            echecs.append(nom)

    if len(echecs) == len(SOURCES):
        print("Toutes les sources ont échoué, rien n'est modifié.", file=sys.stderr)
        return 1

    collectees = list({o["id"]: o for o in collectees}.values())
    existantes = {o["id"]: o for o in lire_csv(FICHIER_OFFRES)}
    toutes, nouvelles = fusionner(existantes, collectees, jour)
    ouvertes = [o for o in toutes.values() if o["derniere_vue"] == jour and est_ouverte(o, aujourdhui)]

    ecrire_csv(FICHIER_OFFRES, sorted(toutes.values(), key=lambda o: (o["vue_le"], o["id"]), reverse=True), COLONNES)

    stats = [s for s in lire_csv(FICHIER_STATS) if s["date"] != jour] + [ligne_stats(jour, ouvertes, nouvelles)]
    ecrire_csv(FICHIER_STATS, sorted(stats, key=lambda s: s["date"]), list(stats[-1].keys()))

    mettre_a_jour_readme(affichage.generer(ouvertes, aujourdhui))

    message = message_commit(jour, nouvelles, ouvertes)
    FICHIER_MESSAGE.write_text(message, encoding="utf-8")
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
