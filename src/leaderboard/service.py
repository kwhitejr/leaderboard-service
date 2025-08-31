"""Business logic service for leaderboard operations."""

from datetime import datetime, UTC
from typing import Any

from .database import LeaderboardDatabase
from .models import (
    LeaderboardResponse,
    ScoreRecord,
    ScoreSubmission,
    LeaderboardType,
)


class LeaderboardService:
    """Service layer containing pure business logic for leaderboard operations."""

    def __init__(self, database: LeaderboardDatabase | None = None) -> None:
        """Initialize service with database dependency."""
        self.db = database or LeaderboardDatabase()

    def health_check(self) -> dict[str, str]:
        """Perform health check."""
        return {"status": "healthy", "service": "leaderboard"}

    def submit_score(self, submission: ScoreSubmission) -> dict[str, Any]:
        """Submit a score to the leaderboard.

        Args:
            submission: Validated score submission data

        Returns:
            Dictionary with submission confirmation details

        Raises:
            RuntimeError: If database operation fails
        """
        # Create score record with timestamp
        score_record = ScoreRecord(
            game_id=submission.game_id,
            label=submission.label,
            label_type=submission.label_type,
            score=submission.score,
            score_type=submission.score_type,
            timestamp=datetime.now(UTC),
        )

        # Submit to database
        self.db.submit_score(score_record)

        return {
            "message": "Score submitted successfully",
            "game_id": submission.game_id,
            "label": submission.label,
            "label_type": submission.label_type.value,
            "score": str(submission.score),
            "score_type": submission.score_type.value,
        }

    def get_leaderboard(
        self, game_id: str, leaderboard_type: LeaderboardType, limit: int
    ) -> LeaderboardResponse:
        """Get leaderboard for a specific game.

        Args:
            game_id: Game identifier
            leaderboard_type: Type of leaderboard ranking to apply
            limit: Maximum number of entries to return

        Returns:
            LeaderboardResponse with game data and entries

        Raises:
            RuntimeError: If database operation fails
        """
        # Get leaderboard from database
        leaderboard_entries = self.db.get_leaderboard(game_id, leaderboard_type, limit)

        # Create response
        return LeaderboardResponse(
            game_id=game_id,
            leaderboard_type=leaderboard_type,
            leaderboard=leaderboard_entries,
        )
