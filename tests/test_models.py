"""Tests for leaderboard models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.leaderboard.models import (
    LeaderboardEntry,
    LeaderboardResponse,
    ScoreRecord,
    ScoreSubmission,
    ScoreType,
)


class TestScoreSubmission:
    """Tests for ScoreSubmission model."""
    
    def test_valid_submission(self) -> None:
        """Test valid score submission."""
        submission = ScoreSubmission(
            game_id="snake_classic",
            initials="KMW",
            score=100.5,
            score_type=ScoreType.HIGH_SCORE
        )
        
        assert submission.game_id == "snake_classic"
        assert submission.initials == "KMW"
        assert submission.score == 100.5
        assert submission.score_type == ScoreType.HIGH_SCORE
    
    def test_initials_validation(self) -> None:
        """Test initials validation."""
        # Test uppercase conversion
        submission = ScoreSubmission(
            game_id="test",
            initials="kmw",
            score=100,
            score_type=ScoreType.HIGH_SCORE
        )
        assert submission.initials == "KMW"
        
        # Test invalid characters
        with pytest.raises(ValidationError):
            ScoreSubmission(
                game_id="test",
                initials="K@W",
                score=100,
                score_type=ScoreType.HIGH_SCORE
            )
    
    def test_game_id_validation(self) -> None:
        """Test game_id validation."""
        # Test valid game IDs
        valid_ids = ["snake", "snake_classic", "snake-game", "game123"]
        for game_id in valid_ids:
            submission = ScoreSubmission(
                game_id=game_id,
                initials="KMW",
                score=100,
                score_type=ScoreType.HIGH_SCORE
            )
            assert submission.game_id == game_id.lower()
        
        # Test invalid game ID
        with pytest.raises(ValidationError):
            ScoreSubmission(
                game_id="snake@game",
                initials="KMW",
                score=100,
                score_type=ScoreType.HIGH_SCORE
            )
    
    def test_score_validation(self) -> None:
        """Test score validation."""
        # Test negative score
        with pytest.raises(ValidationError):
            ScoreSubmission(
                game_id="test",
                initials="KMW",
                score=-10,
                score_type=ScoreType.HIGH_SCORE
            )


class TestScoreRecord:
    """Tests for ScoreRecord model."""
    
    def test_valid_record(self) -> None:
        """Test valid score record."""
        timestamp = datetime.now(timezone.utc)
        record = ScoreRecord(
            game_id="snake_classic",
            initials="KMW",
            score=100.5,
            score_type=ScoreType.HIGH_SCORE,
            timestamp=timestamp
        )
        
        assert record.game_id == "snake_classic"
        assert record.initials == "KMW"
        assert record.score == 100.5
        assert record.score_type == ScoreType.HIGH_SCORE
        assert record.timestamp == timestamp


class TestLeaderboardResponse:
    """Tests for LeaderboardResponse model."""
    
    def test_valid_response(self) -> None:
        """Test valid leaderboard response."""
        entries = [
            LeaderboardEntry(
                rank=1,
                initials="KMW",
                score=100.5,
                timestamp=datetime.now(timezone.utc)
            ),
            LeaderboardEntry(
                rank=2,
                initials="AMY",
                score=95.0,
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        response = LeaderboardResponse(
            game_id="snake_classic",
            score_type=ScoreType.HIGH_SCORE,
            leaderboard=entries
        )
        
        assert response.game_id == "snake_classic"
        assert response.score_type == ScoreType.HIGH_SCORE
        assert len(response.leaderboard) == 2
        assert response.leaderboard[0].rank == 1