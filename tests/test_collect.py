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


def test_deuxieme_collecte_du_jour_garde_les_nouvelles():
    offres = un_careers.analyser((FIXTURES / "un_jobfeed.xml").read_text(encoding="utf-8"))
    toutes, _ = collect.fusionner({}, offres, "2026-11-23")
    toutes, nouvelles = collect.fusionner(toutes, offres, "2026-11-23")
    assert nouvelles == []
    assert len(collect.nouvelles_du_jour(toutes, "2026-11-23")) == 3
    assert collect.nouvelles_du_jour(toutes, "2026-11-24") == []


def _offre(id_, source, derniere_vue, cloture=""):
    return {"id": id_, "source": source, "derniere_vue": derniere_vue, "date_cloture": cloture}


def test_source_en_panne_garde_ses_offres_recentes():
    toutes = {o["id"]: o for o in [
        _offre("onu-vue", "careers.un.org", "2026-11-23"),
        _offre("bad-hier", "afdb.org", "2026-11-22"),
        _offre("bad-rss", "afdb.org (RSS)", "2026-11-20"),
        _offre("bad-ancienne", "afdb.org", "2026-11-10"),
        _offre("bad-close", "afdb.org", "2026-11-22", cloture="2026-11-21"),
        _offre("onu-disparue", "careers.un.org", "2026-11-22"),
    ]}
    ids = {o["id"] for o in collect.offres_affichees(toutes, date(2026, 11, 23), ["Banque africaine de développement"])}
    assert ids == {"onu-vue", "bad-hier", "bad-rss"}


def test_sans_panne_seules_les_offres_du_jour():
    toutes = {"bad-hier": _offre("bad-hier", "afdb.org", "2026-11-22")}
    assert collect.offres_affichees(toutes, date(2026, 11, 23), []) == []


def test_chaque_source_a_ses_origines():
    assert set(collect.ORIGINES) == set(collect.SOURCES)


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
    assert "### Kenya" in texte
    assert "17 déc. 2026, dans 25 jours" in texte
    assert '<a name="kenya"></a>' in texte and "(#kenya)" in texte


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


# ------------------------------------------------- UNESCO / UA (SuccessFactors)

from sources import afdb, successfactors  # noqa: E402
from sources.tableaux_html import lire_date, lire_tableau  # noqa: E402


def test_lire_date():
    assert lire_date("21 Nov 2026") == "2026-11-21"
    assert lire_date("9/12/2026") == "2026-12-09"
    assert lire_date("16-Nov-2026") == "2026-11-16"
    assert lire_date("bientôt") == ""


def test_sitemap_et_tri_sur_le_titre():
    liens, sous = successfactors.lire_sitemap((FIXTURES / "au_sitemap.xml").read_text(encoding="utf-8"))
    assert len(liens) == 3 and sous == []
    assert successfactors.titre_depuis_lien(liens[1]) == "Addis Ababa Senior ICT Officer (MIS)"
    candidats = [l for l in liens if filtres.est_tech(successfactors.titre_depuis_lien(l))]
    assert len(candidats) == 2  # le poste de comptable n'est pas ouvert


def test_fiche_union_africaine():
    site = successfactors.SITES[1]
    lien = "https://jobs.au.int/job/Addis-Ababa-Senior-ICT-Officer-%28MIS%29/1377900001/"
    offre = successfactors.analyser_fiche(site, lien, (FIXTURES / "au_fiche.html").read_text(encoding="utf-8"))
    assert offre["id"] == "ua-1377900001"
    assert offre["titre"] == "Senior ICT Officer (MIS)"
    assert offre["pays"] == "Éthiopie"
    assert offre["ville"] == "Addis Ababa"
    assert offre["niveau"] == "P3"
    assert offre["date_publication"] == "2026-11-18"
    assert offre["date_cloture"] == "2026-12-01"


def test_fiche_unesco():
    site = successfactors.SITES[0]
    lien = "https://careers.unesco.org/job/Dakar-Information-Management-Officer/1379000001/"
    offre = successfactors.analyser_fiche(site, lien, (FIXTURES / "unesco_fiche.html").read_text(encoding="utf-8"))
    assert offre["titre"] == "Information Management Officer"
    assert offre["pays"] == "Sénégal"
    assert offre["ville"] == "Dakar"
    assert offre["niveau"] == "P-2"
    assert offre["date_cloture"] == "2026-12-09"  # 09/12/26 = jour/mois


# ------------------------------------------------------------------- BAD

