"""Tests for leaderboard database operations."""

from datetime import datetime

import boto3
from moto import mock_aws
import pytest
from unittest.mock import patch
from botocore.exceptions import ClientError

from src.leaderboard.database import LeaderboardDatabase
from src.leaderboard.models import LabelType, ScoreRecord, ScoreType


@mock_aws
class TestLeaderboardDatabase:
    """Tests for LeaderboardDatabase class."""

    def setup_method(self, method) -> None:
        """Set up test fixtures."""
        # Create the DynamoDB table for testing
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="test-table",
            KeySchema=[
                {"AttributeName": "game_id", "KeyType": "HASH"},
                {"AttributeName": "sort_key", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "game_id", "AttributeType": "S"},
                {"AttributeName": "sort_key", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        self.db = LeaderboardDatabase("test-table")

    def test_submit_score_high_score(self) -> None:
        """Test submitting a high score."""
        # Create test data
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        score_record = ScoreRecord(
            game_id="snake_classic",
            label="KMW",
            label_type=LabelType.INITIALS,
            score=103.0,
            score_type=ScoreType.HIGH_SCORE,
            timestamp=timestamp,
        )

        # Execute
        self.db.submit_score(score_record)

        # Verify by reading back from table
        response = self.db.table.get_item(
            Key={"game_id": "snake_classic", "sort_key": "high_score#00999999896.000"}
        )

        assert "Item" in response
        item = response["Item"]
        assert item["game_id"] == "snake_classic"
        assert item["label"] == "KMW"
        assert item["label_type"] == "initials"
        assert float(item["score"]) == 103.0
        assert item["score_type"] == "high_score"

    def test_submit_score_fastest_time(self) -> None:
        """Test submitting a fastest time score."""
        # Create test data
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        score_record = ScoreRecord(
            game_id="race_game",
            label="AMY",
            label_type=LabelType.INITIALS,
            score=34.7,
            score_type=ScoreType.FASTEST_TIME,
            timestamp=timestamp,
        )

        # Execute
        self.db.submit_score(score_record)

        # Verify by reading back from table
        response = self.db.table.get_item(
            Key={"game_id": "race_game", "sort_key": "fastest_time#00000000034.700"}
        )

        assert "Item" in response
        item = response["Item"]
        assert item["game_id"] == "race_game"
        assert item["label"] == "AMY"
        assert item["label_type"] == "initials"
        assert float(item["score"]) == 34.7
        assert item["score_type"] == "fastest_time"

    def test_get_leaderboard(self) -> None:
        """Test getting leaderboard."""
        # Set up test data - submit a few scores
        scores = [
            ScoreRecord(
                game_id="snake_classic",
                label="KMW",
                label_type=LabelType.INITIALS,
                score=103.0,
                score_type=ScoreType.HIGH_SCORE,
                timestamp=datetime(2024, 1, 15, 10, 30, 0),
            ),
            ScoreRecord(
                game_id="snake_classic",
                label="AMY",
                label_type=LabelType.INITIALS,
                score=95.0,
                score_type=ScoreType.HIGH_SCORE,
                timestamp=datetime(2024, 1, 14, 15, 20, 0),
            ),
            ScoreRecord(
                game_id="snake_classic",
                label="BOB",
                label_type=LabelType.INITIALS,
                score=87.0,
                score_type=ScoreType.HIGH_SCORE,
                timestamp=datetime(2024, 1, 13, 12, 10, 0),
            ),
        ]

        # Submit scores
        for score in scores:
            self.db.submit_score(score)

        # Execute
        leaderboard = self.db.get_leaderboard("snake_classic", ScoreType.HIGH_SCORE, 10)

        # Verify
        assert len(leaderboard) == 3
        assert leaderboard[0].rank == 1
        assert leaderboard[0].label == "KMW"
        assert leaderboard[0].score == 103.0
        assert leaderboard[1].rank == 2
        assert leaderboard[1].label == "AMY"
        assert leaderboard[1].score == 95.0
        assert leaderboard[2].rank == 3
        assert leaderboard[2].label == "BOB"
        assert leaderboard[2].score == 87.0

    def test_get_leaderboard_fastest_time(self) -> None:
        """Test getting leaderboard for fastest time (ascending order)."""
        # Set up test data - submit times (lower is better)
        scores = [
            ScoreRecord(
                game_id="race_game",
                label="AMY",
                label_type=LabelType.INITIALS,
                score=34.7,
                score_type=ScoreType.FASTEST_TIME,
                timestamp=datetime(2024, 1, 15, 10, 30, 0),
            ),
            ScoreRecord(
                game_id="race_game",
                label="BOB",
                label_type=LabelType.INITIALS,
                score=45.2,
                score_type=ScoreType.FASTEST_TIME,
                timestamp=datetime(2024, 1, 14, 15, 20, 0),
            ),
            ScoreRecord(
                game_id="race_game",
                label="KMW",
                label_type=LabelType.INITIALS,
                score=32.1,
                score_type=ScoreType.FASTEST_TIME,
                timestamp=datetime(2024, 1, 13, 12, 10, 0),
            ),
        ]

        # Submit scores
        for score in scores:
            self.db.submit_score(score)

        # Execute
        leaderboard = self.db.get_leaderboard("race_game", ScoreType.FASTEST_TIME, 10)

        # Verify - fastest time should be first
        assert len(leaderboard) == 3
        assert leaderboard[0].rank == 1
        assert leaderboard[0].label == "KMW"
        assert leaderboard[0].score == 32.1
        assert leaderboard[1].rank == 2
        assert leaderboard[1].label == "AMY"
        assert leaderboard[1].score == 34.7
        assert leaderboard[2].rank == 3
        assert leaderboard[2].label == "BOB"
        assert leaderboard[2].score == 45.2

    def test_submit_score_longest_time(self) -> None:
        """Test submitting a longest time score."""
        # Create test data
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        score_record = ScoreRecord(
            game_id="survival_game",
            label="JOE",
            label_type=LabelType.INITIALS,
            score=245.8,
            score_type=ScoreType.LONGEST_TIME,
            timestamp=timestamp,
        )

        # Execute
        self.db.submit_score(score_record)

        # Verify by reading back from table
        # For longest time, higher score is better, so uses same logic as high score
        # 999999999 - 245.8 = 999999753.2, formatted with padding
        response = self.db.table.get_item(
            Key={"game_id": "survival_game", "sort_key": "longest_time#00999999753.200"}
        )

        assert "Item" in response
        item = response["Item"]
        assert item["game_id"] == "survival_game"
        assert item["label"] == "JOE"
        assert float(item["score"]) == 245.8
        assert item["score_type"] == "longest_time"

    def test_get_leaderboard_longest_time(self) -> None:
        """Test getting leaderboard for longest time (descending order)."""
        # Set up test data - submit times (higher is better)
        scores = [
            ScoreRecord(
                game_id="survival_game",
                label="JOE",
                label_type=LabelType.INITIALS,
                score=245.8,
                score_type=ScoreType.LONGEST_TIME,
                timestamp=datetime(2024, 1, 15, 10, 30, 0),
            ),
            ScoreRecord(
                game_id="survival_game",
                label="AMY",
                label_type=LabelType.INITIALS,
                score=892.3,
                score_type=ScoreType.LONGEST_TIME,
                timestamp=datetime(2024, 1, 14, 15, 20, 0),
            ),
            ScoreRecord(
                game_id="survival_game",
                label="BOB",
                label_type=LabelType.INITIALS,
                score=156.7,
                score_type=ScoreType.LONGEST_TIME,
                timestamp=datetime(2024, 1, 13, 12, 10, 0),
            ),
        ]

        # Submit scores
        for score in scores:
            self.db.submit_score(score)

        # Execute
        leaderboard = self.db.get_leaderboard(
            "survival_game", ScoreType.LONGEST_TIME, 10
        )

        # Verify - longest time should be first
        assert len(leaderboard) == 3
        assert leaderboard[0].rank == 1
        assert leaderboard[0].label == "AMY"
        assert leaderboard[0].score == 892.3
        assert leaderboard[1].rank == 2
        assert leaderboard[1].label == "JOE"
        assert leaderboard[1].score == 245.8
        assert leaderboard[2].rank == 3
        assert leaderboard[2].label == "BOB"
        assert leaderboard[2].score == 156.7

    def test_get_leaderboard_with_string_score_type(self) -> None:
        """Test getting leaderboard when score_type is passed as string."""
        # Set up test data
        score_record = ScoreRecord(
            game_id="test_game",
            label="TST",
            label_type=LabelType.INITIALS,
            score=100.0,
            score_type=ScoreType.HIGH_SCORE,
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
        )
        self.db.submit_score(score_record)

        # Execute with string score type (this tests line 35 in database.py)
        leaderboard = self.db.get_leaderboard("test_game", "high_score", 10)

        # Verify
        assert len(leaderboard) == 1
        assert leaderboard[0].label == "TST"
        assert leaderboard[0].score == 100.0

    def test_get_all_score_types_for_game(self) -> None:
        """Test getting all score types for a game."""
        # Set up test data with different score types
        scores = [
            ScoreRecord(
                game_id="multi_game",
                label="HS1",
                label_type=LabelType.INITIALS,
                score=100.0,
                score_type=ScoreType.HIGH_SCORE,
                timestamp=datetime(2024, 1, 15, 10, 30, 0),
            ),
            ScoreRecord(
                game_id="multi_game",
                label="FT1",
                label_type=LabelType.INITIALS,
                score=45.2,
                score_type=ScoreType.FASTEST_TIME,
                timestamp=datetime(2024, 1, 14, 15, 20, 0),
            ),
            ScoreRecord(
                game_id="multi_game",
                label="LT1",
                label_type=LabelType.INITIALS,
                score=120.7,
                score_type=ScoreType.LONGEST_TIME,
                timestamp=datetime(2024, 1, 13, 12, 10, 0),
            ),
        ]

        for score in scores:
            self.db.submit_score(score)

        # Execute
        score_types = self.db.get_all_score_types_for_game("multi_game")

        # Verify all three score types are present
        assert len(score_types) == 3
        assert ScoreType.HIGH_SCORE in score_types
        assert ScoreType.FASTEST_TIME in score_types
        assert ScoreType.LONGEST_TIME in score_types

    def test_submit_score_database_error(self) -> None:
        """Test submit_score handles DynamoDB errors."""
        # Mock the table's put_item method to raise ClientError
        with patch.object(self.db.table, "put_item") as mock_put_item:
            mock_put_item.side_effect = ClientError(
                error_response={
                    "Error": {"Code": "ValidationException", "Message": "Test error"}
                },
                operation_name="PutItem",
            )

            score_record = ScoreRecord(
                game_id="test_game",
                label="TST",
                label_type=LabelType.INITIALS,
                score=100.0,
                score_type=ScoreType.HIGH_SCORE,
                timestamp=datetime(2024, 1, 15, 10, 30, 0),
            )

            # Should raise RuntimeError
            with pytest.raises(RuntimeError, match="Failed to submit score"):
                self.db.submit_score(score_record)

    def test_get_leaderboard_database_error(self) -> None:
        """Test get_leaderboard handles DynamoDB errors."""
        # Mock the table's query method to raise ClientError
        with patch.object(self.db.table, "query") as mock_query:
            mock_query.side_effect = ClientError(
                error_response={
                    "Error": {
                        "Code": "ResourceNotFoundException",
                        "Message": "Test error",
                    }
                },
                operation_name="Query",
            )

            # Should raise RuntimeError
            with pytest.raises(RuntimeError, match="Failed to get leaderboard"):
                self.db.get_leaderboard("test_game", ScoreType.HIGH_SCORE, 10)

    def test_submit_score_with_string_score_type(self) -> None:
        """Test submit_score when score_type is already a string value."""
        # Create a score record and manually set score_type to string to test line 35
        score_record = ScoreRecord(
            game_id="test_game",
            label="STR",
            label_type=LabelType.INITIALS,
            score=123.0,
            score_type=ScoreType.HIGH_SCORE,
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
        )

        # Manually override the score_type to be a string instead of enum
        # This simulates the case where score_type comes in as a string
        score_record.score_type = "high_score"  # This will cause line 35 to NOT execute

        # Execute - this should work and cover the string handling path
        self.db.submit_score(score_record)

        # Verify it was stored correctly
        response = self.db.table.get_item(
            Key={
                "game_id": "test_game",
                "sort_key": "high_score#00999999876.000",  # 999999999 - 123 = 999999876
            }
        )

        assert "Item" in response
        item = response["Item"]
        assert item["game_id"] == "test_game"
        assert item["label"] == "STR"
        assert float(item["score"]) == 123.0
        assert item["score_type"] == "high_score"

    def test_submit_score_enum_conversion(self) -> None:
        """Test that line 35 is executed when score_type is an enum."""
        # This test specifically ensures that the enum->string conversion is tested
        score_record = ScoreRecord(
            game_id="enum_test",
            label="ENM",
            label_type=LabelType.INITIALS,
            score=456.0,
            score_type=ScoreType.FASTEST_TIME,  # Explicitly use enum
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
        )

        # Since ScoreRecord uses use_enum_values=True, score_type becomes a string
        # To test the enum branch in database.py line 35, we need to manually set it back to enum
        score_record.score_type = ScoreType.FASTEST_TIME  # Force enum for the test

        # This should hit line 35: score_type_value = score_type_value.value
        self.db.submit_score(score_record)

        # Verify the score was stored correctly by retrieving it
        result = self.db.get_leaderboard("enum_test", ScoreType.FASTEST_TIME, 5)
        assert len(result) == 1
        assert result[0].label == "ENM"

        # Verify it was stored correctly with fastest_time logic
        response = self.db.table.get_item(
            Key={
                "game_id": "enum_test",
                "sort_key": "fastest_time#00000000456.000",  # For fastest_time, use positive score
            }
        )

        assert "Item" in response
        item = response["Item"]
        assert item["game_id"] == "enum_test"
        assert item["label"] == "ENM"
        assert float(item["score"]) == 456.0
        assert item["score_type"] == "fastest_time"

    def test_get_all_score_types_database_error(self) -> None:
        """Test get_all_score_types_for_game handles DynamoDB errors."""
        # Mock the table's query method to raise ClientError
        with patch.object(self.db.table, "query") as mock_query:
            mock_query.side_effect = ClientError(
                error_response={
                    "Error": {
                        "Code": "ResourceNotFoundException",
                        "Message": "Test error",
                    }
                },
                operation_name="Query",
            )

            # Should raise RuntimeError
            with pytest.raises(RuntimeError, match="Failed to get score types"):
                self.db.get_all_score_types_for_game("test_game")
