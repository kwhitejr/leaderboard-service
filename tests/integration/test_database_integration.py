"""Database integration tests.

These tests validate database operations with real DynamoDB service running in
LocalStack, including CRUD operations, query performance, data consistency,
and error handling scenarios.
"""

import pytest

from src.leaderboard.models import ScoreRecord, ScoreType
from src.leaderboard.database import LeaderboardDatabase
from botocore.exceptions import ClientError


class TestDatabaseIntegration:
    """Test database operations with real DynamoDB."""

    def test_submit_and_retrieve_single_score(
        self, leaderboard_db: LeaderboardDatabase
    ):
        """Test basic score submission and retrieval."""
        # Submit a score
        score_record = ScoreRecord(
            game_id="db_test_game",
            initials="TST",
            score=1500.0,
            score_type=ScoreType.HIGH_SCORE,
        )

        score_id = leaderboard_db.submit_score(score_record)
        assert score_id is not None
        assert len(score_id) > 0

        # Retrieve the leaderboard
        scores = leaderboard_db.get_leaderboard(
            game_id="db_test_game", score_type=ScoreType.HIGH_SCORE, limit=10
        )

        assert len(scores) == 1
        retrieved_score = scores[0]
        assert retrieved_score.game_id == "db_test_game"
        assert retrieved_score.initials == "TST"
        assert retrieved_score.score == 1500.0
        assert retrieved_score.score_type == ScoreType.HIGH_SCORE
        assert retrieved_score.timestamp is not None

    def test_multiple_scores_ranking_high_score(
        self, leaderboard_db: LeaderboardDatabase
    ):
        """Test proper ranking for high score type."""
        game_id = "ranking_test_high"
        scores_data = [
            ("P1", 1000.0),
            ("P2", 3000.0),
            ("P3", 2000.0),
            ("P4", 1500.0),
        ]

        # Submit scores
        for initials, score in scores_data:
            score_record = ScoreRecord(
                game_id=game_id,
                initials=initials,
                score=score,
                score_type=ScoreType.HIGH_SCORE,
            )
            leaderboard_db.submit_score(score_record)

        # Retrieve leaderboard
        scores = leaderboard_db.get_leaderboard(
            game_id=game_id, score_type=ScoreType.HIGH_SCORE, limit=10
        )

        # Verify ranking (highest first)
        assert len(scores) == 4
        assert scores[0].initials == "P2"  # 3000
        assert scores[0].score == 3000.0
        assert scores[1].initials == "P3"  # 2000
        assert scores[1].score == 2000.0
        assert scores[2].initials == "P4"  # 1500
        assert scores[2].score == 1500.0
        assert scores[3].initials == "P1"  # 1000
        assert scores[3].score == 1000.0

    def test_multiple_scores_ranking_fastest_time(
        self, leaderboard_db: LeaderboardDatabase
    ):
        """Test proper ranking for fastest time type."""
        game_id = "ranking_test_fast"
        scores_data = [
            ("P1", 120.5),  # 2 minutes 30 seconds
            ("P2", 95.3),  # 1 minute 35 seconds (fastest)
            ("P3", 108.7),  # 1 minute 48 seconds
            ("P4", 134.2),  # 2 minutes 14 seconds
        ]

        # Submit scores
        for initials, time_score in scores_data:
            score_record = ScoreRecord(
                game_id=game_id,
                initials=initials,
                score=time_score,
                score_type=ScoreType.FASTEST_TIME,
            )
            leaderboard_db.submit_score(score_record)

        # Retrieve leaderboard
        scores = leaderboard_db.get_leaderboard(
            game_id=game_id, score_type=ScoreType.FASTEST_TIME, limit=10
        )

        # Verify ranking (fastest/lowest first)
        assert len(scores) == 4
        assert scores[0].initials == "P2"  # 95.3 (fastest)
        assert scores[0].score == 95.3
        assert scores[1].initials == "P3"  # 108.7
        assert scores[1].score == 108.7
        assert scores[2].initials == "P1"  # 120.5
        assert scores[2].score == 120.5
        assert scores[3].initials == "P4"  # 134.2 (slowest)
        assert scores[3].score == 134.2

    def test_multiple_scores_ranking_longest_time(
        self, leaderboard_db: LeaderboardDatabase
    ):
        """Test proper ranking for longest time type."""
        game_id = "ranking_test_long"
        scores_data = [
            ("P1", 45.2),  # 45 seconds
            ("P2", 67.8),  # 1 minute 7 seconds (longest)
            ("P3", 52.4),  # 52 seconds
            ("P4", 38.9),  # 38 seconds
        ]

        # Submit scores
        for initials, time_score in scores_data:
            score_record = ScoreRecord(
                game_id=game_id,
                initials=initials,
                score=time_score,
                score_type=ScoreType.LONGEST_TIME,
            )
            leaderboard_db.submit_score(score_record)

        # Retrieve leaderboard
        scores = leaderboard_db.get_leaderboard(
            game_id=game_id, score_type=ScoreType.LONGEST_TIME, limit=10
        )

        # Verify ranking (longest/highest first)
        assert len(scores) == 4
        assert scores[0].initials == "P2"  # 67.8 (longest)
        assert scores[0].score == 67.8
        assert scores[1].initials == "P3"  # 52.4
        assert scores[1].score == 52.4
        assert scores[2].initials == "P1"  # 45.2
        assert scores[2].score == 45.2
        assert scores[3].initials == "P4"  # 38.9 (shortest)
        assert scores[3].score == 38.9

    def test_limit_parameter_functionality(self, leaderboard_db: LeaderboardDatabase):
        """Test leaderboard limit parameter."""
        game_id = "limit_test_db"

        # Submit 10 scores
        for i in range(10):
            score_record = ScoreRecord(
                game_id=game_id,
                initials=f"P{i:02d}",
                score=float((i + 1) * 100),
                score_type=ScoreType.HIGH_SCORE,
            )
            leaderboard_db.submit_score(score_record)

        # Test different limits
        for limit in [3, 5, 8]:
            scores = leaderboard_db.get_leaderboard(
                game_id=game_id, score_type=ScoreType.HIGH_SCORE, limit=limit
            )
            assert len(scores) == limit

            # Verify they're the top scores
            expected_scores = list(range(1000, 1000 - (limit * 100), -100))
            actual_scores = [int(score.score) for score in scores]
            assert actual_scores == expected_scores

    def test_empty_leaderboard(self, leaderboard_db: LeaderboardDatabase):
        """Test retrieving empty leaderboard."""
        scores = leaderboard_db.get_leaderboard(
            game_id="nonexistent_game", score_type=ScoreType.HIGH_SCORE, limit=10
        )
        assert scores == []

    def test_different_score_types_isolation(self, leaderboard_db: LeaderboardDatabase):
        """Test that different score types are properly isolated."""
        game_id = "isolation_test"

        # Submit scores for different types
        high_score = ScoreRecord(
            game_id=game_id,
            initials="HGH",
            score=5000.0,
            score_type=ScoreType.HIGH_SCORE,
        )
        fast_time = ScoreRecord(
            game_id=game_id,
            initials="FST",
            score=89.5,
            score_type=ScoreType.FASTEST_TIME,
        )
        long_time = ScoreRecord(
            game_id=game_id,
            initials="LNG",
            score=245.8,
            score_type=ScoreType.LONGEST_TIME,
        )

        leaderboard_db.submit_score(high_score)
        leaderboard_db.submit_score(fast_time)
        leaderboard_db.submit_score(long_time)

        # Verify each leaderboard only contains its own type
        high_scores = leaderboard_db.get_leaderboard(
            game_id=game_id, score_type=ScoreType.HIGH_SCORE, limit=10
        )
        assert len(high_scores) == 1
        assert high_scores[0].initials == "HGH"

        fast_scores = leaderboard_db.get_leaderboard(
            game_id=game_id, score_type=ScoreType.FASTEST_TIME, limit=10
        )
        assert len(fast_scores) == 1
        assert fast_scores[0].initials == "FST"

        long_scores = leaderboard_db.get_leaderboard(
            game_id=game_id, score_type=ScoreType.LONGEST_TIME, limit=10
        )
        assert len(long_scores) == 1
        assert long_scores[0].initials == "LNG"

    def test_different_games_isolation(self, leaderboard_db: LeaderboardDatabase):
        """Test that different games are properly isolated."""
        # Submit scores for different games
        game1_score = ScoreRecord(
            game_id="game_1",
            initials="G1P",
            score=1000.0,
            score_type=ScoreType.HIGH_SCORE,
        )
        game2_score = ScoreRecord(
            game_id="game_2",
            initials="G2P",
            score=2000.0,
            score_type=ScoreType.HIGH_SCORE,
        )

        leaderboard_db.submit_score(game1_score)
        leaderboard_db.submit_score(game2_score)

        # Verify each game only contains its own scores
        game1_scores = leaderboard_db.get_leaderboard(
            game_id="game_1", score_type=ScoreType.HIGH_SCORE, limit=10
        )
        assert len(game1_scores) == 1
        assert game1_scores[0].initials == "G1P"
        assert game1_scores[0].score == 1000.0

        game2_scores = leaderboard_db.get_leaderboard(
            game_id="game_2", score_type=ScoreType.HIGH_SCORE, limit=10
        )
        assert len(game2_scores) == 1
        assert game2_scores[0].initials == "G2P"
        assert game2_scores[0].score == 2000.0

    def test_get_all_score_types_for_game(self, leaderboard_db: LeaderboardDatabase):
        """Test retrieving all available score types for a game."""
        game_id = "score_types_test"

        # Submit scores for different types
        scores = [
            ScoreRecord(
                game_id=game_id,
                initials="H1",
                score=1000.0,
                score_type=ScoreType.HIGH_SCORE,
            ),
            ScoreRecord(
                game_id=game_id,
                initials="F1",
                score=60.5,
                score_type=ScoreType.FASTEST_TIME,
            ),
        ]

        for score in scores:
            leaderboard_db.submit_score(score)

        # Get all score types
        score_types = leaderboard_db.get_all_score_types_for_game(game_id)

        assert len(score_types) == 2
        assert ScoreType.HIGH_SCORE in score_types
        assert ScoreType.FASTEST_TIME in score_types
        assert ScoreType.LONGEST_TIME not in score_types

    def test_timestamp_ordering_with_identical_scores(
        self, leaderboard_db: LeaderboardDatabase
    ):
        """Test that identical scores are ordered by timestamp."""
        game_id = "timestamp_test"
        identical_score = 1000.0

        # Submit identical scores with slight delays
        import time

        initials_list = ["P1", "P2", "P3"]

        for initials in initials_list:
            score_record = ScoreRecord(
                game_id=game_id,
                initials=initials,
                score=identical_score,
                score_type=ScoreType.HIGH_SCORE,
            )
            leaderboard_db.submit_score(score_record)
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # Retrieve scores
        scores = leaderboard_db.get_leaderboard(
            game_id=game_id, score_type=ScoreType.HIGH_SCORE, limit=10
        )

        assert len(scores) == 3
        # All should have the same score
        for score in scores:
            assert score.score == identical_score

        # Should be ordered by timestamp (first submitted first in case of ties)
        assert scores[0].initials == "P1"
        assert scores[1].initials == "P2"
        assert scores[2].initials == "P3"

    def test_decimal_precision_handling(self, leaderboard_db: LeaderboardDatabase):
        """Test that decimal precision is maintained in DynamoDB."""
        game_id = "precision_test"
        precise_score = 1234.56789

        score_record = ScoreRecord(
            game_id=game_id,
            initials="PRC",
            score=precise_score,
            score_type=ScoreType.HIGH_SCORE,
        )

        leaderboard_db.submit_score(score_record)

        # Retrieve and verify precision
        scores = leaderboard_db.get_leaderboard(
            game_id=game_id, score_type=ScoreType.HIGH_SCORE, limit=1
        )

        assert len(scores) == 1
        # DynamoDB stores as Decimal, but our model converts back to float
        assert abs(scores[0].score - precise_score) < 1e-10

    def test_large_dataset_performance(self, leaderboard_db: LeaderboardDatabase):
        """Test performance with larger dataset."""
        game_id = "performance_test"
        num_scores = 50

        # Submit many scores
        for i in range(num_scores):
            score_record = ScoreRecord(
                game_id=game_id,
                initials=f"P{i:02d}",
                score=float(i * 10),
                score_type=ScoreType.HIGH_SCORE,
            )
            leaderboard_db.submit_score(score_record)

        # Test retrieval with various limits
        import time

        start_time = time.time()
        scores = leaderboard_db.get_leaderboard(
            game_id=game_id, score_type=ScoreType.HIGH_SCORE, limit=10
        )
        end_time = time.time()

        # Verify results
        assert len(scores) == 10
        query_time = end_time - start_time

        # Query should be fast (less than 1 second for this dataset size)
        assert query_time < 1.0

        # Verify top scores are correct (highest first)
        expected_top_score = float((num_scores - 1) * 10)  # P49 with score 490
        assert scores[0].score == expected_top_score

    def test_database_error_handling(self, leaderboard_db: LeaderboardDatabase):
        """Test database error scenarios."""
        # Test with malformed table name to trigger potential errors
        original_table = leaderboard_db.table

        # Create a mock table that will cause errors
        from unittest.mock import Mock

        # Mock a table that raises ClientError on operations
        mock_table = Mock()
        mock_table.put_item.side_effect = ClientError(
            error_response={
                "Error": {"Code": "ValidationException", "Message": "Test error"}
            },
            operation_name="PutItem",
        )

        leaderboard_db.table = mock_table

        # Test that submit_score handles database errors
        score_record = ScoreRecord(
            game_id="error_test",
            initials="ERR",
            score=1000.0,
            score_type=ScoreType.HIGH_SCORE,
        )

        with pytest.raises(Exception):  # Should propagate the database error
            leaderboard_db.submit_score(score_record)

        # Restore original table
        leaderboard_db.table = original_table
