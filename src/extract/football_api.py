"""
Client HTTP pour l'API football-data.org (v4).

Gère l'authentification par token X-Auth-Token, la récupération
des matchs par compétition et plage de dates, et les erreurs HTTP.
Référence : https://www.football-data.org/documentation/quickstart
"""

import logging
from datetime import date
from typing import Any

from src.config import Config

logger = logging.getLogger(__name__)


class FootballApiClient:
    """Client REST pour l'API football-data.org v4."""

    BASE_URL = "https://api.football-data.org/v4"

    def __init__(self, settings: Config) -> None:
        pass

    def get_matches(
        self,
        competition_id: int,
        date_from: date,
        date_to: date,
    ) -> list[dict[str, Any]]:
        """Retourne les matchs d'une compétition pour une plage de dates."""
        pass

    def get_competition(self, competition_id: int) -> dict[str, Any]:
        """Retourne les métadonnées d'une compétition."""
        pass
