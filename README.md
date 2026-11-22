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
_Mis à jour le 2026-11-22 : 7 offres ouvertes, 5 organisations, 3 pays._

| Poste | Organisation | Lieu | Niveau | Clôture |
|---|---|---|---|---|
| [ACS/Data Innovation and Analytics](https://careers.un.org/jobSearchDescription/287673?language=en) | CEA | Addis Ababa, Éthiopie | CON | 2026-11-23 |
| [Programme Officer (Migrant Smuggling and Cybercrime Investigation) - temporary](https://careers.un.org/jobSearchDescription/287979?language=en) | ONUDC | Rabat, Maroc | P-3 | 2026-11-23 |
| [Intern - Data analytics](https://careers.un.org/jobSearchDescription/287931?language=en) | ONU-Habitat | Nairobi, Kenya | I-1 | 2026-11-25 |
| [Information Systems  Intern](https://careers.un.org/jobSearchDescription/288738?language=en) | PNUE | Nairobi, Kenya | I-1 | 2026-11-28 |
| [Senior Consultant: Scientific Assessment and Expert Group Coordination on the Environmental Sustainability of Artificial Intelligence](https://careers.un.org/jobSearchDescription/288720?language=en) | PNUE | Nairobi, Kenya | CON | 2026-11-30 |
| [Software Application Developer](https://careers.un.org/jobSearchDescription/288576?language=en) | PNUE | Nairobi, Kenya | CON | 2026-11-30 |
| [DIGITAL FORENSIC INVESTIGATOR](https://careers.un.org/jobSearchDescription/282126?language=en) | Office of Internal Oversight Services | Nairobi, Kenya | P-4 | 2026-12-12 |
<!-- OFFRES:FIN -->

## Données

Les offres appartiennent aux organisations qui les publient. Ce dépôt ne garde que les métadonnées (titre, organisation, lieu, niveau, dates, lien) et renvoie vers le site d'origine pour le détail et la candidature.
