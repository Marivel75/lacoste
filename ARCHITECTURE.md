# Architecture — Veille Rénovation Énergétique

> Version POC — Mai 2026  
> Stack cible : Python 3.12 · FastAPI · Streamlit · SQLite → PostgreSQL

---

## Objectif

Outil de veille hebdomadaire sur la rénovation énergétique, destiné à être mis à disposition de clients et en interne à OPTIMMO Énergies. Le POC vise une architecture proche des conditions réelles (API REST découplée, BDD relationnelle, frontend client de l'API).

**Cœur du produit : la newsletter hebdomadaire** — sélection automatique des 6 meilleurs articles par thématique NLP, nuage de mots thématique, envoi email HTML. Tout le reste (API, Streamlit) sert à piloter et visualiser cette production.

---

## Structure des dossiers

```
lacoste/
├── main.py                          # CLI : collect | serve | newsletter
├── requirements.txt
├── Makefile                         # run-api, run-front, collect, newsletter, migrate…
├── .env / .env.example
├── .gitignore
├── ARCHITECTURE.md                  # ce fichier
│
├── api/                             # Backend FastAPI
│   ├── main.py                      # Création de l'app + enregistrement des routers
│   ├── dependencies.py              # Injection de la session DB (get_db)
│   ├── routers/
│   │   ├── health.py                # GET  /health
│   │   ├── articles.py              # GET  /articles   GET  /articles/{id}
│   │   ├── weeks.py                 # GET  /weeks  (semaines disponibles)
│   │   ├── nlp.py                   # GET  /nlp/topics  /nlp/sentiment  /nlp/wordfreq  /nlp/timeline
│   │   ├── newsletter.py            # GET  /newsletter/preview   POST /newsletter/send
│   │   └── pipeline.py              # POST /pipeline/run  (déclenchement manuel)
│   └── schemas/
│       ├── article.py               # ArticleOut, ArticleList
│       ├── nlp.py                   # TopicsOut, SentimentOut, WordFreqOut
│       ├── newsletter.py            # NewsletterPreviewOut, NewsletterSendIn
│       └── pipeline.py              # PipelineRunIn, PipelineRunOut
│
├── frontend/                        # Frontend Streamlit (client pur de l'API)
│   ├── app.py                       # Point d'entrée + navigation
│   ├── api_client.py                # Client HTTP (httpx) vers l'API
│   ├── config.py                    # URL API, valeurs par défaut
│   └── pages/
│       ├── 1_articles.py            # Liste des articles (filtres, recherche, pagination)
│       ├── 2_nlp_dashboard.py       # Dashboards NLP (thématiques, sentiments, nuage de mots)
│       └── 3_newsletter.py          # Prévisualisation + envoi de la newsletter
│
├── src/                             # Logique métier
│   ├── config.py                    # Chargement .env + YAML
│   ├── db/
│   │   ├── session.py               # Engine SQLAlchemy + SessionLocal
│   │   └── init_db.py               # create_all() — idempotent
│   ├── models/
│   │   ├── article.py               # Table articles
│   │   ├── collection_run.py        # Table collection_runs (traçabilité)
│   │   ├── newsletter_pick.py       # Table newsletter_picks (curation manuelle)
│   │   └── newsletter_log.py        # Table newsletter_logs (historique d'envois)
│   ├── pipeline/
│   │   ├── fetcher.py               # Récupération RSS (feedparser)
│   │   ├── filter.py                # Scoring par mots-clés
│   │   ├── nlp.py                   # Analyse NLP (topics, sentiment, fréquences)
│   │   └── pipeline.py              # Orchestrateur (fetch → filter → NLP → save DB)
│   └── services/
│       ├── article_service.py       # CRUD articles (lecture + déduplication par URL)
│       ├── nlp_service.py           # Agrégations NLP pour l'API
│       └── newsletter_service.py    # Sélection des articles + rendu HTML + envoi SMTP
│
├── config/
│   ├── keywords.yml                 # 38 mots-clés pondérés
│   └── sources.yml                  # 14 sources RSS
│
├── data/                            # Fichiers CSV legacy (conservés en backup)
│   └── .gitkeep
│
└── .github/
    └── workflows/
        └── weekly.yml               # GitHub Actions — lundi 9h Paris
```

---

## Modèle de données

### Table `articles`

| Colonne | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `url` | TEXT UNIQUE | URL canonique (clé de déduplication) |
| `title` | TEXT | Titre de l'article |
| `source_name` | TEXT | Nom de la source (ex : ADEME) |
| `source_category` | TEXT | Catégorie source (Institution, Presse, DPE…) |
| `published_at` | DATETIME | Date de publication |
| `summary` | TEXT | Résumé (500 cars max) |
| `score` | INTEGER | Score mots-clés (titre ×2) |
| `keywords` | JSON | Mots-clés détectés (liste) |
| `nlp_keywords` | JSON | Mots-clés NLP extraits (TF-IDF) |
| `topics` | JSON | Thématiques NLP détectées (liste) |
| `sentiment_score` | FLOAT | Score de sentiment VADER (−1 à +1) |
| `sentiment_label` | TEXT | `positive` / `neutral` / `negative` |
| `collection_week` | TEXT | Semaine ISO (ex : `2026-W20`) |
| `collected_at` | DATETIME | Horodatage de la collecte |

### Table `collection_runs`

| Colonne | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `week` | TEXT | Semaine ISO |
| `run_at` | DATETIME | Heure de déclenchement |
| `articles_fetched` | INTEGER | Articles récupérés (brut) |
| `articles_new` | INTEGER | Articles nouveaux (après dédup) |
| `status` | TEXT | `success` / `error` |
| `error_message` | TEXT \| NULL | Message d'erreur éventuel |

### Table `newsletter_picks`

| Colonne | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `week` | TEXT | Semaine ISO |
| `article_id` | INTEGER FK → articles.id | Article concerné |
| `action` | TEXT | `pin` (forcer l'inclusion) / `exclude` (forcer l'exclusion) |
| `created_at` | DATETIME | Horodatage de la curation |

### Table `newsletter_logs`

| Colonne | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `week` | TEXT | Semaine ISO |
| `sent_at` | DATETIME | Heure d'envoi |
| `recipients` | JSON | Liste des destinataires |
| `articles_count` | INTEGER | Nombre d'articles inclus |
| `status` | TEXT | `sent` / `error` |
| `error_message` | TEXT \| NULL | Message d'erreur éventuel |

---

## Newsletter & Streamlit — deux faces du même outil

Les deux produits partagent les mêmes données, le même NLP, la même sélection. Streamlit est la **salle de rédaction** ; la newsletter est **l'édition publiée**.

```
┌────────────────────────────────┐         ┌────────────────────────────┐
│       Streamlit                │         │      Newsletter email      │
│  "la salle de rédaction"       │ ◀──────▶│  "l'édition publiée"       │
│                                │  même   │                            │
│  • explore les articles        │  data   │  • 6 articles / thème      │
│  • voit les stats NLP          │         │  • nuage de mots thématique │
│  • cures la sélection          │         │  • lien "rapport complet"  │
│  • prévisualise l'email        │         │    → Streamlit             │
│  • déclenche l'envoi           │         │                            │
└────────────────────────────────┘         └────────────────────────────┘
```

### Ce qui circule dans les deux sens

| Direction | Mécanisme |
|---|---|
| Streamlit → Newsletter | La page 3 prévisualise le HTML exact de l'email ; tout changement de sélection se reflète immédiatement |
| Newsletter → Streamlit | Chaque article de la newsletter contient un lien "Voir le rapport complet" pointant vers le dashboard Streamlit filtré sur la même semaine |
| Streamlit → Newsletter | Un article épinglé (pinned) dans Streamlit est prioritaire dans la sélection newsletter |
| Newsletter → Streamlit | Les articles inclus dans la newsletter sont badgés dans le tableau Streamlit (`✉ W20`) |

### Curation dans Streamlit (page Newsletter)

- **Sélection automatique** : top 6 par thématique, score décroissant (par défaut)
- **Override manuel** : l'utilisateur peut épingler / exclure un article — le choix est persisté dans `newsletter_picks`
- **Prévisualisation** : rendu HTML de l'email dans la page (`st.components.html`)
- **Envoi** : bouton → `POST /newsletter/send` → réponse 202 + envoi en background
- **Historique** : tableau des `newsletter_logs` (semaine, nb articles, destinataires, statut)

### Logique de sélection (`newsletter_service.py`)

1. Charger les picks manuels depuis `newsletter_picks` pour la semaine cible
2. Récupérer tous les articles de la semaine (score ≥ min_score)
3. Regrouper par **thématique NLP** — 6 thèmes :
   `aides_financières` · `dpe_audit` · `réglementation` · `rénovation_geste` · `marché_immobilier` · `études_données`
4. Dans chaque thématique : picks manuels en tête, puis compléter jusqu'à 6 par score
5. Calculer le **nuage de mots thématique** (corpus du thème uniquement)
6. Calculer le **nuage de mots global** (tous articles, top 28 termes)
7. Assembler le HTML et envoyer via SMTP (Gmail SSL)

> **Regroupement par topic NLP, non par catégorie source** — un article Batiactu sur les aides apparaît dans `aides_financières`, pas "Presse".

### Structure du HTML email

```
┌──────────────────────────────────────────────────────┐
│  Veille Rénovation Énergétique — W20 (2026)          │
│  42 articles · collecte du 13/05 au 19/05            │
│                                                      │
│  ▸ Tendances de la semaine (nuage de mots global)    │
│                                                      │
│  ▸ Aides financières     [nuage thématique]          │
│    [article 1] source · titre · score · badges       │
│    ...jusqu'à 6 · "+ X articles — rapport complet →" │
│                                                      │
│  ▸ DPE & audit           [nuage thématique]          │
│    ...                                               │
│                                                      │
│  [4 autres thématiques...]                           │
│                                                      │
│  → Voir le rapport complet  [lien Streamlit]         │
└──────────────────────────────────────────────────────┘
```

Chaque article : source · titre (lien) · mots-clés matchés · badges topics · badge sentiment (▲/▼/● + score).

---

## API REST

Base URL : `http://localhost:8000`

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/health` | Santé de l'API |
| GET | `/weeks` | Liste des semaines disponibles en base |
| GET | `/articles` | Liste paginée — params : `week`, `source`, `topic`, `min_score`, `search`, `page`, `limit` |
| GET | `/articles/{id}` | Détail d'un article |
| GET | `/nlp/topics` | Nb d'articles par thématique — param : `week` |
| GET | `/nlp/sentiment` | Distribution des sentiments — param : `week` |
| GET | `/nlp/wordfreq` | Top 30 mots-clés global — param : `week` |
| GET | `/nlp/wordfreq/{topic}` | Top 20 mots-clés pour un thème donné — param : `week` |
| GET | `/nlp/timeline` | Évolution hebdomadaire — param : `weeks` |
| GET | `/newsletter/preview` | HTML de la newsletter — param : `week` |
| GET | `/newsletter/picks` | Curation manuelle de la semaine — param : `week` |
| POST | `/newsletter/picks` | Épingle ou exclut un article — body : `week`, `article_id`, `action` |
| DELETE | `/newsletter/picks/{id}` | Supprime un override de curation |
| POST | `/newsletter/send` | Envoie la newsletter (background task) — body : `week`, `recipients` |
| POST | `/pipeline/run` | Déclenche la collecte (background task) — body : `days`, `min_score` |

---

## Frontend Streamlit

Le Streamlit est un **client pur** de l'API : aucun accès direct à la base, toutes les données passent par les endpoints.

### Page 1 — Articles

- Sélecteur de semaine de collecte
- Filtres : source, thématique NLP, score minimum, recherche textuelle
- Tableau paginé (titre cliquable, source, date, score, topics, sentiment)
- Export CSV de la sélection courante

### Page 2 — Dashboard NLP

- Sélecteur de semaine (ou comparaison N semaines)
- Barres : articles par thématique
- Barres empilées : distribution des sentiments par thématique
- Nuage de mots global (top 30)
- Nuage de mots par thématique (sélectable)
- Courbe : évolution du volume sur N semaines
- Tableau : top sources par volume

### Page 3 — Newsletter

- Sélecteur de semaine
- Prévisualisation du HTML email (rendu `st.components.html`)
- Bouton **Envoyer** → `POST /newsletter/send` (destinataires configurés dans `.env`)
- Historique des envois (table `newsletter_logs`)

---

## Stack technique

| Couche | Technologie | Version |
|---|---|---|
| Language | Python | 3.12 |
| API | FastAPI + uvicorn | ≥ 0.115 |
| Schemas | Pydantic v2 | ≥ 2.0 |
| ORM | SQLAlchemy | ≥ 2.0 |
| Migrations | Alembic | ≥ 1.13 |
| Base de données | SQLite (POC) → PostgreSQL (prod) | — |
| Frontend | Streamlit | ≥ 1.40 |
| Graphiques | Plotly | ≥ 5.18 |
| Client HTTP | httpx | ≥ 0.27 |
| RSS | feedparser | ≥ 6.0 |
| NLP | scikit-learn (TF-IDF) + VADER | — |
| Email | smtplib (Gmail SSL) | stdlib |
| Config | python-dotenv + PyYAML | — |
| Automatisation | GitHub Actions | — |
| Tests | pytest + httpx | — |

---

## Flux de données

```
GitHub Actions (lundi 9h)
        │
        ▼
  main.py collect
        │
        ▼
  VeillePipeline
  ┌──────────────────────────────────────────┐
  │  fetcher.py    → flux RSS (14 sources)   │
  │  filter.py     → scoring mots-clés       │
  │  nlp.py        → topics + sentiment      │
  │  article_service → INSERT (dédup URL)    │
  └─────────────────┬────────────────────────┘
                    │
                    ▼
             SQLite / PostgreSQL
             ┌──────────────────────┐
             │  articles            │
             │  collection_runs     │
             │  newsletter_logs     │
             └──────────┬───────────┘
                        │
          ┌─────────────┴──────────────┐
          │                            │
          ▼                            ▼
    FastAPI (port 8000)       newsletter_service
          │                   (sélection + HTML)
          ▼                            │
   Streamlit (port 8501)               ▼
   ┌──────────────────────┐     Email SMTP (Gmail)
   │  Page 1 : Articles   │     → destinataires
   │  Page 2 : Dashboard  │
   │  Page 3 : Newsletter │──── preview + envoi
   └──────────────────────┘
```

---

## Commandes de développement (Makefile)

```bash
make install        # pip install -r requirements.txt
make migrate        # alembic upgrade head
make collect        # python main.py collect
make newsletter     # python main.py newsletter  (génère + envoie)
make api            # uvicorn api.main:app --reload --port 8000
make front          # streamlit run frontend/app.py --server.port 8501
make dev            # api + front en parallèle
make test           # pytest
```

---

## Roadmap

### Phase 1 — POC (objectif : juin 2026)

- [ ] Restructuration des dossiers (nouvelle arbo)
- [ ] Modèle SQLAlchemy (`Article`, `CollectionRun`, `NewsletterLog`) + Alembic
- [ ] Migration du pipeline : écriture en base (+ déduplication par URL)
- [ ] `newsletter_service.py` : sélection top-6/topic + nuage thématique + HTML
- [ ] FastAPI : 6 routers (health, articles, weeks, nlp, newsletter, pipeline)
- [ ] Streamlit : 3 pages (articles, dashboard NLP, newsletter)
- [ ] Makefile avec toutes les commandes dev
- [ ] Tests unitaires API (pytest + httpx)
- [ ] README mis à jour

### Phase 2 — Mise en production (objectif : juillet–août 2026)

- [ ] Migration SQLite → PostgreSQL (Alembic + psycopg2)
- [ ] Dockerisation (docker-compose : api + frontend + postgres)
- [ ] Authentification API (API key par client)
- [ ] Déploiement (VPS / Render / Railway)
- [ ] Destinataires newsletter configurables par client (multi-tenant basique)
- [ ] Déclenchement newsletter automatique post-collecte (GitHub Actions)

### Phase 3 — Extensions

- [ ] Sources personnalisables par client (UI d'admin)
- [ ] Résumé IA de la semaine (Claude API) intégré dans la newsletter
- [ ] Export PDF du rapport hebdomadaire
- [ ] Notifications push / webhook
- [ ] Dashboard comparatif multi-semaines
- [ ] Accès mobile (Streamlit responsive ou migration React)

---

## Suggestions

### Techniques

1. **Alembic dès le départ** — indispensable pour la migration SQLite → PostgreSQL sans douleur.

2. **Déduplication par URL en base** — plus fiable que le check Notion. L'index UNIQUE sur `url` garantit l'idempotence.

3. **`POST /newsletter/send` et `/pipeline/run` en background** — les deux opérations durent 30–60 s. Utiliser `BackgroundTasks` FastAPI pour répondre immédiatement (202 Accepted) et exécuter en arrière-plan.

4. **`newsletter_logs` pour la traçabilité** — évite les doubles envois, permet de voir dans Streamlit l'historique des newsletters envoyées.

5. **Nuage de mots thématique calculé à la volée** — pas besoin de le stocker : il se recalcule sur les articles de la thématique en base (rapide, toujours cohérent avec un re-filtrage).

### Produit

6. **Regroupement par topic NLP, pas par catégorie source** — un article Batiactu sur les aides doit apparaître dans "Aides financières", pas dans "Presse". Le NLP fait ce travail bien mieux que la catégorie de la source.

7. **Score de chaleur par thématique** — mettre en évidence les thèmes en progression (`+40% vs semaine passée`) est plus utile pour un client qu'un simple volume.

8. **Résumé IA (Phase 3)** — un brief 3–5 lignes généré par Claude API sur les tendances de la semaine, intégré en tête de newsletter, est la fonctionnalité à plus fort impact perçu pour un client final.
