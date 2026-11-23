"""Collecte quotidienne des offres d'emploi tech des organisations internationales en Afrique.

Sources : ONU (careers.un.org), UNESCO, Union africaine, Banque africaine de développement.
Usage :  python src/collect.py
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
import affichage  # noqa: E402
from sources import USER_AGENT, afdb, successfactors, un_careers, workday  # noqa: E402

SOURCES = {
    "ONU (careers.un.org)": un_careers.collecter,
    "UNESCO et Union africaine": successfactors.collecter,
    "Banque africaine de développement": afdb.collecter,
    # Désactivé : le site Workday du HCR répond 429 aux serveurs de GitHub Actions.
    # "Workday (HCR)": workday.collecter,
}

# Début de la colonne "source" des offres de chaque source : sert à retrouver
# les offres déjà connues d'une source en panne.
ORIGINES = {
    "ONU (careers.un.org)": ("careers.un.org",),
    "UNESCO et Union africaine": tuple(site["url"].split("//")[1] for site in successfactors.SITES),
    "Banque africaine de développement": ("afdb.org",),
}
# Une source en panne garde ses offres vues dans les derniers jours, pas au-delà.
JOURS_DE_GRACE = 7

RACINE = Path(__file__).resolve().parent.parent
FICHIER_OFFRES = RACINE / "data" / "offres.csv"
FICHIER_STATS = RACINE / "data" / "stats_journalieres.csv"
FICHIER_README = RACINE / "README.md"
FICHIER_MESSAGE = RACINE / ".commit_msg"

COLONNES = [
    "id", "titre", "organisation", "organisation_nom", "pays", "ville", "categorie",
    "niveau", "date_publication", "date_cloture", "url", "source", "vue_le", "derniere_vue",
]



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


def offres_affichees(toutes: dict[str, dict], aujourdhui: date, echecs: list[str]) -> list[dict]:
    """Offres ouvertes vues aujourd'hui, plus celles d'une source en panne vues récemment.

    Sans cela, une source qui refuse la collecte un jour ferait disparaître toutes ses offres.
    """
    jour = aujourdhui.isoformat()
    origines = tuple(debut for nom in echecs for debut in ORIGINES.get(nom, ()))
    limite = (aujourdhui - timedelta(days=JOURS_DE_GRACE)).isoformat()

    def affichee(offre: dict) -> bool:
        if offre["derniere_vue"] == jour:
            return True
        return offre["source"].startswith(origines) and offre["derniere_vue"] >= limite

    return [o for o in toutes.values() if affichee(o) and est_ouverte(o, aujourdhui)]


def nouvelles_du_jour(toutes: dict[str, dict], jour: str) -> list[dict]:
    """Offres vues pour la première fois aujourd'hui, même si la collecte tourne deux fois."""
    return [o for o in toutes.values() if o["vue_le"] == jour]


def ligne_stats(jour: str, ouvertes: list[dict], nouvelles: list[dict]) -> dict:
    top = Counter(o["organisation"] for o in ouvertes).most_common(1)
    return {
        "date": jour,
        "offres_ouvertes": len(ouvertes),
        "nouvelles_offres": len(nouvelles),
        "organisations": len({o["organisation"] for o in ouvertes}),
        "pays": len({o["pays"] for o in ouvertes if o["pays"]}),
        "organisation_top": top[0][0] if top else "",
    }


# -------------------------------------------------------------- Sorties

def ecrire_readme(contenu: str) -> None:
    FICHIER_README.write_text(contenu, encoding="utf-8")


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
    toutes, _ = fusionner(existantes, collectees, jour)
    nouvelles = nouvelles_du_jour(toutes, jour)
    ouvertes = offres_affichees(toutes, aujourdhui, echecs)

    ecrire_csv(FICHIER_OFFRES, sorted(toutes.values(), key=lambda o: (o["vue_le"], o["id"]), reverse=True), COLONNES)

    stats = [s for s in lire_csv(FICHIER_STATS) if s["date"] != jour] + [ligne_stats(jour, ouvertes, nouvelles)]
    ecrire_csv(FICHIER_STATS, sorted(stats, key=lambda s: s["date"]), list(stats[-1].keys()))

    ecrire_readme(affichage.generer(ouvertes, aujourdhui, stats, echecs))
    message = message_commit(jour, nouvelles, ouvertes)
    FICHIER_MESSAGE.write_text(message, encoding="utf-8")
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
