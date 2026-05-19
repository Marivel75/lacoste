# Guide de contribution — Lacoste

> Veille Rénovation Énergétique · OPTIMMO Énergies

---

## Branches

```
main          production — stable, déployée
dev           intégration — cible de toutes les features
feature/*     développement — une branche par fonctionnalité
```

**Règle simple :** on ne touche jamais `main` ni `dev` directement. Tout passe par une PR.

---

## Installer l'environnement

```bash
git clone https://github.com/Marivel75/lacoste.git
cd lacoste

conda create -n lacoste python=3.12 -y
conda activate lacoste
pip install -r requirements.txt
pip install ruff

cp .env.example .env
# Remplir .env avec les credentials (voir équipe)
```

---

## Démarrer une feature

```bash
# Toujours partir de dev à jour
git checkout dev
git pull

# Créer la branche
git checkout -b feature/nom-explicite

# Exemple : feature/api-articles, feature/nlp-dashboard, feature/newsletter-service
```

Nommage des branches : `feature/` pour les nouvelles fonctionnalités, `fix/` pour les corrections, `chore/` pour la maintenance.

---

## Travailler et soumettre

```bash
# Développer, tester localement
conda activate lacoste
pytest                        # tous les tests doivent passer
ruff check src/ tests/        # 0 erreur de lint

# Commiter
git add <fichiers>
git commit -m "feat: description courte de ce qui change"

# Pousser
git push -u origin feature/nom-explicite
```

Créer ensuite une **Pull Request vers `dev`** sur GitHub. La CI se déclenche automatiquement.

---

## Conventions de commit

Format : `type: description courte`

| Type | Usage |
|---|---|
| `feat` | Nouvelle fonctionnalité |
| `fix` | Correction de bug |
| `test` | Ajout ou modification de tests |
| `refactor` | Refactoring sans changement de comportement |
| `chore` | Maintenance, dépendances, config |
| `docs` | Documentation uniquement |

---

## CI/CD

Chaque push et chaque PR déclenche la CI (`.github/workflows/ci.yml`) :

1. **Lint** — `ruff check src/ tests/` — 0 erreur autorisée
2. **Tests** — `pytest` — 100% des tests doivent passer

Une PR ne peut pas être mergée si la CI est rouge.

---

## Flux complet

```
feature/ma-feature
    │
    │  git push → PR vers dev → CI verte → merge
    ▼
  dev
    │
    │  PR vers main → CI verte → merge (release)
    ▼
  main  ←  production
```

---

## À faire en rejoignant le projet

- [ ] Lire `ARCHITECTURE.md` — vue complète du projet, stack, modèle de données, API, roadmap
- [ ] Demander les credentials `.env` à l'équipe (Notion token, Gmail SMTP, DB URL)
- [ ] Vérifier que `pytest` passe en local avant le premier commit
- [ ] Demander à être ajouté comme reviewer sur GitHub (Settings → Collaborators)

---

## Note pour le lead dev

Quand un second développeur régulier rejoint le projet, activer la revue obligatoire :

```bash
# Passer required_approving_review_count à 1 sur main et dev
gh api repos/Marivel75/lacoste/branches/main/protection \
  --method PUT --input protection-main.json
```

Ou directement dans GitHub : Settings → Branches → Edit protection rule → "Require approvals: 1".
