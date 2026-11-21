"""Règles de filtrage : l'offre est-elle en Afrique, et est-ce un métier tech ?"""

from __future__ import annotations

import re
import unicodedata

# Pays d'Afrique : nom anglais (tel que les sites l'écrivent) -> nom français.
PAYS = {
    "Algeria": "Algérie", "Angola": "Angola", "Benin": "Bénin", "Botswana": "Botswana",
    "Burkina Faso": "Burkina Faso", "Burundi": "Burundi", "Cabo Verde": "Cap-Vert",
    "Cape Verde": "Cap-Vert", "Cameroon": "Cameroun",
    "Central African Republic": "Centrafrique", "Chad": "Tchad", "Comoros": "Comores",
    "Congo": "Congo", "Republic of the Congo": "Congo",
    "Democratic Republic of the Congo": "RD Congo", "DR Congo": "RD Congo",
    "Congo, Democratic Republic of the": "RD Congo",
    "Cote d'Ivoire": "Côte d'Ivoire", "Côte d'Ivoire": "Côte d'Ivoire", "Ivory Coast": "Côte d'Ivoire",
    "Djibouti": "Djibouti", "Egypt": "Égypte", "Equatorial Guinea": "Guinée équatoriale",
    "Eritrea": "Érythrée", "Eswatini": "Eswatini", "Swaziland": "Eswatini", "Ethiopia": "Éthiopie",
    "Gabon": "Gabon", "Gambia": "Gambie", "The Gambia": "Gambie", "Ghana": "Ghana",
    "Guinea": "Guinée", "Guinea-Bissau": "Guinée-Bissau", "Kenya": "Kenya", "Lesotho": "Lesotho",
    "Liberia": "Libéria", "Libya": "Libye", "Madagascar": "Madagascar", "Malawi": "Malawi",
    "Mali": "Mali", "Mauritania": "Mauritanie", "Mauritius": "Maurice", "Morocco": "Maroc",
    "Mozambique": "Mozambique", "Namibia": "Namibie", "Niger": "Niger", "Nigeria": "Nigéria",
    "Rwanda": "Rwanda", "Sao Tome and Principe": "Sao Tomé-et-Principe", "Senegal": "Sénégal",
    "Seychelles": "Seychelles", "Sierra Leone": "Sierra Leone", "Somalia": "Somalie",
    "South Africa": "Afrique du Sud", "South Sudan": "Soudan du Sud", "Sudan": "Soudan",
    "Tanzania": "Tanzanie", "United Republic of Tanzania": "Tanzanie", "Togo": "Togo",
    "Tunisia": "Tunisie", "Uganda": "Ouganda", "Zambia": "Zambie", "Zimbabwe": "Zimbabwe",
    "Western Sahara": "Sahara occidental",
}

