"""Tests for leaderboard handler."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from moto import mock_aws

from src.leaderboard.models import LabelType, LeaderboardEntry, ScoreType


@mock_aws
class TestHandler:
    """Tests for Lambda handler endpoints."""

    def setup_method(self, method) -> None:
        """Set up test environment."""
        # Import here to avoid region issues during module import
        from src.leaderboard.handler import app

        self.app = app

    def test_health_check(self) -> None:
        """Test health check endpoint."""
        # Mock event
        event = {
            "resource": "/leaderboard/health",
            "httpMethod": "GET",
            "path": "/leaderboard/health",
            "headers": {},
            "queryStringParameters": None,
            "body": None,
        }

        # Execute
        response = self.app.resolve(event, {})

        # Verify
        assert response["statusCode"] == 200
        body = response["body"]
        assert "healthy" in body
        assert "leaderboard" in body

    @patch("src.leaderboard.handler.service")
    def test_submit_score_valid(self, mock_service: MagicMock) -> None:
        """Test valid score submission."""
        # Setup mock return value
        mock_service.submit_score.return_value = {
            "message": "Score submitted successfully",
            "game_id": "snake_classic",
            "label": "KMW",
            "label_type": "initials",
            "score": "103.0",
            "score_type": "high_score",
        }

        # Mock event
        event = {
            "resource": "/leaderboard/scores/v1",
            "httpMethod": "POST",
            "path": "/leaderboard/scores/v1",
            "headers": {"Content-Type": "application/json"},
            "queryStringParameters": None,
            "body": '{"game_id": "snake_classic", "label": "KMW", "label_type": "initials", "score": 103.0, "score_type": "high_score"}',
        }

        # Execute
        response = self.app.resolve(event, {})

        # Verify
        assert response["statusCode"] == 200
        mock_service.submit_score.assert_called_once()

        # Verify the submission passed to service
        call_args = mock_service.submit_score.call_args[0][0]
        assert call_args.game_id == "snake_classic"
        assert call_args.label == "KMW"
        assert call_args.score == 103.0
        assert call_args.score_type == ScoreType.HIGH_SCORE

    @patch("src.leaderboard.handler.service")
    def test_submit_score_invalid_data(self, mock_service: MagicMock) -> None:
        """Test score submission with invalid data."""
        # Mock event with invalid score
        event = {
            "resource": "/leaderboard/scores/v1",
            "httpMethod": "POST",
            "path": "/leaderboard/scores/v1",
            "headers": {"Content-Type": "application/json"},
            "queryStringParameters": None,
            "body": '{"game_id": "snake_classic", "label": "KMW", "label_type": "initials", "score": -10, "score_type": "high_score"}',
        }

        # Execute
        response = self.app.resolve(event, {})

        # Verify
        assert response["statusCode"] == 400
        mock_service.submit_score.assert_not_called()

    @patch("src.leaderboard.handler.service")
    def test_get_leaderboard_valid(self, mock_service: MagicMock) -> None:
        """Test valid leaderboard request."""
        # Setup mock return value
        from src.leaderboard.models import LeaderboardResponse

        mock_entries = [
            LeaderboardEntry(
                rank=1,
                label="KMW",
                label_type=LabelType.INITIALS,
                score=103.0,
                timestamp=datetime(2024, 1, 15, 10, 30, 0),
            ),
            LeaderboardEntry(
                rank=2,
                label="AMY",
                label_type=LabelType.INITIALS,
                score=95.0,
                timestamp=datetime(2024, 1, 14, 15, 20, 0),
            ),
        ]
        mock_response = LeaderboardResponse(
            game_id="snake_classic",
            score_type=ScoreType.HIGH_SCORE,
            leaderboard=mock_entries,
        )
        mock_service.get_leaderboard.return_value = mock_response

        # Mock event
        event = {
            "resource": "/leaderboard/leaderboards/v1/{game_id}",
            "httpMethod": "GET",
            "path": "/leaderboard/leaderboards/v1/snake_classic",
            "pathParameters": {"game_id": "snake_classic"},
            "headers": {},
            "queryStringParameters": {"score_type": "high_score", "limit": "10"},
            "body": None,
        }

        # Execute
        response = self.app.resolve(event, {})

        # Verify
        assert response["statusCode"] == 200
        mock_service.get_leaderboard.assert_called_once_with(
            "snake_classic", ScoreType.HIGH_SCORE, 10
        )

    @patch("src.leaderboard.handler.service")
    def test_get_leaderboard_invalid_score_type(self, mock_service: MagicMock) -> None:
        """Test leaderboard request with invalid score type."""
        # Mock event
        event = {
            "resource": "/leaderboard/leaderboards/v1/{game_id}",
            "httpMethod": "GET",
            "path": "/leaderboard/leaderboards/v1/snake_classic",
            "pathParameters": {"game_id": "snake_classic"},
            "headers": {},
            "queryStringParameters": {"score_type": "invalid_type"},
            "body": None,
        }

        # Execute
        response = self.app.resolve(event, {})

        # Verify
        assert response["statusCode"] == 400
        mock_service.get_leaderboard.assert_not_called()

    @patch("src.leaderboard.handler.service")
    def test_get_leaderboard_invalid_limit(self, mock_service: MagicMock) -> None:
        """Test leaderboard request with invalid limit."""
        # Mock event
        event = {
            "resource": "/leaderboard/leaderboards/v1/{game_id}",
            "httpMethod": "GET",
            "path": "/leaderboard/leaderboards/v1/snake_classic",
            "pathParameters": {"game_id": "snake_classic"},
            "headers": {},
            "queryStringParameters": {"limit": "150"},
            "body": None,
        }

        # Execute
        response = self.app.resolve(event, {})

        # Verify
        assert response["statusCode"] == 400
        mock_service.get_leaderboard.assert_not_called()

    @patch("src.leaderboard.handler.service")
    def test_submit_score_database_error(self, mock_service: MagicMock) -> None:
        """Test score submission with database error."""
        # Setup mock to raise RuntimeError
        mock_service.submit_score.side_effect = RuntimeError("Database error")

        # Mock event
        event = {
            "resource": "/leaderboard/scores/v1",
            "httpMethod": "POST",
            "path": "/leaderboard/scores/v1",
            "headers": {"Content-Type": "application/json"},
            "queryStringParameters": None,
            "body": '{"game_id": "snake_classic", "label": "KMW", "label_type": "initials", "score": 103.0, "score_type": "high_score"}',
        }

        # Execute and verify it raises the RuntimeError
        with pytest.raises(RuntimeError, match="Database error"):
            self.app.resolve(event, {})

    @patch("src.leaderboard.handler.service")
    def test_submit_score_unexpected_error(self, mock_service: MagicMock) -> None:
        """Test score submission with unexpected error."""
        # Setup mock to raise generic Exception
        mock_service.submit_score.side_effect = Exception("Unexpected error")

        # Mock event
        event = {
            "resource": "/leaderboard/scores/v1",
            "httpMethod": "POST",
            "path": "/leaderboard/scores/v1",
            "headers": {"Content-Type": "application/json"},
            "queryStringParameters": None,
            "body": '{"game_id": "snake_classic", "label": "KMW", "label_type": "initials", "score": 103.0, "score_type": "high_score"}',
        }

        # Execute and verify it raises the Exception
        with pytest.raises(Exception, match="Unexpected error"):
            self.app.resolve(event, {})

    @patch("src.leaderboard.handler.service")
    def test_get_leaderboard_database_error(self, mock_service: MagicMock) -> None:
        """Test leaderboard request with database error."""
        # Setup mock to raise RuntimeError
        mock_service.get_leaderboard.side_effect = RuntimeError("Database error")

        # Mock event
        event = {
            "resource": "/leaderboard/leaderboards/v1/{game_id}",
            "httpMethod": "GET",
            "path": "/leaderboard/leaderboards/v1/snake_classic",
            "pathParameters": {"game_id": "snake_classic"},
            "headers": {},
            "queryStringParameters": {"score_type": "high_score", "limit": "10"},
            "body": None,
        }

        # Execute and verify it raises the RuntimeError
        with pytest.raises(RuntimeError, match="Database error"):
            self.app.resolve(event, {})

    @patch("src.leaderboard.handler.service")
    def test_get_leaderboard_unexpected_error(self, mock_service: MagicMock) -> None:
        """Test leaderboard request with unexpected error."""
        # Setup mock to raise generic Exception
        mock_service.get_leaderboard.side_effect = Exception("Unexpected error")

        # Mock event
        event = {
            "resource": "/leaderboard/leaderboards/v1/{game_id}",
            "httpMethod": "GET",
            "path": "/leaderboard/leaderboards/v1/snake_classic",
            "pathParameters": {"game_id": "snake_classic"},
            "headers": {},
            "queryStringParameters": {"score_type": "high_score", "limit": "10"},
            "body": None,
        }

        # Execute and verify it raises the Exception
        with pytest.raises(Exception, match="Unexpected error"):
            self.app.resolve(event, {})

    @patch("src.leaderboard.handler.service")
    def test_get_leaderboard_parameter_validation_error(
        self, mock_service: MagicMock
    ) -> None:
        """Test leaderboard request with parameter validation error."""
        # Mock event with invalid limit format
        event = {
            "resource": "/leaderboard/leaderboards/v1/{game_id}",
            "httpMethod": "GET",
            "path": "/leaderboard/leaderboards/v1/snake_classic",
            "pathParameters": {"game_id": "snake_classic"},
            "headers": {},
            "queryStringParameters": {"limit": "not_a_number"},
            "body": None,
        }

        # Execute
        response = self.app.resolve(event, {})

        # Verify
        assert response["statusCode"] == 400
        mock_service.get_leaderboard.assert_not_called()

    def test_lambda_handler_integration(self) -> None:
        """Test the lambda_handler entry point."""
        # Import the lambda_handler function
        from src.leaderboard.handler import lambda_handler

        # Mock event for health check
        event = {
            "resource": "/leaderboard/health",
            "httpMethod": "GET",
            "path": "/leaderboard/health",
            "headers": {},
            "queryStringParameters": None,
            "body": None,
        }

        # Mock context with all required attributes
        context = type(
            "Context",
            (),
            {
                "aws_request_id": "test-request-id",
                "function_name": "test-function",
                "function_version": "$LATEST",
                "invoked_function_arn": "arn:aws:lambda:us-east-1:123456789012:function:test-function",
                "memory_limit_in_mb": "128",
                "remaining_time_in_millis": lambda: 30000,
            },
        )()

        # Execute
        response = lambda_handler(event, context)

        # Verify
        assert response["statusCode"] == 200
        body = response["body"]
        assert "healthy" in body
        assert "leaderboard" in body

    @patch("src.leaderboard.handler.service")
    def test_get_leaderboard_generic_value_error(self, mock_service: MagicMock) -> None:
        """Test leaderboard request with generic ValueError (not parameter validation)."""
        # Mock the service to raise a ValueError
        mock_service.get_leaderboard.side_effect = ValueError("Invalid response data")

        # Mock event
        event = {
            "resource": "/leaderboard/leaderboards/v1/{game_id}",
            "httpMethod": "GET",
            "path": "/leaderboard/leaderboards/v1/test_game",
            "pathParameters": {"game_id": "test_game"},
            "headers": {},
            "queryStringParameters": {"score_type": "high_score", "limit": "10"},
            "body": None,
        }

        # Execute
        response = self.app.resolve(event, {})

        # Verify - should catch ValueError and return 400
        assert response["statusCode"] == 400
        mock_service.get_leaderboard.assert_called_once()
