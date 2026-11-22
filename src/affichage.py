"""Mise en forme des offres ouvertes pour le README."""

from __future__ import annotations

import re
import unicodedata
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
    if o["ville"] and o["pays"]:
        return f"{o['ville']}, {o['pays']}"
    return o["ville"] or o["pays"] or "Non précisé"


def _ferme_bientot(o: dict, aujourdhui: date) -> bool:
    return bool(o["date_cloture"]) and (date.fromisoformat(o["date_cloture"]) - aujourdhui).days <= JOURS_URGENTS


def _bloc_offre(o: dict, aujourdhui: date) -> list[str]:
    nouveau = " 🆕" if o.get("vue_le") == aujourdhui.isoformat() else ""
    details = " · ".join(x for x in [o["organisation"], o["ville"], niveau_lisible(o["niveau"])] if x)
    return [
        f"- **[{o['titre']}]({o['url']})**{nouveau}  ",
        f"  {details}  ",
        f"  {_ligne_cloture(o, aujourdhui)}",
        "",
    ]


def _tableau(offres: list[dict], aujourdhui: date) -> list[str]:
    lignes = ["| Poste | Organisation | Lieu | Clôture |", "|---|---|---|---|"]
    for o in offres:
        titre = o["titre"].replace("|", "/")
        cloture = f"{date_fr(o['date_cloture'])} ({delai(o['date_cloture'], aujourdhui)})" if o["date_cloture"] else "non précisée"
        lignes.append(f"| [{titre}]({o['url']}) | {o['organisation']} | {_lieu(o)} | {cloture} |")
    return lignes


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
    nouvelles = [o for o in par_cloture if o.get("vue_le") == jour]

    L = [
        '<a name="haut"></a>',
        "",
        "# 💼 Offres d'emploi tech en Afrique",
        "",
        "**Les postes en informatique, data, développement, systèmes d'information, GIS et statistiques "
        "publiés en Afrique par l'ONU, l'UNESCO, l'Union africaine et la Banque africaine de développement.**",
        "",
        "Cette page est mise à jour automatiquement chaque matin. "
        "Cliquez sur le titre d'une offre pour lire la fiche complète et postuler sur le site officiel de l'organisation.",
        "",
        f"> **{_pluriel(len(ouvertes), 'offre ouverte')}** "
        f"dans **{nb_pays} pays** · **{_pluriel(len(nouvelles), 'nouvelle offre')}** aujourd'hui "
        f"· mise à jour le {date_fr(jour)}",
        "",
    ]

    if not ouvertes:
        L += ["Aucune offre ouverte pour le moment. Revenez demain.", ""]
    else:
        liens = [f"[{drapeau(p)} {p} ({len(par_pays[p])})](#{ancre(p)})" for p in ordre_pays]
        L += ["**Aller directement à un pays :** " + " · ".join(liens), ""]

    if urgentes:
        L += [f"## ⏳ Ferment dans les {JOURS_URGENTS} prochains jours", ""] + _tableau(urgentes, aujourdhui) + [""]

    if nouvelles:
        L += ["## 🆕 Nouvelles offres du jour", ""] + _tableau(nouvelles, aujourdhui) + [""]

    if ouvertes:
        L += ["## 🌍 Toutes les offres, par pays", ""]
        for pays in ordre_pays:
            L += [f'<a name="{ancre(pays)}"></a>', "", f"### {drapeau(pays)} {pays} ({len(par_pays[pays])})", ""]
            for o in sorted(par_pays[pays], key=lambda o: o["date_cloture"] or "9999-12-31"):
                L += _bloc_offre(o, aujourdhui)
            L += ["[↑ Retour en haut](#haut)", ""]

    graphiques = [graphique_pays(par_pays), graphique_organisations(ouvertes), graphique_evolution(stats or [])]
    graphiques = [g for g in graphiques if g]
    if graphiques:
        L += ["## 📊 En chiffres", ""]
        for g in graphiques:
            L += g + [""]

    L += ["## ℹ️ Bon à savoir", "", "**Comment lire le niveau d'un poste**", ""]
    L += [f"- **{nom}** : {texte}" for nom, texte in NIVEAUX]
    L += [
        "",
        "**Pour postuler**",
        "",
        "- La candidature se fait toujours sur le site officiel de l'organisation, en suivant le lien de l'offre.",
        "- Les organisations internationales ne demandent jamais de frais pour postuler. "
        "Méfiez-vous de toute demande de paiement.",
        "- Vérifiez la date de clôture et les conditions (nationalité, langues, expérience) sur la fiche de l'offre.",
        "",
        "**Organisations suivies**",
        "",
    ]
    L += [f"- [{sigle}]({url}) : {nom}" for sigle, nom, url in ORGANISATIONS]
    L += [
        "",
        "---",
        "",
        "Les offres appartiennent aux organisations qui les publient. Cette page reprend uniquement le titre, "
        "le lieu, le niveau et les dates, avec un lien vers l'annonce officielle. "
        "Fonctionnement du projet : [TECHNIQUE.md](TECHNIQUE.md).",
        "",
    ]
    return "\n".join(L)
