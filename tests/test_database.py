"""Tests for leaderboard database operations."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from src.leaderboard.database import LeaderboardDatabase
from src.leaderboard.models import ScoreRecord, ScoreType


class TestLeaderboardDatabase:
    """Tests for LeaderboardDatabase class."""
    
    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.db = LeaderboardDatabase("test-table")
    
    @patch("src.leaderboard.database.boto3")
    def test_submit_score_high_score(self, mock_boto3: MagicMock) -> None:
        """Test submitting a high score."""
        # Setup mock
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Create test data
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        score_record = ScoreRecord(
            game_id="snake_classic",
            initials="KMW",
            score=103.0,
            score_type=ScoreType.HIGH_SCORE,
            timestamp=timestamp
        )
        
        # Execute
        db = LeaderboardDatabase("test-table")
        db.submit_score(score_record)
        
        # Verify
        expected_item = {
            "game_id": "snake_classic",
            "sort_key": "high_score#-000000103.000",
            "initials": "KMW",
            "score": Decimal("103.0"),
            "score_type": "high_score",
            "timestamp": "2024-01-15T10:30:00"
        }
        mock_table.put_item.assert_called_once_with(Item=expected_item)
    
    @patch("src.leaderboard.database.boto3")
    def test_submit_score_fastest_time(self, mock_boto3: MagicMock) -> None:
        """Test submitting a fastest time score."""
        # Setup mock
        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Create test data
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        score_record = ScoreRecord(
            game_id="race_game",
            initials="AMY",
            score=34.7,
            score_type=ScoreType.FASTEST_TIME,
            timestamp=timestamp
        )
        
        # Execute
        db = LeaderboardDatabase("test-table")
        db.submit_score(score_record)
        
        # Verify
        expected_item = {
            "game_id": "race_game",
            "sort_key": "fastest_time#000000034.700",
            "initials": "AMY",
            "score": Decimal("34.7"),
            "score_type": "fastest_time",
            "timestamp": "2024-01-15T10:30:00"
        }
        mock_table.put_item.assert_called_once_with(Item=expected_item)
    
    @patch("src.leaderboard.database.boto3")
    def test_submit_score_database_error(self, mock_boto3: MagicMock) -> None:
        """Test database error during score submission."""
        # Setup mock to raise error
        mock_table = MagicMock()
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ValidationException"}}, "PutItem"
        )
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Create test data
        score_record = ScoreRecord(
            game_id="test",
            initials="KMW",
            score=100.0,
            score_type=ScoreType.HIGH_SCORE,
            timestamp=datetime.utcnow()
        )
        
        # Execute and verify
        db = LeaderboardDatabase("test-table")
        with pytest.raises(RuntimeError, match="Failed to submit score"):
            db.submit_score(score_record)
    
    @patch("src.leaderboard.database.boto3")
    def test_get_leaderboard(self, mock_boto3: MagicMock) -> None:
        """Test getting leaderboard."""
        # Setup mock response
        mock_table = MagicMock()
        mock_response = {
            "Items": [
                {
                    "initials": "KMW",
                    "score": Decimal("103.0"),
                    "timestamp": "2024-01-15T10:30:00"
                },
                {
                    "initials": "AMY",
                    "score": Decimal("95.0"),
                    "timestamp": "2024-01-14T15:20:00"
                }
            ]
        }
        mock_table.query.return_value = mock_response
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Execute
        db = LeaderboardDatabase("test-table")
        leaderboard = db.get_leaderboard("snake_classic", ScoreType.HIGH_SCORE, 10)
        
        # Verify
        assert len(leaderboard) == 2
        assert leaderboard[0].rank == 1
        assert leaderboard[0].initials == "KMW"
        assert leaderboard[0].score == 103.0
        assert leaderboard[1].rank == 2
        assert leaderboard[1].initials == "AMY"
        assert leaderboard[1].score == 95.0
    
    @patch("src.leaderboard.database.boto3")
    def test_get_leaderboard_database_error(self, mock_boto3: MagicMock) -> None:
        """Test database error during leaderboard retrieval."""
        # Setup mock to raise error
        mock_table = MagicMock()
        mock_table.query.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException"}}, "Query"
        )
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Execute and verify
        db = LeaderboardDatabase("test-table")
        with pytest.raises(RuntimeError, match="Failed to get leaderboard"):
            db.get_leaderboard("test", ScoreType.HIGH_SCORE, 10)