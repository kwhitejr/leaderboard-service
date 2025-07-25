"""Tests for leaderboard handler."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from moto import mock_dynamodb

from src.leaderboard.models import LeaderboardEntry, ScoreType


@mock_dynamodb
class TestHandler:
    """Tests for Lambda handler endpoints."""
    
    def setup_method(self) -> None:
        """Set up test environment."""
        # Import here to avoid region issues during module import
        from src.leaderboard.handler import app
        self.app = app
    
    def test_health_check(self) -> None:
        """Test health check endpoint."""
        # Mock event
        event = {
            "resource": "/health",
            "httpMethod": "GET",
            "path": "/health",
            "headers": {},
            "queryStringParameters": None,
            "body": None
        }
        
        # Execute
        response = self.app.resolve(event, {})
        
        # Verify
        assert response["statusCode"] == 200
        body = response["body"]
        assert "healthy" in body
        assert "leaderboard" in body
    
    @patch("src.leaderboard.handler.db")
    def test_submit_score_valid(self, mock_db: MagicMock) -> None:
        """Test valid score submission."""
        # Mock event
        event = {
            "resource": "/games/scores/v1",
            "httpMethod": "POST",
            "path": "/games/scores/v1",
            "headers": {"Content-Type": "application/json"},
            "queryStringParameters": None,
            "body": '{"game_id": "snake_classic", "initials": "KMW", "score": 103.0, "score_type": "high_score"}'
        }
        
        # Execute
        response = self.app.resolve(event, {})
        
        # Verify
        assert response["statusCode"] == 200
        mock_db.submit_score.assert_called_once()
        
        # Verify the score record passed to db
        call_args = mock_db.submit_score.call_args[0][0]
        assert call_args.game_id == "snake_classic"
        assert call_args.initials == "KMW"
        assert call_args.score == 103.0
        assert call_args.score_type == ScoreType.HIGH_SCORE
    
    @patch("src.leaderboard.handler.db")
    def test_submit_score_invalid_data(self, mock_db: MagicMock) -> None:
        """Test score submission with invalid data."""
        # Mock event with invalid score
        event = {
            "resource": "/games/scores/v1",
            "httpMethod": "POST",
            "path": "/games/scores/v1",
            "headers": {"Content-Type": "application/json"},
            "queryStringParameters": None,
            "body": '{"game_id": "snake_classic", "initials": "KMW", "score": -10, "score_type": "high_score"}'
        }
        
        # Execute
        response = self.app.resolve(event, {})
        
        # Verify
        assert response["statusCode"] == 400
        mock_db.submit_score.assert_not_called()
    
    @patch("src.leaderboard.handler.db")
    def test_get_leaderboard_valid(self, mock_db: MagicMock) -> None:
        """Test valid leaderboard request."""
        # Setup mock return value
        mock_entries = [
            LeaderboardEntry(
                rank=1,
                initials="KMW",
                score=103.0,
                timestamp=datetime(2024, 1, 15, 10, 30, 0)
            ),
            LeaderboardEntry(
                rank=2,
                initials="AMY",
                score=95.0,
                timestamp=datetime(2024, 1, 14, 15, 20, 0)
            )
        ]
        mock_db.get_leaderboard.return_value = mock_entries
        
        # Mock event
        event = {
            "resource": "/games/leaderboards/v1/{game_id}",
            "httpMethod": "GET",
            "path": "/games/leaderboards/v1/snake_classic",
            "pathParameters": {"game_id": "snake_classic"},
            "headers": {},
            "queryStringParameters": {"score_type": "high_score", "limit": "10"},
            "body": None
        }
        
        # Execute
        response = self.app.resolve(event, {})
        
        # Verify
        assert response["statusCode"] == 200
        mock_db.get_leaderboard.assert_called_once_with("snake_classic", ScoreType.HIGH_SCORE, 10)
    
    @patch("src.leaderboard.handler.db")
    def test_get_leaderboard_invalid_score_type(self, mock_db: MagicMock) -> None:
        """Test leaderboard request with invalid score type."""
        # Mock event
        event = {
            "resource": "/games/leaderboards/v1/{game_id}",
            "httpMethod": "GET",
            "path": "/games/leaderboards/v1/snake_classic",
            "pathParameters": {"game_id": "snake_classic"},
            "headers": {},
            "queryStringParameters": {"score_type": "invalid_type"},
            "body": None
        }
        
        # Execute
        response = self.app.resolve(event, {})
        
        # Verify
        assert response["statusCode"] == 400
        mock_db.get_leaderboard.assert_not_called()
    
    @patch("src.leaderboard.handler.db")
    def test_get_leaderboard_invalid_limit(self, mock_db: MagicMock) -> None:
        """Test leaderboard request with invalid limit."""
        # Mock event
        event = {
            "resource": "/games/leaderboards/v1/{game_id}",
            "httpMethod": "GET",
            "path": "/games/leaderboards/v1/snake_classic",
            "pathParameters": {"game_id": "snake_classic"},
            "headers": {},
            "queryStringParameters": {"limit": "150"},
            "body": None
        }
        
        # Execute
        response = self.app.resolve(event, {})
        
        # Verify
        assert response["statusCode"] == 400
        mock_db.get_leaderboard.assert_not_called()