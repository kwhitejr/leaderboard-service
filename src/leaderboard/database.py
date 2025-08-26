"""DynamoDB operations for leaderboard service."""

import os
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from .models import LeaderboardEntry, ScoreRecord, ScoreType


class LeaderboardDatabase:
    """DynamoDB operations for leaderboard data."""

    def __init__(self, table_name: str | None = None) -> None:
        """Initialize database connection."""
        resolved_table_name = table_name or os.environ.get(
            "LEADERBOARD_TABLE", "leaderboard-scores"
        )
        if not resolved_table_name:
            raise ValueError("Table name must be provided")
        self.table_name = resolved_table_name
        region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.table = self.dynamodb.Table(self.table_name)

    def submit_score(self, score_record: ScoreRecord) -> None:
        """Submit a score to the leaderboard."""
        try:
            # Create composite sort key: score_type#score_value
            # For high_score: use negative score for descending order
            # For fastest_time: use positive score for ascending order
            # For longest_time: use negative score for descending order

            # Handle both enum and string values for score_type
            score_type_value: str
            if isinstance(score_record.score_type, ScoreType):
                score_type_value = score_record.score_type.value
            else:
                score_type_value = str(score_record.score_type)

            if score_type_value == ScoreType.FASTEST_TIME.value:
                # For fastest time, lower is better, so use positive score for ascending order
                sort_key_score = score_record.score
            elif score_type_value == ScoreType.HIGH_SCORE.value:
                # For high score, higher is better, so use negative score for descending order
                # But we need the sort to work correctly: higher scores should sort first
                # Since DynamoDB sorts ascending, we use (max_possible_score - actual_score)
                sort_key_score = 999999999 - score_record.score
            else:  # LONGEST_TIME
                # For longest time, higher is better, so same logic as high score
                sort_key_score = 999999999 - score_record.score

            sort_key = f"{score_type_value}#{sort_key_score:015.3f}"

            item: Dict[str, Any] = {
                "game_id": score_record.game_id,
                "sort_key": sort_key,
                "initials": score_record.initials,
                "score": Decimal(str(score_record.score)),
                "score_type": score_type_value,
                "timestamp": score_record.timestamp.isoformat(),
            }

            self.table.put_item(Item=item)

        except ClientError as e:
            raise RuntimeError(f"Failed to submit score: {e}") from e

    def get_leaderboard(
        self, game_id: str, score_type: ScoreType, limit: int = 10
    ) -> list[LeaderboardEntry]:
        """Get leaderboard for a game and score type."""
        try:
            # Handle both enum and string values for score_type
            score_type_value: str
            if isinstance(score_type, ScoreType):
                score_type_value = score_type.value
            else:
                score_type_value = str(score_type)

            # Query with begins_with to get all scores for this type
            response = self.table.query(
                KeyConditionExpression=Key("game_id").eq(game_id)
                & Key("sort_key").begins_with(f"{score_type_value}#"),
                Limit=limit,
                ScanIndexForward=True,  # Ascending order (best scores first due to our key design)
            )

            leaderboard = []
            for rank, item in enumerate(response["Items"], 1):
                entry = LeaderboardEntry(
                    rank=rank,
                    initials=str(item["initials"]),
                    score=float(item["score"]),
                    timestamp=datetime.fromisoformat(str(item["timestamp"])),
                )
                leaderboard.append(entry)

            return leaderboard

        except ClientError as e:
            raise RuntimeError(f"Failed to get leaderboard: {e}") from e

    def get_all_score_types_for_game(self, game_id: str) -> list[ScoreType]:
        """Get all score types that exist for a game."""
        try:
            response = self.table.query(
                KeyConditionExpression=Key("game_id").eq(game_id),
                ProjectionExpression="score_type",
            )

            score_types = set()
            for item in response["Items"]:
                score_types.add(ScoreType(item["score_type"]))

            return list(score_types)

        except ClientError as e:
            raise RuntimeError(f"Failed to get score types: {e}") from e
