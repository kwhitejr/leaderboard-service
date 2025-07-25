#!/usr/bin/env python3
"""Simple validation script for leaderboard service."""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from leaderboard.models import ScoreSubmission, ScoreRecord, ScoreType, LeaderboardResponse, LeaderboardEntry
    print("✓ Models imported successfully")
    
    # Test ScoreSubmission validation
    submission = ScoreSubmission(
        game_id="snake_classic",
        initials="kmw",  # Should be converted to uppercase
        score=103.0,
        score_type=ScoreType.HIGH_SCORE
    )
    assert submission.initials == "KMW"
    print("✓ ScoreSubmission validation works")
    
    # Test ScoreRecord creation
    record = ScoreRecord(
        game_id="snake_classic",
        initials="KMW",
        score=103.0,
        score_type=ScoreType.HIGH_SCORE,
        timestamp=datetime.utcnow()
    )
    print("✓ ScoreRecord creation works")
    
    # Test LeaderboardResponse
    entries = [
        LeaderboardEntry(
            rank=1,
            initials="KMW",
            score=103.0,
            timestamp=datetime.utcnow()
        )
    ]
    response = LeaderboardResponse(
        game_id="snake_classic",
        score_type=ScoreType.HIGH_SCORE,
        leaderboard=entries
    )
    print("✓ LeaderboardResponse creation works")
    
    print("\n✅ All model validations passed!")
    
except Exception as e:
    print(f"❌ Validation failed: {e}")
    sys.exit(1)