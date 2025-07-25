"""DynamoDB operations for leaderboard service."""

import os
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from .models import LeaderboardEntry, ScoreRecord, ScoreType


class LeaderboardDatabase:
    """DynamoDB operations for leaderboard data."""
    
    def __init__(self, table_name: Optional[str] = None) -> None:
        """Initialize database connection."""
        self.table_name = table_name or os.environ.get("LEADERBOARD_TABLE", "leaderboard-scores")
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(self.table_name)
    
    def submit_score(self, score_record: ScoreRecord) -> None:
        """Submit a score to the leaderboard."""
        try:
            # Create composite sort key: score_type#score_value
            # For high_score: use negative score for descending order
            # For fastest_time: use positive score for ascending order
            # For longest_time: use negative score for descending order
            
            if score_record.score_type == ScoreType.FASTEST_TIME:
                sort_key_score = score_record.score
            else:  # HIGH_SCORE or LONGEST_TIME
                sort_key_score = -score_record.score
            
            sort_key = f"{score_record.score_type.value}#{sort_key_score:015.3f}"
            
            item = {
                "game_id": score_record.game_id,
                "sort_key": sort_key,
                "initials": score_record.initials,
                "score": Decimal(str(score_record.score)),
                "score_type": score_record.score_type.value,
                "timestamp": score_record.timestamp.isoformat(),
            }
            
            self.table.put_item(Item=item)
            
        except ClientError as e:
            raise RuntimeError(f"Failed to submit score: {e}")
    
    def get_leaderboard(
        self,
        game_id: str,
        score_type: ScoreType,
        limit: int = 10
    ) -> List[LeaderboardEntry]:
        """Get leaderboard for a game and score type."""
        try:
            # Query with begins_with to get all scores for this type
            response = self.table.query(
                KeyConditionExpression=Key("game_id").eq(game_id) & 
                                     Key("sort_key").begins_with(f"{score_type.value}#"),
                Limit=limit,
                ScanIndexForward=True  # Ascending order (best scores first due to our key design)
            )
            
            leaderboard = []
            for rank, item in enumerate(response["Items"], 1):
                entry = LeaderboardEntry(
                    rank=rank,
                    initials=item["initials"],
                    score=float(item["score"]),
                    timestamp=datetime.fromisoformat(item["timestamp"])
                )
                leaderboard.append(entry)
            
            return leaderboard
            
        except ClientError as e:
            raise RuntimeError(f"Failed to get leaderboard: {e}")
    
    def get_all_score_types_for_game(self, game_id: str) -> List[ScoreType]:
        """Get all score types that exist for a game."""
        try:
            response = self.table.query(
                KeyConditionExpression=Key("game_id").eq(game_id),
                ProjectionExpression="score_type"
            )
            
            score_types = set()
            for item in response["Items"]:
                score_types.add(ScoreType(item["score_type"]))
            
            return list(score_types)
            
        except ClientError as e:
            raise RuntimeError(f"Failed to get score types: {e}")