"""Mise en forme des offres ouvertes pour le README."""

from __future__ import annotations

from collections import defaultdict
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


def generer(ouvertes: list[dict], aujourdhui: date) -> str:
    nb_orgs = len({o["organisation"] for o in ouvertes})
    par_pays = defaultdict(list)
    for offre in ouvertes:
        par_pays[offre["pays"]].append(offre)

    s = lambda n: "s" if n > 1 else ""  # noqa: E731
    lignes = [
        f"**{len(ouvertes)} offre{s(len(ouvertes))} ouverte{s(len(ouvertes))}** "
        f"· {nb_orgs} organisation{s(nb_orgs)} · {len(par_pays)} pays "
        f"· mise à jour le {date_fr(aujourdhui.isoformat())}",
        "",
    ]
    if not ouvertes:
        lignes.append("Aucune offre ouverte aujourd'hui.")

    # Pays avec le plus d'offres en premier, puis ordre alphabétique.
    for pays in sorted(par_pays, key=lambda p: (-len(par_pays[p]), p)):
        offres = sorted(par_pays[pays], key=lambda o: o["date_cloture"] or "9999-12-31")
        lignes += [f"### {drapeau(pays)} {pays} ({len(offres)})", ""]
        for o in offres:
            details = " · ".join(x for x in [o["organisation"], o["ville"], niveau_lisible(o["niveau"])] if x)
            lignes += [
                f"- **[{o['titre']}]({o['url']})**  ",
                f"  {details}  ",
                f"  {_ligne_cloture(o, aujourdhui)}",
                "",
            ]
    return "\n".join(lignes).rstrip() + "\n"
