"""Mise en forme des offres ouvertes pour le README."""

from __future__ import annotations

import re
import unicodedata
from html import escape
from collections import Counter, defaultdict
from datetime import date

MOIS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

# Code ISO à deux lettres de chaque pays, pour afficher le drapeau.
CODES_PAYS = {
    "Afrique du Sud": "ZA", "Algérie": "DZ", "Angola": "AO", "Bénin": "BJ", "Botswana": "BW",
    "Burkina Faso": "BF", "Burundi": "BI", "Cameroun": "CM", "Cap-Vert": "CV",
    "Centrafrique": "CF", "Comores": "KM", "Congo": "CG", "Côte d'Ivoire": "CI",
    "Djibouti": "DJ", "Égypte": "EG", "Érythrée": "ER", "Eswatini": "SZ", "Éthiopie": "ET",
    "Gabon": "GA", "Gambie": "GM", "Ghana": "GH", "Guinée": "GN", "Guinée-Bissau": "GW",
    "Guinée équatoriale": "GQ", "Kenya": "KE", "Lesotho": "LS", "Libéria": "LR", "Libye": "LY",
    "Madagascar": "MG", "Malawi": "MW", "Mali": "ML", "Maroc": "MA", "Maurice": "MU",
    "Mauritanie": "MR", "Mozambique": "MZ", "Namibie": "NA", "Niger": "NE", "Nigéria": "NG",
    "Ouganda": "UG", "RD Congo": "CD", "Rwanda": "RW", "Sahara occidental": "EH",
    "Sao Tomé-et-Principe": "ST", "Sénégal": "SN", "Seychelles": "SC", "Sierra Leone": "SL",
    "Somalie": "SO", "Soudan": "SD", "Soudan du Sud": "SS", "Tanzanie": "TZ", "Tchad": "TD",
    "Togo": "TG", "Tunisie": "TN", "Zambie": "ZM", "Zimbabwe": "ZW",
}


SANS_LIEU = "Lieu non précisé"


def drapeau(pays: str) -> str:
    code = CODES_PAYS.get(pays)
    if not code:
        return "🌍"
    return "".join(chr(0x1F1E6 + ord(lettre) - ord("A")) for lettre in code)


def date_fr(iso: str) -> str:
    """'2026-11-30' -> '30 novembre 2026'."""
    if not iso:
        return ""
    annee, mois, jour = (int(x) for x in iso.split("-"))
    return f"{'1er' if jour == 1 else jour} {MOIS[mois - 1]} {annee}"


