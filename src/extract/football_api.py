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
        if not isinstance(settings, Config):
            raise TypeError(
                "La configuration du client API doit être une instance de Config"
            )
        if not isinstance(settings.football_api_base_url, str):
            raise ValueError(
                "L'URL de l'API football doit être une chaîne de caractères"
            )
        if not isinstance(settings.api_key, str):
            raise ValueError(
                "Le token de l'API football doit être une chaîne de caractères"
            )
        self.base_url = settings.football_api_base_url.strip().rstrip("/")
        if not self.base_url:
            raise ValueError("L'URL de l'API football ne peut pas être vide")

        api_key = settings.api_key.strip()
        if not api_key:
            raise ValueError("Le token de l'API football ne peut pas être vide")

        self.headers = {"X-Auth-Token": api_key}

    def get_matches(
        self,
        competition_id: int,
        date_from: date,
        date_to: date,
    ) -> list[dict[str, Any]]:
        """Retourne les matchs d'une compétition pour une plage de dates."""
        _validate_competition_id(competition_id)
        _validate_date("date_from", date_from)
        _validate_date("date_to", date_to)
        if date_from > date_to:
            raise ValueError("date_from doit être antérieure ou égale à date_to")

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
        if not isinstance(matches, list) or not all(
            isinstance(match, dict) for match in matches
        ):
            raise ValueError(
                "Réponse API invalide : 'matches' doit être une liste d'objets"
            )
        return matches

    def get_competition(self, competition_id: int) -> dict[str, Any]:
        """Retourne les métadonnées d'une compétition."""
        _validate_competition_id(competition_id)
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


def _validate_competition_id(competition_id: int) -> None:
    """Rejette les identifiants qui ne peuvent pas désigner une compétition."""
    if (
        isinstance(competition_id, bool)
        or not isinstance(competition_id, int)
        or competition_id <= 0
    ):
        raise ValueError("competition_id doit être un entier strictement positif")


def _validate_date(name: str, value: date) -> None:
    """Rejette les valeurs qui ne peuvent pas former un paramètre de date API."""
    if not isinstance(value, date):
        raise ValueError(f"{name} doit être une date")
