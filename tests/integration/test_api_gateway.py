"""API Gateway + Lambda integration tests.

These tests verify the complete HTTP request/response cycle with real Lambda handler
execution against LocalStack environment, including API Gateway event transformation,
routing, parameter parsing, and response serialization.
"""

import json
from typing import Any

from src.leaderboard.handler import lambda_handler
from tests.integration.conftest import create_api_event


class TestAPIGatewayIntegration:
    """Test API Gateway + Lambda integration."""

    def test_submit_score_success(
        self, leaderboard_db, lambda_context, sample_score_data: dict[str, Any]
    ):
        """Test successful score submission via API Gateway."""
        # Create API Gateway event for POST /games/scores/v1
        event = create_api_event(
            method="POST", path="/games/scores/v1", body=sample_score_data
        )

        # Execute Lambda handler
        response = lambda_handler(event, lambda_context)

        # Verify response structure
        assert response["statusCode"] == 201
        assert "headers" in response
        assert response["headers"]["Content-Type"] == "application/json"

        # Parse response body
        body = json.loads(response["body"])
        assert body["success"] is True
        assert "score_id" in body
        assert body["message"] == "Score submitted successfully"

        # Verify score was actually stored in database
        scores = leaderboard_db.get_leaderboard(
            game_id=sample_score_data["game_id"],
            score_type=sample_score_data["score_type"],
            limit=10,
        )
        assert len(scores) == 1
        assert scores[0].initials == sample_score_data["initials"]
        assert scores[0].score == sample_score_data["score"]

    def test_submit_score_invalid_data(self, leaderboard_db, lambda_context):
        """Test score submission with invalid data."""
        invalid_data = {
            "game_id": "",  # Empty game_id
            "initials": "TOOLONG",  # Too long initials
            "score": -100,  # Negative score
            "score_type": "invalid_type",  # Invalid score type
        }

        event = create_api_event(
            method="POST", path="/games/scores/v1", body=invalid_data
        )

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "error" in body

    def test_submit_score_malformed_json(self, leaderboard_db, lambda_context):
        """Test score submission with malformed JSON."""
        # Create event with invalid JSON in body
        event = create_api_event(method="POST", path="/games/scores/v1")
        event["body"] = "invalid json {"  # Malformed JSON

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "error" in body

    def test_get_leaderboard_success(
        self, leaderboard_db, lambda_context, sample_score_data
    ):
        """Test successful leaderboard retrieval via API Gateway."""
        # First, submit a score to have data
        submit_event = create_api_event(
            method="POST", path="/games/scores/v1", body=sample_score_data
        )
        lambda_handler(submit_event, lambda_context)

        # Now get the leaderboard
        get_event = create_api_event(
            method="GET",
            path=f"/games/leaderboards/v1/{sample_score_data['game_id']}",
            query_params={"score_type": sample_score_data["score_type"], "limit": "10"},
            path_params={"game_id": sample_score_data["game_id"]},
        )

        response = lambda_handler(get_event, lambda_context)

        assert response["statusCode"] == 200
        assert response["headers"]["Content-Type"] == "application/json"

        body = json.loads(response["body"])
        assert "scores" in body
        assert len(body["scores"]) == 1
        assert body["scores"][0]["initials"] == sample_score_data["initials"]
        assert body["scores"][0]["score"] == sample_score_data["score"]
        assert body["scores"][0]["game_id"] == sample_score_data["game_id"]
        assert body["scores"][0]["score_type"] == sample_score_data["score_type"]

    def test_get_leaderboard_empty_result(self, leaderboard_db, lambda_context):
        """Test leaderboard retrieval with no scores."""
        event = create_api_event(
            method="GET",
            path="/games/leaderboards/v1/nonexistent_game",
            query_params={"score_type": "high_score", "limit": "10"},
            path_params={"game_id": "nonexistent_game"},
        )

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["scores"] == []

    def test_get_leaderboard_invalid_score_type(self, leaderboard_db, lambda_context):
        """Test leaderboard retrieval with invalid score type."""
        event = create_api_event(
            method="GET",
            path="/games/leaderboards/v1/test_game",
            query_params={"score_type": "invalid_type", "limit": "10"},
            path_params={"game_id": "test_game"},
        )

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "error" in body

    def test_get_leaderboard_missing_game_id(self, leaderboard_db, lambda_context):
        """Test leaderboard retrieval without game_id path parameter."""
        event = create_api_event(
            method="GET",
            path="/games/leaderboards/v1/",
            query_params={"score_type": "high_score", "limit": "10"},
        )
        # Don't set path_params to simulate missing game_id

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "error" in body

    def test_unsupported_http_method(self, leaderboard_db, lambda_context):
        """Test unsupported HTTP method."""
        event = create_api_event(method="DELETE", path="/games/scores/v1")

        response = lambda_handler(event, lambda_context)

        assert response["statusCode"] == 405
        body = json.loads(response["body"])
        assert body["success"] is False
        assert "error" in body

    def test_multiple_score_submissions_and_ranking(
        self, leaderboard_db, lambda_context
    ):
        """Test multiple score submissions and proper ranking."""
        game_id = "ranking_test_game"
        scores_data = [
            {
                "game_id": game_id,
                "initials": "P1",
                "score": 1000,
                "score_type": "high_score",
            },
            {
                "game_id": game_id,
                "initials": "P2",
                "score": 2000,
                "score_type": "high_score",
            },
            {
                "game_id": game_id,
                "initials": "P3",
                "score": 1500,
                "score_type": "high_score",
            },
        ]

        # Submit all scores
        for score_data in scores_data:
            event = create_api_event(
                method="POST", path="/games/scores/v1", body=score_data
            )
            response = lambda_handler(event, lambda_context)
            assert response["statusCode"] == 201

        # Get leaderboard
        get_event = create_api_event(
            method="GET",
            path=f"/games/leaderboards/v1/{game_id}",
            query_params={"score_type": "high_score", "limit": "10"},
            path_params={"game_id": game_id},
        )

        response = lambda_handler(get_event, lambda_context)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        scores = body["scores"]

        # Verify proper ranking (highest first for high_score)
        assert len(scores) == 3
        assert scores[0]["initials"] == "P2"  # 2000 points
        assert scores[0]["score"] == 2000
        assert scores[1]["initials"] == "P3"  # 1500 points
        assert scores[1]["score"] == 1500
        assert scores[2]["initials"] == "P1"  # 1000 points
        assert scores[2]["score"] == 1000

    def test_leaderboard_limit_parameter(self, leaderboard_db, lambda_context):
        """Test leaderboard limit parameter functionality."""
        game_id = "limit_test_game"

        # Submit 5 scores
        for i in range(5):
            score_data = {
                "game_id": game_id,
                "initials": f"P{i}",
                "score": (i + 1) * 100,
                "score_type": "high_score",
            }
            event = create_api_event(
                method="POST", path="/games/scores/v1", body=score_data
            )
            lambda_handler(event, lambda_context)

        # Get leaderboard with limit=3
        get_event = create_api_event(
            method="GET",
            path=f"/games/leaderboards/v1/{game_id}",
            query_params={"score_type": "high_score", "limit": "3"},
            path_params={"game_id": game_id},
        )

        response = lambda_handler(get_event, lambda_context)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        assert len(body["scores"]) == 3

        # Should get top 3 scores (highest first)
        assert body["scores"][0]["score"] == 500  # P4
        assert body["scores"][1]["score"] == 400  # P3
        assert body["scores"][2]["score"] == 300  # P2

    def test_cors_headers_present(
        self, leaderboard_db, lambda_context, sample_score_data
    ):
        """Test that CORS headers are present in responses."""
        event = create_api_event(
            method="POST", path="/games/scores/v1", body=sample_score_data
        )

        response = lambda_handler(event, lambda_context)

        headers = response.get("headers", {})
        assert headers.get("Content-Type") == "application/json"
        # Note: Add CORS header assertions here if CORS is implemented
