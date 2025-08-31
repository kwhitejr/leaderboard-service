"""Tests for leaderboard service layer."""

from datetime import datetime, UTC
from unittest.mock import MagicMock, patch
import pytest

from src.leaderboard.models import (
    LabelType,
    LeaderboardEntry,
    LeaderboardResponse,
    LeaderboardType,
    ScoreRecord,
    ScoreSubmission,
    ScoreType,
)
from src.leaderboard.service import LeaderboardService


class TestLeaderboardService:
    """Tests for LeaderboardService business logic."""

    def setup_method(self, method) -> None:
        """Set up test environment."""
        self.mock_database = MagicMock()
        self.service = LeaderboardService(database=self.mock_database)

    def test_health_check(self) -> None:
        """Test health check returns correct response."""
        result = self.service.health_check()

        assert result == {"status": "healthy", "service": "leaderboard"}

    def test_submit_score_success(self) -> None:
        """Test successful score submission."""
        # Create test submission
        submission = ScoreSubmission(
            game_id="snake_classic",
            label="KMW",
            label_type=LabelType.INITIALS,
            score=103.0,
            score_type=ScoreType.POINTS,
        )

        # Execute
        with patch("src.leaderboard.service.datetime") as mock_datetime:
            fixed_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
            mock_datetime.now.return_value = fixed_time

            result = self.service.submit_score(submission)

        # Verify database was called with correct ScoreRecord
        self.mock_database.submit_score.assert_called_once()
        call_args = self.mock_database.submit_score.call_args[0][0]

        assert isinstance(call_args, ScoreRecord)
        assert call_args.game_id == "snake_classic"
        assert call_args.label == "KMW"
        assert call_args.label_type == LabelType.INITIALS
        assert call_args.score == 103.0
        assert call_args.score_type == ScoreType.POINTS
        assert call_args.timestamp == fixed_time

        # Verify return value
        expected_result = {
            "message": "Score submitted successfully",
            "game_id": "snake_classic",
            "label": "KMW",
            "label_type": "INITIALS",
            "score": "103.0",
            "score_type": "POINTS",
        }
        assert result == expected_result

    def test_submit_score_database_error(self) -> None:
        """Test score submission with database error."""
        # Setup
        submission = ScoreSubmission(
            game_id="snake_classic",
            label="KMW",
            label_type=LabelType.INITIALS,
            score=103.0,
            score_type=ScoreType.POINTS,
        )
        self.mock_database.submit_score.side_effect = RuntimeError("Database error")

        # Execute and verify
        with pytest.raises(RuntimeError, match="Database error"):
            self.service.submit_score(submission)

        # Verify database was called
        self.mock_database.submit_score.assert_called_once()

    def test_get_leaderboard_success(self) -> None:
        """Test successful leaderboard retrieval."""
        # Setup mock database response
        mock_entries = [
            LeaderboardEntry(
                rank=1,
                label="KMW",
                label_type=LabelType.INITIALS,
                score=103.0,
                timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            ),
            LeaderboardEntry(
                rank=2,
                label="AMY",
                label_type=LabelType.INITIALS,
                score=95.0,
                timestamp=datetime(2024, 1, 14, 15, 20, 0, tzinfo=UTC),
            ),
        ]
        self.mock_database.get_leaderboard.return_value = mock_entries

        # Execute
        result = self.service.get_leaderboard(
            "snake_classic", LeaderboardType.HIGH_SCORE, 10
        )

        # Verify database was called correctly
        self.mock_database.get_leaderboard.assert_called_once_with(
            "snake_classic", LeaderboardType.HIGH_SCORE, 10
        )

        # Verify return value
        assert isinstance(result, LeaderboardResponse)
        assert result.game_id == "snake_classic"
        assert result.leaderboard_type == LeaderboardType.HIGH_SCORE
        assert result.leaderboard == mock_entries

    def test_get_leaderboard_empty_result(self) -> None:
        """Test leaderboard retrieval with empty results."""
        # Setup mock database response
        self.mock_database.get_leaderboard.return_value = []

        # Execute
        result = self.service.get_leaderboard(
            "new_game", LeaderboardType.FASTEST_TIME, 5
        )

        # Verify database was called correctly
        self.mock_database.get_leaderboard.assert_called_once_with(
            "new_game", LeaderboardType.FASTEST_TIME, 5
        )

        # Verify return value
        assert isinstance(result, LeaderboardResponse)
        assert result.game_id == "new_game"
        assert result.leaderboard_type == LeaderboardType.FASTEST_TIME
        assert result.leaderboard == []

    def test_get_leaderboard_database_error(self) -> None:
        """Test leaderboard retrieval with database error."""
        # Setup
        self.mock_database.get_leaderboard.side_effect = RuntimeError("Database error")

        # Execute and verify
        with pytest.raises(RuntimeError, match="Database error"):
            self.service.get_leaderboard(
                "snake_classic", LeaderboardType.HIGH_SCORE, 10
            )

        # Verify database was called
        self.mock_database.get_leaderboard.assert_called_once()

    def test_submit_score_different_score_types(self) -> None:
        """Test score submission with different score types."""
        test_cases = [
            (ScoreType.POINTS, "POINTS"),
            (ScoreType.TIME_IN_MILLISECONDS, "TIME_IN_MILLISECONDS"),
        ]

        for score_type, expected_value in test_cases:
            # Reset mocks for each test case
            self.mock_database.reset_mock()

            submission = ScoreSubmission(
                game_id="test_game",
                label="TST",
                label_type=LabelType.INITIALS,
                score=50.0,
                score_type=score_type,
            )

            result = self.service.submit_score(submission)

            # Verify the score_type is correctly handled
            assert result["score_type"] == expected_value

            # Verify database call
            call_args = self.mock_database.submit_score.call_args[0][0]
            assert call_args.score_type == score_type

    def test_get_leaderboard_different_limits(self) -> None:
        """Test leaderboard retrieval with different limit values."""
        # Setup mock response
        mock_entries = [
            LeaderboardEntry(
                rank=1,
                label="TST",
                label_type=LabelType.INITIALS,
                score=100.0,
                timestamp=datetime.now(UTC),
            )
        ]
        self.mock_database.get_leaderboard.return_value = mock_entries

        test_limits = [1, 5, 10, 50, 100]

        for limit in test_limits:
            self.mock_database.reset_mock()

            result = self.service.get_leaderboard(
                "test_game", LeaderboardType.HIGH_SCORE, limit
            )

            # Verify database was called with correct limit
            self.mock_database.get_leaderboard.assert_called_once_with(
                "test_game", LeaderboardType.HIGH_SCORE, limit
            )

            # Verify response structure
            assert isinstance(result, LeaderboardResponse)

    def test_service_with_default_database(self) -> None:
        """Test service initialization with default database."""
        with patch("src.leaderboard.service.LeaderboardDatabase") as mock_db_class:
            mock_db_instance = MagicMock()
            mock_db_class.return_value = mock_db_instance

            service = LeaderboardService()

            # Verify database was instantiated
            mock_db_class.assert_called_once()
            assert service.db == mock_db_instance

    def test_service_with_custom_database(self) -> None:
        """Test service initialization with custom database."""
        custom_db = MagicMock()
        service = LeaderboardService(database=custom_db)

        assert service.db == custom_db

    def test_submit_score_preserves_submission_data(self) -> None:
        """Test that score submission preserves all original data correctly."""
        submission = ScoreSubmission(
            game_id="complex-game_name-123",
            label="ABC",
            label_type=LabelType.INITIALS,
            score=999.999,
            score_type=ScoreType.TIME_IN_MILLISECONDS,
        )

        with patch("src.leaderboard.service.datetime") as mock_datetime:
            fixed_time = datetime(2024, 12, 25, 12, 0, 0, tzinfo=UTC)
            mock_datetime.now.return_value = fixed_time

            result = self.service.submit_score(submission)

        # Verify all data is preserved correctly
        call_args = self.mock_database.submit_score.call_args[0][0]
        assert call_args.game_id == "complex-game_name-123"
        assert call_args.label == "ABC"
        assert call_args.score == 999.999
        assert call_args.score_type == ScoreType.TIME_IN_MILLISECONDS
        assert call_args.timestamp == fixed_time

        # Verify response contains correct data
        assert result["game_id"] == "complex-game_name-123"
        assert result["label"] == "ABC"
        assert result["score"] == "999.999"
        assert result["score_type"] == "TIME_IN_MILLISECONDS"