MOIS_COURTS = ["janv.", "févr.", "mars", "avr.", "mai", "juin",
               "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def date_courte(iso: str) -> str:
    """'2026-11-30' -> '30 nov. 2026'."""
    annee, mois, jour = (int(x) for x in iso.split("-"))
    return f"{'1er' if jour == 1 else jour} {MOIS_COURTS[mois - 1]} {annee}"


def delai(iso: str, aujourdhui: date) -> str:
    if not iso:
        return ""
    jours = (date.fromisoformat(iso) - aujourdhui).days
    if jours <= 0:
        return "dernier jour"
    if jours == 1:
        return "demain"
    return f"dans {jours} jours"


def niveau_lisible(niveau: str) -> str:
    """Traduit les grades ONU : 'CON' -> 'Consultant', 'P-3' -> 'Professionnel (P-3)'."""
    n = niveau.strip().upper()
    if not n:
        return ""
    if n == "CON":
        return "Consultant"
    if n.startswith("I-"):
        return "Stage"
    if n.startswith("PL"):
        return f"Professionnel ({n})"
    if n.startswith("GS"):
        return f"Services généraux ({n})"
    if n == "INDIVIDUAL CONSULTANT":
        return "Consultant individuel"
    if n == "JUNIOR CONSULTANT":
        return "Consultant junior"
    if n.startswith("P-"):
        return f"Professionnel ({n})"
    if n.startswith("D-"):
        return f"Direction ({n})"
    if n.startswith("NO"):
        return f"Administrateur national ({n})"
    if n.startswith("G-"):
        return f"Services généraux ({n})"
    if n.startswith("FS-"):
        return f"Service mobile ({n})"
    if n in {"FULL TIME", "FULL_TIME"}:
        return "Temps plein"
    if n in {"PART TIME", "PART_TIME"}:
        return "Temps partiel"
    return niveau.strip()


def _ligne_cloture(offre: dict, aujourdhui: date) -> str:
    if not offre["date_cloture"]:
        return "Clôture : non précisée"
    texte = f"Clôture : {date_fr(offre['date_cloture'])} ({delai(offre['date_cloture'], aujourdhui)})"
    if (date.fromisoformat(offre["date_cloture"]) - aujourdhui).days <= 2:
        return f"⏳ **{texte}**"
    return texte


# ------------------------------------------------------------- Graphiques

def _etiquette(texte: str) -> str:
    return '"' + texte.replace('"', "'") + '"'


def graphique_pays(par_pays: dict[str, list]) -> list[str]:
    pays = sorted((p for p in par_pays if p != SANS_LIEU), key=lambda p: (-len(par_pays[p]), p))[:12]
    if not pays:
        return []
    valeurs = [len(par_pays[p]) for p in pays]
    return [
        "```mermaid",
        "xychart-beta",
        '    title "Offres ouvertes par pays"',
        f"    x-axis [{', '.join(_etiquette(p) for p in pays)}]",
        f'    y-axis "Offres" 0 --> {max(valeurs) + 1}',
        f"    bar [{', '.join(map(str, valeurs))}]",
        "```",
    ]


def graphique_organisations(ouvertes: list[dict]) -> list[str]:
    compte = Counter(o["organisation"] for o in ouvertes)
    if not compte:
        return []
    lignes = ["```mermaid", "pie showData", '    title "Offres ouvertes par organisation"']
    lignes += [f"    {_etiquette(org)} : {n}" for org, n in compte.most_common()]
    return lignes + ["```"]


def graphique_evolution(stats: list[dict], jours: int = 30) -> list[str]:
    recents = sorted(stats, key=lambda s: s["date"])[-jours:]
    if len(recents) < 2:
        return []
    dates = [f'"{s["date"][8:10]}/{s["date"][5:7]}"' for s in recents]
    ouvertes = [int(s["offres_ouvertes"]) for s in recents]
    nouvelles = [int(s["nouvelles_offres"]) for s in recents]
    return [
        "```mermaid",
        "xychart-beta",
        f'    title "Évolution sur les {len(recents)} derniers jours"',
        f"    x-axis [{', '.join(dates)}]",
        f'    y-axis "Offres" 0 --> {max(ouvertes + nouvelles) + 1}',
        f"    line [{', '.join(map(str, ouvertes))}]",
        f"    bar [{', '.join(map(str, nouvelles))}]",
        "```",
        "",
        "_Courbe : offres ouvertes. Barres : nouvelles offres du jour._",
    ]


# ------------------------------------------------------------------ Page

ORGANISATIONS = [
    ("ONU", "Secrétariat de l'ONU : CEA, PNUE, ONU-Habitat, OCHA, missions de paix...", "https://careers.un.org"),
    ("UNESCO", "Organisation des Nations unies pour l'éducation, la science et la culture", "https://careers.unesco.org"),
    ("UA", "Union africaine", "https://jobs.au.int"),
    ("BAD", "Banque africaine de développement", "https://www.afdb.org/en/about-careers/current-vacancies"),
]

NIVEAUX = [
    ("Stage", "stage, généralement pour étudiants ou jeunes diplômés."),
    ("Consultant", "contrat de courte durée, pour une mission précise."),
    ("Professionnel (P-1 à P-5, PL à la BAD)", "poste de cadre, avec recrutement international."),
    ("Administrateur national (NO)", "poste de cadre réservé aux ressortissants du pays où se trouve le poste."),
    ("Services généraux (G, GS)", "poste d'appui, recruté sur place."),
]

JOURS_URGENTS = 7


def ancre(pays: str) -> str:
    """"Côte d'Ivoire" -> "cote-d-ivoire"."""
    texte = "".join(c for c in unicodedata.normalize("NFD", pays) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", texte.lower()).strip("-")


def _pluriel(n: int, texte: str) -> str:
    """_pluriel(3, "offre ouverte") -> "3 offres ouvertes"."""
    if n > 1:
        texte = " ".join(mot + "s" for mot in texte.split())
    return f"{n} {texte}"


def _lieu(o: dict) -> str:
    return o["ville"] or o["pays"] or "Non précisé"


def _ferme_bientot(o: dict, aujourdhui: date) -> bool:
    return bool(o["date_cloture"]) and (date.fromisoformat(o["date_cloture"]) - aujourdhui).days <= JOURS_URGENTS


def _cloture(o: dict, aujourdhui: date) -> str:
    if not o["date_cloture"]:
        return "Non précisée"
    texte = f"{date_courte(o['date_cloture'])}, {delai(o['date_cloture'], aujourdhui)}"
    if (date.fromisoformat(o["date_cloture"]) - aujourdhui).days <= 2:
        return f"**{texte}**"
    return texte


def _poste(o: dict, aujourdhui: date) -> str:
    titre = o["titre"].replace("|", "/")
    nouveau = " *(nouveau)*" if o.get("vue_le") == aujourdhui.isoformat() else ""
    return f"[{titre}]({o['url']}){nouveau}"


def _tableau(offres: list[dict], aujourdhui: date, avec_pays: bool) -> list[str]:
    if avec_pays:
        lignes = ["| Poste | Organisation | Lieu | Clôture |", "|---|---|---|---|"]
        for o in offres:
            lieu = ", ".join(x for x in [o["ville"], o["pays"]] if x) or "Non précisé"
            lignes.append(f"| {_poste(o, aujourdhui)} | {o['organisation']} | {lieu} | {_cloture(o, aujourdhui)} |")
    else:
        lignes = ["| Poste | Organisation | Ville | Niveau | Clôture |", "|---|---|---|---|---|"]
        for o in offres:
            lignes.append(
                f"| {_poste(o, aujourdhui)} | {o['organisation']} | {o['ville'] or '-'} | "
                f"{niveau_lisible(o['niveau']) or '-'} | {_cloture(o, aujourdhui)} |"
            )
    return lignes


# ------------------------------------------------------------------- Page

# Photo de Naboth Otieno sur Pexels (licence Pexels : utilisation gratuite).
# Pour changer de photo : remplacer l'identifiant dans l'adresse, ou mettre une image
# dans assets/ et indiquer ici son chemin (par exemple "assets/banniere.jpg").
PHOTO = "assets/banniere.jpg"
PHOTO_PAGE = ""
PHOTO_AUTEUR = ""


def generer(ouvertes: list[dict], aujourdhui: date, stats: list[dict] | None = None) -> str:
    """Construit tout le README, pensé pour les candidats."""
    jour = aujourdhui.isoformat()
    par_pays = defaultdict(list)
    for offre in ouvertes:
        par_pays[offre["pays"] or SANS_LIEU].append(offre)
    ordre_pays = sorted(par_pays, key=lambda p: (p == SANS_LIEU, -len(par_pays[p]), p))
    nb_pays = len([p for p in par_pays if p != SANS_LIEU])
    par_cloture = sorted(ouvertes, key=lambda o: o["date_cloture"] or "9999-12-31")
    urgentes = [o for o in par_cloture if _ferme_bientot(o, aujourdhui)]
    nb_nouvelles = len([o for o in ouvertes if o.get("vue_le") == jour])

    L = [
        '<a name="haut"></a>',
        "",
        f'<img src="{escape(PHOTO)}" width="100%" alt="Développeur au travail dans un bureau à Nairobi">',
        "",
        f'<p align="right"><sub>Photo : <a href="{PHOTO_PAGE}">{PHOTO_AUTEUR}, Pexels</a></sub></p>',
        "",
        "# Offres d'emploi tech en Afrique",
        "",
        "Les postes en informatique, data, développement, GIS et statistiques publiés en Afrique "
        "par l'ONU, l'UNESCO, l'Union africaine et la Banque africaine de développement. "
        "La page est mise à jour chaque matin.",
        "",
        f"**{_pluriel(len(ouvertes), 'offre ouverte')} · {nb_pays} pays · "
        f"{_pluriel(nb_nouvelles, 'nouvelle')} aujourd'hui** · mise à jour le {date_fr(jour)}",
        "",
    ]

    if not ouvertes:
        L += ["Aucune offre ouverte pour le moment. Revenez demain.", ""]
    else:
        liens = [f"[{p} ({len(par_pays[p])})](#{ancre(p)})" for p in ordre_pays]
        L += ["Pays : " + " · ".join(liens), ""]

    if urgentes:
        L += [f"## Ferment dans les {JOURS_URGENTS} prochains jours", ""]
        L += _tableau(urgentes, aujourdhui, avec_pays=True) + [""]

    if ouvertes:
        L += ["## Toutes les offres", ""]
        for pays in ordre_pays:
            offres = sorted(par_pays[pays], key=lambda o: o["date_cloture"] or "9999-12-31")
            L += [f'<a name="{ancre(pays)}"></a>', "", f"### {pays}", ""]
            L += _tableau(offres, aujourdhui, avec_pays=False)
            L += ["", "[Retour en haut](#haut)", ""]

    graphiques = [graphique_pays(par_pays), graphique_organisations(ouvertes), graphique_evolution(stats or [])]
    graphiques = [g for g in graphiques if g]
    if graphiques:
        L += ["## En chiffres", "", "<details>", "<summary>Afficher les graphiques</summary>", ""]
        for g in graphiques:
            L += g + [""]
        L += ["</details>", ""]

    L += ["## Bon à savoir", "", "<details>", "<summary>Comment lire le niveau d'un poste</summary>", ""]
    L += [f"- **{nom}** : {texte}" for nom, texte in NIVEAUX]
    L += [
        "",
        "</details>",
        "",
        "<details>",
        "<summary>Conseils pour postuler</summary>",
        "",
        "- La candidature se fait toujours sur le site officiel de l'organisation, en suivant le lien de l'offre.",
        "- Les organisations internationales ne demandent jamais de frais pour postuler. "
        "Méfiez-vous de toute demande de paiement.",
        "- Vérifiez la date de clôture et les conditions (nationalité, langues, expérience) sur la fiche de l'offre.",
        "",
        "</details>",
        "",
        "<details>",
        "<summary>Organisations suivies</summary>",
        "",
    ]
    L += [f"- [{sigle}]({url}) : {nom}" for sigle, nom, url in ORGANISATIONS]
    L += [
        "",
        "</details>",
        "",
        "---",
        "",
        "<sub>Les offres appartiennent aux organisations qui les publient. Cette page reprend uniquement le titre, "
        "le lieu, le niveau et les dates, avec un lien vers l'annonce officielle. "
        "Fonctionnement du projet : [TECHNIQUE.md](TECHNIQUE.md).</sub>",
        "",
    ]
    return "\n".join(L)
