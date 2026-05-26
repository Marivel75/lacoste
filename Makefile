.PHONY: install initdb collect newsletter veille api streamlit cron-install cron-remove test help

ENV            = lacoste
RUN            = conda run -n $(ENV)
PROJECT_DIR   := $(shell pwd)
SCRIPT         = $(PROJECT_DIR)/scripts/daily_newsletter.sh
LOG            = $(PROJECT_DIR)/logs/veille.log

# Destinataires supplémentaires passés directement en ligne de commande :
#   make newsletter emma@... gabriel@...
# Les cibles non reconnues (adresses email) sont capturées ici pour être transmises
# à python et silencées côté Make via la règle attrape-tout en fin de fichier.
_KNOWN        := install initdb collect newsletter newsletter-prod veille api streamlit cron-install cron-remove test help
_EXTRA_RCPT   := $(filter-out $(_KNOWN),$(MAKECMDGOALS))

help:
	@echo ""
	@echo "  make install            Créer l'env conda + installer les dépendances"
	@echo "  make initdb             Créer les tables en base"
	@echo "  make collect            Collecter les articles RSS (7 jours)"
	@echo "  make collect DAYS=14    Collecter sur N jours"
	@echo "  make newsletter                            Envoyer à EMAIL_RECIPIENTS (test — juste toi)"
	@echo "  make newsletter LIMIT=5                   Envoyer N articles"
	@echo "  make newsletter-prod                      Envoyer à NEWSLETTER_RECIPIENTS (toute l'équipe)"
	@echo "  make newsletter emma@... gabriel@...      Ajouter des destinataires ad-hoc à l'envoi de test"
	@echo "  make veille             Collecte + newsletter (workflow complet)"
	@echo "  make test               Lancer la suite de tests"
	@echo "  make api                Lancer l'API FastAPI (port 8000, reload auto)"
	@echo "  make streamlit          Lancer le dashboard Streamlit (port 8501)"
	@echo "  make cron-install       Programmer l'envoi quotidien automatique (tous les jours 8h45)"
	@echo "  make cron-remove        Supprimer le cron quotidien"
	@echo ""

# ── Setup ──────────────────────────────────────────────────────────────────────

install:
	conda create -n $(ENV) python=3.12 -y
	$(RUN) pip install -r requirements.txt
	cp -n .env.example .env || true
	@echo "Environnement prêt. Complète .env avec tes credentials."

initdb:
	$(RUN) python main.py initdb

# ── Pipeline ───────────────────────────────────────────────────────────────────

DAYS  ?= 7
LIMIT ?= 10

collect:
	$(RUN) python main.py collect --days $(DAYS)

newsletter:
	$(RUN) python main.py newsletter --limit $(LIMIT) $(_EXTRA_RCPT)

newsletter-prod:
	$(RUN) python main.py newsletter --limit $(LIMIT) --prod $(_EXTRA_RCPT)

veille: collect
	$(RUN) python main.py newsletter --limit $(LIMIT) $(_EXTRA_RCPT)

# ── Tests ──────────────────────────────────────────────────────────────────────

test:
	$(RUN) python -m pytest tests/ -v

# ── Frontend ───────────────────────────────────────────────────────────────────

api:
	$(RUN) uvicorn api.main:app --reload --port 8000

streamlit:
	PYTHONPATH=$(PROJECT_DIR) $(RUN) streamlit run frontend/app.py

# ── Cron ───────────────────────────────────────────────────────────────────────

cron-install:
	mkdir -p logs
	chmod +x $(SCRIPT)
	( crontab -l 2>/dev/null | grep -v "daily_newsletter"; \
	  echo "45 8 * * * /bin/bash $(SCRIPT) >> $(LOG) 2>&1" ) | crontab -
	@echo "Cron installé — tous les jours à 8h45 :"
	@crontab -l | grep daily_newsletter

cron-remove:
	crontab -l 2>/dev/null | grep -v "daily_newsletter" | crontab - || true
	@echo "Cron supprimé."

# ── Attrape-tout : silencer les adresses email passées comme faux-targets ──────
%:
	@:
