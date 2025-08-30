"""Tests for leaderboard models."""

from datetime import datetime, UTC

import pytest
from pydantic import ValidationError

from src.leaderboard.models import (
    LeaderboardEntry,
    LeaderboardResponse,
    LabelType,
    ScoreRecord,
    ScoreSubmission,
    ScoreType,
)


class TestScoreSubmission:
    """Tests for ScoreSubmission model."""

    def test_valid_submission_with_initials(self) -> None:
        """Test valid score submission with initials."""
        submission = ScoreSubmission(
            game_id="snake_classic",
            label="KMW",
            label_type=LabelType.INITIALS,
            score=100.5,
            score_type=ScoreType.HIGH_SCORE,
        )

        assert submission.game_id == "snake_classic"
        assert submission.label == "KMW"
        assert submission.label_type == LabelType.INITIALS
        assert submission.score == 100.5
        assert submission.score_type == ScoreType.HIGH_SCORE

    def test_valid_submission_with_username(self) -> None:
        """Test valid score submission with username."""
        submission = ScoreSubmission(
            game_id="snake_classic",
            label="player123",
            label_type=LabelType.USERNAME,
            score=100.5,
            score_type=ScoreType.HIGH_SCORE,
        )

        assert submission.game_id == "snake_classic"
        assert submission.label == "player123"
        assert submission.label_type == LabelType.USERNAME
        assert submission.score == 100.5
        assert submission.score_type == ScoreType.HIGH_SCORE

    def test_valid_submission_with_team_name(self) -> None:
        """Test valid score submission with team name."""
        submission = ScoreSubmission(
            game_id="snake_classic",
            label="Blue Team",
            label_type=LabelType.TEAM_NAME,
            score=100.5,
            score_type=ScoreType.HIGH_SCORE,
        )

        assert submission.game_id == "snake_classic"
        assert submission.label == "Blue Team"
        assert submission.label_type == LabelType.TEAM_NAME
        assert submission.score == 100.5
        assert submission.score_type == ScoreType.HIGH_SCORE

    def test_default_label_type(self) -> None:
        """Test default label type when not specified."""
        submission = ScoreSubmission(
            game_id="test",
            label="CustomLabel",
            score=100,
            score_type=ScoreType.HIGH_SCORE,
        )
        assert submission.label_type == LabelType.CUSTOM

    def test_player_label_validation(self) -> None:
        """Test player label validation."""
        # Test empty label
        with pytest.raises(ValidationError):
            ScoreSubmission(
                game_id="test",
                label="",
                score=100,
                score_type=ScoreType.HIGH_SCORE,
            )

        # Test whitespace-only label
        with pytest.raises(ValidationError):
            ScoreSubmission(
                game_id="test",
                label="   ",
                score=100,
                score_type=ScoreType.HIGH_SCORE,
            )

    def test_initials_validation(self) -> None:
        """Test initials validation for exactly 3 characters."""
        # Test valid 3-character initials
        submission = ScoreSubmission(
            game_id="test",
            label="ABC",
            label_type=LabelType.INITIALS,
            score=100,
            score_type=ScoreType.HIGH_SCORE,
        )
        assert submission.label == "ABC"
        assert submission.label_type == LabelType.INITIALS

        # Test valid 3-character alphanumeric initials
        submission = ScoreSubmission(
            game_id="test",
            label="A1B",
            label_type=LabelType.INITIALS,
            score=100,
            score_type=ScoreType.HIGH_SCORE,
        )
        assert submission.label == "A1B"

        # Test too short initials (2 characters)
        with pytest.raises(
            ValidationError,
            match="Label must be exactly 3 characters when label_type is INITIALS",
        ):
            ScoreSubmission(
                game_id="test",
                label="AB",
                label_type=LabelType.INITIALS,
                score=100,
                score_type=ScoreType.HIGH_SCORE,
            )

        # Test too long initials (4 characters)
        with pytest.raises(
            ValidationError,
            match="Label must be exactly 3 characters when label_type is INITIALS",
        ):
            ScoreSubmission(
                game_id="test",
                label="ABCD",
                label_type=LabelType.INITIALS,
                score=100,
                score_type=ScoreType.HIGH_SCORE,
            )

        # Test initials with special characters
        with pytest.raises(
            ValidationError, match="Initials must contain only alphanumeric characters"
        ):
            ScoreSubmission(
                game_id="test",
                label="A-B",
                label_type=LabelType.INITIALS,
                score=100,
                score_type=ScoreType.HIGH_SCORE,
            )

        # Test initials with spaces
        with pytest.raises(
            ValidationError, match="Initials must contain only alphanumeric characters"
        ):
            ScoreSubmission(
                game_id="test",
                label="A B",
                label_type=LabelType.INITIALS,
                score=100,
                score_type=ScoreType.HIGH_SCORE,
            )

    def test_non_initials_not_affected_by_length_validation(self) -> None:
        """Test that non-INITIALS label types are not affected by 3-character validation."""
        # Test USERNAME with 2 characters (should be fine)
        submission = ScoreSubmission(
            game_id="test",
            label="AB",
            label_type=LabelType.USERNAME,
            score=100,
            score_type=ScoreType.HIGH_SCORE,
        )
        assert submission.label == "AB"

        # Test CUSTOM with 4+ characters (should be fine)
        submission = ScoreSubmission(
            game_id="test",
            label="LongCustomLabel",
            label_type=LabelType.CUSTOM,
            score=100,
            score_type=ScoreType.HIGH_SCORE,
        )
        assert submission.label == "LongCustomLabel"

    def test_game_id_validation(self) -> None:
        """Test game_id validation."""
        # Test valid game IDs
        valid_ids = ["snake", "snake_classic", "snake-game", "game123"]
        for game_id in valid_ids:
            submission = ScoreSubmission(
                game_id=game_id,
                label="KMW",
                score=100,
                score_type=ScoreType.HIGH_SCORE,
            )
            assert submission.game_id == game_id.lower()

        # Test invalid game ID
        with pytest.raises(ValidationError):
            ScoreSubmission(
                game_id="snake@game",
                label="KMW",
                score=100,
                score_type=ScoreType.HIGH_SCORE,
            )

    def test_score_validation(self) -> None:
        """Test score validation."""
        # Test negative score
        with pytest.raises(ValidationError):
            ScoreSubmission(
                game_id="test",
                label="KMW",
                score=-10,
                score_type=ScoreType.HIGH_SCORE,
            )


class TestScoreRecord:
    """Tests for ScoreRecord model."""

    def test_valid_record(self) -> None:
        """Test valid score record."""
        timestamp = datetime.now(UTC)
        record = ScoreRecord(
            game_id="snake_classic",
            label="KMW",
            label_type=LabelType.INITIALS,
            score=100.5,
            score_type=ScoreType.HIGH_SCORE,
            timestamp=timestamp,
        )

        assert record.game_id == "snake_classic"
        assert record.label == "KMW"
        assert record.label_type == LabelType.INITIALS
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
                label="KMW",
                label_type=LabelType.INITIALS,
                score=100.5,
                timestamp=datetime.now(UTC),
            ),
            LeaderboardEntry(
                rank=2,
                label="AMY",
                label_type=LabelType.INITIALS,
                score=95.0,
                timestamp=datetime.now(UTC),
            ),
        ]

        response = LeaderboardResponse(
            game_id="snake_classic",
            score_type=ScoreType.HIGH_SCORE,
            leaderboard=entries,
        )

        assert response.game_id == "snake_classic"
        assert response.score_type == ScoreType.HIGH_SCORE
        assert len(response.leaderboard) == 2
        assert response.leaderboard[0].rank == 1
