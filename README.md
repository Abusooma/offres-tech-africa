# Offres tech en Afrique dans les organisations internationales

Collecte automatique, chaque matin, des offres d'emploi dans les métiers de la tech (ICT, data, développement, GIS, systèmes d'information, statistiques) publiées en Afrique par les organisations internationales.

## Sources

| Source | Organisations couvertes | Accès |
|---|---|---|
| [careers.un.org](https://careers.un.org) | Secrétariat de l'ONU : CEA, PNUE, ONU-Habitat, OCHA, missions de paix, bureaux de Nairobi et Addis-Abeba... | Flux RSS public `careers.un.org/jobfeed` |
| [Carrières HCR](https://unhcr.wd3.myworkdayjobs.com/External) | HCR (UNHCR) | API JSON du site carrière Workday |

Chaque source est indépendante : si l'une est en panne, les autres continuent d'alimenter le dépôt.

## Fonctionnement

1. Chaque jour, un GitHub Action lance `src/collect.py`.
2. Le script garde les offres situées dans un pays africain (d'après le lieu d'affectation) et dont le titre ou la famille de métier relève de la tech.
3. Il ajoute les nouvelles offres à l'historique, met à jour les statistiques du jour et la liste ci-dessous.
4. Il commite le résultat avec un message qui résume la journée.

## Structure

```
src/
├── collect.py          # orchestration : collecte, fusion, statistiques, README
├── filtres.py          # pays et villes africaines, mots-clés tech
└── sources/
    ├── un_careers.py   # flux RSS de l'ONU
    └── workday.py      # sites carrières Workday (HCR)
data/
├── offres.csv              # historique de toutes les offres vues
└── stats_journalieres.csv  # une ligne par jour
```

## Lancer en local

```bash
pip install -r requirements.txt
python src/collect.py
```

Tests :

```bash
pip install pytest
pytest
```

## Offres ouvertes

<!-- OFFRES:DEBUT -->
_La liste apparaîtra après la première collecte._
<!-- OFFRES:FIN -->

## Données

Les offres appartiennent aux organisations qui les publient. Ce dépôt ne garde que les métadonnées (titre, organisation, lieu, niveau, dates, lien) et renvoie vers le site d'origine pour le détail et la candidature.
