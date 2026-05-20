"""Configuration du frontend Streamlit.

Lit API_BASE_URL depuis l'environnement (défaut : http://localhost:8000).
Permet de pointer vers une instance distante en production sans modifier le code.
"""

import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
