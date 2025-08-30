"""Data models for leaderboard service."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class ScoreType(str, Enum):
    """Supported score types for leaderboards."""

    HIGH_SCORE = "HIGH_SCORE"
    FASTEST_TIME = "FASTEST_TIME"
    LONGEST_TIME = "LONGEST_TIME"


class LabelType(str, Enum):
    """Supported label types for player identification."""

    INITIALS = "INITIALS"
    USERNAME = "USERNAME"
    TEAM_NAME = "TEAM_NAME"
    CUSTOM = "CUSTOM"


class ScoreSubmission(BaseModel):
    """Model for score submission requests."""

    game_id: str = Field(
        ..., min_length=1, max_length=50, description="Game identifier"
    )
    label: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Player identifier (username, team name, etc.)",
    )
    label_type: LabelType = Field(
        default=LabelType.CUSTOM, description="Type of player label"
    )
    score: float = Field(..., ge=0, description="Score value")
    score_type: ScoreType = Field(..., description="Type of score")

    @field_validator("label")
    @classmethod
    def validate_label(cls, v: str) -> str:
        """Validate label format."""
        v = v.strip()
        if not v:
            raise ValueError("Label cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_initials(self) -> "ScoreSubmission":
        """Validate that initials are exactly 3 characters."""
        if self.label_type == LabelType.INITIALS:
            if len(self.label) != 3:
                raise ValueError(
                    "Label must be exactly 3 characters when label_type is INITIALS"
                )
            if not self.label.isalnum():
                raise ValueError("Initials must contain only alphanumeric characters")
        return self

    @field_validator("game_id")
    @classmethod
    def validate_game_id(cls, v: str) -> str:
        """Validate game_id format."""
        v = v.strip().lower()
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Game ID must contain only alphanumeric characters, hyphens, and underscores"
            )
        return v


class ScoreRecord(BaseModel):
    """Model for stored score records."""

    game_id: str
    label: str
    label_type: LabelType
    score: float
    score_type: ScoreType
    timestamp: datetime

    model_config = ConfigDict(use_enum_values=True)


class LeaderboardEntry(BaseModel):
    """Model for leaderboard entries in responses."""

    rank: int = Field(..., ge=1, description="Rank position")
    label: str
    label_type: LabelType
    score: float
    timestamp: datetime


class LeaderboardResponse(BaseModel):
    """Model for leaderboard API responses."""

    game_id: str
    score_type: ScoreType
    leaderboard: list[LeaderboardEntry]

    model_config = ConfigDict(use_enum_values=True)
