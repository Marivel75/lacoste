.PHONY: install run run-14j streamlit init-db setup help

help:
	@echo "Commandes disponibles :"
	@echo "  make install     Créer l'environnement conda et installer les dépendances"
	@echo "  make run         Lancer la veille sur 7 jours"
	@echo "  make run-14j     Lancer la veille sur 14 jours"
	@echo "  make streamlit   Lancer le dashboard Streamlit (port 8501)"

install:
	conda create -n veille-reno python=3.12 -y
	conda run -n veille-reno pip install -r requirements.txt
	cp -n .env.example .env || true
	@echo "Environnement prêt. Remplis .env avec tes credentials."

run:
	conda run -n veille-reno python -m src.main

run-14j:
	conda run -n veille-reno python -m src.main --days 14

streamlit:
	conda run -n veille-reno streamlit run streamlit_app.py

init-db:
	conda run -n veille-reno python -m src.main init-db

setup:
	conda run -n veille-reno python -m src.main setup --page-id $(PAGE_ID)
