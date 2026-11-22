from datetime import date
from pathlib import Path

import collect
import filtres
from sources import un_careers, workday

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------- Filtres

def test_pays_depuis_ville():
    assert filtres.pays_depuis_ville("NAIROBI") == "Kenya"
    assert filtres.pays_depuis_ville("ABIDJAN-LOCAL") == "Côte d'Ivoire"
    assert filtres.pays_depuis_ville("Yaoundé") == "Cameroun"
    assert filtres.pays_depuis_ville("GENEVA") is None


def test_est_tech():
    assert filtres.est_tech("Senior Software Developer")
    assert filtres.est_tech("ICT Assistant")
    assert filtres.est_tech("Programme Officer", famille="Information Management")
    assert not filtres.est_tech("Digital Communication Specialist")
    assert not filtres.est_tech("Programme Officer, it is a great job")


# ---------------------------------------------------------- careers.un.org

def test_un_careers_garde_seulement_tech_en_afrique():
    offres = un_careers.analyser((FIXTURES / "un_jobfeed.xml").read_text(encoding="utf-8"))
    ids = {o["id"] for o in offres}
    assert ids == {"un-280001", "un-280002", "un-280005"}  # Genève et Droits de l'homme exclus


def test_un_careers_champs():
    offres = un_careers.analyser((FIXTURES / "un_jobfeed.xml").read_text(encoding="utf-8"))
    offre = next(o for o in offres if o["id"] == "un-280001")
    assert offre["organisation"] == "ONUN"
    assert offre["pays"] == "Kenya"
    assert offre["ville"] == "Nairobi"
    assert offre["date_cloture"] == "2026-12-17"
    assert offre["niveau"] == "P-3"


# ------------------------------------------------------------------ Workday

def test_workday_detail():
    site = workday.SITES[0]
    info = {
        "title": "Information Management Officer",
        "location": "Juba",
        "country": {"descriptor": "South Sudan"},
        "jobReqId": "JR2600123",
        "startDate": "2026-11-20",
        "timeType": "Full time",
        "externalUrl": "https://unhcr.wd3.myworkdayjobs.com/External/job/Juba/IMO_JR2600123",
    }
    offre = workday.analyser_detail(site, "/job/Juba/IMO_JR2600123", info)
    assert offre["id"] == "unhcr-JR2600123"
    assert offre["pays"] == "Soudan du Sud"
    assert offre["organisation"] == "HCR"


def test_workday_hors_afrique_exclu():
    site = workday.SITES[0]
    info = {"title": "Data Officer", "location": "Geneva", "country": {"descriptor": "Switzerland"}}
    assert workday.analyser_detail(site, "/job/Geneva/Data_JR1", info) is None


# --------------------------------------------------------------- Collecte

def test_offre_expiree_est_fermee():
    assert collect.est_ouverte({"date_cloture": ""}, date(2026, 11, 21))
    assert not collect.est_ouverte({"date_cloture": "2026-11-01"}, date(2026, 11, 21))


def test_fusion_garde_la_premiere_date_vue():
    offres = un_careers.analyser((FIXTURES / "un_jobfeed.xml").read_text(encoding="utf-8"))
    toutes, nouvelles = collect.fusionner({}, offres, "2026-11-20")
    assert len(nouvelles) == 3

    toutes, nouvelles = collect.fusionner(toutes, offres[:1], "2026-11-21")
    assert nouvelles == []
    assert toutes[offres[0]["id"]]["vue_le"] == "2026-11-20"
    assert toutes[offres[0]["id"]]["derniere_vue"] == "2026-11-21"


def test_message_commit():
    offres = un_careers.analyser((FIXTURES / "un_jobfeed.xml").read_text(encoding="utf-8"))
    assert collect.message_commit("2026-11-21", offres, offres).startswith(
        "data: 3 nouvelles offres tech le 2026-11-21"
    )
    assert "aucune nouvelle offre" in collect.message_commit("2026-11-21", [], offres)


# --------------------------------------------------------------- Affichage

import affichage  # noqa: E402


def test_date_fr():
    assert affichage.date_fr("2026-11-30") == "30 novembre 2026"
    assert affichage.date_fr("2026-08-01") == "1er août 2026"


def test_delai():
    jour = date(2026, 11, 22)
    assert affichage.delai("2026-11-22", jour) == "dernier jour"
    assert affichage.delai("2026-11-23", jour) == "demain"
    assert affichage.delai("2026-11-30", jour) == "dans 8 jours"


def test_niveau_lisible():
    assert affichage.niveau_lisible("CON") == "Consultant"
    assert affichage.niveau_lisible("I-1") == "Stage"
    assert affichage.niveau_lisible("P-4") == "Professionnel (P-4)"


def test_affichage_groupe_par_pays():
    offres = un_careers.analyser((FIXTURES / "un_jobfeed.xml").read_text(encoding="utf-8"))
    texte = affichage.generer(offres, date(2026, 11, 22))
    assert "### 🇰🇪 Kenya (1)" in texte
    assert "17 décembre 2026 (dans 25 jours)" in texte


# ------------------------------------------------- Workday : gestion du 429

class _Reponse:
    def __init__(self, code, contenu=None):
        self.status_code, self._contenu, self.headers = code, contenu or {}, {"Retry-After": "0"}

    def raise_for_status(self):
        pass

    def json(self):
        return self._contenu


class _Session:
    def __init__(self, reponses):
        self.reponses = list(reponses)

    def request(self, *args, **kwargs):
        return self.reponses.pop(0)


def test_workday_reessaie_apres_429(monkeypatch):
    monkeypatch.setattr(workday, "PAUSE", 0)
    session = _Session([_Reponse(429), _Reponse(200, {"total": 1, "jobPostings": [{"title": "x"}]})])
    assert workday._requete(session, "POST", "https://exemple")["total"] == 1


def test_workday_abandonne_apres_trois_429(monkeypatch):
    import pytest
    monkeypatch.setattr(workday, "PAUSE", 0)
    session = _Session([_Reponse(429)] * 3)
    with pytest.raises(workday.TropDeRequetes):
        workday._requete(session, "POST", "https://exemple")
