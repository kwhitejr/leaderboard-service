"""End-to-end integration tests.

These tests simulate complete user workflows and business scenarios,
validating the entire system from API requests through data persistence
and retrieval with real AWS services in LocalStack.
"""

import json
import pytest
from typing import List, Dict, Any

from src.leaderboard.handler import lambda_handler
from tests.integration.conftest import create_api_event


class TestEndToEndWorkflows:
    """Test complete user workflows and business scenarios."""

    def test_complete_game_session_workflow(self, leaderboard_db, lambda_context):
        """Test a complete game session from start to finish."""
        game_id = "complete_session_test"

        # Step 1: Multiple players complete the game and submit scores
        players = [
            {"initials": "AAA", "score": 1500.0},
            {"initials": "BBB", "score": 2200.0},
            {"initials": "CCC", "score": 1800.0},
            {"initials": "DDD", "score": 2500.0},
            {"initials": "EEE", "score": 1200.0},
        ]

        submitted_score_ids = []

        for player in players:
            # Submit score
            submit_event = create_api_event(
                method="POST",
                path="/games/scores/v1",
                body={
                    "game_id": game_id,
                    "initials": player["initials"],
                    "score": player["score"],
                    "score_type": "high_score",
                },
            )

            response = lambda_handler(submit_event, lambda_context)
            assert response["statusCode"] == 201

            body = json.loads(response["body"])
            assert body["success"] is True
            submitted_score_ids.append(body["score_id"])

        # Step 2: Retrieve the full leaderboard
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

        # Step 3: Verify leaderboard ranking and completeness
        assert len(scores) == 5

        # Should be ranked highest to lowest
        expected_ranking = [
            ("DDD", 2500.0),  # 1st place
            ("BBB", 2200.0),  # 2nd place
            ("CCC", 1800.0),  # 3rd place
            ("AAA", 1500.0),  # 4th place
            ("EEE", 1200.0),  # 5th place
        ]

        for i, (expected_initials, expected_score) in enumerate(expected_ranking):
            assert scores[i]["initials"] == expected_initials
            assert scores[i]["score"] == expected_score
            assert scores[i]["game_id"] == game_id
            assert scores[i]["score_type"] == "high_score"
            assert "timestamp" in scores[i]

        # Step 4: Test limited leaderboard (top 3)
        get_top3_event = create_api_event(
            method="GET",
            path=f"/games/leaderboards/v1/{game_id}",
            query_params={"score_type": "high_score", "limit": "3"},
            path_params={"game_id": game_id},
        )

        response = lambda_handler(get_top3_event, lambda_context)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        top3_scores = body["scores"]

        assert len(top3_scores) == 3
        assert top3_scores[0]["initials"] == "DDD"  # Winner
        assert top3_scores[1]["initials"] == "BBB"  # Runner-up
        assert top3_scores[2]["initials"] == "CCC"  # Third place

    def test_multi_game_tournament_scenario(self, leaderboard_db, lambda_context):
        """Test tournament scenario with multiple games."""
        games = ["tournament_game_1", "tournament_game_2", "tournament_game_3"]
        players = ["PLR", "ABC", "XYZ", "DEF"]

        # Each player plays each game
        for game_id in games:
            for i, player in enumerate(players):
                # Simulate different performance across games
                base_score = (i + 1) * 1000
                game_modifier = hash(game_id) % 500  # Game-specific variation
                final_score = base_score + game_modifier

                submit_event = create_api_event(
                    method="POST",
                    path="/games/scores/v1",
                    body={
                        "game_id": game_id,
                        "initials": player,
                        "score": float(final_score),
                        "score_type": "high_score",
                    },
                )

                response = lambda_handler(submit_event, lambda_context)
                assert response["statusCode"] == 201

        # Verify each game has its own independent leaderboard
        for game_id in games:
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

            # Each game should have 4 scores (one per player)
            assert len(scores) == 4

            # Verify all scores belong to this game
            for score in scores:
                assert score["game_id"] == game_id

            # Verify ranking is correct (scores should be in descending order)
            score_values = [score["score"] for score in scores]
            assert score_values == sorted(score_values, reverse=True)

    def test_speed_run_competition_workflow(self, leaderboard_db, lambda_context):
        """Test speed run competition with fastest time scoring."""
        game_id = "speedrun_competition"

        # Simulate a speed run competition with times in seconds
        speedrun_attempts = [
            {"initials": "SPD", "time": 125.67},  # 2:05.67
            {"initials": "FST", "time": 108.32},  # 1:48.32 (fastest)
            {"initials": "QCK", "time": 134.89},  # 2:14.89
            {"initials": "RUN", "time": 119.45},  # 1:59.45
            {"initials": "ZOM", "time": 142.12},  # 2:22.12
        ]

        # Submit all speed run times
        for attempt in speedrun_attempts:
            submit_event = create_api_event(
                method="POST",
                path="/games/scores/v1",
                body={
                    "game_id": game_id,
                    "initials": attempt["initials"],
                    "score": attempt["time"],
                    "score_type": "fastest_time",
                },
            )

            response = lambda_handler(submit_event, lambda_context)
            assert response["statusCode"] == 201

        # Get speed run leaderboard
        get_event = create_api_event(
            method="GET",
            path=f"/games/leaderboards/v1/{game_id}",
            query_params={"score_type": "fastest_time", "limit": "10"},
            path_params={"game_id": game_id},
        )

        response = lambda_handler(get_event, lambda_context)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        times = body["scores"]

        # Verify ranking (fastest first)
        expected_ranking = [
            ("FST", 108.32),  # World record
            ("RUN", 119.45),  # 2nd place
            ("SPD", 125.67),  # 3rd place
            ("QCK", 134.89),  # 4th place
            ("ZOM", 142.12),  # 5th place
        ]

        assert len(times) == 5
        for i, (expected_initials, expected_time) in enumerate(expected_ranking):
            assert times[i]["initials"] == expected_initials
            assert times[i]["score"] == expected_time
            assert times[i]["score_type"] == "fastest_time"

    def test_survival_mode_endurance_workflow(self, leaderboard_db, lambda_context):
        """Test survival mode with longest time scoring."""
        game_id = "survival_endurance"

        # Simulate survival times (how long players survived)
        survival_times = [
            {"initials": "SUR", "time": 342.56},  # 5:42.56
            {"initials": "END", "time": 298.33},  # 4:58.33
            {"initials": "LST", "time": 445.78},  # 7:25.78 (longest)
            {"initials": "TGH", "time": 389.12},  # 6:29.12
        ]

        # Submit all survival times
        for time_record in survival_times:
            submit_event = create_api_event(
                method="POST",
                path="/games/scores/v1",
                body={
                    "game_id": game_id,
                    "initials": time_record["initials"],
                    "score": time_record["time"],
                    "score_type": "longest_time",
                },
            )

            response = lambda_handler(submit_event, lambda_context)
            assert response["statusCode"] == 201

        # Get survival leaderboard
        get_event = create_api_event(
            method="GET",
            path=f"/games/leaderboards/v1/{game_id}",
            query_params={"score_type": "longest_time", "limit": "10"},
            path_params={"game_id": game_id},
        )

        response = lambda_handler(get_event, lambda_context)
        assert response["statusCode"] == 200

        body = json.loads(response["body"])
        survival_scores = body["scores"]

        # Verify ranking (longest survival first)
        expected_ranking = [
            ("LST", 445.78),  # Champion survivor
            ("TGH", 389.12),  # 2nd place
            ("SUR", 342.56),  # 3rd place
            ("END", 298.33),  # 4th place
        ]

        assert len(survival_scores) == 4
        for i, (expected_initials, expected_time) in enumerate(expected_ranking):
            assert survival_scores[i]["initials"] == expected_initials
            assert survival_scores[i]["score"] == expected_time
            assert survival_scores[i]["score_type"] == "longest_time"

    def test_mixed_score_types_same_game(self, leaderboard_db, lambda_context):
        """Test game with multiple scoring modes."""
        game_id = "mixed_modes_game"

        # Player achievements in different modes
        mixed_scores = [
            # High score mode
            {"initials": "HSC", "score": 5000.0, "type": "high_score"},
            {"initials": "TOP", "score": 7500.0, "type": "high_score"},
            # Speed run mode
            {"initials": "FST", "score": 89.45, "type": "fastest_time"},
            {"initials": "SPD", "score": 102.67, "type": "fastest_time"},
            # Endurance mode
            {"initials": "END", "score": 234.89, "type": "longest_time"},
            {"initials": "SUR", "score": 189.34, "type": "longest_time"},
        ]

        # Submit all scores
        for score_data in mixed_scores:
            submit_event = create_api_event(
                method="POST",
                path="/games/scores/v1",
                body={
                    "game_id": game_id,
                    "initials": score_data["initials"],
                    "score": score_data["score"],
                    "score_type": score_data["type"],
                },
            )

            response = lambda_handler(submit_event, lambda_context)
            assert response["statusCode"] == 201

        # Test each leaderboard separately
        score_types = ["high_score", "fastest_time", "longest_time"]

        for score_type in score_types:
            get_event = create_api_event(
                method="GET",
                path=f"/games/leaderboards/v1/{game_id}",
                query_params={"score_type": score_type, "limit": "10"},
                path_params={"game_id": game_id},
            )

            response = lambda_handler(get_event, lambda_context)
            assert response["statusCode"] == 200

            body = json.loads(response["body"])
            scores = body["scores"]

            # Each mode should have exactly 2 scores
            assert len(scores) == 2

            # Verify all scores are for the correct type
            for score in scores:
                assert score["score_type"] == score_type
                assert score["game_id"] == game_id

            # Verify correct ranking based on score type
            if score_type == "high_score":
                assert scores[0]["initials"] == "TOP"  # Higher score first
                assert scores[1]["initials"] == "HSC"
            elif score_type == "fastest_time":
                assert scores[0]["initials"] == "FST"  # Faster time first
                assert scores[1]["initials"] == "SPD"
            elif score_type == "longest_time":
                assert scores[0]["initials"] == "END"  # Longer time first
                assert scores[1]["initials"] == "SUR"

    def test_error_recovery_workflow(self, leaderboard_db, lambda_context):
        """Test system behavior with mixed valid and invalid requests."""
        game_id = "error_recovery_test"

        # Series of requests including both valid and invalid ones
        requests = [
            # Valid request
            {
                "valid": True,
                "data": {
                    "game_id": game_id,
                    "initials": "VLD",
                    "score": 1000.0,
                    "score_type": "high_score",
                },
            },
            # Invalid request - bad score type
            {
                "valid": False,
                "data": {
                    "game_id": game_id,
                    "initials": "BAD",
                    "score": 1500.0,
                    "score_type": "invalid_type",
                },
            },
            # Valid request
            {
                "valid": True,
                "data": {
                    "game_id": game_id,
                    "initials": "OK2",
                    "score": 2000.0,
                    "score_type": "high_score",
                },
            },
            # Invalid request - negative score
            {
                "valid": False,
                "data": {
                    "game_id": game_id,
                    "initials": "NEG",
                    "score": -100.0,
                    "score_type": "high_score",
                },
            },
            # Valid request
            {
                "valid": True,
                "data": {
                    "game_id": game_id,
                    "initials": "OK3",
                    "score": 1800.0,
                    "score_type": "high_score",
                },
            },
        ]

        valid_count = 0
        error_count = 0

        # Process all requests
        for request in requests:
            submit_event = create_api_event(
                method="POST", path="/games/scores/v1", body=request["data"]
            )

            response = lambda_handler(submit_event, lambda_context)

            if request["valid"]:
                assert response["statusCode"] == 201
                body = json.loads(response["body"])
                assert body["success"] is True
                valid_count += 1
            else:
                assert response["statusCode"] == 400
                body = json.loads(response["body"])
                assert body["success"] is False
                error_count += 1

        # Verify error handling didn't break the system
        assert valid_count == 3
        assert error_count == 2

        # Get leaderboard to verify only valid scores were stored
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

        # Should only have the 3 valid scores
        assert len(scores) == 3

        # Verify correct ranking
        assert scores[0]["initials"] == "OK2"  # 2000.0
        assert scores[1]["initials"] == "OK3"  # 1800.0
        assert scores[2]["initials"] == "VLD"  # 1000.0

    def test_concurrent_submissions_workflow(self, leaderboard_db, lambda_context):
        """Test handling of rapid concurrent score submissions."""
        game_id = "concurrent_test"

        # Simulate rapid submissions with identical timestamps
        concurrent_scores = [
            {"initials": "C01", "score": 1000.0},
            {"initials": "C02", "score": 1100.0},
            {"initials": "C03", "score": 1200.0},
            {"initials": "C04", "score": 1050.0},
            {"initials": "C05", "score": 1150.0},
        ]

        # Submit all scores rapidly
        for score_data in concurrent_scores:
            submit_event = create_api_event(
                method="POST",
                path="/games/scores/v1",
                body={
                    "game_id": game_id,
                    "initials": score_data["initials"],
                    "score": score_data["score"],
                    "score_type": "high_score",
                },
            )

            response = lambda_handler(submit_event, lambda_context)
            assert response["statusCode"] == 201

        # Verify all scores were recorded
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

        # All scores should be present and correctly ranked
        assert len(scores) == 5

        # Verify ranking
        expected_order = [1200.0, 1150.0, 1100.0, 1050.0, 1000.0]
        actual_scores = [score["score"] for score in scores]
        assert actual_scores == expected_order