def test_afdb_postes():
    url = afdb.PAGES[0]
    lignes = lire_tableau((FIXTURES / "afdb_vacancies.html").read_text(encoding="utf-8"), url)
    offres = [o for o in map(afdb.analyser_ligne, lignes) if o]
    assert [o["titre"] for o in offres] == ["IT Systems and Web Specialist"]
    assert offres[0]["pays"] == "Côte d'Ivoire"
    assert offres[0]["niveau"] == "PL5"
    assert offres[0]["date_cloture"] == "2026-12-06"
    assert offres[0]["url"] == "https://www.afdb.org/en/vacancy/it-systems-and-web-specialist-98700"


def test_afdb_consultances_sans_lieu_et_sans_cabinets():
    url = afdb.PAGES[1]
    lignes = lire_tableau((FIXTURES / "afdb_consultants.html").read_text(encoding="utf-8"), url)
    offres = [o for o in map(afdb.analyser_ligne, lignes) if o]
    assert len(offres) == 1  # cabinet exclu, Research Analyst pas tech
    assert offres[0]["id"] == "afdb-98776"
    assert offres[0]["pays"] == ""
    assert offres[0]["niveau"] == "Individual Consultant"


def test_affichage_lieu_non_precise_en_dernier():
    offres = [
        {"titre": "A", "url": "u", "organisation": "BAD", "ville": "", "pays": "", "niveau": "", "date_cloture": ""},
        {"titre": "B", "url": "u", "organisation": "ONU", "ville": "Nairobi", "pays": "Kenya", "niveau": "", "date_cloture": ""},
    ]
    texte = affichage.generer(offres, date(2026, 11, 22))
    assert texte.index("Kenya") < texte.index("Lieu non précisé")
    assert "### Lieu non précisé" in texte
    assert "· 1 pays ·" in texte


# -------------------------------------------------------------- Graphiques

def test_affichage_signale_une_source_indisponible():
    texte = affichage.generer([], date(2026, 11, 23), indisponibles=["Banque africaine de développement"])
    assert "Source indisponible aujourd'hui : Banque africaine de développement." in texte
    assert "indisponible" not in affichage.generer([], date(2026, 11, 23))


def test_graphiques_mermaid():
    offres = un_careers.analyser((FIXTURES / "un_jobfeed.xml").read_text(encoding="utf-8"))
    stats = [
        {"date": "2026-11-21", "offres_ouvertes": "2", "nouvelles_offres": "2"},
        {"date": "2026-11-22", "offres_ouvertes": "3", "nouvelles_offres": "1"},
    ]
    texte = affichage.generer(offres, date(2026, 11, 22), stats)
    assert texte.count("```mermaid") == 3
    assert '"Côte d\'Ivoire"' in texte
    assert 'x-axis ["21/11", "22/11"]' in texte
    assert "line [2, 3]" in texte


def test_pas_de_courbe_avec_un_seul_jour():
    offres = un_careers.analyser((FIXTURES / "un_jobfeed.xml").read_text(encoding="utf-8"))
    texte = affichage.generer(offres, date(2026, 11, 22), [{"date": "2026-11-22", "offres_ouvertes": "3", "nouvelles_offres": "3"}])
    assert texte.count("```mermaid") == 2



def test_sitemap_autres_formats():
    # Préfixe d'espace de noms, entités HTML, sitemap d'index.
    xml = (
        '<ns0:urlset xmlns:ns0="x"><ns0:url><ns0:loc>https://a.org/job/Dakar-Data-Officer/12/</ns0:loc></ns0:url>'
        '<ns0:url><ns0:loc> https://a.org/job/Rabat-IT-Lead/13/?x=1&amp;y=2 </ns0:loc></ns0:url></ns0:urlset>'
    )
    liens, _ = successfactors.lire_sitemap(xml)
    assert liens == ["https://a.org/job/Dakar-Data-Officer/12/", "https://a.org/job/Rabat-IT-Lead/13/?x=1&y=2"]
    index = "<sitemapindex><sitemap><loc>https://a.org/sitemap_jobs_1.xml</loc></sitemap></sitemapindex>"
    assert successfactors.lire_sitemap(index) == ([], ["https://a.org/sitemap_jobs_1.xml"])


def test_afdb_rss():
    xml = """<rss><channel>
      <item><title>IT Systems and Web Specialist</title>
        <link>https://www.afdb.org/en/vacancy/it-systems-and-web-specialist-98700</link>
        <pubDate>Mon, 16 Nov 2026 10:00:00 +0000</pubDate></item>
      <item><title>Chief Program Officer, PSF</title>
        <link>https://www.afdb.org/en/vacancy/chief-program-officer-psf-98650</link>
        <pubDate>Mon, 16 Nov 2026 10:00:00 +0000</pubDate></item>
    </channel></rss>"""
    offres = afdb.analyser_rss(xml)
    assert [o["id"] for o in offres] == ["afdb-98700"]
    assert offres[0]["date_publication"] == "2026-11-16"
    assert offres[0]["pays"] == ""
