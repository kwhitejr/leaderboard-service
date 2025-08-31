"""DynamoDB operations for leaderboard service."""

import os
from datetime import datetime
from decimal import Decimal
from typing import Any, TypedDict

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from .models import LeaderboardEntry, ScoreRecord, ScoreType, LeaderboardType, LabelType


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

            # Score type no longer determines sorting - that's handled by leaderboard_type
            # Just use the raw score value for the sort key since we'll apply sorting logic in get_leaderboard
            sort_key_score = score_record.score

            sort_key = f"{score_type_value}#{sort_key_score:015.3f}"

            # Handle both enum and string values for label_type
            label_type_value: str
            if isinstance(score_record.label_type, LabelType):
                label_type_value = score_record.label_type.value
            else:
                label_type_value = str(score_record.label_type)

            item: dict[str, Any] = {
                "game_id": score_record.game_id,
                "sort_key": sort_key,
                "label": score_record.label,
                "label_type": label_type_value,
                "score": Decimal(str(score_record.score)),
                "score_type": score_type_value,
                "timestamp": score_record.created_at_timestamp.isoformat(),
            }

            self.table.put_item(Item=item)

        except ClientError as e:
            raise RuntimeError(f"Failed to submit score: {e}") from e

    def get_leaderboard(
        self, game_id: str, leaderboard_type: LeaderboardType, limit: int = 10
    ) -> list[LeaderboardEntry]:
        """Get leaderboard for a game and leaderboard type."""
        try:
            # Query all scores for this game (we'll filter and sort in memory)
            response = self.table.query(
                KeyConditionExpression=Key("game_id").eq(game_id),
                ScanIndexForward=True,
            )

            # Define typed dict for raw entries
            class RawEntry(TypedDict):
                label: str
                label_type: LabelType
                score: float
                created_at_timestamp: datetime

            # Convert items to simple data structures for sorting
            raw_entries: list[RawEntry] = []
            for item in response["Items"]:
                # Parse label type with fallback
                label_type_str = str(item.get("label_type", "custom"))
                try:
                    label_type = LabelType(label_type_str)
                except ValueError:
                    label_type = LabelType.CUSTOM

                raw_entries.append(
                    {
                        "label": str(item["label"]),
                        "label_type": label_type,
                        "score": float(str(item["score"])),
                        "created_at_timestamp": datetime.fromisoformat(
                            str(item["timestamp"])
                        ),
                    }
                )

            # Sort based on leaderboard type
            if (
                leaderboard_type == LeaderboardType.HIGH_SCORE
                or leaderboard_type == LeaderboardType.LONGEST_TIME
            ):
                # Higher scores rank better (descending)
                raw_entries.sort(key=lambda x: x["score"], reverse=True)
            elif leaderboard_type == LeaderboardType.FASTEST_TIME:
                # Lower scores rank better (ascending)
                raw_entries.sort(key=lambda x: x["score"])

            # Create leaderboard entries with correct ranks and limit results
            leaderboard = []
            for rank, raw_entry in enumerate(raw_entries[:limit], 1):
                entry = LeaderboardEntry(
                    rank=rank,
                    label=raw_entry["label"],
                    label_type=raw_entry["label_type"],
                    score=raw_entry["score"],
                    created_at_timestamp=raw_entry["created_at_timestamp"],
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
                try:
                    score_types.add(ScoreType(item["score_type"]))
                except ValueError:
                    # Skip invalid score types that might exist from old data
                    pass

            return list(score_types)

        except ClientError as e:
            raise RuntimeError(f"Failed to get score types: {e}") from e
