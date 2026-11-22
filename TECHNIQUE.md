# Fonctionnement technique du projet

Collecte automatique, chaque matin, des offres d'emploi dans les métiers de la tech (ICT, data, développement, GIS, systèmes d'information, statistiques) publiées en Afrique par les organisations internationales et panafricaines.

## Sources

| Organisation | Source | Accès |
|---|---|---|
| ONU (Secrétariat : CEA, PNUE, ONU-Habitat, OCHA, missions de paix...) | [careers.un.org](https://careers.un.org) | Flux RSS public |
| UNESCO | [careers.unesco.org](https://careers.unesco.org) | Sitemap public et fiches des offres |
| Union africaine | [jobs.au.int](https://jobs.au.int) | Sitemap public et fiches des offres |
| Banque africaine de développement | [afdb.org](https://www.afdb.org/en/about-careers/current-vacancies) | Pages des postes et des consultances |

Chaque source est indépendante : si l'une est en panne, les autres continuent d'alimenter le dépôt. La collecte respecte le robots.txt de chaque site et marque une pause entre les requêtes.

Organisations non couvertes : le HCR (son site refuse les requêtes venant de GitHub Actions), l'UNICEF (son robots.txt exclut la recherche automatisée), l'OMS (ses flux RSS n'indiquent pas le lieu du poste).

## Fonctionnement

1. Chaque jour, un GitHub Action lance `src/collect.py`.
2. Le script garde les offres situées dans un pays africain (d'après le lieu d'affectation) et dont le titre ou la famille de métier relève de la tech.
3. Il ajoute les nouvelles offres à l'historique, met à jour les statistiques du jour et réécrit le README (la page destinée aux candidats).
4. Il commite le résultat avec un message qui résume la journée.

## Structure

```
src/
├── collect.py          # orchestration : collecte, fusion, statistiques
├── affichage.py        # page README destinée aux candidats
├── filtres.py          # pays et villes africaines, mots-clés tech
└── sources/
    ├── un_careers.py      # flux RSS de l'ONU
    ├── successfactors.py  # UNESCO et Union africaine
    ├── afdb.py            # Banque africaine de développement
    ├── tableaux_html.py   # lecture des tableaux d'offres en HTML
    └── workday.py         # sites carrières Workday (désactivé)
data/
├── offres.csv              # historique de toutes les offres vues
└── stats_journalieres.csv  # une ligne par jour
```

## Lancer en local

```bash
pip install -r requirements.txt
python src/collect.py
```

Le script réécrit `README.md` en entier à chaque collecte : c'est la page destinée aux candidats. Pour changer sa présentation, modifier `src/affichage.py`, pas le README.

Tests :

```bash
pip install pytest
pytest
```

## Données

Les offres appartiennent aux organisations qui les publient. Ce dépôt ne garde que les métadonnées (titre, organisation, lieu, niveau, dates, lien) et renvoie vers le site d'origine pour le détail et la candidature.
