# Veille Rénovation Énergétique

Outil de veille hebdomadaire sur la rénovation énergétique et le DPE. Agrège les actualités de 14 sources (Google News, ADEME, France Rénov, ANAH, presse sectorielle…), filtre par mots-clés, et publie les résultats dans une base Notion.

---

## Fonctionnement

1. **Collecte** — récupère les flux RSS de toutes les sources configurées
2. **Filtrage** — score chaque article selon les mots-clés (`config/keywords.yml`)
3. **Déduplication** — vérifie les URLs déjà présentes dans Notion
4. **Publication** — crée une fiche Notion par nouvel article

Exécution automatique chaque **lundi à 9h** via GitHub Actions, ou à la demande.

---

## Installation

```bash
git clone <url-du-repo>
cd veille-renovation
pip install -r requirements.txt
cp .env.example .env
```

Remplis `.env` avec tes credentials Notion :

```env
NOTION_TOKEN=secret_xxxx
NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Utilisation

### Créer la base Notion (première fois uniquement)

Si tu n'as pas encore de base de données Notion, l'outil peut la créer automatiquement dans une page existante :

```bash
python -m src.main setup --page-id <ID_PAGE_NOTION>
```

L'ID de page se trouve dans l'URL Notion : `notion.so/MonEspace/**abc123...**`

Le script affiche l'ID de la base créée à coller dans `.env`.

### Lancer la veille

```bash
# Collecte des 7 derniers jours (défaut)
python -m src.main run

# Collecte sur 14 jours
python -m src.main run --days 14

# Score minimum plus élevé (articles très pertinents uniquement)
python -m src.main run --min-score 3
```

---

## Base Notion

Chaque article est publié avec les propriétés suivantes :

| Propriété | Type | Description |
|---|---|---|
| Titre | Titre | Intitulé de l'article |
| Source | Sélection | Nom de la source (ex : ADEME, Batiactu) |
| Catégorie | Sélection | Actualité, Étude/Rapport, Réglementation, Aide, Institution, Presse |
| Date de publication | Date | Date de parution |
| URL | URL | Lien vers l'article |
| Résumé | Texte | Extrait (500 caractères max) |
| Mots-clés | Multi-sélection | Mots-clés détectés dans l'article |
| Score | Nombre | Pertinence (mots-clés en titre = ×2) |
| Statut | Sélection | À lire / Lu / Archivé |
| Semaine de collecte | Date | Date de la collecte |

---

## Automatisation (GitHub Actions)

Le workflow [`.github/workflows/weekly.yml`](.github/workflows/weekly.yml) tourne automatiquement chaque lundi à 9h (Paris, heure d'été).

**Configuration des secrets GitHub** (Settings → Secrets and variables → Actions) :

| Secret | Valeur |
|---|---|
| `NOTION_TOKEN` | Token d'intégration Notion |
| `NOTION_DATABASE_ID` | ID de la base de données cible |

Le workflow peut aussi être déclenché manuellement depuis l'onglet Actions avec des paramètres personnalisés (nombre de jours, score minimum).

---

## Configuration

### Mots-clés — `config/keywords.yml`

38 termes couvrant : DPE, rénovation thermique, aides (MaPrimeRénov, CEE, éco-PTZ), normes (BBC, RE2020), acteurs (ADEME, ANAH, France Rénov).

Ajouter un mot-clé :

```yaml
keywords:
  - "mon nouveau terme"
```

### Sources — `config/sources.yml`

14 sources préconfigurées :

- **Google News RSS** — rénovation énergétique, DPE, MaPrimeRénov, passoires thermiques, ADEME
- **Presse sectorielle** — Batiactu, Le Moniteur, Effinergie
- **Institutions** — ADEME, ANAH, France Rénov, Ministère du Logement, Observatoire BBC

Ajouter une source RSS :

```yaml
sources:
  - name: "Ma nouvelle source"
    type: rss
    url: "https://example.com/feed.xml"
    category: "Presse"  # Actualité | Étude/Rapport | Réglementation | Aide | Institution | Presse
```

---

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `NOTION_TOKEN` | — | Token d'intégration Notion (obligatoire) |
| `NOTION_DATABASE_ID` | — | ID de la base de données cible (obligatoire) |
| `LOOKBACK_DAYS` | `7` | Fenêtre de collecte en jours |
| `MIN_SCORE` | `1` | Score minimum pour publier un article |
