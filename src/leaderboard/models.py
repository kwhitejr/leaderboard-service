"""Data models for leaderboard service."""

from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, Field, field_validator, ConfigDict


class ScoreType(str, Enum):
    """Supported score types for leaderboards."""
    
    HIGH_SCORE = "high_score"
    FASTEST_TIME = "fastest_time"
    LONGEST_TIME = "longest_time"


class ScoreSubmission(BaseModel):
    """Model for score submission requests."""
    
    game_id: str = Field(..., min_length=1, max_length=50, description="Game identifier")
    initials: str = Field(..., min_length=1, max_length=3, description="Player initials")
    score: float = Field(..., ge=0, description="Score value")
    score_type: ScoreType = Field(..., description="Type of score")
    
    @field_validator("initials")
    @classmethod
    def validate_initials(cls, v: str) -> str:
        """Validate initials are alphanumeric and uppercase."""
        v = v.upper().strip()
        if not v.isalnum():
            raise ValueError("Initials must be alphanumeric")
        return v
    
    @field_validator("game_id")
    @classmethod
    def validate_game_id(cls, v: str) -> str:
        """Validate game_id format."""
        v = v.strip().lower()
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Game ID must contain only alphanumeric characters, hyphens, and underscores")
        return v


class ScoreRecord(BaseModel):
    """Model for stored score records."""
    
    game_id: str
    initials: str
    score: float
    score_type: ScoreType
    timestamp: datetime
    
    model_config = ConfigDict(use_enum_values=True)


class LeaderboardEntry(BaseModel):
    """Model for leaderboard entries in responses."""
    
    rank: int = Field(..., ge=1, description="Rank position")
    initials: str
    score: float
    timestamp: datetime


class LeaderboardResponse(BaseModel):
    """Model for leaderboard API responses."""
    
    game_id: str
    score_type: ScoreType
    leaderboard: List[LeaderboardEntry]
    
    model_config = ConfigDict(use_enum_values=True)