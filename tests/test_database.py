"""Tests for leaderboard database operations."""

from datetime import datetime

import boto3
from moto import mock_dynamodb

from src.leaderboard.database import LeaderboardDatabase
from src.leaderboard.models import ScoreRecord, ScoreType


@mock_dynamodb
class TestLeaderboardDatabase:
    """Tests for LeaderboardDatabase class."""
    
    def setup_method(self, method) -> None:
        """Set up test fixtures."""
        # Create the DynamoDB table for testing
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="test-table",
            KeySchema=[
                {"AttributeName": "game_id", "KeyType": "HASH"},
                {"AttributeName": "sort_key", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "game_id", "AttributeType": "S"},
                {"AttributeName": "sort_key", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        
        self.db = LeaderboardDatabase("test-table")
    
    def test_submit_score_high_score(self) -> None:
        """Test submitting a high score."""
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
        self.db.submit_score(score_record)
        
        # Verify by reading back from table
        response = self.db.table.get_item(
            Key={
                "game_id": "snake_classic",
                "sort_key": "high_score#00999999896.000"
            }
        )
        
        assert "Item" in response
        item = response["Item"]
        assert item["game_id"] == "snake_classic"
        assert item["initials"] == "KMW"
        assert float(item["score"]) == 103.0
        assert item["score_type"] == "high_score"
    
    def test_submit_score_fastest_time(self) -> None:
        """Test submitting a fastest time score."""
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
        self.db.submit_score(score_record)
        
        # Verify by reading back from table
        response = self.db.table.get_item(
            Key={
                "game_id": "race_game",
                "sort_key": "fastest_time#00000000034.700"
            }
        )
        
        assert "Item" in response
        item = response["Item"]
        assert item["game_id"] == "race_game"
        assert item["initials"] == "AMY"
        assert float(item["score"]) == 34.7
        assert item["score_type"] == "fastest_time"
    
    def test_get_leaderboard(self) -> None:
        """Test getting leaderboard."""
        # Set up test data - submit a few scores
        scores = [
            ScoreRecord(
                game_id="snake_classic",
                initials="KMW",
                score=103.0,
                score_type=ScoreType.HIGH_SCORE,
                timestamp=datetime(2024, 1, 15, 10, 30, 0)
            ),
            ScoreRecord(
                game_id="snake_classic", 
                initials="AMY",
                score=95.0,
                score_type=ScoreType.HIGH_SCORE,
                timestamp=datetime(2024, 1, 14, 15, 20, 0)
            ),
            ScoreRecord(
                game_id="snake_classic",
                initials="BOB", 
                score=87.0,
                score_type=ScoreType.HIGH_SCORE,
                timestamp=datetime(2024, 1, 13, 12, 10, 0)
            )
        ]
        
        # Submit scores
        for score in scores:
            self.db.submit_score(score)
        
        # Execute
        leaderboard = self.db.get_leaderboard("snake_classic", ScoreType.HIGH_SCORE, 10)
        
        # Verify
        assert len(leaderboard) == 3
        assert leaderboard[0].rank == 1
        assert leaderboard[0].initials == "KMW"
        assert leaderboard[0].score == 103.0
        assert leaderboard[1].rank == 2
        assert leaderboard[1].initials == "AMY"
        assert leaderboard[1].score == 95.0
        assert leaderboard[2].rank == 3
        assert leaderboard[2].initials == "BOB"
        assert leaderboard[2].score == 87.0
    
    def test_get_leaderboard_fastest_time(self) -> None:
        """Test getting leaderboard for fastest time (ascending order)."""
        # Set up test data - submit times (lower is better)
        scores = [
            ScoreRecord(
                game_id="race_game",
                initials="AMY",
                score=34.7,
                score_type=ScoreType.FASTEST_TIME,
                timestamp=datetime(2024, 1, 15, 10, 30, 0)
            ),
            ScoreRecord(
                game_id="race_game",
                initials="BOB",
                score=45.2,
                score_type=ScoreType.FASTEST_TIME,
                timestamp=datetime(2024, 1, 14, 15, 20, 0)
            ),
            ScoreRecord(
                game_id="race_game",
                initials="KMW",
                score=32.1,
                score_type=ScoreType.FASTEST_TIME,
                timestamp=datetime(2024, 1, 13, 12, 10, 0)
            )
        ]
        
        # Submit scores
        for score in scores:
            self.db.submit_score(score)
        
        # Execute
        leaderboard = self.db.get_leaderboard("race_game", ScoreType.FASTEST_TIME, 10)
        
        # Verify - fastest time should be first
        assert len(leaderboard) == 3
        assert leaderboard[0].rank == 1
        assert leaderboard[0].initials == "KMW"
        assert leaderboard[0].score == 32.1
        assert leaderboard[1].rank == 2
        assert leaderboard[1].initials == "AMY"
        assert leaderboard[1].score == 34.7
        assert leaderboard[2].rank == 3
        assert leaderboard[2].initials == "BOB"
        assert leaderboard[2].score == 45.2