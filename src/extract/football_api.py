"""
Client HTTP pour l'API football-data.org (v4).

Gère l'authentification par token X-Auth-Token, la récupération
des matchs par compétition et plage de dates, et les erreurs HTTP.
Référence : https://www.football-data.org/documentation/quickstart
"""

import logging
from datetime import date
from typing import Any

import requests

from src.config import Config

logger = logging.getLogger(__name__)


class FootballApiClient:
    """Client REST pour l'API football-data.org v4."""

    BASE_URL = "https://api.football-data.org/v4"

    def __init__(self, settings: Config) -> None:
        self.base_url = settings.football_api_base_url.rstrip("/")
        self.headers = {"X-Auth-Token": settings.api_key}

    def get_matches(
        self,
        competition_id: int,
        date_from: date,
        date_to: date,
    ) -> list[dict[str, Any]]:
        """Retourne les matchs d'une compétition pour une plage de dates."""
        response = requests.get(
            f"{self.base_url}/competitions/{competition_id}/matches",
            headers=self.headers,
            params={"dateFrom": date_from.isoformat(), "dateTo": date_to.isoformat()},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Réponse API invalide : objet JSON attendu")

        matches = payload.get("matches", [])
        if not isinstance(matches, list):
            raise ValueError("Réponse API invalide : 'matches' doit être une liste")
        return matches

    def get_competition(self, competition_id: int) -> dict[str, Any]:
        """Retourne les métadonnées d'une compétition."""
        response = requests.get(
            f"{self.base_url}/competitions/{competition_id}",
            headers=self.headers,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Réponse API invalide : objet JSON attendu")
        return payload