# Villes d'affectation fréquentes dans le système ONU -> pays (en français).
VILLES = {
    "ABIDJAN": "Côte d'Ivoire", "ABUJA": "Nigéria", "LAGOS": "Nigéria", "MAIDUGURI": "Nigéria",
    "ACCRA": "Ghana", "ADDIS ABABA": "Éthiopie", "GAMBELLA": "Éthiopie", "ALGIERS": "Algérie",
    "TINDOUF": "Algérie", "ANTANANARIVO": "Madagascar", "ARUSHA": "Tanzanie",
    "DAR ES SALAAM": "Tanzanie", "DODOMA": "Tanzanie", "KIGOMA": "Tanzanie", "ASMARA": "Érythrée",
    "BAMAKO": "Mali", "GAO": "Mali", "MOPTI": "Mali", "TIMBUKTU": "Mali", "KIDAL": "Mali",
    "BANGUI": "Centrafrique", "BRIA": "Centrafrique", "BOUAR": "Centrafrique",
    "KAGA BANDORO": "Centrafrique", "BAMBARI": "Centrafrique", "BANJUL": "Gambie",
    "BISSAU": "Guinée-Bissau", "BRAZZAVILLE": "Congo", "BUJUMBURA": "Burundi", "GITEGA": "Burundi",
    "CAIRO": "Égypte", "CONAKRY": "Guinée", "COTONOU": "Bénin", "DAKAR": "Sénégal",
    "DJIBOUTI": "Djibouti", "ENTEBBE": "Ouganda", "KAMPALA": "Ouganda", "FREETOWN": "Sierra Leone",
    "GABORONE": "Botswana", "GOMA": "RD Congo", "KINSHASA": "RD Congo", "BUNIA": "RD Congo",
    "BENI": "RD Congo", "BUKAVU": "RD Congo", "LUBUMBASHI": "RD Congo", "KANANGA": "RD Congo",
    "HARARE": "Zimbabwe", "JOHANNESBURG": "Afrique du Sud", "PRETORIA": "Afrique du Sud",
    "CAPE TOWN": "Afrique du Sud", "JUBA": "Soudan du Sud", "MALAKAL": "Soudan du Sud",
    "BENTIU": "Soudan du Sud", "WAU": "Soudan du Sud", "BOR": "Soudan du Sud",
    "KHARTOUM": "Soudan", "PORT SUDAN": "Soudan", "EL FASHER": "Soudan", "NYALA": "Soudan",
    "KADUGLI": "Soudan", "ABYEI": "Abyei", "KIGALI": "Rwanda", "LAAYOUNE": "Sahara occidental",
    "LIBREVILLE": "Gabon", "LILONGWE": "Malawi", "LOME": "Togo", "LUANDA": "Angola",
    "LUSAKA": "Zambie", "MALABO": "Guinée équatoriale", "MAPUTO": "Mozambique",
    "MASERU": "Lesotho", "MBABANE": "Eswatini", "MOGADISHU": "Somalie", "BAIDOA": "Somalie",
    "GAROWE": "Somalie", "HARGEISA": "Somalie", "KISMAYO": "Somalie", "MONROVIA": "Libéria",
    "MORONI": "Comores", "NAIROBI": "Kenya", "MOMBASA": "Kenya", "KAKUMA": "Kenya",
    "DADAAB": "Kenya", "N'DJAMENA": "Tchad", "NDJAMENA": "Tchad", "ABECHE": "Tchad",
    "NIAMEY": "Niger", "NOUAKCHOTT": "Mauritanie", "OUAGADOUGOU": "Burkina Faso",
    "PORT LOUIS": "Maurice", "PRAIA": "Cap-Vert", "RABAT": "Maroc", "SAO TOME": "Sao Tomé-et-Principe",
    "TRIPOLI": "Libye", "BENGHAZI": "Libye", "TUNIS": "Tunisie", "VICTORIA": "Seychelles",
    "WINDHOEK": "Namibie", "YAOUNDE": "Cameroun", "DOUALA": "Cameroun", "MAROUA": "Cameroun",
}

# Mots-clés tech cherchés dans le titre et la famille de métier.
MOTS_TECH = [
    r"(?-i:\bICT\b)", r"(?-i:\bIT\b)", r"information technology", r"information management",
    r"information systems?", r"\bdata\b", r"database", r"developer", r"software", r"programmer",
    r"digital", r"\bGIS\b", r"geospatial", r"cyber", r"security information",
    r"machine learning", r"artificial intelligence", r"(?-i:\bAI\b)", r"devops", r"cloud",
    r"network", r"telecom", r"systems? administrator", r"web", r"statistic",
    r"informatique", r"numérique", r"données", r"développeur", r"télécom",
]
_REGEX_TECH = re.compile("|".join(MOTS_TECH), re.IGNORECASE)

# "Digital" et "web" sortent aussi pour la com. On écarte ces titres.
_EXCLUSIONS = re.compile(r"communication|social media|content|graphic|photograph|video", re.IGNORECASE)


def _sans_accents(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn")


def pays_depuis_ville(lieu: str) -> str | None:
    """'NAIROBI' -> 'Kenya', 'ABIDJAN-LOCAL' -> "Côte d'Ivoire", 'GENEVA' -> None."""
    lieu = _sans_accents(lieu).upper().strip()
    for ville, pays in VILLES.items():
        if lieu == ville or lieu.startswith(ville + "-") or lieu.startswith(ville + " "):
            return pays
    return None


def pays_depuis_nom(nom: str) -> str | None:
    """'Kenya' -> 'Kenya', 'Cameroon' -> 'Cameroun', 'France' -> None."""
    return PAYS.get(nom.strip())


def est_tech(titre: str, famille: str = "") -> bool:
    if _REGEX_TECH.search(famille or ""):
        return True
    return bool(_REGEX_TECH.search(titre)) and not _EXCLUSIONS.search(titre)
